// content/arxiv-watcher.js
// 监听 arXiv 页面的 PDF 下载链接点击
document.addEventListener('click', (e) => {
  const link = e.target.closest('a[href$=".pdf"]');
  if (!link) return;

  const arxivId = extractArxivId(link.href);
  if (!arxivId) return;

  // 通知 background 开始归档
  chrome.runtime.sendMessage({
    action: "archiveArxivPaper",
    arxivId: arxivId,
    pdfUrl: link.href
  });
});

function extractArxivId(url) {
  // 匹配 arxiv.org/pdf/2312.12345 或 arxiv.org/abs/2312.12345
  const match = url.match(/arxiv\.org\/(?:pdf|abs)\/(\d{4}\.\d{4,5})/);
  return match ? match[1] : null;
}

// 监听页面上的 arXiv ID 显示区域，捕获用户浏览的论文
const observer = new MutationObserver(() => {
  const abstractBlock = document.querySelector('.abstract');
  if (abstractBlock) {
    const idEl = document.querySelector('.arxivid');
    if (idEl) {
      const arxivId = extractArxivId(idEl.textContent);
      if (arxivId) {
        chrome.runtime.sendMessage({
          action: "viewArxivPaper",
          arxivId: arxivId
        });
      }
    }
  }
});

observer.observe(document.body, { childList: true, subtree: true });
