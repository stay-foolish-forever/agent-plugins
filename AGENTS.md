# Agent Plugins Repository

This is a plugin repository for Claude Code CLI and Crush. It contains a collection of plugins and skills that add custom commands and capabilities.

## Repository Structure

```
agent-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Plugin marketplace metadata (name, owner, plugin list)
├── .crush/
│   └── marketplace.json          # Skills marketplace metadata (name, owner, skills list)
├── plugins/
│   └── <plugin-name>/
│       ├── .claude-plugin/
│       │   └── plugin.json       # Plugin metadata (name, version, commands path)
│       └── commands/
│           └── <command>.md      # Command definitions with YAML frontmatter
└── skills/
    └── <skill-name>/
        └── SKILL.md               # Skill definition with YAML frontmatter
```

## Adding a New Plugin

1. Create directory: `plugins/<plugin-name>/`
2. Create `.claude-plugin/plugin.json`:
   ```json
   {
     "name": "<plugin-name>",
     "description": "<brief description>",
     "version": "1.0.0",
     "commands": "./commands"
   }
   ```
3. Create `commands/` directory with markdown files for each command
4. Add plugin entry to root `.claude-plugin/marketplace.json`

## Command File Format

Commands are markdown files with YAML frontmatter:

```markdown
---
allowed-tools: Bash(echo *), Read
description: Brief description of what the command does
---

## Command Title

Your prompt content here. Can include embedded bash commands:
!`echo $RANDOM`
```

### Frontmatter Fields

- **allowed-tools**: Restricts which tools this command can use. Format is comma-separated list. Bash patterns use glob syntax: `Bash(echo *)` allows echo with any arguments.
- **description**: Short description shown to users when listing available commands

### Embedded Commands

Use the `!` syntax to embed bash command output:
```
!`echo $RANDOM`
```

The command output is injected into the prompt at that location.

## Conventions

- Plugin names use kebab-case (e.g., `fortune-telling-plugin`)
- Command files use kebab-case matching the command name (e.g., `fortune-telling.md`)
- Descriptions should be concise but informative
- Commands are prompts, not code - they guide Claude's behavior

## Skills

Skills are reusable prompt templates for Crush CLI that can be installed via `npx skills add`.

### Installing Skills

Users can install skills from this repository using:

```bash
npx skills add everlearner/agent-plugins#skills/fortune-telling
```

Or install all skills at once:

```bash
npx skills add everlearner/agent-plugins
```

### Adding a New Skill

1. Create directory: `skills/<skill-name>/`
2. Create `SKILL.md` with YAML frontmatter:
   ```markdown
   ---
   name: <skill-name>
   description: Brief description of what the skill does
   license: MIT
   metadata:
     author: your-name
     version: "1.0.0"
   ---

   # Skill Title

   Instructions for the skill...
   ```
3. Add skill entry to `.crush/marketplace.json`:
   ```json
   {
     "skills": [
       {
         "name": "<skill-name>",
         "source": "./skills/<skill-name>",
         "description": "<brief description>",
         "version": "1.0.0",
         "license": "MIT"
       }
     ]
   }
   ```

### SKILL.md Frontmatter Fields

- **name**: Skill identifier (required)
- **description**: Short description shown to users (required)
- **license**: License identifier (optional, default: MIT)
- **metadata**: Additional metadata like author and version (optional)

### Skill Content

The body of `SKILL.md` contains instructions that guide the AI's behavior. Include:
- Clear description of when to use the skill
- Step-by-step workflow or commands to execute
- Examples of expected output
- Any prerequisites or gotchas

## No Build Process

This repository has no build, test, or lint commands. Plugins and skills are static configuration files consumed directly by Claude Code and Crush.