import { useEffect, useState } from "react";

// The backend runs detect -> verify (-> PPE check) in one request, so these
// stages are approximate timings, not live status.
const STAGES = [
  { from: 0, label: "Detecting hazards in the photo" },
  { from: 15, label: "Verifying each hazard against the photo" },
  { from: 32, label: "Final checks" },
];

export default function Progress() {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const start = Date.now();
    const id = setInterval(() => setSeconds(Math.floor((Date.now() - start) / 1000)), 500);
    return () => clearInterval(id);
  }, []);

  const current = STAGES.filter((s) => seconds >= s.from).length - 1;

  return (
    <div className="progress" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p className="progress-title">Analyzing photo… {seconds}s</p>
      <ol className="stages">
        {STAGES.map((s, i) => (
          <li key={s.label} className={i < current ? "done" : i === current ? "active" : ""}>
            {s.label}
          </li>
        ))}
      </ol>
      <p className="muted">This usually takes 30–40 seconds.</p>
    </div>
  );
}
