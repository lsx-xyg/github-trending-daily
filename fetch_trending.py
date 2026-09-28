#!/usr/bin/env python3
"""
每日爬取 GitHub Trending 页面，生成 Markdown 存档。
用法: python fetch_trending.py
"""

import os
import re
import sys
from datetime import datetime, timezone, timedelta

import requests
from bs4 import BeautifulSoup

# 北京时间
CST = timezone(timedelta(hours=8))
TODAY = datetime.now(CST).strftime("%Y-%m-%d")

# 要爬取的语言列表：None 表示全语言，其余为 GitHub 语言 slug
LANGUAGES = [
    (None, "全部语言"),
    ("python", "Python"),
    ("javascript", "JavaScript"),
    ("typescript", "TypeScript"),
    ("java", "Java"),
    ("go", "Go"),
    ("rust", "Rust"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_trending(language=None):
    """爬取 GitHub Trending 页面，返回仓库列表。"""
    url = "https://github.com/trending"
    if language:
        url += f"/{language}"
    url += "?since=daily"

    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.Box-row")

    repos = []
    for article in articles:
        # 仓库名
        h2 = article.select_one("h2 a")
        if not h2:
            continue
        repo_path = h2.get("href", "").strip().lstrip("/")
        if not repo_path:
            continue

        # 描述
        desc_tag = article.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 语言
        lang_tag = article.select_one('[itemprop="programmingLanguage"]')
        language_name = lang_tag.get_text(strip=True) if lang_tag else ""

        # star 数
        star_tag = article.select_one('a[href$="/stargazers"]')
        stars = star_tag.get_text(strip=True) if star_tag else "0"

        # fork 数
        fork_tag = article.select_one('a[href$="/forks"]')
        forks = fork_tag.get_text(strip=True) if fork_tag else "0"

        # 今日增量
        today_tag = article.select_one("span.d-inline-block.float-sm-right")
        today_stars = today_tag.get_text(strip=True) if today_tag else ""

        repos.append({
            "repo": repo_path,
            "url": f"https://github.com/{repo_path}",
            "description": description,
            "language": language_name,
            "stars": stars,
            "forks": forks,
            "today_stars": today_stars,
        })

    return repos


def render_section(title, repos):
    """渲染一个语言分类的 Markdown 表格。"""
    lines = [f"## {title}", ""]
    if not repos:
        lines.append("_暂无数据_")
        lines.append("")
        return "\n".join(lines)

    lines.append("| # | 仓库 | 语言 | Star | 今日新增 | 描述 |")
    lines.append("|---|---|---|---|---|---|")
    for i, r in enumerate(repos, 1):
        desc = r["description"].replace("|", "\\|").replace("\n", " ")
        if len(desc) > 80:
            desc = desc[:77] + "..."
        lines.append(
            f"| {i} | [{r['repo']}]({r['url']}) | {r['language'] or '-'} | "
            f"{r['stars']} | {r['today_stars'] or '-'} | {desc} |"
        )
    lines.append("")
    return "\n".join(lines)


def generate_daily_markdown(all_data):
    """生成当天的完整 Markdown。"""
    parts = [
        f"# GitHub Trending 日报 - {TODAY}",
        "",
        f"> 自动爬取于 {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')} CST",
        "",
        "---",
        "",
    ]
    for lang_slug, lang_name in LANGUAGES:
        repos = all_data.get(lang_slug, [])
        parts.append(render_section(lang_name, repos))
    return "\n".join(parts)


def generate_readme(all_data):
    """生成 README，展示最新一天 + 历史归档。"""
    # 列出 daily/ 下所有文件作为历史归档
    daily_dir = os.path.join(os.path.dirname(__file__), "daily")
    archives = []
    if os.path.isdir(daily_dir):
        for f in sorted(os.listdir(daily_dir), reverse=True):
            if f.endswith(".md") and f != "README.md":
                date_str = f.replace(".md", "")
                archives.append(f"- [{date_str}](daily/{f})")

    parts = [
        "# GitHub Trending Daily",
        "",
        "每日自动收集 GitHub Trending 项目，防止错过。",
        "",
        f"**最新更新：{TODAY}**",
        "",
        "---",
        "",
    ]

    # 只在 README 展示全语言 top 10
    top_repos = all_data.get(None, [])[:10]
    if top_repos:
        parts.append("## 今日热门 Top 10（全部语言）")
        parts.append("")
        parts.append("| # | 仓库 | 语言 | Star | 今日新增 | 描述 |")
        parts.append("|---|---|---|---|---|---|")
        for i, r in enumerate(top_repos, 1):
            desc = r["description"].replace("|", "\\|").replace("\n", " ")
            if len(desc) > 80:
                desc = desc[:77] + "..."
            parts.append(
                f"| {i} | [{r['repo']}]({r['url']}) | {r['language'] or '-'} | "
                f"{r['stars']} | {r['today_stars'] or '-'} | {desc} |"
            )
        parts.append("")

    parts.append("---")
    parts.append("")
    parts.append("## 历史归档")
    parts.append("")
    if archives:
        parts.extend(archives[:30])  # 最多展示最近 30 天
        if len(archives) > 30:
            parts.append(f"- ... 共 {len(archives)} 天，查看 [daily/](daily/) 目录")
    else:
        parts.append("_暂无历史数据_")
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append("## 说明")
    parts.append("")
    parts.append("- 数据来源：[GitHub Trending](https://github.com/trending)")
    parts.append("- 更新频率：每天北京时间 08:00 自动执行")
    parts.append("- 完整日报见 [daily/](daily/) 目录")
    parts.append("")

    return "\n".join(parts)


def main():
    print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] 开始爬取 GitHub Trending...")

    all_data = {}
    for lang_slug, lang_name in LANGUAGES:
        try:
            repos = fetch_trending(lang_slug)
            all_data[lang_slug] = repos
            print(f"  ✓ {lang_name}: {len(repos)} 个仓库")
        except Exception as e:
            print(f"  ✗ {lang_name}: 爬取失败 - {e}", file=sys.stderr)
            all_data[lang_slug] = []

    if not any(all_data.values()):
        print("错误：所有语言均爬取失败", file=sys.stderr)
        sys.exit(1)

    # 确保目录存在
    base_dir = os.path.dirname(os.path.abspath(__file__))
    daily_dir = os.path.join(base_dir, "daily")
    os.makedirs(daily_dir, exist_ok=True)

    # 写当天日报
    daily_path = os.path.join(daily_dir, f"{TODAY}.md")
    with open(daily_path, "w", encoding="utf-8") as f:
        f.write(generate_daily_markdown(all_data))
    print(f"  已写入: daily/{TODAY}.md")

    # 更新 README
    readme_path = os.path.join(base_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(generate_readme(all_data))
    print(f"  已更新: README.md")

    print(f"[{datetime.now(CST).strftime('%H:%M:%S')}] 完成！")


if __name__ == "__main__":
    main()
