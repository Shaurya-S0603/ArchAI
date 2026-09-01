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

export function exportPdf(brief, layout, projectName) {
  return request("/api/v1/exports/pdf", {
    method: "POST",
    body: JSON.stringify({ brief, layout, project_name: projectName }),
  });
}

export function listProjects() {
  return request("/api/v1/projects");
}

export function loadProject(projectId) {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}`);
}

export function saveProject(projectId, project) {
  const path = projectId
    ? `/api/v1/projects/${encodeURIComponent(projectId)}`
    : "/api/v1/projects";
  return request(path, {
    method: projectId ? "PUT" : "POST",
    body: JSON.stringify(project),
  });
}

export function deleteProject(projectId) {
  return request(`/api/v1/projects/${encodeURIComponent(projectId)}`, { method: "DELETE" });
}
