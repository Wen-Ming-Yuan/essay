// atlas.js
const canvas = document.getElementById("atlasCanvas");
const ctx = canvas.getContext("2d");
const tooltip = document.getElementById("atlasTooltip");
let points = [];

async function init() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight - 60;

  const papers = await chrome.runtime.sendMessage({ action: "searchAll", filters: {} });
  if (!papers || papers.length === 0) return;

  const embedder = new AtlasEmbedder();
  const embeddings = [];
  for (const p of papers.slice(0, 200)) {
    const text = `${p.title} ${p.abstract || ""}`;
    embeddings.push(await embedder.embed(text));
  }

  const projected = embedder.project2D(embeddings);

  // 归一化到画布
  const xs = projected.map(p => p.x), ys = projected.map(p => p.y);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const pad = 40;
  const scaleX = (canvas.width - pad*2) / (maxX - minX || 1);
  const scaleY = (canvas.height - pad*2) / (maxY - minY || 1);

  points = papers.slice(0, 200).map((p, i) => ({
    x: pad + (projected[i].x - minX) * scaleX,
    y: pad + (projected[i].y - minY) * scaleY,
    paper: p
  }));

  draw();
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 绘制阅读路径（最后30天）
  const recent = points.filter(p => (p.paper.addedAt || 0) > Date.now() - 30*86400000)
    .sort((a,b) => (a.paper.addedAt||0) - (b.paper.addedAt||0));
  if (recent.length > 1) {
    ctx.beginPath();
    ctx.strokeStyle = "rgba(37, 99, 235, 0.3)";
    ctx.lineWidth = 2;
    recent.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
    ctx.stroke();
  }

  // 绘制点
  for (const pt of points) {
    const isCCF = pt.paper.source === "ccf";
    const isRecent = (pt.paper.addedAt || 0) > Date.now() - 30*86400000;
    ctx.beginPath();
    ctx.arc(pt.x, pt.y, isRecent ? 6 : 4, 0, Math.PI * 2);
    ctx.fillStyle = isCCF ? "#dc2626" : (isRecent ? "#2563eb" : "#94a3b8");
    ctx.fill();
    if (isRecent) {
      ctx.strokeStyle = "#fff"; ctx.lineWidth = 2; ctx.stroke();
    }
  }
}

// 悬停提示
canvas.addEventListener("mousemove", (e) => {
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  const hit = points.find(p => Math.hypot(p.x - mx, p.y - my) < 10);
  if (hit) {
    tooltip.style.display = "block";
    tooltip.style.left = (e.clientX + 12) + "px";
    tooltip.style.top = (e.clientY + 12) + "px";
    tooltip.innerHTML = `<strong>${hit.paper.title}</strong><br>
      <small>${(hit.paper.authors||[]).slice(0,3).join(", ")}</small><br>
      <small>${hit.paper.source === 'ccf' ? 'CCF-A' : 'arXiv'} · ${hit.paper.year || ''}</small>`;
  } else {
    tooltip.style.display = "none";
  }
});

document.getElementById("btnBack").addEventListener("click", () =>
  chrome.tabs.update({ url: chrome.runtime.getURL("dashboard.html") }));

window.addEventListener("resize", () => {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight - 60;
  draw();
});

init();
