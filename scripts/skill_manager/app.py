"""A terminal UI for listing and creating skills in the agent-plugins repo."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TextArea,
)

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

DEFAULT_AUTHOR = "everlearner"
DEFAULT_VERSION = "1.0.0"
DEFAULT_LICENSE = "MIT"

DEFAULT_CONTENT = """# My Skill

Describe what this skill does and when it should be used.

## When to Use

- Situation A
- Situation B

## Workflow

1. First step
2. Second step
3. Third step

## Examples

Show an example of the expected behavior here.
"""


def find_repo_root() -> Path | None:
    cwd = Path.cwd()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / "skills").is_dir():
            return candidate
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / "skills").is_dir():
            return candidate
    return None


def title_case(name: str) -> str:
    return name.replace("-", " ").title()


def parse_skill_md(path: Path) -> dict | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    frontmatter = parts[1]
    body = parts[2].lstrip("\n")
    try:
        meta = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict):
        return None
    metadata = meta.get("metadata") or {}
    return {
        "name": meta.get("name", path.parent.name),
        "description": meta.get("description", ""),
        "license": meta.get("license", DEFAULT_LICENSE),
        "author": metadata.get("author", "") if isinstance(metadata, dict) else "",
        "version": metadata.get("version", "") if isinstance(metadata, dict) else "",
        "_content": body,
        "_path": str(path),
    }


def list_skills(skills_dir: Path) -> list[dict]:
    if not skills_dir.is_dir():
        return []
    skills: list[dict] = []
    for entry in sorted(skills_dir.iterdir(), key=lambda p: p.name):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue
        info = parse_skill_md(skill_md)
        if info is not None:
            skills.append(info)
    return skills


def build_skill_md(data: dict) -> str:
    content = data.get("content", "").rstrip()
    if not content:
        content = (
            f"# {title_case(data['name'])}\n\n"
            "Describe what this skill does and when it should be used."
        )
    return (
        "---\n"
        f"name: {data['name']}\n"
        f"description: {data['description']}\n"
        f"license: {data['license']}\n"
        "metadata:\n"
        f"  author: {data['author']}\n"
        f'  version: "{data["version"]}"\n'
        "---\n\n"
        f"{content}\n"
    )


def upsert_marketplace(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(existing, dict):
                existing = {}
        except (OSError, json.JSONDecodeError):
            existing = {}
    else:
        existing = {}
    skills = existing.get("skills", [])
    if not isinstance(skills, list):
        skills = []
    skills = [
        s for s in skills if isinstance(s, dict) and s.get("name") != data["name"]
    ]
    skills.append(
        {
            "name": data["name"],
            "source": f"./skills/{data['name']}",
            "description": data["description"],
            "version": data["version"],
            "license": data["license"],
        }
    )
    existing["skills"] = skills
    path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


class CreateSkillScreen(Screen):
    CSS = """
    #create-form { height: 1fr; padding: 1 2; }
    #form-title { text-style: bold; text-align: center; margin-bottom: 1; color: $accent; }
    #create-form Label { margin-top: 1; }
    #create-form Input, #create-form TextArea { margin-bottom: 1; }
    #create-form TextArea { height: 12; }
    #form-actions { height: auto; align-horizontal: center; padding: 1 0; }
    #form-actions Button { margin: 0 1; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    FIELD_ORDER = ["name", "description", "author", "version", "license"]

    def __init__(self, skills_dir: Path) -> None:
        super().__init__()
        self.skills_dir = skills_dir

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="create-form"):
            yield Label("Create a New Skill", id="form-title")
            yield Label("Name (kebab-case):")
            yield Input(placeholder="my-awesome-skill", id="name")
            yield Label("Description:")
            yield Input(placeholder="What this skill does", id="description")
            yield Label("Author:")
            yield Input(value=DEFAULT_AUTHOR, id="author")
            yield Label("Version:")
            yield Input(value=DEFAULT_VERSION, id="version")
            yield Label("License:")
            yield Input(value=DEFAULT_LICENSE, id="license")
            yield Label("Instructions (markdown body):")
            yield TextArea(DEFAULT_CONTENT, id="content")
            with Horizontal(id="form-actions"):
                yield Button("Save", id="save", variant="success")
                yield Button("Cancel", id="cancel", variant="default")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Create Skill"
        self.query_one("#name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in self.FIELD_ORDER:
            idx = self.FIELD_ORDER.index(event.input.id)
            if idx + 1 < len(self.FIELD_ORDER):
                self.query_one(f"#{self.FIELD_ORDER[idx + 1]}", Input).focus()
            else:
                self.query_one("#content", TextArea).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "save":
            self._save()

    def _gather(self) -> dict:
        return {
            "name": self.query_one("#name", Input).value.strip(),
            "description": self.query_one("#description", Input).value.strip(),
            "author": self.query_one("#author", Input).value.strip(),
            "version": self.query_one("#version", Input).value.strip(),
            "license": self.query_one("#license", Input).value.strip(),
            "content": self.query_one("#content", TextArea).text.strip(),
        }

    def _save(self) -> None:
        data = self._gather()
        errors: list[str] = []
        if not data["name"]:
            errors.append("Name is required.")
        elif not NAME_RE.match(data["name"]):
            errors.append("Name must be kebab-case (lowercase letters, digits, hyphens).")
        elif (self.skills_dir / data["name"]).exists():
            errors.append(f"A skill named '{data['name']}' already exists.")
        if not data["description"]:
            errors.append("Description is required.")
        if not data["author"]:
            errors.append("Author is required.")
        if not data["license"]:
            errors.append("License is required.")
        if not VERSION_RE.match(data["version"]):
            errors.append("Version must look like X.Y.Z (e.g. 1.0.0).")
        if errors:
            for err in errors:
                self.app.notify(err, severity="error", timeout=5)
            return
        self.dismiss(data)


class SkillDetailScreen(Screen):
    CSS = """
    #detail-scroll { height: 1fr; padding: 1 2; }
    #detail-text { width: 1fr; }
    """

    BINDINGS = [Binding("escape", "app.pop_screen", "Back")]

    def __init__(self, skill: dict) -> None:
        super().__init__()
        self.skill = skill

    def compose(self) -> ComposeResult:
        s = self.skill
        header = "\n".join(
            [
                f"# {s.get('name', '')}",
                "",
                f"  Version : {s.get('version', '')}",
                f"  Author  : {s.get('author', '')}",
                f"  License : {s.get('license', '')}",
                f"  Path    : {s.get('_path', '')}",
                "",
                s.get("description", ""),
                "",
                "─" * 60,
                "",
            ]
        )
        text = header + "\n" + s.get("_content", "")
        with VerticalScroll(id="detail-scroll"):
            yield Static(text, id="detail-text", markup=False)
        yield Footer()


class SkillManagerApp(App):
    CSS = """
    #main { height: 1fr; }
    #skills-table { height: 1fr; }
    """

    TITLE = "Skill Manager"

    BINDINGS = [
        Binding("n", "new_skill", "New"),
        Binding("r", "refresh", "Refresh"),
        Binding("enter", "view", "View", priority=True),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, repo_root: Path) -> None:
        super().__init__()
        self.repo_root = repo_root
        self.skills_dir = repo_root / "skills"
        self.crush_marketplace = repo_root / ".crush" / "marketplace.json"
        self._skills: list[dict] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main"):
            yield DataTable(id="skills-table")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = str(self.repo_root)
        table = self.query_one("#skills-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "Version", "Author", "License", "Description")
        self.action_refresh()

    def action_refresh(self) -> None:
        self._skills = list_skills(self.skills_dir)
        table = self.query_one("#skills-table", DataTable)
        table.clear()
        for s in self._skills:
            table.add_row(
                s.get("name", ""),
                s.get("version", ""),
                s.get("author", ""),
                s.get("license", ""),
                s.get("description", ""),
                key=s.get("name"),
            )
        self.notify(f"Loaded {len(self._skills)} skill(s).")

    def action_view(self) -> None:
        table = self.query_one("#skills-table", DataTable)
        if table.row_count == 0:
            return
        idx = table.cursor_row
        if idx is None or idx < 0:
            return
        try:
            row = table.get_row_at(idx)
        except Exception:
            return
        name = row[0]
        skill = next((s for s in self._skills if s.get("name") == name), None)
        if skill:
            self.push_screen(SkillDetailScreen(skill))

    def action_new_skill(self) -> None:
        self.push_screen(CreateSkillScreen(self.skills_dir), self._on_created)

    def _on_created(self, data: dict | None) -> None:
        if not data:
            return
        self._create_skill(data)

    def _create_skill(self, data: dict) -> None:
        skill_dir = self.skills_dir / data["name"]
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(build_skill_md(data), encoding="utf-8")
        upsert_marketplace(self.crush_marketplace, data)
        self.notify(
            f"Created skill '{data['name']}' (also updated .crush/marketplace.json).",
            severity="success",
            timeout=4,
        )
        self.action_refresh()


def main() -> None:
    repo = find_repo_root()
    if repo is None:
        print(
            "Error: could not locate the project root (no 'skills/' directory found).",
            file=sys.stderr,
        )
        print("Run this tool from within the agent-plugins repository.", file=sys.stderr)
        sys.exit(1)
    app = SkillManagerApp(repo)
    app.run()


if __name__ == "__main__":
    main()
