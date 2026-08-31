import { analyzeLayout, exportObj, generateLayouts } from "./api.js";
import { MassingViewer } from "./viewer3d.js";

const form = document.querySelector("#brief-form");
const formStatus = document.querySelector("#form-status");
const emptyState = document.querySelector("#empty-state");
const resultsPanel = document.querySelector("#results");
const workspaceActions = document.querySelector("#workspace-actions");
const tabs = document.querySelector("#variation-tabs");
const svg = document.querySelector("#plan-svg");
const viewer = new MassingViewer(document.querySelector("#model-canvas"));
const state = { brief: null, results: [], active: 0, view: "2d", selectedRoom: null, undo: [], redo: [] };

function briefFromForm() {
  const data = new FormData(form);
  return {
    site_width_m: Number(data.get("site_width_m")),
    site_depth_m: Number(data.get("site_depth_m")),
    household_size: Number(data.get("household_size")),
    bedrooms: Number(data.get("bedrooms")),
    bathrooms: Number(data.get("bathrooms")),
    other_rooms: data.getAll("other_rooms"),
    style: data.get("style"),
    currency: data.get("currency"),
    budget: Number(data.get("budget")),
    sustainability: data.has("sustainability"),
    accessibility: data.has("accessibility"),
  };
}

function activeResult() { return state.results[state.active]; }
function cloneRooms() { return structuredClone(activeResult().layout.rooms); }

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button[type=submit]");
  state.brief = briefFromForm();
  button.disabled = true;
  formStatus.classList.remove("is-error");
  formStatus.textContent = "Generating and evaluating five concepts…";
  try {
    const payload = await generateLayouts(state.brief);
    state.brief = payload.brief;
    state.results = payload.results;
    state.active = 0;
    state.undo = [];
    state.redo = [];
    emptyState.hidden = true;
    resultsPanel.hidden = false;
    workspaceActions.hidden = false;
    renderAll();
    formStatus.textContent = `Generated ${state.results.length} concepts successfully.`;
    resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    formStatus.classList.add("is-error");
    formStatus.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});

function renderAll() {
  renderTabs();
  renderConcept();
  updateHistoryButtons();
}

function renderTabs() {
  tabs.replaceChildren(...state.results.map((result, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.role = "tab";
    button.className = index === state.active ? "is-active" : "";
    button.ariaSelected = String(index === state.active);
    button.innerHTML = `<span>Option ${index + 1} · ${Math.round(result.layout.score)} score</span><strong>${result.layout.name}</strong>`;
    button.addEventListener("click", () => {
      state.active = index;
      state.undo = [];
      state.redo = [];
      renderAll();
    });
    return button;
  }));
}

function renderConcept() {
  const result = activeResult();
  document.querySelector("#concept-name").textContent = result.layout.name;
  document.querySelector("#concept-objective").textContent = result.layout.objective;
  const metrics = [
    [result.layout.floor_area.toFixed(0) + " m²", "Floor area"],
    [result.layout.rooms.length, "Rooms"],
    [result.layout.metrics.adjacency_score + "%", "Adjacency"],
  ];
  document.querySelector("#metric-strip").innerHTML = metrics.map(([value, label]) => `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`).join("");
  renderPlan(result.layout);
  viewer.setLayout(result.layout);
  renderCompliance(result.compliance);
  renderCost(result.cost);
}

