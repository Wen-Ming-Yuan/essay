// js/storage.js
class PaperStorage {
  constructor() {
    this.KEY_PAPERS = "pp_papers";
    this.KEY_CCF = "pp_ccf_papers";
    this.KEY_TOPICS = "pp_topics";
    this.KEY_LAST_FETCH = "pp_last_fetch";
    this.KEY_SETTINGS = "pp_settings";
  }

  // ===== arXiv 论文 =====
  async getPapers() {
    const r = await chrome.storage.local.get(this.KEY_PAPERS);
    return r[this.KEY_PAPERS] || [];
  }

  async addPaper(paper) {
    const papers = await this.getPapers();
    const key = paper.arxivId || paper.doi || paper.title;
    if (papers.some(p => (p.arxivId || p.doi || p.title) === key)) {
      return { added: false };
    }
    papers.push({
      ...paper,
      addedAt: Date.now(),
      tags: paper.tags || [],
      tldr: paper.tldr || null,
      topic: paper.topic || null
    });
    await chrome.storage.local.set({ [this.KEY_PAPERS]: papers });
    return { added: true, total: papers.length };
  }

  // ===== CCF A类论文 =====
  async getCCFPapers() {
    const r = await chrome.storage.local.get(this.KEY_CCF);
    return r[this.KEY_CCF] || [];
  }

  async addCCFPapers(newPapers) {
    const existing = await this.getCCFPapers();
    const keys = new Set(existing.map(p => p.dblpKey || p.doi || p.title));
    let added = 0;
    for (const p of newPapers) {
      const k = p.dblpKey || p.doi || p.title;
      if (k && !keys.has(k)) {
        existing.push({ ...p, addedAt: Date.now(), ccfRank: "A" });
        keys.add(k); added++;
      }
    }
    await chrome.storage.local.set({
      [this.KEY_CCF]: existing,
      [this.KEY_LAST_FETCH]: Date.now()
    });
    return { added, total: existing.length };
  }

  // ===== 统一检索 =====
  async searchAll(filters = {}) {
    const [arxivPapers, ccfPapers] = await Promise.all([
      this.getPapers(),
      this.getCCFPapers()
    ]);
    let all = [
      ...arxivPapers.map(p => ({ ...p, source: "arxiv" })),
      ...ccfPapers.map(p => ({ ...p, source: "ccf" }))
    ];

    if (filters.keyword) {
      const kw = filters.keyword.toLowerCase();
      all = all.filter(p =>
        (p.title || "").toLowerCase().includes(kw) ||
        (p.authors || []).some(a => a.toLowerCase().includes(kw)) ||
        (p.abstract || "").toLowerCase().includes(kw)
      );
    }
    if (filters.tags && filters.tags.length) {
      all = all.filter(p => filters.tags.every(t => (p.tags || []).includes(t)));
    }
    if (filters.source) {
      all = all.filter(p => p.source === filters.source);
    }
    if (filters.year) {
      all = all.filter(p => String(p.year || p.published?.slice(0,4)) === String(filters.year));
    }
    if (filters.category) {
      all = all.filter(p => p.ccfArea === filters.category || (p.categories || []).includes(filters.category));
    }
    return all;
  }

  // ===== Topic 管理 =====
  async getTopics() {
    const r = await chrome.storage.local.get(this.KEY_TOPICS);
    return r[this.KEY_TOPICS] || [];
  }

  async createTopic(name, paperIds, summary) {
    const topics = await this.getTopics();
    const allPapers = await this.searchAll({});
    const selected = allPapers.filter(p => paperIds.includes(p.id || p.arxivId || p.dblpKey));
    const tagUnion = [...new Set(selected.flatMap(p => p.tags || []))];

    topics.push({
      id: `topic_${Date.now()}`,
      name, summary, paperIds, tags: tagUnion,
      createdAt: Date.now()
    });
    await chrome.storage.local.set({ [this.KEY_TOPICS]: topics });
    return topics[topics.length - 1];
  }

  // ===== 统计 =====
  async getStats() {
    const [arxiv, ccf, topics] = await Promise.all([
      this.getPapers(), this.getCCFPapers(), this.getTopics()
    ]);
    const thisYear = new Date().getFullYear();
    return {
      arxivTotal: arxiv.length,
      ccfTotal: ccf.length,
      topicsTotal: topics.length,
      thisYearArxiv: arxiv.filter(p => (p.published || "").startsWith(thisYear)).length,
      thisYearCCF: ccf.filter(p => p.year === thisYear).length
    };
  }

  // ===== 清理 =====
  async clearAll() {
    await chrome.storage.local.remove([this.KEY_PAPERS, this.KEY_CCF, this.KEY_TOPICS]);
  }
}
