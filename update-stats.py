#!/usr/bin/env python3
"""更新 README.md 中的 GitHub 数据徽章（每日定时）。

数据来源:
  - GitHub REST API : 用户资料(followers/repos)、跨仓库星数、作者历史总提交数(search)
  - GitHub GraphQL  : 当年贡献数据(commits/PRs/issues/总贡献)

用法:
    python update-stats.py

需要 `gh` CLI 已登录（GitHub API 认证通过 gh 完成）。
"""
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
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

COLOR = "f59e0b"         # 徽章颜色（金色，与原来 stars 徽章一致）
LOGO = "github"


def gh_graphql(query: str) -> dict:
    """通过 gh CLI 调用 GitHub GraphQL API。"""
    out = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True, encoding="utf-8", check=True,
    ).stdout
    return json.loads(out)


def gh_json(url: str) -> dict:
    """通过 gh CLI 调用 GitHub REST API。"""
    out = subprocess.run(
        ["gh", "api", url], capture_output=True, text=True,
        encoding="utf-8", check=True,
    ).stdout
    return json.loads(out)


def fetch_stats() -> dict:
    """拉取全部统计数字。"""
    # 1. 用户资料
    user = gh_json("users/" + USER)
    followers = user["followers"]
    repos = user["public_repos"]

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

    # 4. 当年贡献（GraphQL，from=今年1月1日, to=现在）
    year = datetime.now(timezone.utc).year
    data = gh_graphql(
        "query { user(login: " + json.dumps(USER) + ") { "
        "contributionsCollection(from: "
        + json.dumps(f"{year}-01-01T00:00:00Z")
        + ") { "
        "totalCommitContributions "
        "totalPullRequestContributions "
        "totalIssueContributions "
        "contributionCalendar { totalContributions } } } }"
    )["data"]["user"]["contributionsCollection"]

    return {
        "year": year,
        "followers": followers,
        "repos": repos,
        "total_stars": total_stars,
        "total_commits": total_commits,
        "year_commits": data["totalCommitContributions"],
        "year_prs": data["totalPullRequestContributions"],
        "year_issues": data["totalIssueContributions"],
        "year_contributions": data["contributionCalendar"]["totalContributions"],
    }


def badge(label: str, value) -> str:
    """生成一个 shields.io 徽章（金色、github logo）。"""
    src = (
        "https://img.shields.io/badge/"
        + urllib.parse.quote(label, safe="")
        + "-"
        + urllib.parse.quote(f"{value:,}", safe="")
        + f"-{COLOR}?style=flat-square&logo={LOGO}&logoColor=white"
    )
    return f'  <img alt="{label}" src="{src}">'


def build_block(s: dict) -> str:
    """两行徽章：规模 / 当年贡献。"""
    row1 = [
        badge("commits", s["total_commits"]),
        badge("stars", s["total_stars"]),
        badge("followers", s["followers"]),
        badge("repos", s["repos"]),
    ]
    row2 = [
        badge(f"commits {s['year']}", s["year_commits"]),
        badge(f"contributions {s['year']}", s["year_contributions"]),
        badge(f"prs {s['year']}", s["year_prs"]),
        badge(f"issues {s['year']}", s["year_issues"]),
    ]
    return (
        '<p align="center">\n'
        + " ".join(row1)
        + "\n<br>\n"
        + " ".join(row2)
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
