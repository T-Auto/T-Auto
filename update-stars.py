#!/usr/bin/env python3
"""更新 README.md 中总星数徽章的数字。

用法:
    python update-stars.py

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

# 要统计的仓库: (owner/repo, 我的角色)
REPOS = [
    ("ccch1mneyyy/dsh-TUI", "Admin"),
    ("SlimeBoyOwO/LingChat", "协作"),
]

ROOT = Path(__file__).resolve().parent
README = ROOT / "README.md"

START = "<!-- STARS:START -->"
END = "<!-- STARS:END -->"

COLOR = "f59e0b"  # 徽章颜色，和 README 里的保持一致

LABEL = "stars"


def gh_graphql(query: str) -> dict:
    """通过 gh CLI 调用 GitHub GraphQL API。"""
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def fetch_total() -> int:
    """一次 GraphQL 查询拿到所有仓库星数之和。"""
    aliases = []
    for i, (full, _) in enumerate(REPOS):
        owner, name = full.split("/")
        aliases.append(
            f'r{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) '
            f"{{ stargazerCount }}"
        )
    query = "query { " + " ".join(aliases) + " }"
    data = gh_graphql(query)["data"]
    return sum(data[f"r{i}"]["stargazerCount"] for i in range(len(REPOS)))


def build_block(total: int) -> str:
    """生成徽章所在的行。"""
    total_text = f"{total:,}"
    src = (
        "https://img.shields.io/badge/"
        + LABEL
        + "-"
        + urllib.parse.quote(total_text)
        + f"-{COLOR}?style=flat-square&logo=github&logoColor=white"
    )
    return (
        '<p align="center">\n'
        f'  <img alt="{LABEL}" src="{src}">\n'
        "</p>"
    )


def main() -> None:
    content = README.read_text(encoding="utf-8")
    block = build_block(fetch_total())
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(content):
        raise SystemExit(f"README.md 中找不到 {START} ... {END} 标记块")
    new_content = pattern.sub(f"{START}\n{block}\n{END}", content)
    README.write_text(new_content, encoding="utf-8")
    print("已更新 README.md 总星数徽章")


if __name__ == "__main__":
    main()
