// Calls the FastAPI backend. In development Vite proxies /api to :8000;
// in production the backend serves this app from the same origin.

async function errorMessage(res) {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* not JSON */
  }
  return `Request failed (HTTP ${res.status})`;
}

export async function getHealth() {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json();
}

// provider: "claude" | "domo"
export async function analyzeImage(file, provider, signal) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`/api/analyze/${provider}`, { method: "POST", body: form, signal });
  if (!res.ok) throw new Error(await errorMessage(res));
  const result = await res.json();
  const h = res.headers;
  const cost = h.get("X-Cost-USD");
  const usage = {
    provider: h.get("X-Provider"),
    model: h.get("X-Model"),
    runId: h.get("X-Run-Id"),
    calls: Number(h.get("X-API-Calls") || 0),
    inputTokens: Number(h.get("X-Input-Tokens") || 0),
    outputTokens: Number(h.get("X-Output-Tokens") || 0),
    costUsd: cost && cost !== "n/a" ? Number(cost) : null, // null = billed via Domo contract
    durationS: Number(h.get("X-Duration-S") || 0),
  };
  return { result, usage };
}
