#!/usr/bin/env python3
"""更新 README.md 中的 GitHub 数据徽章（每日定时）。

数据来源（GitHub REST API）:
  - search  : 作者历史总提交数
  - users   : 粉丝数
  - repos   : 名下 + 协作仓库总星数

用法:
    python update-stats.py

需要 `gh` CLI 已登录（GitHub API 认证通过 gh 完成）。
注意：CI 的 GITHUB_TOKEN 只能统计公共仓库提交数（对外口径）；
本地 PAT 含私有仓库，数字会偏大，以 CI 生成为准。
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
# 协作/参与但不在自己名下的仓库，星数一并计入（与原 stars 徽章口径一致）
EXTRA_REPOS = [
    "ccch1mneyyy/dsh-TUI",
    "SlimeBoyOwO/LingChat",
]
ROOT = Path(__file__).resolve().parent
README = ROOT / "README.md"

START = "<!-- STATS:START -->"
END = "<!-- STATS:END -->"

# 每个徽章的颜色：commits 绿 / followers 蓝 / stars 金黄（GitHub 官方色系）
COLORS = {
    "commits": "3fb950",
    "followers": "58a6ff",
    "stars": "f59e0b",
}
LOGO = "github"


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

    # 2. 跨仓库总星数 = 名下公开仓库 + 协作仓库（分页遍历）
    total_stars = 0
    page = 1
    while True:
        batch = gh_json(f"users/{USER}/repos?per_page=100&page={page}")
        if not batch:
            break
        total_stars += sum(r["stargazers_count"] for r in batch)
        page += 1
    for full in EXTRA_REPOS:
        owner, name = full.split("/")
        repo = gh_json(f"repos/{owner}/{name}")
        total_stars += repo["stargazers_count"]

    # 3. 该作者的历史总提交数（search API，所有仓库所有年份）
    search = gh_json("search/commits?q=author:" + USER + "&per_page=1")
    total_commits = search["total_count"]

    return {
        "followers": followers,
        "total_stars": total_stars,
        "total_commits": total_commits,
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
    """一行三枚徽章：commits / followers / stars（纯文字、无 github 标志）。"""
    return (
        '<p align="center">\n'
        + " ".join(
            [
                badge("commits", s["total_commits"], COLORS["commits"], with_logo=False),
                badge("followers", s["followers"], COLORS["followers"], with_logo=False),
                badge("stars", s["total_stars"], COLORS["stars"], with_logo=False),
            ]
        )
        + "\n</p>"
    )


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
