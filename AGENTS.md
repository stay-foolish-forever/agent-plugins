# Agent Plugins Repository

This is a plugin repository for Claude Code CLI. It contains a collection of plugins that add custom commands to Claude Code.

## Repository Structure

```
agent-plugins/
├── .claude-plugin/
│   └── marketplace.json          # Marketplace metadata (name, owner, plugin list)
└── plugins/
    └── <plugin-name>/
        ├── .claude-plugin/
        │   └── plugin.json       # Plugin metadata (name, version, commands path)
        └── commands/
            └── <command>.md      # Command definitions with YAML frontmatter
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

## No Build Process

This repository has no build, test, or lint commands. Plugins are static configuration files consumed directly by Claude Code.