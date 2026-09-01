import {
  analyzeLayout,
  deleteProject,
  exportPdf,
  exportObj,
  generateLayouts,
  listProjects,
  loadProject,
  saveProject,
} from "./api.js";
import { MassingViewer } from "./viewer3d.js";

const form = document.querySelector("#brief-form");
const formStatus = document.querySelector("#form-status");
const emptyState = document.querySelector("#empty-state");
const resultsPanel = document.querySelector("#results");
const workspaceActions = document.querySelector("#workspace-actions");
const tabs = document.querySelector("#variation-tabs");
const svg = document.querySelector("#plan-svg");
const viewer = new MassingViewer(document.querySelector("#model-canvas"));
const projectName = document.querySelector("#project-name");
const projectSelect = document.querySelector("#saved-projects");
const projectStatus = document.querySelector("#project-status");
const saveProjectButton = document.querySelector("#save-project-button");
const loadProjectButton = document.querySelector("#load-project-button");
const deleteProjectButton = document.querySelector("#delete-project-button");
const conceptPanel = document.querySelector("#concept-panel");
const roomEditor = document.querySelector("#room-editor");
const roomEditorTitle = document.querySelector("#room-editor-title");
const roomInputs = {
  x: document.querySelector("#room-x"),
  y: document.querySelector("#room-y"),
  width: document.querySelector("#room-width"),
  depth: document.querySelector("#room-depth"),
};
const state = {
  projectId: null,
  brief: null,
  results: [],
  active: 0,
  view: "2d",
  selectedRoom: null,
  undo: [],
  redo: [],
};
const MIN_ROOM_DIMENSION = 1.8;
const GRID_STEP = 0.25;

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

function fillBriefForm(brief) {
  for (const [key, value] of Object.entries(brief)) {
    const controls = form.elements.namedItem(key);
    if (!controls) continue;
    if (key === "other_rooms") {
      form.querySelectorAll('[name="other_rooms"]').forEach((control) => {
        control.checked = value.includes(control.value);
      });
    } else if (controls instanceof RadioNodeList) {
      controls.value = String(value);
    } else if (controls.type === "checkbox") {
      controls.checked = Boolean(value);
    } else {
      controls.value = String(value);
    }
  }
}

function updateProjectButtons() {
  const hasSelection = Boolean(projectSelect.value);
  saveProjectButton.disabled = state.results.length === 0;
  loadProjectButton.disabled = !hasSelection;
  deleteProjectButton.disabled = !hasSelection;
}

async function refreshProjects(selectedId = state.projectId) {
  const payload = await listProjects();
  projectSelect.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = payload.projects.length ? "Choose a saved project" : "No saved projects";
  projectSelect.append(placeholder);
  payload.projects.forEach((project) => {
    const option = document.createElement("option");
    option.value = project.id;
    option.textContent = `${project.name} · ${project.layout_count} layouts`;
    projectSelect.append(option);
  });
  if (selectedId && payload.projects.some((project) => project.id === selectedId)) {
    projectSelect.value = selectedId;
  }
  updateProjectButtons();
}

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
    state.selectedRoom = null;
    state.undo = [];
    state.redo = [];
    emptyState.hidden = true;
    resultsPanel.hidden = false;
    workspaceActions.hidden = false;
    renderAll();
    updateProjectButtons();
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

function selectConcept(index, focusTab = false) {
  state.active = index;
  state.selectedRoom = null;
  state.undo = [];
  state.redo = [];
  renderAll();
  if (focusTab) {
    tabs.querySelector(`[data-concept-index="${index}"]`)?.focus();
  }
}

function renderTabs() {
  tabs.replaceChildren(...state.results.map((result, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.role = "tab";
    button.id = `concept-tab-${index}`;
    button.dataset.conceptIndex = String(index);
    button.setAttribute("aria-controls", "concept-panel");
    button.className = index === state.active ? "is-active" : "";
    button.ariaSelected = String(index === state.active);
    button.tabIndex = index === state.active ? 0 : -1;
    const score = document.createElement("span");
    score.textContent = `Option ${index + 1} · ${Math.round(result.layout.score)} score`;
    const name = document.createElement("strong");
    name.textContent = result.layout.name;
    button.append(score, name);
    button.addEventListener("click", () => selectConcept(index));
    button.addEventListener("keydown", (event) => {
      const lastIndex = state.results.length - 1;
      const destinations = {
        ArrowLeft: index === 0 ? lastIndex : index - 1,
        ArrowRight: index === lastIndex ? 0 : index + 1,
        Home: 0,
        End: lastIndex,
      };
      if (!(event.key in destinations)) return;
      event.preventDefault();
      selectConcept(destinations[event.key], true);
    });
    return button;
  }));
  conceptPanel.setAttribute("aria-labelledby", `concept-tab-${state.active}`);
}

