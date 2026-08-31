const palette = { background: "#eef0ea", line: "rgba(33, 56, 44, .34)", wall: "rgba(250, 247, 236, .70)" };

export class MassingViewer {
  constructor(canvas) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.layout = null;
    this.angle = -0.65;
    this.zoom = 1;
    this.dragging = false;
    this.lastX = 0;
    this.resizeObserver = new ResizeObserver(() => this.draw());
    this.resizeObserver.observe(canvas);
    canvas.addEventListener("pointerdown", (event) => this.startDrag(event));
    canvas.addEventListener("pointermove", (event) => this.drag(event));
    canvas.addEventListener("pointerup", () => { this.dragging = false; });
    canvas.addEventListener("pointercancel", () => { this.dragging = false; });
    canvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      this.zoom = Math.max(.55, Math.min(2.1, this.zoom * (event.deltaY > 0 ? .92 : 1.08)));
      this.draw();
    }, { passive: false });
  }

  setLayout(layout) { this.layout = layout; this.draw(); }

  startDrag(event) {
    this.dragging = true;
    this.lastX = event.clientX;
    this.canvas.setPointerCapture(event.pointerId);
  }

  drag(event) {
    if (!this.dragging) return;
    this.angle += (event.clientX - this.lastX) * .009;
    this.lastX = event.clientX;
    this.draw();
  }

  sizeCanvas() {
    const rect = this.canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    const width = Math.max(1, Math.round(rect.width * ratio));
    const height = Math.max(1, Math.round(rect.height * ratio));
    if (this.canvas.width !== width || this.canvas.height !== height) {
      this.canvas.width = width;
      this.canvas.height = height;
    }
    this.context.setTransform(ratio, 0, 0, ratio, 0, 0);
    return rect;
  }

  project(x, y, z, rect) {
    const cx = this.layout.site_width_m / 2;
    const cy = this.layout.site_depth_m / 2;
    const dx = x - cx;
    const dy = y - cy;
    const rotatedX = dx * Math.cos(this.angle) - dy * Math.sin(this.angle);
    const rotatedY = dx * Math.sin(this.angle) + dy * Math.cos(this.angle);
    const scale = Math.min(rect.width / this.layout.site_width_m, rect.height / this.layout.site_depth_m) * .65 * this.zoom;
    return [rect.width / 2 + rotatedX * scale, rect.height * .67 + rotatedY * scale * .44 - z * scale];
  }

  polygon(points, fill, stroke = palette.line) {
    const ctx = this.context;
    ctx.beginPath();
    ctx.moveTo(...points[0]);
    points.slice(1).forEach((point) => ctx.lineTo(...point));
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  drawRoom(room, rect) {
    const height = 2.8;
    const p = (x, y, z) => this.project(x, y, z, rect);
    const floor = [p(room.x, room.y, .05), p(room.x + room.width, room.y, .05), p(room.x + room.width, room.y + room.depth, .05), p(room.x, room.y + room.depth, .05)];
    this.polygon(floor, room.color);
    const edges = [
      [[room.x, room.y], [room.x + room.width, room.y]],
      [[room.x + room.width, room.y], [room.x + room.width, room.y + room.depth]],
      [[room.x + room.width, room.y + room.depth], [room.x, room.y + room.depth]],
      [[room.x, room.y + room.depth], [room.x, room.y]],
    ];
    edges.forEach(([a, b]) => this.polygon([p(a[0], a[1], .05), p(b[0], b[1], .05), p(b[0], b[1], height), p(a[0], a[1], height)], palette.wall));
    const label = p(room.x + room.width / 2, room.y + room.depth / 2, .12);
    this.context.fillStyle = "#17362a";
    this.context.font = "600 11px system-ui";
    this.context.textAlign = "center";
    this.context.fillText(room.label, label[0], label[1]);
  }

  draw() {
    const rect = this.sizeCanvas();
    const ctx = this.context;
    ctx.clearRect(0, 0, rect.width, rect.height);
    ctx.fillStyle = palette.background;
    ctx.fillRect(0, 0, rect.width, rect.height);
    if (!this.layout) return;
    const sorted = [...this.layout.rooms].sort((a, b) => {
      const depthA = (a.x + a.width / 2) * Math.sin(this.angle) + (a.y + a.depth / 2) * Math.cos(this.angle);
      const depthB = (b.x + b.width / 2) * Math.sin(this.angle) + (b.y + b.depth / 2) * Math.cos(this.angle);
      return depthA - depthB;
    });
    sorted.forEach((room) => this.drawRoom(room, rect));
  }
}
