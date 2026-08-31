async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.blob();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed with status ${response.status}.`);
  }
  return payload;
}

export function generateLayouts(brief) {
  return request("/api/v1/layouts/generate", { method: "POST", body: JSON.stringify(brief) });
}

export function analyzeLayout(brief, layout) {
  return request("/api/v1/layouts/analyze", {
    method: "POST",
    body: JSON.stringify({ brief, layout }),
  });
}

export async function exportObj(layout) {
  return request("/api/v1/exports/obj", { method: "POST", body: JSON.stringify({ layout }) });
}
