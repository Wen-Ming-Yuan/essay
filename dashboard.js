// dashboard.js
let selectedPapers = new Set();

document.addEventListener("DOMContentLoaded", async () => {
  await populateFilters();
  await renderPapers();
  await renderTagCloud();
  bindEvents();
});

async function populateFilters() {
  const papers = await chrome.runtime.sendMessage({ action: "searchAll", filters: {} });
  if (!papers) return;
  const years = [...new Set(papers.map(p => p.year || (p.published||"").slice(0,4)).filter(Boolean))].sort((a,b)=>b-a);
  const yearSel = document.getElementById("yearFilter");
  years.forEach(y => { const o = document.createElement("option"); o.value=y; o.textContent=y; yearSel.appendChild(o); });
}

async function renderTagCloud() {
  const papers = await chrome.runtime.sendMessage({ action: "searchAll", filters: {} });
  const freq = {};
  (papers||[]).forEach(p => (p.tags||[]).forEach(t => freq[t]=(freq[t]||0)+1));
  const cloud = document.getElementById("tagCloud");
  cloud.innerHTML = "";
  Object.entries(freq).sort((a,b)=>b[1]-a[1]).slice(0,30).forEach(([tag,count])=>{
    const span = document.createElement("span");
    span.className = "tag-chip";
    span.textContent = `${tag} (${count})`;
    span.onclick = () => { document.getElementById("searchInput").value = tag; renderPapers(); };
    cloud.appendChild(span);
  });
}

async function renderPapers() {
  const filters = {
    keyword: document.getElementById("searchInput").value,
    source: document.getElementById("sourceFilter").value,
    category: document.getElementById("categoryFilter").value,
    year: document.getElementById("yearFilter").value
  };
  const papers = await chrome.runtime.sendMessage({ action: "searchAll", filters });
  const grid = document.getElementById("paperGrid");
  document.getElementById("resultsCount").textContent = `找到 ${(papers||[]).length} 篇论文`;
  grid.innerHTML = "";
  if (!papers || papers.length === 0) { grid.innerHTML = '<p class="empty">没有匹配的论文</p>'; return; }

  papers.slice(0, 300).forEach(p => {
    const card = document.createElement("div");
    card.className = "paper-card";
    const key = p.arxivId || p.dblpKey || p.title;
    card.innerHTML = `
      <label class="card-check"><input type="checkbox" data-key="${key}"></label>
      <h3 class="card-title"><a href="${p.url || p.pdfUrl || '#'}" target="_blank">${p.title}</a></h3>
      <p class="card-authors">${(p.authors||[]).slice(0,4).join(", ")}${(p.authors||[]).length>4?' 等':''}</p>
      ${p.tldr ? `<div class="card-tldr">
        <span class="tldr-label">背景</span><span>${p.tldr.background||''}</span>
        <span class="tldr-label">方法</span><span>${p.tldr.method||''}</span>
        <span class="tldr-label">结果</span><span>${p.tldr.keyResult||''}</span>
      </div>` : ""}
      <div class="card-meta">
        <span class="tag tag-src ${p.source}">${p.source==='ccf'?'CCF-A':'arXiv'}</span>
        <span class="tag tag-year">${p.year || (p.published||'').slice(0,4)}</span>
        ${p.ccfArea ? `<span class="tag tag-area">${p.ccfArea}</span>` : ""}
        ${(p.tags||[]).slice(0,3).map(t=>`<span class="tag tag-mini">${t}</span>`).join('')}
      </div>`;
    grid.appendChild(card);
  });

  // 绑定复选框
  grid.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener("change", (e) => {
      if (e.target.checked) selectedPapers.add(e.target.dataset.key);
      else selectedPapers.delete(e.target.dataset.key);
    });
  });
}

function bindEvents() {
  document.getElementById("searchInput").addEventListener("input", debounce(renderPapers, 300));
  ["sourceFilter","categoryFilter","yearFilter"].forEach(id =>
    document.getElementById(id).addEventListener("change", renderPapers));

  document.getElementById("btnExport").addEventListener("click", async () => {
    const papers = await chrome.runtime.sendMessage({ action: "searchAll", filters: {} });
    const blob = new Blob([JSON.stringify(papers, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url;
    a.download = `paperprism-${new Date().toISOString().slice(0,10)}.json`;
    a.click(); URL.revokeObjectURL(url);
  });

  document.getElementById("btnAtlas").addEventListener("click", () =>
    chrome.tabs.create({ url: chrome.runtime.getURL("atlas.html") }));
  document.getElementById("btnOptions").addEventListener("click", () =>
    chrome.runtime.openOptionsPage());
}

function debounce(fn, delay) {
  let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), delay); };
}
