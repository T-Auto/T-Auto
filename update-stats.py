#!/usr/bin/env python3
"""更新 README.md 中的 GitHub 数据徽章（每日定时）。

数据来源（GitHub REST API）:
  - users : 粉丝数
  - repos : 两个 star 徽章各自名下仓库的星数之和

star 徽章口径（按 T-Auto 在各仓库中的身份分组）:
  - star · owner/admin  : 自己拥有 / 担任 owner、admin 的仓库
                          = tui + eac + spec + std
  - star · collaborator : 仅以协作者身份参与的仓库
                          = lingchat + DeepSeek-Balance-Whale-Widget

提示: 徽章上的文字由 shields.io 依据 src 里的 URL 渲染，
      改 README 里的 alt 属性不会改变显示效果；要改标签请改这里的 STAR_GROUPS。

用法:
    python update-stats.py

需要 `gh` CLI 已登录（GitHub API 认证通过 gh 完成）。
"""
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

# Windows 控制台可能是 GBK 编码，强制 UTF-8 输出避免打印报错
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

USER = "T-Auto"          # 统计哪个账号

# 星数分组：每组 = (内部键, 徽章标签, 仓库列表)
# 注意：同一个仓库只能出现在一组里，否则会重复计数；
#       GitHub 的仓库改名/转移会自动 302 到新地址，gh api 能正常跟随。
STAR_GROUPS = [
    (
        "owner_admin",
        "star · owner/admin",
        [
            "ccch1mneyyy/dsh-TUI",          # tui
            "DSH-EAC/DSH-Desktop-EAC",      # eac
            "T-Auto/dsh-ecosystem-spec",    # spec
            "T-Auto/dsh-std",               # std
        ],
    ),
    (
        "collaborator",
        "star · collaborator",
        [
            "SlimeBoyOwO/LingChat",                       # lingchat
            "MeteorNOX/DeepSeek-Balance-Whale-Widget",    # whale widget
        ],
    ),
]

ROOT = Path(__file__).resolve().parent
README = ROOT / "README.md"

START = "<!-- STATS:START -->"
END = "<!-- STATS:END -->"

# 每个徽章的颜色：followers 蓝 / star 金黄（GitHub 官方色系）
# collaborator 用更淡的琥珀色（amber-300），和 owner/admin 的 amber-500 区分开
COLORS = {
    "followers": "58a6ff",
    "owner_admin": "f59e0b",
    "collaborator": "fcd34d",
}
LOGO = "github"

# visitors 计数器：ghpvc 动态徽章，base 参数从 500 起跳（真实访问在此之上累加）
VISITORS_BADGE = (
    "https://komarev.com/ghpvc/?username=T-Auto"
    "&base=500&style=flat-square&label=visitors&color=2ea043"
)


def gh_json(url: str) -> dict:
    """通过 gh CLI 调用 GitHub REST API。"""
    out = subprocess.run(
        ["gh", "api", url], capture_output=True, text=True,
        encoding="utf-8", check=True,
    ).stdout
    return json.loads(out)


def fetch_stats() -> dict:
    """拉取全部统计数字。"""
    # 1. 粉丝数
    user = gh_json("users/" + USER)
    followers = user["followers"]

    # 2. 两个 star 分组：各自仓库列表的星数之和
    stars = {}
    for key, _label, repos in STAR_GROUPS:
        total = 0
        for full in repos:
            owner, name = full.split("/")
            total += gh_json(f"repos/{owner}/{name}")["stargazers_count"]
        stars[key] = total

    return {
        "followers": followers,
        "stars": stars,
    }


def badge(label: str, value, color: str, with_logo: bool = True) -> str:
    """生成一个 shields.io 徽章。with_logo=False 时不带 github 标志。"""
    query = "?style=flat-square"
    if with_logo:
        query += f"&logo={LOGO}&logoColor=white"
    src = (
        "https://img.shields.io/badge/"
        + urllib.parse.quote(label, safe="")
        + "-"
        + urllib.parse.quote(f"{value:,}", safe="")
        + f"-{color}{query}"
    )
    return f'  <img alt="{label}" src="{src}">'


def build_block(s: dict) -> str:
    """一行徽章：star(owner/admin) / star(collaborator) / followers / visitors。"""
    stars = s["stars"]
    badges = [
        badge(label, stars[key], COLORS[key], with_logo=False)
        for key, label, _repos in STAR_GROUPS
    ]
    badges.append(badge("followers", s["followers"], COLORS["followers"], with_logo=False))
    badges.append(f'  <img alt="visitors" src="{VISITORS_BADGE}">')
    return '<p align="center">\n' + " ".join(badges) + "\n</p>"


def main() -> None:
    content = README.read_text(encoding="utf-8")
    block = build_block(fetch_stats())
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(content):
        raise SystemExit(f"README.md 中找不到 {START} ... {END} 标记块")
    new_content = pattern.sub(f"{START}\n{block}\n{END}", content)
    README.write_text(new_content, encoding="utf-8")
    print("已更新 README.md 数据徽章")


if __name__ == "__main__":
    main()