function svgElement(name, attrs = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function renderPlan(layout) {
  const padding = Math.max(layout.site_width_m, layout.site_depth_m) * .08;
  svg.setAttribute("viewBox", `${-padding} ${-padding} ${layout.site_width_m + 2 * padding} ${layout.site_depth_m + 2 * padding}`);
  svg.replaceChildren();
  svg.append(svgElement("rect", { class: "site-boundary", x: 0, y: 0, width: layout.site_width_m, height: layout.site_depth_m, rx: .2 }));
  const bounds = layout.building_bounds;
  svg.append(svgElement("rect", { class: "building-boundary", x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.depth }));
  layout.rooms.forEach((room) => {
    const group = svgElement("g", { class: `room${state.selectedRoom === room.id ? " is-selected" : ""}`, "data-room-id": room.id, tabindex: "0", role: "button", "aria-label": `${room.label}, ${room.area.toFixed(1)} square metres. Drag to move.` });
    const rect = svgElement("rect", { x: room.x, y: room.y, width: room.width, height: room.depth, fill: room.color, rx: .08 });
    const name = svgElement("text", { x: room.x + room.width / 2, y: room.y + room.depth / 2 - .25 });
    name.textContent = room.label;
    const area = svgElement("text", { class: "room-area", x: room.x + room.width / 2, y: room.y + room.depth / 2 + .42 });
    area.textContent = `${room.area.toFixed(1)} m²`;
    group.append(rect, name, area);
    rect.addEventListener("pointerdown", (event) => startRoomDrag(event, room, group));
    group.addEventListener("keydown", (event) => nudgeRoom(event, room));
    svg.append(group);
  });
  const north = svgElement("text", { class: "north-arrow", x: layout.site_width_m - .8, y: 1.2 });
  north.textContent = "N ↑";
  svg.append(north);
}

function pointInSvg(event) {
  const point = new DOMPoint(event.clientX, event.clientY);
  return point.matrixTransform(svg.getScreenCTM().inverse());
}

function startRoomDrag(event, room, group) {
  event.preventDefault();
  state.selectedRoom = room.id;
  state.undo.push(cloneRooms());
  state.redo = [];
  const start = pointInSvg(event);
  const origin = { x: room.x, y: room.y };
  group.classList.add("is-selected");
  event.target.setPointerCapture(event.pointerId);
  const move = (moveEvent) => {
    const current = pointInSvg(moveEvent);
    const bounds = activeResult().layout.building_bounds;
    room.x = Math.max(bounds.x, Math.min(bounds.x + bounds.width - room.width, origin.x + current.x - start.x));
    room.y = Math.max(bounds.y, Math.min(bounds.y + bounds.depth - room.depth, origin.y + current.y - start.y));
    const rect = group.querySelector("rect");
    const texts = group.querySelectorAll("text");
    rect.setAttribute("x", room.x); rect.setAttribute("y", room.y);
    texts.forEach((text, index) => { text.setAttribute("x", room.x + room.width / 2); text.setAttribute("y", room.y + room.depth / 2 + (index ? .42 : -.25)); });
    viewer.setLayout(activeResult().layout);
  };
  const end = async () => {
    event.target.removeEventListener("pointermove", move);
    event.target.removeEventListener("pointerup", end);
    updateHistoryButtons();
    await reanalyze();
  };
  event.target.addEventListener("pointermove", move);
  event.target.addEventListener("pointerup", end, { once: true });
}

function nudgeRoom(event, room) {
  const deltas = { ArrowLeft: [-.25, 0], ArrowRight: [.25, 0], ArrowUp: [0, -.25], ArrowDown: [0, .25] };
  if (!deltas[event.key]) return;
  event.preventDefault();
  state.undo.push(cloneRooms()); state.redo = [];
  const bounds = activeResult().layout.building_bounds;
  room.x = Math.max(bounds.x, Math.min(bounds.x + bounds.width - room.width, room.x + deltas[event.key][0]));
  room.y = Math.max(bounds.y, Math.min(bounds.y + bounds.depth - room.depth, room.y + deltas[event.key][1]));
  renderConcept(); updateHistoryButtons(); reanalyze();
}

async function reanalyze() {
  formStatus.classList.remove("is-error");
  formStatus.textContent = "Rechecking edited concept…";
  try {
    const analysis = await analyzeLayout(state.brief, activeResult().layout);
    activeResult().compliance = analysis.compliance;
    activeResult().cost = analysis.cost;
    renderCompliance(analysis.compliance);
    renderCost(analysis.cost);
    formStatus.textContent = "Edited concept rechecked.";
  } catch (error) {
    formStatus.classList.add("is-error");
    formStatus.textContent = error.message;
  }
}

function renderCompliance(compliance) {
  const badge = document.querySelector("#compliance-badge");
  badge.className = `badge ${compliance.status}`;
  badge.textContent = `${compliance.status} · ${compliance.score}`;
  document.querySelector("#compliance-summary").innerHTML = [
    [compliance.summary.errors, "Errors"], [compliance.summary.warnings, "Warnings"], [compliance.summary.info, "Notes"],
  ].map(([value, label]) => `<div><strong>${value}</strong><span>${label}</span></div>`).join("");
  const issueList = document.querySelector("#issue-list");
  issueList.innerHTML = compliance.issues.length
    ? compliance.issues.map((issue) => `<li class="${issue.severity}"><strong>${issue.message}</strong>${issue.suggestion}</li>`).join("")
    : "<li><strong>No preliminary issues found.</strong>Continue with professional review and detailed geometry.</li>";
  document.querySelector("#compliance-disclaimer").textContent = compliance.disclaimer;
}

function money(value, currency) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
}

