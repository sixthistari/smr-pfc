# smr-pfc

Stanmore PFC (Pre-Frontal Cortex) — Enterprise Architect operational workbench for the Stanmore Intelligence System (SIS Brain).

## Quick Start

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest tests/

# Start chat interface
uv run chainlit run src/ea_workbench/chat/app.py
```

## Project Structure

```
smr-pfc/
├── CLAUDE.md               # Claude Code instructions (read automatically)
├── .claude/settings.json   # Claude Code permission allow-list
├── design/                 # Specification documents (read-only reference)
├── src/ea_workbench/       # Application code
├── tests/                  # Pytest test suite
├── stanmore-pfc/           # EA knowledge base (capabilities, elements, specs, staging)
├── pyproject.toml          # uv project config
└── chainlit.md             # Chat interface welcome message
```

## Building with Claude Code

```bash
claude --model opusplan
# Then: "Read all files in /design/. Build Phase 0 following BUILD-INSTRUCTIONS.md."
# Press Shift+Tab for auto-accept edits mode.
```

See `design/BUILD-INSTRUCTIONS.md` for the full build sequence.

## Owner

Justin Hume — Enterprise Architect, AI & Advanced Analytics
Stanmore Resources | Technology — Enterprise Systems
