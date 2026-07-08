# Skill Manager

A terminal UI (TUI) for listing existing skills and interactively creating new
skills in this `agent-plugins` repository. Built with [Textual](https://textual.textualize.io/)
and managed with [uv](https://docs.astral.sh/uv/).

## Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) installed

## Usage

Run from the `scripts/` directory (uv will create the environment and install
dependencies automatically):

```bash
uv run skill-manager
```

Alternatively, from anywhere inside the repository:

```bash
uv run python -m skill_manager.app
```

If you want a stable, pre-installed environment, sync once first:

```bash
uv sync
uv run skill-manager
```

## Key bindings

| Key       | Action                                  |
|-----------|-----------------------------------------|
| `n`       | Create a new skill (interactive form)   |
| `enter`   | View the selected skill's details       |
| `r`       | Refresh the skill list                  |
| `q`       | Quit                                    |
| `escape`  | Back / Cancel (in sub-screens)          |

## What it does

### Listing skills

On startup the app scans `<repo>/skills/*/SKILL.md`, parses the YAML
frontmatter (`name`, `description`, `license`, `metadata.author`,
`metadata.version`) and shows a table of all skills. Press `enter` to read a
skill's full content.

### Creating a skill

Press `n` to open a form. The fields map directly to the `SKILL.md` frontmatter
defined in the repository's `AGENTS.md`:

- **Name** — kebab-case identifier (e.g. `my-awesome-skill`)
- **Description** — short description of when to use the skill
- **Author** — defaults to `everlearner`
- **Version** — semver `X.Y.Z`, defaults to `1.0.0`
- **License** — defaults to `MIT`
- **Instructions** — the markdown body (workflow, examples, etc.)

On save the tool:

1. Creates `skills/<name>/SKILL.md` with the correct frontmatter + body.
2. Adds the skill entry to `.crush/marketplace.json` (creating the file if it
   does not exist, or replacing an existing entry with the same name).
3. Refreshes the list.

Validation prevents empty required fields, bad name formats, version strings
that aren't `X.Y.Z`, and skill names that already exist.

> Note: `.crush/` is currently listed in `.gitignore`. If you want the
> generated `.crush/marketplace.json` to be tracked in git, adjust
> `.gitignore` accordingly (e.g. add an exception for `.crush/marketplace.json`).
