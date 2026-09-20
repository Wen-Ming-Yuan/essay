"""论文个性化推荐：基于研究兴趣的相关性排序"""
import re
from typing import Dict, List, Tuple

class PaperRecommender:
    def __init__(self, interests: List[str] = None):
        self.interests = [i.lower() for i in (interests or [])]
    
    def compute_relevance(self, title: str, abstract: str) -> float:
        """计算论文与研究兴趣的相关性分数（0-1）"""
        if not self.interests:
            return 0.5
        
        text = f"{title} {abstract}".lower()
        score = 0.0
        matched = 0
        
        for interest in self.interests:
            # 兴趣词在标题中出现，权重更高
            if re.search(rf"\b{re.escape(interest)}\b", title.lower()):
                score += 1.0
                matched += 1
            elif interest in text:
                score += 0.5
                matched += 1
        
        return min(score / max(len(self.interests), 1), 1.0)
    
    def rank_papers(self, papers: List[Dict]) -> List[Dict]:
        """对论文列表按相关性排序"""
        for p in papers:
            p["relevance_score"] = self.compute_relevance(
                p.get("title", ""), p.get("abstract", "")
            )
        return sorted(papers, key=lambda x: x["relevance_score"], reverse=True)
