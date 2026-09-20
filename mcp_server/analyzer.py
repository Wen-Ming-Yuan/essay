"""论文智能分析：LLM 驱动的标签生成与摘要"""
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("essay-mcp.analyzer")

class PaperAnalyzer:
    def __init__(self, llm_client=None):
        """初始化分析器，可传入任意 LLM 客户端"""
        self.llm = llm_client
    
    def generate_tags(self, title: str, abstract: str, max_tags: int = 5) -> List[str]:
        """基于标题和摘要生成 2-5 个标签"""
        if not self.llm:
            # 无 LLM 时，使用规则式降级方案
            return self._rule_based_tags(title, abstract, max_tags)
        
        prompt = f"""Generate {max_tags} short tags for this paper.
Title: {title}
Abstract: {abstract[:1000]}
Return only a JSON array of strings."""
        
        try:
            response = self.llm.generate(prompt)
            tags = json.loads(response)
            return tags[:max_tags]
        except Exception as e:
            logger.error(f"LLM 标签生成失败: {e}")
            return self._rule_based_tags(title, abstract, max_tags)
    
    def generate_tldr(self, title: str, abstract: str) -> Dict[str, str]:
        """生成 TL;DR 摘要（背景/方法/关键结果）"""
        if not self.llm:
            return {"background": "", "method": "", "key_result": ""}
        
        prompt = f"""Summarize this paper in three parts:
1. Background (1 sentence)
2. Method (1 sentence)  
3. Key Result (1 sentence)

Title: {title}
Abstract: {abstract[:1500]}

Return JSON: {{"background": "...", "method": "...", "key_result": "..."}}"""
        
        try:
            response = self.llm.generate(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"TL;DR 生成失败: {e}")
            return {"background": "", "method": "", "key_result": ""}
    
    def _rule_based_tags(self, title: str, abstract: str, max_tags: int) -> List[str]:
        """基于关键词规则的降级标签方案"""
        text = f"{title} {abstract}".lower()
        tag_rules = {
            "security": ["security", "attack", "vulnerability", "malware", "fuzzing", "privacy"],
            "ml": ["neural", "deep learning", "transformer", "llm", "language model"],
            "systems": ["operating system", "kernel", "distributed", "storage"],
            "network": ["network", "protocol", "routing", "tcp", "wireless"],
            "graphics": ["rendering", "geometry", "ray tracing", "mesh"],
            "hci": ["user study", "interaction", "usability", "interface"],
        }
        matched = []
        for tag, keywords in tag_rules.items():
            if any(kw in text for kw in keywords):
                matched.append(tag)
        return matched[:max_tags] or ["general"]
