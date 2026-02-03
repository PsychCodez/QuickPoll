from fastapi import FastAPI
from typing import List
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

polls = {}  # in-memory; later you can add SQLite

class Poll(BaseModel):
    question: str
    choices: List[str]

@app.post("/polls")
def create_poll(poll: Poll):
    poll_id = len(polls) + 1
    polls[poll_id] = {"question": poll.question, "choices": poll.choices, "votes": [0]*len(poll.choices)}
    return {"id": poll_id, "poll": polls[poll_id]}

@app.post("/polls/{poll_id}/vote")
def vote(poll_id: int, choice: int):
    polls[poll_id]["votes"][choice] += 1
    return {"ok": True}

@app.get("/polls/{poll_id}")
def get_poll(poll_id: int):
    return polls[poll_id]