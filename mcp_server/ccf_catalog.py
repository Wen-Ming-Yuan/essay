# mcp_server/ccf_catalog.py
"""
CCF 第七版（2026）A 类会议 / 期刊 DBLP 标识符目录。
数据来源：CCF 官方目录 + 0xca1x/ccf-catalog-analysis 的 DBLP 对齐结果。
"""

from dataclasses import dataclass, field
from typing import Literal
 
Kind = Literal["conference", "journal"]


@dataclass(frozen=True)
class Venue:
    abbr: str          # 会议/期刊简称，用于 tag
    name: str          # 全称
    dblp_key: str      # DBLP stream key，如 conf/sigcomm、journals/tdsc
    kind: Kind
    area: str          # 二级领域标签（用于你自己的关注方向）
    ccf: str = "A"
    # 该 venue 是否为本次补全的缺口
    was_gap: bool = False

    @property
    def stream_url(self) -> str:
        return f"https://dblp.org/streams/{self.dblp_key}"

    @property
    def tags(self) -> list[str]:
        return ["ccf-a", self.kind, self.abbr.lower(), self.area]


# ─────────────────────────────────────────────────────────────
# 会议
# ─────────────────────────────────────────────────────────────
CONFERENCES: list[Venue] = [
    # —— 网络（本次补齐的 4 个 A 会）——
    Venue("SIGCOMM", "ACM SIGCOMM Conference", "conf/sigcomm", "conference", "network", was_gap=True),
    Venue("MobiCom", "ACM MobiCom", "conf/mobicom", "conference", "network", was_gap=True),
    Venue("INFOCOM", "IEEE INFOCOM", "conf/infocom", "conference", "network", was_gap=True),
    Venue("NSDI", "USENIX Symposium on Networked Systems Design and Implementation", "conf/nsdi", "conference", "network", was_gap=True),

    # —— 信息安全 / 密码 ——
    Venue("S&P", "IEEE Symposium on Security and Privacy", "conf/sp", "conference", "security"),
    Venue("CCS", "ACM Conference on Computer and Communications Security", "conf/ccs", "conference", "security"),
    Venue("USENIX Security", "USENIX Security Symposium", "conf/uss", "conference", "security"),
    Venue("NDSS", "Network and Distributed System Security Symposium", "conf/ndss", "conference", "security"),
    Venue("CRYPTO", "International Cryptology Conference", "conf/crypto", "conference", "security"),
    Venue("EUROCRYPT", "European Cryptology Conference", "conf/eurocrypt", "conference", "security"),

    # —— 形式化方法 / 程序语言 ——
    Venue("CAV", "Computer Aided Verification", "conf/cav", "conference", "formal"),
    Venue("LICS", "Logic in Computer Science", "conf/lics", "conference", "formal"),
    Venue("POPL", "Principles of Programming Languages", "conf/popl", "conference", "formal"),
    Venue("PLDI", "Programming Language Design and Implementation", "conf/pldi", "conference", "formal"),

    # —— 图形学 / 多媒体 ——
    Venue("SIGGRAPH", "ACM SIGGRAPH", "conf/siggraph", "conference", "graphics"),
    Venue("SIGGRAPH Asia", "ACM SIGGRAPH Asia", "conf/siggrapha", "conference", "graphics"),
    Venue("ACM MM", "ACM Multimedia", "conf/mm", "conference", "graphics"),

    # —— CV ——
    Venue("CVPR", "Computer Vision and Pattern Recognition", "conf/cvpr", "conference", "cv"),
    Venue("ICCV", "International Conference on Computer Vision", "conf/iccv", "conference", "cv"),

    # —— HCI ——
    Venue("CHI", "ACM CHI Conference on Human Factors in Computing Systems", "conf/chi", "conference", "hci"),
    Venue("UIST", "ACM User Interface Software and Technology", "conf/uist", "conference", "hci"),
    Venue("CSCW", "Computer-Supported Cooperative Work and Social Computing", "conf/cscw", "conference", "hci"),

    # —— AI / NLP ——
    Venue("AAAI", "AAAI Conference on Artificial Intelligence", "conf/aaai", "conference", "ai"),
    Venue("NeurIPS", "Neural Information Processing Systems", "conf/nips", "conference", "ai"),
    Venue("ICML", "International Conference on Machine Learning", "conf/icml", "conference", "ai"),
    Venue("IJCAI", "International Joint Conference on Artificial Intelligence", "conf/ijcai", "conference", "ai"),
    Venue("ACL", "Annual Meeting of the ACL", "conf/acl", "conference", "ai"),

    # —— 系统 / 体系结构 / 软件工程 ——
    Venue("SOSP", "ACM Symposium on Operating Systems Principles", "conf/sosp", "conference", "systems"),
    Venue("OSDI", "USENIX OSDI", "conf/osdi", "conference", "systems"),
    Venue("ASPLOS", "Architectural Support for Programming Languages and OS", "conf/asplos", "conference", "systems"),
    Venue("ISCA", "International Symposium on Computer Architecture", "conf/isca", "conference", "systems"),
    Venue("MICRO", "International Symposium on Microarchitecture", "conf/micro", "conference", "systems"),
    Venue("ICSE", "International Conference on Software Engineering", "conf/icse", "conference", "systems"),
    Venue("FSE", "Foundations of Software Engineering", "conf/sigsoft", "conference", "systems"),
    Venue("ASE", "Automated Software Engineering", "conf/kbse", "conference", "systems"),

    # —— 数据库 / 数据挖掘 ——
    Venue("SIGMOD", "ACM SIGMOD", "conf/sigmod", "conference", "data"),
    Venue("VLDB", "Very Large Data Bases", "conf/vldb", "conference", "data"),
    Venue("ICDE", "International Conference on Data Engineering", "conf/icde", "conference", "data"),
    Venue("KDD", "Knowledge Discovery and Data Mining", "conf/kdd", "conference", "data"),
    Venue("WWW", "The Web Conference", "conf/www", "conference", "data"),
]


