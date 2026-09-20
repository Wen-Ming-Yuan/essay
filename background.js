// background.js
importScripts(
  'js/ccf-data.js', 'js/dblp-api.js', 'js/arxiv-api.js',
  'js/storage.js', 'js/tracker.js', 'js/llm-client.js', 'js/atlas-embed.js'
);

const storage = new PaperStorage();
const arxivClient = new ArxivClient();
const ccfTracker = new CCFTracker();
const FETCH_ALARM = "pp_ccf_fetch";
const ARXIV_FEED_ALARM = "pp_arxiv_feed";

// ===== 安装初始化 =====
chrome.runtime.onInstalled.addListener(async (details) => {
  if (details.reason === "install") {
    chrome.alarms.create(FETCH_ALARM, { periodInMinutes: 1440 });   // CCF每日
    chrome.alarms.create(ARXIV_FEED_ALARM, { periodInMinutes: 360 }); // arXiv每6小时
  }
});

// ===== 定时任务 =====
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === FETCH_ALARM) {
    const result = await ccfTracker.run(1);
    if (result.totalAdded > 0) {
      chrome.notifications.create({
        type: "basic", iconUrl: "icons/icon128.png",
        title: "CCF A类会议更新",
        message: `发现 ${result.totalAdded} 篇新论文`
      });
    }
  }
  if (alarm.name === ARXIV_FEED_ALARM) {
    await fetchArxivFeed();
  }
});

// ===== arXiv 订阅源抓取 =====
async function fetchArxivFeed() {
  const settings = await getSettings();
  const categories = settings.arxivCategories || ["cs.CR", "cs.AI", "cs.CL", "cs.CV"];
  for (const cat of categories) {
    const papers = await arxivClient.searchByCategory(cat, 50);
    for (const paper of papers) {
      const enriched = await enrichPaper(paper);
      await storage.addPaper(enriched);
    }
  }
}

// ===== LLM 增强 =====
async function enrichPaper(paper) {
  const settings = await getSettings();
  const llm = new LLMClient(settings.llm || {});

  // 获取 PDF 全文（如果可能）
  let fullText = "";
  try {
    const pdfResp = await fetch(paper.pdfUrl);
    const pdfText = await extractPDFText(await pdfResp.arrayBuffer());
    fullText = pdfText;
  } catch (e) { /* 忽略 */ }

  const classification = await llm.classifyPaper(paper.title, paper.abstract, fullText);

  return {
    ...paper,
    topic: classification.topic || "",
    task: classification.task || "",
    methodology: classification.methodology || "",
    venue: classification.venue || "",
    tags: classification.tags || [],
    tldr: classification.tldr || null
  };
}

function extractPDFText(arrayBuffer) {
  // 简化处理，完整PDF解析需要pdf.js
  return "";
}

// ===== 消息处理 =====
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === "archiveArxivPaper") {
    (async () => {
      const paper = await arxivClient.fetchById(msg.arxivId);
      if (paper.length > 0) {
        const enriched = await enrichPaper(paper[0]);
        const result = await storage.addPaper(enriched);
        sendResponse(result);
      } else {
        sendResponse({ added: false, error: "Paper not found" });
      }
    })();
    return true;
  }

  if (msg.action === "fetchCCFNow") {
    (async () => {
      const result = await ccfTracker.run(msg.yearsBack || 1);
      sendResponse(result);
    })();
    return true;
  }

  if (msg.action === "searchAll") {
    (async () => {
      const results = await storage.searchAll(msg.filters || {});
      sendResponse(results);
    })();
    return true;
  }

  if (msg.action === "getStats") {
    (async () => {
      sendResponse(await storage.getStats());
    })();
    return true;
  }

  if (msg.action === "createTopic") {
    (async () => {
      const topic = await storage.createTopic(msg.name, msg.paperIds, msg.summary);
      sendResponse(topic);
    })();
    return true;
  }

  if (msg.action === "getTopics") {
    (async () => {
      sendResponse(await storage.getTopics());
    })();
    return true;
  }

  if (msg.action === "clearAll") {
    (async () => {
      await storage.clearAll();
      sendResponse({ success: true });
    })();
    return true;
  }

  if (msg.action === "getSettings") {
    (async () => {
      sendResponse(await getSettings());
    })();
    return true;
  }

  if (msg.action === "saveSettings") {
    (async () => {
      await chrome.storage.local.set({ pp_settings: msg.settings });
      sendResponse({ success: true });
    })();
    return true;
  }
});

async function getSettings() {
  const r = await chrome.storage.local.get("pp_settings");
  return r.pp_settings || {
    llm: { provider: "openai", apiKey: "", model: "gpt-4o-mini" },
    arxivCategories: ["cs.CR", "cs.AI", "cs.CL", "cs.CV"],
    ccfAutoFetch: true
  };
}
