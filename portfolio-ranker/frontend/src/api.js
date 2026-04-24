const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:5000";

/**
 * POST /analyze — returns parsed `data` on success, throws Error with message on failure.
 */
export async function analyzePortfolio(payload) {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const json = await res.json().catch(() => ({}));

  if (json.status === "error" && json.message) {
    throw new Error(json.message);
  }
  if (json.status === "success" && json.data != null) {
    return json.data;
  }
  if (!res.ok) {
    throw new Error(json.message || res.statusText || "Request failed");
  }
  throw new Error("Unexpected response from server");
}
