#!/usr/bin/env python3
"""更新 README.md 中的 GitHub 数据徽章（每日定时）。

数据来源:
  - users : 粉丝数（GitHub REST API）
  - repos : 两个 star 徽章各自名下仓库的星数之和（GitHub REST API）
  - ghpvc : 访客数（komarev.com/ghpvc 返回的 SVG 里解析出来）

访客数为什么是"每日快照"而不是直接嵌 komarev 动态图:
  GitHub 渲染 README 时会把外链图片改写成自家 camo 代理
  （camo.githubusercontent.com）。camo 取 komarev.com 长期不稳定，会直接
  返回 404 "Cannot proxy the given URL" —— komarev 是单机免费服务、响应头
  带 no-store，每次浏览都必须让 camo 实时回源，链路一抖徽章就碎。
  所以这里改成：本脚本每天抓一次数字，渲染成 shields.io 静态徽章（camo 取
  shields.io 是稳的）。取不到 komarev 时沿用 README 里已显示的数字，不会把
  徽章弄坏。

star 徽章口径（按 T-Auto 在各仓库中的身份分组）:
  - star · owner/admin  : 自己拥有 / 担任 owner、admin 的仓库
                          = tui + spec + std + dsh-ops
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
import urllib.request
from pathlib import Path

# Windows 控制台可能是 GBK 编码，强制 UTF-8 输出避免打印报错
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

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
            "T-Auto/dsh-ecosystem-spec",    # spec
            "T-Auto/dsh-std",               # std
            "T-Auto/dsh-ops",               # dsh-ops
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
# collaborator 用淡紫色（H264 S82 L78），与 owner/admin 的金色区分开。
# 注意：shields.io 会按背景亮度自动挑字色，底色一旦偏浅，数字就变成深灰 #333，
#       而且没有 textColor 之类参数可以强制白字；要保持白字只能选足够深的底色
#       （实测这个紫色色相下亮度上限约 L78，例如 bf9bf5；再淡如 c4a3fb 数字就变灰）。
COLORS = {
    "followers": "58a6ff",
    "owner_admin": "f59e0b",
    "collaborator": "bf9bf5",
    "visitors": "2ea043",
}
LOGO = "github"

# visitors 计数器的数据源：仍是 komarev 的 ghpvc，但只由本脚本抓取解析，
# 渲染出去的是 shields.io 静态徽章（原因见文件头 docstring）。
# base 参数保持 500，让读到的数字与原来动态徽章显示的口径一致。
GHPVC_URL = (
    "https://komarev.com/ghpvc/?username=T-Auto"
    "&base=500&style=flat-square&label=visitors&color=2ea043"
)


def fetch_visitors(prev: int) -> int:
    """从 komarev 的 SVG 里解析访客数；取不到就沿用上一次的数字。"""
    try:
        req = urllib.request.Request(
            GHPVC_URL, headers={"User-Agent": "T-Auto-profile-readme/1.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            svg = resp.read().decode("utf-8", "replace")
        found = re.search(r"<text[^>]*>([\d,]+)</text>", svg)
        if found:
            return int(found.group(1).replace(",", ""))
        print("  ! komarev 返回的内容里没有解析到数字，沿用旧值", file=sys.stderr)
    except Exception as exc:  # 网络抖动、超时、被墙都不要把徽章弄坏
        print(f"  ! 读取 komarev 访客数失败（{exc}），沿用旧值 {prev:,}", file=sys.stderr)
    return prev


def gh_json(url: str) -> dict:
    """通过 gh CLI 调用 GitHub REST API。"""
    out = subprocess.run(
        ["gh", "api", url], capture_output=True, text=True,
        encoding="utf-8", check=True,
    ).stdout
    return json.loads(out)


def fetch_stats(prev_visitors: int) -> dict:
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

    # 3. 访客数（komarev 快照，失败则沿用上一次）
    visitors = fetch_visitors(prev_visitors)

    return {
        "followers": followers,
        "stars": stars,
        "visitors": visitors,
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
    badges.append(badge("visitors", s["visitors"], COLORS["visitors"], with_logo=False))
    return '<p align="center">\n' + " ".join(badges) + "\n</p>"


def prev_visitors(content: str) -> int:
    """读出 README 里当前显示的访客数，作为抓取失败时的兜底。"""
    found = re.search(r"badge/visitors-([^-]+)-", content)
    if not found:
        return 0
    digits = urllib.parse.unquote(found.group(1)).replace(",", "")
    return int(digits) if digits.isdigit() else 0


def main() -> None:
    content = README.read_text(encoding="utf-8")
    block = build_block(fetch_stats(prev_visitors(content)))
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)
    if not pattern.search(content):
        raise SystemExit(f"README.md 中找不到 {START} ... {END} 标记块")
    new_content = pattern.sub(f"{START}\n{block}\n{END}", content)
    README.write_text(new_content, encoding="utf-8")
    print("已更新 README.md 数据徽章")


if __name__ == "__main__":
    main()
