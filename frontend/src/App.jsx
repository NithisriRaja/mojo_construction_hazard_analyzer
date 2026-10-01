import { useEffect, useRef, useState } from "react";
import { analyzeImage, getHealth } from "./api.js";
import Uploader from "./components/Uploader.jsx";
import Progress from "./components/Progress.jsx";
import Results from "./components/Results.jsx";

const PROVIDERS = [
  { id: "claude", label: "Claude" },
  { id: "domo", label: "Domo" },
];

export default function App() {
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(false);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | analyzing | done | error
  const [error, setError] = useState("");
  const [data, setData] = useState(null); // { result, usage }
  const [provider, setProvider] = useState("claude");
  const abortRef = useRef(null);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealthError(true));
  }, []);

  useEffect(() => {
    if (!file) return undefined;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function selectFile(f) {
    abortRef.current?.abort();
    setFile(f);
    setData(null);
    setError("");
    setStatus("idle");
  }

  async function runAnalysis() {
    if (!file) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("analyzing");
    setError("");
    setData(null);
    try {
      setData(await analyzeImage(file, provider, controller.signal));
      setStatus("done");
    } catch (e) {
      if (e.name === "AbortError") return;
      setError(e.message || "Something went wrong.");
      setStatus("error");
    }
  }

  function reset() {
    abortRef.current?.abort();
    setFile(null);
    setPreviewUrl(null);
    setData(null);
    setError("");
    setStatus("idle");
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">⚠</span>
          <div>
            <h1>Site Hazard Analyzer</h1>
            <p className="subtitle">Upload a construction site photo to identify visible safety hazards.</p>
          </div>
        </div>
        <div className={`service ${healthError ? "service-down" : ""}`}>
          <span className="dot" aria-hidden="true" />
          {healthError ? "Backend unavailable" : health ? "Backend connected" : "Connecting…"}
        </div>
      </header>

      <main className="layout">
        <section className="panel">
          <div className="providers" role="radiogroup" aria-label="Model provider">
            {PROVIDERS.map((p) => {
              const info = health?.providers?.[p.id];
              const unavailable = health && !info?.available;
              return (
                <button
                  key={p.id}
                  role="radio"
                  aria-checked={provider === p.id}
                  className={`provider ${provider === p.id ? "selected" : ""}`}
                  onClick={() => setProvider(p.id)}
                  disabled={status === "analyzing" || unavailable}
                  title={unavailable ? `${p.label} is not configured on the server` : info?.model}
                >
                  <span className="provider-name">{p.label}</span>
                  <span className="provider-model">{unavailable ? "not configured" : info?.model || "…"}</span>
                </button>
              );
            })}
          </div>
          <Uploader file={file} previewUrl={previewUrl} disabled={status === "analyzing"} onSelect={selectFile} onError={setError} />
          <div className="actions">
            <button className="btn primary" onClick={runAnalysis} disabled={!file || status === "analyzing" || healthError}>
              {status === "analyzing" ? "Analyzing…" : "Analyze photo"}
            </button>
            {file && (
              <button className="btn" onClick={reset} disabled={status === "analyzing"}>
                Clear
              </button>
            )}
          </div>
          {error && <div className="alert" role="alert">{error}</div>}
        </section>

        <section className="panel results-panel">
          {status === "analyzing" && <Progress />}
          {status === "done" && data && <Results result={data.result} usage={data.usage} fileName={file?.name} />}
          {(status === "idle" || status === "error") && (
            <div className="empty">
              <p className="empty-title">No results yet</p>
              <p>Choose a photo and click <strong>Analyze photo</strong>. Each analysis takes about 30–40 seconds.</p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
