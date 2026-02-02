import { useState } from "react";

export default function App() {
  const [question, setQuestion] = useState("");
  const [choices, setChoices] = useState("Yes,No");
  const [poll, setPoll] = useState(null);

  const createPoll = async () => {
    const res = await fetch("/api/polls", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({
        question,
        choices: choices.split(",")
      })
    });
    setPoll(await res.json());
  };

  return (
    <div style={{ padding: 40 }}>
      <h1>QuickPoll</h1>

      {!poll ? (
        <div>
          <input placeholder="Question" value={question} onChange={e=>setQuestion(e.target.value)} />
          <input placeholder="Choices" value={choices} onChange={e=>setChoices(e.target.value)} />
          <button onClick={createPoll}>Create</button>
        </div>
      ) :
      <pre>{JSON.stringify(poll, null, 2)}</pre>}
    </div>
  );
}