function renderConcept() {
  const result = activeResult();
  document.querySelector("#concept-name").textContent = result.layout.name;
  document.querySelector("#concept-objective").textContent = result.layout.objective;
  const metrics = [
    [result.layout.floor_area.toFixed(0) + " m²", "Floor area"],
    [result.layout.rooms.length, "Rooms"],
    [result.layout.metrics.adjacency_score + "%", "Adjacency"],
    [
      `${result.layout.topology?.summary?.doors || 0}/${result.layout.topology?.summary?.windows || 0}`,
      "Doors/windows",
    ],
    [
      `${result.layout.zones?.summary?.furniture_zones || 0}/${result.layout.zones?.summary?.clearance_zones || 0}`,
      "Furniture/clearance",
    ],
  ];
  document.querySelector("#metric-strip").innerHTML = metrics.map(([value, label]) => `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`).join("");
  renderPlan(result.layout);
  viewer.setLayout(result.layout);
  renderCompliance(result.compliance);
  renderCost(result.cost);
  renderRoomEditor(result.layout.rooms.find((room) => room.id === state.selectedRoom));
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
    const group = svgElement("g", { class: `room${state.selectedRoom === room.id ? " is-selected" : ""}`, "data-room-id": room.id, tabindex: "0", role: "button", "aria-label": `${room.label}, ${room.area.toFixed(1)} square metres. Select for exact editing or use arrow keys to move.` });
    const rect = svgElement("rect", { x: room.x, y: room.y, width: room.width, height: room.depth, fill: room.color, rx: .08 });
    const name = svgElement("text", { x: room.x + room.width / 2, y: room.y + room.depth / 2 - .25 });
    name.textContent = room.label;
    const area = svgElement("text", { class: "room-area", x: room.x + room.width / 2, y: room.y + room.depth / 2 + .42 });
    area.textContent = `${room.area.toFixed(1)} m²`;
    group.append(rect, name, area);
    rect.addEventListener("pointerdown", (event) => startRoomDrag(event, room, group));
    group.addEventListener("click", () => selectRoom(room));
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectRoom(room, true);
        return;
      }
      nudgeRoom(event, room);
    });
    ["nw", "ne", "se", "sw"].forEach((corner) => {
      const handle = resizeHandle(room, corner);
      handle.addEventListener("pointerdown", (event) => startRoomResize(event, room, corner));
      group.append(handle);
    });
    svg.append(group);
  });
  renderZones(layout.zones);
  renderTopology(layout.topology);
  const north = svgElement("text", { class: "north-arrow", x: layout.site_width_m - .8, y: 1.2 });
  north.textContent = "N ↑";
  svg.append(north);
}

function renderZones(zones) {
  if (!zones) return;
  const layer = svgElement("g", { class: "zoning-layer", "aria-hidden": "true" });
  zones.furniture.forEach((zone) => {
    layer.append(svgElement("rect", {
      class: `furniture-zone furniture-zone--${zone.kind}`,
      x: zone.x,
      y: zone.y,
      width: zone.width,
      height: zone.depth,
      rx: 0.08,
    }));
  });
  zones.clearances.forEach((zone) => {
    if (zone.shape === "circle") {
      layer.append(svgElement("circle", {
        class: "clearance-zone clearance-zone--circle",
        cx: zone.cx,
        cy: zone.cy,
        r: zone.radius,
      }));
    } else {
      layer.append(svgElement("rect", {
        class: "clearance-zone",
        x: zone.x,
        y: zone.y,
        width: zone.width,
        height: zone.depth,
        rx: 0.06,
      }));
    }
  });
  svg.append(layer);
}

function renderTopology(topology) {
  if (!topology) return;
  const layer = svgElement("g", { class: "topology-layer", "aria-hidden": "true" });
  topology.walls.forEach((wall) => {
    layer.append(svgElement("line", {
      class: `wall wall--${wall.kind}`,
      x1: wall.x1,
      y1: wall.y1,
      x2: wall.x2,
      y2: wall.y2,
    }));
  });
  topology.openings.forEach((opening) => {
    layer.append(svgElement("line", {
      class: "opening-cut",
      x1: opening.x1,
      y1: opening.y1,
      x2: opening.x2,
      y2: opening.y2,
    }));
    layer.append(svgElement("line", {
      class: `opening opening--${opening.kind}`,
      x1: opening.x1,
      y1: opening.y1,
      x2: opening.x2,
      y2: opening.y2,
    }));
  });
  svg.append(layer);
}

