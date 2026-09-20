// popup.js
document.addEventListener("DOMContentLoaded", async () => {
  await loadStats();
  await loadRecent();
  await checkAgent();
  bindEvents();
});

async function loadStats() {
  const stats = await chrome.runtime.sendMessage({ action: "getStats" });
  if (stats) {
    document.getElementById("statArxiv").textContent = stats.arxivTotal || 0;
    document.getElementById("statCCF").textContent = stats.ccfTotal || 0;
    document.getElementById("statTopics").textContent = stats.topicsTotal || 0;
  }
}

async function loadRecent() {
  const papers = await chrome.runtime.sendMessage({ action: "searchAll", filters: {} });
  const list = document.getElementById("recentList");
  list.innerHTML = "";
  if (!papers || papers.length === 0) {
    list.innerHTML = '<li class="empty">暂无数据</li>';
    return;
  }
  const recent = papers.sort((a, b) => (b.addedAt || 0) - (a.addedAt || 0)).slice(0, 6);
  for (const p of recent) {
    const li = document.createElement("li");
    li.className = "paper-item";
    li.innerHTML = `
      <a href="${p.url || p.pdfUrl || '#'}" target="_blank" class="paper-title">${p.title}</a>
      <div class="paper-meta">
        <span class="src-tag ${p.source}">${p.source === 'ccf' ? 'CCF-A' : 'arXiv'}</span>
        <span class="year-tag">${p.year || (p.published || '').slice(0,4)}</span>
        ${(p.tags||[]).slice(0,2).map(t=>`<span class="tag-mini">${t}</span>`).join('')}
      </div>`;
    list.appendChild(li);
  }
}

async function checkAgent() {
  const el = document.getElementById("agentStatus");
  try {
    const resp = await fetch("http://127.0.0.1:17321/health", { method: "GET" });
    el.textContent = resp.ok ? "Agent 在线" : "Agent 离线";
    el.className = "agent-status " + (resp.ok ? "online" : "offline");
  } catch {
    el.textContent = "Agent 离线";
    el.className = "agent-status offline";
  }
}

function bindEvents() {
  document.getElementById("btnFetchCCF").addEventListener("click", async () => {
    const btn = document.getElementById("btnFetchCCF");
    btn.disabled = true; btn.textContent = "抓取中...";
    document.getElementById("progressSection").style.display = "block";
    const result = await chrome.runtime.sendMessage({ action: "fetchCCFNow", yearsBack: 1 });
    btn.disabled = false; btn.textContent = "抓取 CCF A类";
    document.getElementById("progressSection").style.display = "none";
    alert(`完成！新增 ${result.totalAdded} 篇。`);
    await loadStats(); await loadRecent();
  });
  document.getElementById("btnDashboard").addEventListener("click", () =>
    chrome.tabs.create({ url: chrome.runtime.getURL("dashboard.html") }));
  document.getElementById("btnAtlas").addEventListener("click", () =>
    chrome.tabs.create({ url: chrome.runtime.getURL("atlas.html") }));
  document.getElementById("btnOptions").addEventListener("click", () =>
    chrome.runtime.openOptionsPage());
}
