from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta
import os

# DB
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import sessionmaker, relationship, declarative_base

# Socket.IO
import socketio

# FastAPI app where routes live
api_app = FastAPI()
api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database URL: use env var DATABASE_URL, default to local sqlite for convenience
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./quickpoll.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PollModel(Base):
    __tablename__ = "polls"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    choices = relationship("ChoiceModel", back_populates="poll", cascade="all, delete-orphan")


class ChoiceModel(Base):
    __tablename__ = "choices"
    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("polls.id"))
    label = Column(String, nullable=False)
    poll = relationship("PollModel", back_populates="choices")
    votes = relationship("VoteModel", back_populates="choice", cascade="all, delete-orphan")


class VoteModel(Base):
    __tablename__ = "votes"
    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey("polls.id"))
    choice_id = Column(Integer, ForeignKey("choices.id"))
    voter = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    choice = relationship("ChoiceModel", back_populates="votes")


def init_db():
    Base.metadata.create_all(bind=engine)


class CreatePoll(BaseModel):
    question: str
    choices: List[str]


class VoteIn(BaseModel):
    voter: str
    choice: int


@api_app.on_event("startup")
def on_startup():
    init_db()


# Socket.IO server (ASGI)
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")


@sio.event
async def connect(sid, environ):
    print("socket connect", sid)


@sio.event
async def disconnect(sid):
    print("socket disconnect", sid)


@sio.event
async def join(sid, data):
    # data expected: {"poll_id": <id>}
    poll_id = data.get("poll_id")
    if poll_id is not None:
        await sio.save_session(sid, {"poll_id": poll_id})
        sio.enter_room(sid, f"poll_{poll_id}")


def poll_to_dict(db, poll: PollModel):
    choices = []
    for c in poll.choices:
        voters = [v.voter for v in c.votes]
        choices.append({"id": c.id, "label": c.label, "votes": len(c.votes), "voters": voters})
    return {
        "id": poll.id,
        "question": poll.question,
        "created_at": poll.created_at.isoformat(),
        "expires_at": poll.expires_at.isoformat(),
        "choices": choices,
        "is_expired": datetime.utcnow() >= poll.expires_at,
    }


@api_app.post("/api/polls")
def create_poll(payload: CreatePoll):
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expires = now + timedelta(days=1)
        poll = PollModel(question=payload.question, created_at=now, expires_at=expires)
        db.add(poll)
        db.flush()  # get id
        for label in payload.choices:
            choice = ChoiceModel(poll_id=poll.id, label=label)
            db.add(choice)
        db.commit()
        db.refresh(poll)
        return {"id": poll.id, "poll": poll_to_dict(db, poll)}
    finally:
        db.close()


@api_app.get("/api/polls")
def list_polls():
    db = SessionLocal()
    try:
        polls = db.query(PollModel).order_by(PollModel.created_at.desc()).all()
        return [poll_to_dict(db, p) for p in polls]
    finally:
        db.close()


@api_app.get("/api/polls/{poll_id}")
def get_poll(poll_id: int):
    db = SessionLocal()
    try:
        poll = db.query(PollModel).filter(PollModel.id == poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="poll not found")
        return poll_to_dict(db, poll)
    finally:
        db.close()


@api_app.post("/api/polls/{poll_id}/vote")
async def vote(poll_id: int, payload: VoteIn, request: Request):
    db = SessionLocal()
    try:
        poll = db.query(PollModel).filter(PollModel.id == poll_id).first()
        if not poll:
            raise HTTPException(status_code=404, detail="poll not found")
        if datetime.utcnow() >= poll.expires_at:
            raise HTTPException(status_code=400, detail="poll expired")
        if payload.choice < 0 or payload.choice >= len(poll.choices):
            raise HTTPException(status_code=400, detail="invalid choice")
        choice = poll.choices[payload.choice]
        vote = VoteModel(poll_id=poll.id, choice_id=choice.id, voter=payload.voter)
        db.add(vote)
        db.commit()

        # emit update to room
        updated = poll_to_dict(db, poll)
        await sio.emit("poll_update", updated, room=f"poll_{poll.id}")
        return {"ok": True, "poll": updated}
    finally:
        db.close()


# Compose ASGI app: socketio wraps the FastAPI app so uvicorn can serve both
asgi_app = socketio.ASGIApp(sio, other_asgi_app=api_app)

# export top-level `app` for uvicorn
app = asgi_app