function resizeHandle(room, corner) {
  const east = corner.includes("e");
  const south = corner.includes("s");
  return svgElement("rect", {
    class: `resize-handle resize-handle--${corner}`,
    x: east ? room.x + room.width - 0.18 : room.x - 0.18,
    y: south ? room.y + room.depth - 0.18 : room.y - 0.18,
    width: 0.36,
    height: 0.36,
    rx: 0.06,
    "data-corner": corner,
    "aria-hidden": "true",
  });
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

function snap(value) {
  return Math.round(value / GRID_STEP) * GRID_STEP;
}

function startRoomResize(event, room, corner) {
  event.preventDefault();
  event.stopPropagation();
  state.selectedRoom = room.id;
  state.undo.push(cloneRooms());
  state.redo = [];
  const bounds = activeResult().layout.building_bounds;
  const origin = { x: room.x, y: room.y, right: room.x + room.width, bottom: room.y + room.depth };
  const west = corner.includes("w");
  const north = corner.includes("n");
  const maxWidth = west ? origin.right - bounds.x : bounds.x + bounds.width - origin.x;
  const maxDepth = north ? origin.bottom - bounds.y : bounds.y + bounds.depth - origin.y;
  const group = event.target.closest(".room");
  group.classList.add("is-selected");
  event.target.setPointerCapture(event.pointerId);

  const move = (moveEvent) => {
    const point = pointInSvg(moveEvent);
    let width = snap(west ? origin.right - point.x : point.x - origin.x);
    let depth = snap(north ? origin.bottom - point.y : point.y - origin.y);
    width = Math.max(MIN_ROOM_DIMENSION, Math.min(maxWidth, width));
    depth = Math.max(MIN_ROOM_DIMENSION, Math.min(maxDepth, depth));

    const minimumArea = Number(room.minimum_area || 4);
    if (width * depth < minimumArea) {
      width = Math.min(maxWidth, Math.max(width, minimumArea / depth));
    }
    if (width * depth < minimumArea) {
      depth = Math.min(maxDepth, Math.max(depth, minimumArea / width));
    }

    room.width = Math.round(width * 1000) / 1000;
    room.depth = Math.round(depth * 1000) / 1000;
    room.x = west ? Math.round((origin.right - room.width) * 1000) / 1000 : origin.x;
    room.y = north ? Math.round((origin.bottom - room.depth) * 1000) / 1000 : origin.y;
    const roomRect = group.querySelector("rect:not(.resize-handle)");
    roomRect.setAttribute("x", room.x);
    roomRect.setAttribute("y", room.y);
    roomRect.setAttribute("width", room.width);
    roomRect.setAttribute("height", room.depth);
    const texts = group.querySelectorAll("text");
    texts.forEach((text, index) => {
      text.setAttribute("x", room.x + room.width / 2);
      text.setAttribute("y", room.y + room.depth / 2 + (index ? 0.42 : -0.25));
    });
    texts[1].textContent = `${(room.width * room.depth).toFixed(1)} m²`;
    group.querySelectorAll(".resize-handle").forEach((handle) => {
      const handleCorner = handle.dataset.corner;
      handle.setAttribute("x", handleCorner.includes("e") ? room.x + room.width - 0.18 : room.x - 0.18);
      handle.setAttribute("y", handleCorner.includes("s") ? room.y + room.depth - 0.18 : room.y - 0.18);
    });
    viewer.setLayout(activeResult().layout);
  };

  const end = async () => {
    event.target.removeEventListener("pointermove", move);
    event.target.removeEventListener("pointerup", end);
    renderConcept();
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
  state.selectedRoom = room.id;
  state.undo.push(cloneRooms()); state.redo = [];
  const bounds = activeResult().layout.building_bounds;
  room.x = Math.max(bounds.x, Math.min(bounds.x + bounds.width - room.width, room.x + deltas[event.key][0]));
  room.y = Math.max(bounds.y, Math.min(bounds.y + bounds.depth - room.depth, room.y + deltas[event.key][1]));
  renderConcept(); updateHistoryButtons(); reanalyze();
}

function selectRoom(room, focusEditor = false) {
  state.selectedRoom = room.id;
  renderConcept();
  if (focusEditor) roomInputs.x.focus();
}

function renderRoomEditor(room) {
  roomEditor.hidden = !room;
  if (!room) return;
  const bounds = activeResult().layout.building_bounds;
  roomEditorTitle.textContent = `Selected room: ${room.label}`;
  roomInputs.x.value = room.x.toFixed(2);
  roomInputs.y.value = room.y.toFixed(2);
  roomInputs.width.value = room.width.toFixed(2);
  roomInputs.depth.value = room.depth.toFixed(2);
  roomInputs.x.min = bounds.x;
  roomInputs.y.min = bounds.y;
  roomInputs.x.max = bounds.x + bounds.width - room.width;
  roomInputs.y.max = bounds.y + bounds.depth - room.depth;
  roomInputs.width.max = bounds.x + bounds.width - room.x;
  roomInputs.depth.max = bounds.y + bounds.depth - room.y;
}

document.querySelector("#apply-room-edit").addEventListener("click", async () => {
  const room = activeResult().layout.rooms.find((candidate) => candidate.id === state.selectedRoom);
  if (!room) return;
  const values = Object.fromEntries(
    Object.entries(roomInputs).map(([key, input]) => [key, Number(input.value)]),
  );
  const bounds = activeResult().layout.building_bounds;
  const insideBounds = values.x >= bounds.x
    && values.y >= bounds.y
    && values.x + values.width <= bounds.x + bounds.width + 0.001
    && values.y + values.depth <= bounds.y + bounds.depth + 0.001;
  if (!Object.values(values).every(Number.isFinite)
      || values.width < MIN_ROOM_DIMENSION
      || values.depth < MIN_ROOM_DIMENSION
      || values.width * values.depth < Number(room.minimum_area || 4)
      || !insideBounds) {
    formStatus.classList.add("is-error");
    formStatus.textContent = "Room edits must stay inside the footprint and meet minimum dimensions and area.";
    roomInputs.x.focus();
    return;
  }
  state.undo.push(cloneRooms());
  state.redo = [];
  Object.assign(room, values);
  renderConcept();
  updateHistoryButtons();
  await reanalyze();
});

async function reanalyze() {
  formStatus.classList.remove("is-error");
  formStatus.textContent = "Rechecking edited concept…";
  try {
    const analysis = await analyzeLayout(state.brief, activeResult().layout);
    activeResult().layout = analysis.layout;
    activeResult().compliance = analysis.compliance;
    activeResult().cost = analysis.cost;
    renderConcept();
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
  const summaries = [
    [compliance.summary.errors, "Errors"], [compliance.summary.warnings, "Warnings"], [compliance.summary.info, "Notes"],
  ].map(([value, label]) => {
    const item = document.createElement("div");
    const count = document.createElement("strong");
    count.textContent = value;
    const caption = document.createElement("span");
    caption.textContent = label;
    item.append(count, caption);
    return item;
  });
  document.querySelector("#compliance-summary").replaceChildren(...summaries);
  const issueList = document.querySelector("#issue-list");
  const issues = compliance.issues.length ? compliance.issues : [{
    severity: "info",
    message: "No preliminary issues found.",
    suggestion: "Continue with professional review and detailed geometry.",
  }];
  issueList.replaceChildren(...issues.map((issue) => {
    const item = document.createElement("li");
    item.className = ["error", "warning", "info"].includes(issue.severity) ? issue.severity : "info";
    const message = document.createElement("strong");
    message.textContent = issue.message;
    item.append(message, document.createTextNode(issue.suggestion));
    return item;
  }));
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

saveProjectButton.addEventListener("click", async () => {
  projectStatus.classList.remove("is-error");
  const name = projectName.value.trim();
  if (!name) {
    projectStatus.classList.add("is-error");
    projectStatus.textContent = "Enter a project name before saving.";
    projectName.focus();
    return;
  }
  saveProjectButton.disabled = true;
  projectStatus.textContent = state.projectId ? "Updating project…" : "Saving project…";
  try {
    const payload = await saveProject(state.projectId, {
      name,
      brief: state.brief,
      results: state.results,
      active_index: state.active,
    });
    const saved = payload.project;
    state.projectId = saved.id;
    state.brief = saved.brief;
    state.results = saved.results;
    state.active = saved.active_index;
    projectName.value = saved.name;
    renderAll();
    await refreshProjects(saved.id);
    projectStatus.textContent = `Saved “${saved.name}” locally.`;
  } catch (error) {
    projectStatus.classList.add("is-error");
    projectStatus.textContent = error.message;
  } finally {
    updateProjectButtons();
  }
});

loadProjectButton.addEventListener("click", async () => {
  if (!projectSelect.value) return;
  projectStatus.classList.remove("is-error");
  projectStatus.textContent = "Loading project…";
  try {
    const payload = await loadProject(projectSelect.value);
    const project = payload.project;
    state.projectId = project.id;
    state.brief = project.brief;
    state.results = project.results;
    state.active = project.active_index;
    state.selectedRoom = null;
    state.undo = [];
    state.redo = [];
    projectName.value = project.name;
    fillBriefForm(project.brief);
    emptyState.hidden = true;
    resultsPanel.hidden = false;
    workspaceActions.hidden = false;
    renderAll();
    updateProjectButtons();
    projectStatus.textContent = `Loaded “${project.name}”.`;
    resultsPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    projectStatus.classList.add("is-error");
    projectStatus.textContent = error.message;
  }
});

deleteProjectButton.addEventListener("click", async () => {
  const projectId = projectSelect.value;
  const selectedName = projectSelect.selectedOptions[0]?.textContent || "this project";
  if (!projectId || !window.confirm(`Delete ${selectedName}? This cannot be undone.`)) return;
  projectStatus.classList.remove("is-error");
  projectStatus.textContent = "Deleting project…";
  try {
    await deleteProject(projectId);
    if (state.projectId === projectId) state.projectId = null;
    await refreshProjects();
    projectStatus.textContent = "Project deleted. The open layout remains available until you leave this page.";
  } catch (error) {
    projectStatus.classList.add("is-error");
    projectStatus.textContent = error.message;
  }
});

projectSelect.addEventListener("change", updateProjectButtons);

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

function exportableSvg() {
  const copy = svg.cloneNode(true);
  copy.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  copy.querySelectorAll(".resize-handle").forEach((handle) => handle.remove());
  copy.querySelectorAll(".is-selected").forEach((room) => room.classList.remove("is-selected"));
  return copy;
}

async function planPng() {
  const copy = exportableSvg();
  const viewBox = svg.viewBox.baseVal;
  const outputWidth = 1800;
  const outputHeight = Math.round(outputWidth * viewBox.height / viewBox.width);
  copy.setAttribute("width", outputWidth);
  copy.setAttribute("height", outputHeight);
  const source = new Blob([new XMLSerializer().serializeToString(copy)], { type: "image/svg+xml" });
  const url = URL.createObjectURL(source);
  try {
    const image = await new Promise((resolve, reject) => {
      const candidate = new Image();
      candidate.onload = () => resolve(candidate);
      candidate.onerror = () => reject(new Error("The plan could not be rendered as PNG."));
      candidate.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = outputWidth;
    canvas.height = outputHeight;
    const context = canvas.getContext("2d");
    context.fillStyle = "#fffdf8";
    context.fillRect(0, 0, outputWidth, outputHeight);
    context.drawImage(image, 0, 0, outputWidth, outputHeight);
    return await new Promise((resolve, reject) => canvas.toBlob(
      (blob) => blob ? resolve(blob) : reject(new Error("PNG encoding failed.")),
      "image/png",
    ));
  } finally {
    URL.revokeObjectURL(url);
  }
}

document.querySelectorAll("[data-export]").forEach((button) => button.addEventListener("click", async () => {
  const layout = activeResult().layout;
  const kind = button.dataset.export;
  if (kind === "json") download(new Blob([JSON.stringify({ brief: state.brief, ...activeResult() }, null, 2)], { type: "application/json" }), `${layout.id}.json`);
  if (kind === "svg") {
    const copy = exportableSvg();
    download(new Blob([new XMLSerializer().serializeToString(copy)], { type: "image/svg+xml" }), `${layout.id}.svg`);
  }
  if (kind === "png") {
    button.disabled = true;
    try { download(await planPng(), `${layout.id}.png`); }
    catch (error) { formStatus.classList.add("is-error"); formStatus.textContent = error.message; }
    finally { button.disabled = false; }
  }
  if (kind === "pdf") {
    button.disabled = true;
    try { download(await exportPdf(state.brief, layout, projectName.value.trim()), `${layout.id}-concept-plan.pdf`); }
    catch (error) { formStatus.classList.add("is-error"); formStatus.textContent = error.message; }
    finally { button.disabled = false; }
  }
  if (kind === "obj") {
    button.disabled = true;
    try { download(await exportObj(layout), `${layout.id}.obj`); }
    catch (error) { formStatus.classList.add("is-error"); formStatus.textContent = error.message; }
    finally { button.disabled = false; }
  }
  if (kind === "print") window.print();
}));

refreshProjects().catch((error) => {
  projectStatus.classList.add("is-error");
  projectStatus.textContent = `Saved projects are unavailable: ${error.message}`;
});