# ─────────────────────────────────────────────────────────────
# 期刊
# ─────────────────────────────────────────────────────────────
JOURNALS: list[Venue] = [
    # —— 网络与信息安全（本次补齐的 3 个 A 刊）——
    Venue("TDSC", "IEEE Transactions on Dependable and Secure Computing", "journals/tdsc", "journal", "security", was_gap=True),
    Venue("TIFS", "IEEE Transactions on Information Forensics and Security", "journals/tifs", "journal", "security", was_gap=True),
    Venue("JOC", "Journal of Cryptology", "journals/joc", "journal", "security", was_gap=True),

    # —— 网络 ——
    Venue("TON", "IEEE/ACM Transactions on Networking", "journals/ton", "journal", "network"),
    Venue("JSAC", "IEEE Journal on Selected Areas in Communications", "journals/jsac", "journal", "network"),

    # —— 图形学 / 多媒体 / CV ——
    Venue("TOG", "ACM Transactions on Graphics", "journals/tog", "journal", "graphics"),
    Venue("TIP", "IEEE Transactions on Image Processing", "journals/tip", "journal", "graphics"),
    Venue("TPAMI", "IEEE Transactions on Pattern Analysis and Machine Intelligence", "journals/pami", "journal", "cv"),
    Venue("IJCV", "International Journal of Computer Vision", "journals/ijcv", "journal", "cv"),

    # —— HCI ——
    Venue("TOCHI", "ACM Transactions on Computer-Human Interaction", "journals/tochi", "journal", "hci"),

    # —— 形式化 / 理论 / 程序语言 ——
    Venue("TOPLAS", "ACM Transactions on Programming Languages and Systems", "journals/toplas", "journal", "formal"),
    Venue("JACM", "Journal of the ACM", "journals/jacm", "journal", "formal"),
    Venue("SICOMP", "SIAM Journal on Computing", "journals/siamcomp", "journal", "formal"),

    # —— 系统 / 软件工程 ——
    Venue("TSE", "IEEE Transactions on Software Engineering", "journals/tse", "journal", "systems"),
    Venue("TOCS", "ACM Transactions on Computer Systems", "journals/tocs", "journal", "systems"),
    Venue("TOS", "ACM Transactions on Storage", "journals/tos", "journal", "systems"),

    # —— 数据库 / 数据挖掘 ——
    Venue("TKDE", "IEEE Transactions on Knowledge and Data Engineering", "journals/tkde", "journal", "data"),
    Venue("TODS", "ACM Transactions on Database Systems", "journals/tods", "journal", "data"),
    Venue("VLDBJ", "The VLDB Journal", "journals/vldb", "journal", "data"),
]


ALL_VENUES: list[Venue] = CONFERENCES + JOURNALS

# DBLP stream URL -> Venue，供 dblp_dump 做 O(1) 命中
BY_STREAM: dict[str, Venue] = {v.stream_url: v for v in ALL_VENUES}
BY_DBLP_KEY: dict[str, Venue] = {v.dblp_key: v for v in ALL_VENUES}
BY_ABBR: dict[str, Venue] = {v.abbr.lower(): v for v in ALL_VENUES}

# 你重点关注的方向，dashboard 默认筛这几类
FOCUS_AREAS = {"security", "formal", "graphics", "cv", "hci"}


def gaps() -> list[Venue]:
    """返回本次补齐的 7 个缺口，便于自检。"""
    return [v for v in ALL_VENUES if v.was_gap]

ALL_CCF_A: dict[str, str] = {v.abbr: v.dblp_key for v in ALL_VENUES}

if __name__ == "__main__":
    print(f"total={len(ALL_VENUES)} conf={len(CONFERENCES)} journal={len(JOURNALS)}")
    for v in gaps():
        print(f"[gap] {v.kind:10s} {v.abbr:14s} {v.dblp_key}")
