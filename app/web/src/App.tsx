import { useEffect, useState, useRef } from "react";
import { io } from "socket.io-client";

type Choice = {
  id: number;
  label: string;
  votes: number;
  voters: string[];
};

type Poll = {
  id: number;
  question: string;
  created_at: string;
  expires_at: string;
  choices: Choice[];
  is_expired: boolean;
};

export default function App() {
  const [polls, setPolls] = useState<Poll[]>([]);
  const [selected, setSelected] = useState<Poll | null>(null);
  const [question, setQuestion] = useState("");
  const [choices, setChoices] = useState("Yes,No");
  const [name, setName] = useState<string>(localStorage.getItem("voter") || "");
  const socketRef = useRef<any>(null);

  useEffect(() => {
    fetchPolls();
    const s = io({ path: "/socket.io" });
    socketRef.current = s;
    s.on("connect", () => console.log("socket connected"));
    s.on("poll_update", (data: Poll) => {
      setPolls((p) => p.map((x) => (x.id === data.id ? data : x)));
      if (selected && selected.id === data.id) setSelected(data);
    });
    return () => { s.disconnect(); };
  }, []);

  const fetchPolls = async () => {
    const res = await fetch("/api/polls");
    setPolls(await res.json());
  };

  const createPoll = async () => {
    const res = await fetch("/api/polls", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, choices: choices.split(",") }),
    });
    const data = await res.json();
    await fetchPolls();
    setSelected(data.poll);
  };

  const openPoll = async (id: number) => {
    const res = await fetch(`/api/polls/${id}`);
    const data = await res.json();
    setSelected(data);
    // join socket room
    socketRef.current?.emit("join", { poll_id: id });
  };

  const doVote = async (choiceIndex: number) => {
    if (!selected) return;
    const voter = name || "Anonymous";
    localStorage.setItem("voter", voter);
    const res = await fetch(`/api/polls/${selected.id}/vote`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voter, choice: choiceIndex }),
    });
    if (res.status === 200) {
      const data = await res.json();
      setSelected(data.poll);
      setPolls((p) => p.map((x) => (x.id === data.poll.id ? data.poll : x)));
    } else {
      const err = await res.json();
      alert(err.detail || "error");
    }
  };

  const winnerLabel = (p: Poll) => {
    if (!p.is_expired) return null;
    let max = -1;
    let winner: Choice | null = null;
    for (const c of p.choices) {
      if (c.votes > max) { max = c.votes; winner = c; }
    }
    return winner?.label ?? null;
  };

  return (
    <div style={{ padding: 20, fontFamily: "Arial, sans-serif" }}>
      <h1>QuickPoll</h1>
      <div style={{ display: "flex", gap: 20 }}>
        <div style={{ width: 320 }}>
          <h3>Create Poll</h3>
          <input placeholder="Question" value={question} onChange={e => setQuestion(e.target.value)} style={{ width: "100%" }} />
          <input placeholder="Choices (comma separated)" value={choices} onChange={e => setChoices(e.target.value)} style={{ width: "100%", marginTop: 8 }} />
          <button onClick={createPoll} style={{ marginTop: 8 }}>Create</button>

          <h3 style={{ marginTop: 20 }}>Active Polls</h3>
          <ul>
            {polls.map(p => (
              <li key={p.id} style={{ marginBottom: 8 }}>
                <a href="#" onClick={e => { e.preventDefault(); openPoll(p.id); }}>{p.question}</a>
                <div style={{ fontSize: 12, color: "#666" }}>
                  Expires: {new Date(p.expires_at).toLocaleString()}
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div style={{ flex: 1 }}>
          <h3>Details</h3>
          {!selected ? (
            <div>Select a poll to view details</div>
          ) : (
            <div>
              <h2>{selected.question}</h2>
              <div style={{ marginBottom: 8 }}>
                Expires: {new Date(selected.expires_at).toLocaleString()}
                {selected.is_expired && <strong style={{ marginLeft: 10, color: "green" }}>Expired</strong>}
              </div>
              <div style={{ marginTop: 12 }}>
                <label>Your name: </label>
                <input value={name} onChange={e => setName(e.target.value)} style={{ marginLeft: 8 }} />
              </div>
              <div style={{ marginTop: 12 }}>
                {selected.choices.map((c, idx) => (
                  <div key={c.id} style={{ border: "1px solid #ddd", padding: 8, marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <div><strong>{c.label}</strong> — {c.votes} votes</div>
                      <div>
                        {!selected.is_expired && <button onClick={() => doVote(idx)}>Vote</button>}
                        {selected.is_expired && <span style={{ color: c.voters.includes(localStorage.getItem("voter") || "") ? "green" : "" }}>{c.voters.includes(localStorage.getItem("voter") || "") ? "You voted" : ""}</span>}
                      </div>
                    </div>
                    <div style={{ marginTop: 6, fontSize: 12 }}>
                      Voters: {c.voters.join(", ") || "—"}
                    </div>
                  </div>
                ))}
              </div>
              {selected.is_expired && (
                <div style={{ marginTop: 12, padding: 8, background: "#f6ffed", border: "1px solid #b7eb8f" }}>
                  Winner: <strong>{winnerLabel(selected)}</strong>
                  <div style={{ marginTop: 6 }}>
                    {selected.choices.some(c => c.voters.includes(localStorage.getItem("voter") || "")) && (
                      <div style={{ color: "green" }}>Congrats — you voted and may have won!</div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
