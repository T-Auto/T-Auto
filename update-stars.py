#!/usr/bin/env python3
"""更新 README.md 中的星数统计板块。

用法:
    python update-stars.py

需要 `gh` CLI 已登录（GitHub API 认证通过 gh 完成）。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# Windows 控制台可能是 GBK 编码，强制 UTF-8 输出避免打印 ⭐ 时报错
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


def gh_graphql(query: str) -> dict:
    """通过 gh CLI 调用 GitHub GraphQL API。"""
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def fetch_stars() -> list[int]:
    """一次 GraphQL 查询拿到所有仓库的星数（顺序与 REPOS 一致）。"""
    aliases = []
    for i, (full, _) in enumerate(REPOS):
        owner, name = full.split("/")
        aliases.append(
            f'r{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) '
            f"{{ stargazerCount }}"
        )
    query = "query { " + " ".join(aliases) + " }"
    data = gh_graphql(query)["data"]
    return [data[f"r{i}"]["stargazerCount"] for i in range(len(REPOS))]


def build_block() -> str:
    """生成标记块内的表格行。"""
    stars = fetch_stars()
    total = sum(stars)
    rows = []
    for (full, role), n in zip(REPOS, stars):
        name = full.split("/")[1]
        rows.append(f"| [{name}](https://github.com/{full}) | {role} | ⭐ {n:,} |")
    rows.append(f"| **合计（含我参与的仓库）** | | **⭐ {total:,}** |")
    return "\n".join(rows)


def main() -> None:
    content = README.read_text(encoding="utf-8")
    block = build_block()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(content):
        raise SystemExit(f"README.md 中找不到 {START} ... {END} 标记块")
    new_content = pattern.sub(f"{START}\n{block}\n{END}", content)
    README.write_text(new_content, encoding="utf-8")
    print("已更新 README.md 星数统计:")
    print(block)


if __name__ == "__main__":
    main()
