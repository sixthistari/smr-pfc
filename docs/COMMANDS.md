# EA Workbench — Slash Command Reference

All commands are entered in the Chainlit chat interface.

## Command Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `/help` | Show all commands | `/help` |
| `/run <agent> [input]` | Execute a registered agent | `/run adr-generator "Use PostgreSQL for registry"` |
| `/triage` | Review and approve staged entity files | `/triage` |
| `/staging` | Show staging area file counts | `/staging` |
| `/status` | Show recent agent run summaries | `/status` |
| `/health` | Show latest wiki integrity check results | `/health` |
| `/capabilities` | Show capability model summary | `/capabilities` |
| `/analytics` | Show practice artefact analytics | `/analytics` |
| `/capture <type> <domain>` | Scaffold a motivation record | `/capture need safety` |
| `/migrate` | Migrate Phase 0 data to Option C schema | `/migrate` |
| `/wrap` | Generate and persist a session summary | `/wrap` |

## Agent IDs for `/run`

See [AGENTS.md](AGENTS.md) for the full list. Common examples:

```
/run transcript-classifier stanmore-pfc/.staging/entities/meeting-2026-03-01.txt
/run adr-generator "Use Azure Cosmos DB for the knowledge store"
/run wiki-integrity .
/run weekly-summary .
/run architecture-review path/to/pr-diff.patch
/run spec-decomposition stanmore-pfc/specs/safety-agent.md
```

## Capture Types

`/capture` scaffolds a YAML template in the chat for you to fill in:

| Type | Produces |
|------|----------|
| `need` | ArchiMate Goal/Need record |
| `requirement` | ArchiMate Requirement record |
| `engagement` | Stakeholder Engagement record |

## Triage Flow

1. Agents write staged entities to `.staging/entities/*.yaml`
2. `/triage` presents each file with **Approve** / **Reject** action buttons
3. **Approve** routes entities to the correct Option C concern table in `registry.db`
4. **Reject** deletes the staging file

The `/staging` command shows how many files are waiting in each staging subdirectory.
