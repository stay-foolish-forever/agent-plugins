#!/usr/bin/env python3
"""
自动列出当前仓库支持的 Skills 和 Plugins 安装方式以及对应的安装命令。

数据来源：
  - Plugins:  .claude-plugin/marketplace.json  +  plugins/<name>/.claude-plugin/plugin.json
  - Skills :  .crush/marketplace.json          +  skills/<name>/SKILL.md (YAML frontmatter)
  - 外部 Skills: skills-lock.json (通过 npx skills add 安装的外部 skill)

用法:
  python3 scripts/list_skills_plugins.py            # 表格形式（默认）
  python3 scripts/list_skills_plugins.py --json     # JSON 格式输出
  python3 scripts/list_skills_plugins.py --markdown # Markdown 格式输出
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# 仓库信息
# ---------------------------------------------------------------------------


def get_repo_root() -> Path:
    """返回 git 仓库根目录。"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"❌ 无法确定 git 仓库根目录: {exc}", file=sys.stderr)
        sys.exit(1)


def get_github_repo(repo_root: Path) -> str | None:
    """从 git remote origin 解析出 '<owner>/<repo>' 形式的 GitHub 仓库标识。"""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        url = result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

    # SSH:  git@github.com:owner/repo.git
    ssh_match = re.match(r"git@github\.com:(.+?)(?:\.git)?$", url)
    if ssh_match:
        return ssh_match.group(1)

    # HTTPS: https://github.com/owner/repo.git
    https_match = re.match(r"https?://github\.com/(.+?)(?:\.git)?$", url)
    if https_match:
        return https_match.group(1)

    return None


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------


@dataclass
class PluginInfo:
    name: str
    description: str
    version: str
    license: str
    source: str
    install_command: str
    install_method: str = "Claude Code Plugin"


@dataclass
class SkillInfo:
    name: str
    description: str
    version: str
    license: str
    source: str
    install_command: str
    install_method: str = "Crush Skill (npx skills add)"
    external: bool = False  # 是否为外部 skill（来自 skills-lock.json）


