"""向量化与语义地图：sentence-transformers + UMAP"""
import logging
from typing import Dict, List

logger = logging.getLogger("essay-mcp.atlas")

DEFAULT_MODEL = "all-MiniLM-L6-v2"


class AtlasEmbedder:
    """论文摘要向量化 + 2D 投影"""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError("请安装 sentence-transformers: pip install sentence-transformers")
            logger.info(f"加载嵌入模型: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
        embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return embeddings.tolist()

    def project_2d(self, embeddings: List[List[float]]) -> List[Dict[str, float]]:
        try:
            import umap
            import numpy as np
        except ImportError:
            raise ImportError("请安装 umap-learn: pip install umap-learn")

        arr = np.array(embeddings)
        if arr.shape[0] < 3:
            if arr.shape[1] >= 2:
                return [{"x": float(v[0]), "y": float(v[1])} for v in arr]
            return [{"x": 0.0, "y": 0.0} for _ in arr]

        n_neighbors = min(15, max(2, arr.shape[0] - 1))
        reducer = umap.UMAP(
            n_components=2, n_neighbors=n_neighbors,
            min_dist=0.1, metric="cosine", random_state=42,
        )
        proj = reducer.fit_transform(arr)
        return [{"x": float(p[0]), "y": float(p[1])} for p in proj]

    def build_atlas(self, papers: List[Dict], max_papers: int = 500) -> Dict:
        papers = papers[:max_papers]
        if not papers:
            return {"points": [], "count": 0}

        texts = [f"{p.get('title', '')} {(p.get('abstract') or '')[:500]}" for p in papers]
        embeddings = self.embed(texts)
        coords = self.project_2d(embeddings)

        points = []
        for p, c in zip(papers, coords):
            authors = p.get("authors", [])
            if isinstance(authors, str):
                try:
                    import json
                    authors = json.loads(authors)
                except Exception:
                    authors = []
            points.append({
                "x": c["x"], "y": c["y"], "id": p.get("id"),
                "title": p.get("title", ""),
                "authors": authors[:3] if isinstance(authors, list) else [],
                "venue": p.get("venue", ""), "year": p.get("year"),
                "source": p.get("source", ""), "tags": p.get("tags", ""),
                "url": p.get("url", ""),
            })

        return {"points": points, "count": len(points)}
