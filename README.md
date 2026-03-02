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

## DevOps Configuration

### PFC Link Custom Field (Manual Step — DevOps Admin)

To enable bidirectional traceability between Stanmore PFC conversations and DevOps work items,
add a custom field called **"PFC Link"** to DevOps work item types:

1. Go to **Azure DevOps → Organisation Settings → Process**
2. Select your process (Agile / Scrum / etc.)
3. Navigate to the work item type (Task, Bug, User Story, Issue)
4. Add a new field:
   - **Field name**: `PFC Link`
   - **Field type**: `String` or `URL`
   - **Display name**: `PFC Link`
5. Repeat for each work item type used by the Technology — Enterprise Systems team
6. Place the field in the **Details** tab for visibility

**Usage**: When the PFC pushes a staged work item to DevOps via `/triage`, the field is
populated with the Chainlit session URL (e.g. `http://localhost:8000/chat/abc123`).
This allows any team member to launch a contextual chat session directly from the work item.

**DevOps → PFC URL pattern**:
```
http://<pfc-host>/chat?init=devops-item&id={{System.Id}}
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | _(required)_ |
| `AZURE_OPENAI_ENDPOINT` | Azure AI Foundry endpoint (overrides Anthropic) | _(optional)_ |
| `PFC_WORKSPACE` | Path to stanmore-pfc knowledge base | `./stanmore-pfc` |
| `DEFAULT_MODEL` | Default LLM model | `claude-sonnet-4-6` |
| `FAST_MODEL` | Fast model for extraction tasks | `gemini-2.5-flash` |
| `CHAINLIT_DB_URI` | SQLAlchemy URI for session persistence | `sqlite:///./sessions.db` |
| `REGISTRY_DB_PATH` | Path to element registry SQLite DB | `stanmore-pfc/elements/registry.db` |

## Owner

Justin Hume — Enterprise Architect, AI & Advanced Analytics
Stanmore Resources | Technology — Enterprise Systems
