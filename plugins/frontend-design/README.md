# frontend-design

Opinionated frontend design skill for Claude Code. Replaces the generic built-in `frontend-design` skill with a concrete design system anchored on curated reference sites.

## What it does

When Claude builds frontend interfaces, it defaults to generic "AI slop" — Inter font, purple gradients, excessive shadows, rounded everything. This skill overrides those defaults with a specific, opinionated design system derived from sites like **Bluesky**, **GitHub**, **Gmail**, **LessWrong**, and **Claude.ai**.

### Design philosophy

- **Dark mode by default** — dark backgrounds (#0d1117), off-white text (#e6edf3), never pure white
- **Information-dense** — 14px base font, compact spacing, sidebar navigation
- **Flat and quiet** — no shadows, no gradients, depth via background color layering
- **System fonts** — no Google Fonts, no web font loading
- **Single muted accent** — one blue (#58a6ff), not Material's rainbow
- **Content-focused** — minimal decoration, structural borders only

### What's included

- **Design tokens**: Complete CSS custom properties and Tailwind config for colors, typography, spacing, and layout
- **Component patterns**: Sidebar nav, cards, lists/feeds, buttons, forms, tables, command palette
- **Anti-pattern table**: 14 common "LLM-default" mistakes and their corrections
- **Implementation checklist**: Pre-ship verification list
- **Escape hatches**: When and how to use light theme, serif fonts, or editorial styles

## Installation

```bash
claude plugin marketplace add https://github.com/Jython1415/jshoes-claude-plugins
claude plugin install frontend-design@jshoes-claude-plugins --scope user
```

## Requirements

- Claude Code CLI

## Author

**Jython1415** — [github.com/Jython1415](https://github.com/Jython1415)
