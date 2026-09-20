// js/atlas-embed.js
class AtlasEmbedder {
  constructor() {
    this.modelName = "BAAI/bge-small-en-v1.5";
    this.dim = 384;
  }

  /**
   * 使用简化嵌入（基于TF-IDF+哈希）替代完整模型
   * 完整模型需要在本地Agent中运行
   */
  async embed(text) {
    // 尝试调用本地 Agent 的嵌入接口
    try {
      const resp = await fetch("http://127.0.0.1:17321/api/embed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      });
      if (resp.ok) {
        const data = await resp.json();
        return data.embedding;
      }
    } catch (e) {
      // Agent 未运行，回退到简化嵌入
    }
    return this._simpleEmbed(text);
  }

  _simpleEmbed(text) {
    // 简化的哈希嵌入，用于无Agent时的降级方案
    const vec = new Float32Array(this.dim);
    const words = text.toLowerCase().split(/\s+/);
    for (const word of words) {
      let hash = 0;
      for (let i = 0; i < word.length; i++) {
        hash = ((hash << 5) - hash) + word.charCodeAt(i);
        hash |= 0;
      }
      vec[Math.abs(hash) % this.dim] += 1;
    }
    // 归一化
    const norm = Math.sqrt(vec.reduce((s, v) => s + v * v, 0)) || 1;
    return Array.from(vec.map(v => v / norm));
  }

  /**
   * 简化的2D投影（使用前两个主成分的近似）
   */
  project2D(embeddings) {
    // 在真实实现中应使用UMAP
    // 这里使用简单的PCA降维
    const n = embeddings.length;
    if (n === 0) return [];

    const mean = new Float32Array(this.dim);
    for (const emb of embeddings) {
      for (let i = 0; i < this.dim; i++) mean[i] += emb[i] / n;
    }

    return embeddings.map(emb => {
      // 简单投影：取方差最大的两个维度
      let maxVar1 = 0, maxVar2 = 0, idx1 = 0, idx2 = 1;
      for (let i = 0; i < this.dim; i++) {
        const v = Math.abs(emb[i] - mean[i]);
        if (v > maxVar1) { maxVar2 = maxVar1; idx2 = idx1; maxVar1 = v; idx1 = i; }
        else if (v > maxVar2) { maxVar2 = v; idx2 = i; }
      }
      return { x: emb[idx1], y: emb[idx2] };
    });
  }
}
