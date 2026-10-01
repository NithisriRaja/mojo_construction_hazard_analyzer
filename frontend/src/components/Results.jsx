import { useMemo, useState } from "react";
import HazardCard from "./HazardCard.jsx";

const SEVERITIES = ["High", "Medium", "Low"];

function downloadJson(result, fileName) {
  const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${(fileName || "hazards").replace(/\.[^.]+$/, "")}_hazards.json`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function Results({ result, usage, fileName }) {
  const [filter, setFilter] = useState(null); // null = all
  const [showRaw, setShowRaw] = useState(false);
  const [copied, setCopied] = useState(false);

  const counts = useMemo(
    () => Object.fromEntries(SEVERITIES.map((s) => [s, result.hazards.filter((h) => h.severity === s).length])),
    [result],
  );
  const shown = filter ? result.hazards.filter((h) => h.severity === filter) : result.hazards;

  async function copy() {
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked; user can use Download instead */
    }
  }

  return (
    <div className="results">
      <h2 className="message">{result.message}</h2>

      <div className="chips" role="group" aria-label="Filter by severity">
        <button className={`chip ${filter === null ? "selected" : ""}`} onClick={() => setFilter(null)}>
          All <span className="count">{result.hazards.length}</span>
        </button>
        {SEVERITIES.map((s) => (
          <button
            key={s}
            className={`chip sev-${s.toLowerCase()} ${filter === s ? "selected" : ""}`}
            onClick={() => setFilter(filter === s ? null : s)}
            disabled={counts[s] === 0}
          >
            {s} <span className="count">{counts[s]}</span>
          </button>
        ))}
      </div>

      {shown.length > 0 ? (
        <ul className="hazard-list">
          {shown.map((h, i) => (
            <HazardCard key={`${h.title}-${i}`} hazard={h} />
          ))}
        </ul>
      ) : (
        <p className="muted">{result.hazards.length === 0 ? "No hazards were found in this photo." : "No hazards at this severity."}</p>
      )}

      <div className="result-actions">
        <button className="btn" onClick={() => downloadJson(result, fileName)}>Download JSON</button>
        <button className="btn" onClick={copy}>{copied ? "Copied" : "Copy JSON"}</button>
        <button className="btn ghost" onClick={() => setShowRaw((v) => !v)}>{showRaw ? "Hide raw JSON" : "View raw JSON"}</button>
      </div>
      {showRaw && <pre className="raw">{JSON.stringify(result, null, 2)}</pre>}

      {usage && (
        <dl className="usage" aria-label="Usage for this analysis">
          <div><dt>Model</dt><dd>{usage.model}</dd></div>
          <div><dt>Cost</dt><dd>{usage.costUsd === null ? "Domo contract" : `$${usage.costUsd.toFixed(4)}`}</dd></div>
          <div><dt>Tokens</dt><dd>{usage.inputTokens.toLocaleString()} in · {usage.outputTokens.toLocaleString()} out</dd></div>
          <div><dt>API calls</dt><dd>{usage.calls}</dd></div>
          <div><dt>Time</dt><dd>{usage.durationS.toFixed(1)}s</dd></div>
        </dl>
      )}
    </div>
  );
}