function renderCost(cost) {
  document.querySelector("#cost-total").textContent = money(cost.estimated_total, cost.currency);
  document.querySelector("#cost-rate").textContent = `${money(cost.rate_per_m2, cost.currency)} per m² · ${cost.floor_area_m2.toFixed(1)} m²`;
  const badge = document.querySelector("#budget-badge");
  badge.className = `badge ${cost.within_budget === true ? "pass" : cost.within_budget === false ? "review" : ""}`;
  badge.textContent = cost.within_budget === true ? "Within target" : cost.within_budget === false ? "Above target" : "No target";
  document.querySelector("#cost-breakdown").innerHTML = cost.breakdown.map((item) => `<div class="cost-row"><span>${item.category}</span><strong>${money(item.amount, cost.currency)}</strong><div class="bar"><span style="width:${item.share * 100}%"></span></div></div>`).join("");
}

document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => {
  state.view = button.dataset.view;
  document.querySelectorAll("[data-view]").forEach((candidate) => {
    const active = candidate === button;
    candidate.classList.toggle("is-active", active);
    candidate.setAttribute("aria-pressed", String(active));
  });
  document.querySelector("#plan-wrap").hidden = state.view !== "2d";
  document.querySelector("#model-wrap").hidden = state.view !== "3d";
  if (state.view === "3d") requestAnimationFrame(() => viewer.draw());
}));

function updateHistoryButtons() {
  document.querySelector("#undo-button").disabled = state.undo.length === 0;
  document.querySelector("#redo-button").disabled = state.redo.length === 0;
}

document.querySelector("#undo-button").addEventListener("click", async () => {
  if (!state.undo.length) return;
  state.redo.push(cloneRooms());
  activeResult().layout.rooms = state.undo.pop();
  renderConcept(); updateHistoryButtons(); await reanalyze();
});

document.querySelector("#redo-button").addEventListener("click", async () => {
  if (!state.redo.length) return;
  state.undo.push(cloneRooms());
  activeResult().layout.rooms = state.redo.pop();
  renderConcept(); updateHistoryButtons(); await reanalyze();
});

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

document.querySelectorAll("[data-export]").forEach((button) => button.addEventListener("click", async () => {
  const layout = activeResult().layout;
  const kind = button.dataset.export;
  if (kind === "json") download(new Blob([JSON.stringify({ brief: state.brief, ...activeResult() }, null, 2)], { type: "application/json" }), `${layout.id}.json`);
  if (kind === "svg") {
    const copy = svg.cloneNode(true);
    copy.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    download(new Blob([new XMLSerializer().serializeToString(copy)], { type: "image/svg+xml" }), `${layout.id}.svg`);
  }
  if (kind === "obj") {
    button.disabled = true;
    try { download(await exportObj(layout), `${layout.id}.obj`); }
    catch (error) { formStatus.classList.add("is-error"); formStatus.textContent = error.message; }
    finally { button.disabled = false; }
  }
}));