@dataclass
class RepoSummary:
    repo_root: Path
    github_repo: str | None
    plugins: list[PluginInfo] = field(default_factory=list)
    skills: list[SkillInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 解析工具
# ---------------------------------------------------------------------------


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_yaml_frontmatter(text: str) -> dict[str, Any]:
    """非常轻量的 YAML frontmatter 解析器，仅支持本仓库使用的简单结构。

    支持的特性：
      - 顶层 `key: value`
      - 带引号的字符串 `key: "value"`
      - 字典 `key:` 后跟缩进的子字段
      - 块标量 `key: >` 后跟缩进的多行文本（折叠为单行）
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        return {}

    frontmatter: dict[str, Any] = {}
    current_key: str | None = None
    current_dict: dict[str, Any] | None = None
    block_lines: list[str] = []  # 用于收集 > 块标量的多行内容
    in_block: bool = False  # 是否正在收集 > 块标量

    def finalize_block() -> None:
        """把收集到的块标量多行内容折叠为单行并写入 frontmatter。"""
        nonlocal current_key, block_lines, in_block
        if current_key is not None and block_lines:
            # YAML 折叠标量：把换行替换为空格，并去除首尾空白
            folded = " ".join(line.strip() for line in block_lines if line.strip())
            frontmatter[current_key] = folded
        block_lines = []
        in_block = False

    for line in match.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            # 空行在块标量中作为段落分隔，这里简化为忽略
            continue

        # 正在收集 > 块标量内容（后续缩进行）
        if in_block and line.startswith("  "):
            block_lines.append(line)
            continue

        # 块标量结束（遇到非缩进行）
        if in_block:
            finalize_block()

        # 缩进行 -> metadata 子字段
        if line.startswith("  ") and current_key and current_dict is not None:
            sub_match = re.match(r"\s+(\w+):\s*(.*)$", line)
            if sub_match:
                key, value = sub_match.group(1), sub_match.group(2).strip()
                # 去除引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                current_dict[key] = value
            continue

        # 顶层 key: value
        top_match = re.match(r"^(\w+):\s*(.*)$", line)
        if top_match:
            key, value = top_match.group(1), top_match.group(2).strip()

            if value == "":
                # 字典
                current_key = key
                current_dict = {}
                frontmatter[key] = current_dict
                continue

            if value == ">":
                # 块标量开始，后续缩进行会被收集
                current_key = key
                block_lines = []
                in_block = True
                frontmatter[key] = ""
                continue

            # 去除引号
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]

            frontmatter[key] = value
            current_key = key
            current_dict = None

    # 文件结束时若仍在收集块标量，做收尾
    if in_block:
        finalize_block()

    return frontmatter


# ---------------------------------------------------------------------------
# 收集 Plugins
# ---------------------------------------------------------------------------


def collect_plugins(repo_root: Path, github_repo: str | None) -> list[PluginInfo]:
    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.exists():
        return []

    marketplace = load_json(marketplace_path)
    plugins: list[PluginInfo] = []

    for entry in marketplace.get("plugins", []):
        name = entry.get("name", "")
        source = entry.get("source", "")
        description = entry.get("description", "")
        version = entry.get("version", "")
        license_ = entry.get("license", "MIT")

        # 安装命令：Claude Code 插件通过 marketplace 安装
        if github_repo:
            install_cmd = (
                f"claude plugin install {github_repo} --plugin {name}"
            )
        else:
            install_cmd = f"claude plugin install <repo> --plugin {name}"

        plugins.append(
            PluginInfo(
                name=name,
                description=description,
                version=version,
                license=license_,
                source=source,
                install_command=install_cmd,
            )
        )

    return plugins


# ---------------------------------------------------------------------------
# 收集 Skills
# ---------------------------------------------------------------------------


def collect_local_skills(repo_root: Path, github_repo: str | None) -> list[SkillInfo]:
    """收集本仓库内的 skills（来自 .crush/marketplace.json）。"""
    marketplace_path = repo_root / ".crush" / "marketplace.json"
    if not marketplace_path.exists():
        return []

    marketplace = load_json(marketplace_path)
    skills: list[SkillInfo] = []

    for entry in marketplace.get("skills", []):
        name = entry.get("name", "")
        source = entry.get("source", "")
        description = entry.get("description", "")
        version = entry.get("version", "")
        license_ = entry.get("license", "MIT")

        # 安装命令：npx skills add <owner>/<repo>#<path>
        if github_repo:
            install_cmd = f"npx skills add {github_repo}#{source.lstrip('./')}"
        else:
            install_cmd = f"npx skills add <repo>#{source.lstrip('./')}"

        skills.append(
            SkillInfo(
                name=name,
                description=description,
                version=version,
                license=license_,
                source=source,
                install_command=install_cmd,
            )
        )

    return skills


def collect_external_skills(repo_root: Path) -> list[SkillInfo]:
    """收集通过 skills-lock.json 记录的外部 skills。"""
    lock_path = repo_root / "skills-lock.json"
    if not lock_path.exists():
        return []

    lock = load_json(lock_path)
    skills: list[SkillInfo] = []

    for name, info in lock.get("skills", {}).items():
        source = info.get("source", "")
        source_type = info.get("sourceType", "github")
        skill_path = info.get("skillPath", "SKILL.md")

        # 读取 SKILL.md 获取描述/版本/许可证
        description = ""
        version = ""
        license_ = "Unknown"
        skill_md_path = repo_root / ".agents" / "skills" / name / "SKILL.md"
        if skill_md_path.exists():
            text = skill_md_path.read_text(encoding="utf-8")
            fm = parse_yaml_frontmatter(text)
            description = fm.get("description", "")
            version = str(fm.get("metadata", {}).get("version", "")) if isinstance(
                fm.get("metadata"), dict
            ) else ""
            license_ = fm.get("license", "Unknown")

        # 安装命令：npx skills add <source>
        if source_type == "github":
            install_cmd = f"npx skills add {source}"
        else:
            install_cmd = f"npx skills add {source}"

        skills.append(
            SkillInfo(
                name=name,
                description=description,
                version=version,
                license=license_,
                source=source,
                install_command=install_cmd,
                external=True,
                install_method="External Skill (npx skills add)",
            )
        )

    return skills


# ---------------------------------------------------------------------------
# 输出格式化
# ---------------------------------------------------------------------------


def render_table(summary: RepoSummary) -> str:
    lines: list[str] = []
    lines.append("=" * 80)
    lines.append(f"📦 仓库: {summary.repo_root.name}")
    if summary.github_repo:
        lines.append(f"   GitHub: {summary.github_repo}")
    lines.append("=" * 80)

    # Plugins
    lines.append("")
    lines.append(f"🔌 Plugins ({len(summary.plugins)})")
    lines.append("-" * 80)
    if not summary.plugins:
        lines.append("  （无）")
    for p in summary.plugins:
        lines.append(f"  • {p.name}  v{p.version}  [{p.license}]")
        lines.append(f"    描述: {p.description}")
        lines.append(f"    来源: {p.source}")
        lines.append(f"    安装方式: {p.install_method}")
        lines.append(f"    安装命令: {p.install_command}")
        lines.append("")

    # Skills
    lines.append(f"🧩 Skills ({len(summary.skills)})")
    lines.append("-" * 80)
    if not summary.skills:
        lines.append("  （无）")
    for s in summary.skills:
        tag = " [external]" if s.external else ""
        lines.append(f"  • {s.name}  v{s.version}  [{s.license}]{tag}")
        lines.append(f"    描述: {s.description}")
        lines.append(f"    来源: {s.source}")
        lines.append(f"    安装方式: {s.install_method}")
        lines.append(f"    安装命令: {s.install_command}")
        lines.append("")

    return "\n".join(lines)


def render_markdown(summary: RepoSummary) -> str:
    lines: list[str] = []
    lines.append(f"# {summary.repo_root.name} - Skills & Plugins")
    lines.append("")
    if summary.github_repo:
        lines.append(f"**GitHub 仓库:** [{summary.github_repo}](https://github.com/{summary.github_repo})")
        lines.append("")

    # Plugins
    lines.append(f"## 🔌 Plugins ({len(summary.plugins)})")
    lines.append("")
    if not summary.plugins:
        lines.append("_无_")
    else:
        lines.append("| 名称 | 版本 | 许可证 | 描述 | 安装命令 |")
        lines.append("|------|------|--------|------|----------|")
        for p in summary.plugins:
            desc = p.description.replace("|", "\\|")
            lines.append(
                f"| `{p.name}` | {p.version} | {p.license} | {desc} | `{p.install_command}` |"
            )
    lines.append("")

    # Skills
    lines.append(f"## 🧩 Skills ({len(summary.skills)})")
    lines.append("")
    if not summary.skills:
        lines.append("_无_")
    else:
        lines.append("| 名称 | 版本 | 许可证 | 描述 | 安装命令 |")
        lines.append("|------|------|--------|------|----------|")
        for s in summary.skills:
            desc = s.description.replace("|", "\\|")
            tag = " 🔗" if s.external else ""
            lines.append(
                f"| `{s.name}`{tag} | {s.version} | {s.license} | {desc} | `{s.install_command}` |"
            )
    lines.append("")
    lines.append("> 🔗 标记表示来自外部仓库的 skill。")

    return "\n".join(lines)


def render_json(summary: RepoSummary) -> str:
    data = {
        "repo": summary.repo_root.name,
        "github": summary.github_repo,
        "plugins": [p.__dict__ for p in summary.plugins],
        "skills": [s.__dict__ for s in summary.skills],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="列出当前仓库支持的 Skills 和 Plugins 安装方式及命令"
    )
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "--json", action="store_true", help="以 JSON 格式输出"
    )
    format_group.add_argument(
        "--markdown", action="store_true", help="以 Markdown 格式输出"
    )
    args = parser.parse_args()

    repo_root = get_repo_root()
    github_repo = get_github_repo(repo_root)

    summary = RepoSummary(repo_root=repo_root, github_repo=github_repo)
    summary.plugins = collect_plugins(repo_root, github_repo)
    summary.skills = collect_local_skills(repo_root, github_repo)
    summary.skills.extend(collect_external_skills(repo_root))

    if args.json:
        print(render_json(summary))
    elif args.markdown:
        print(render_markdown(summary))
    else:
        print(render_table(summary))

    return 0


if __name__ == "__main__":
    sys.exit(main())
