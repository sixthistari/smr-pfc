# EA Workbench — Stanmore PFC

**EA Workbench** is an AI-assisted Enterprise Architecture tool purpose-built for Stanmore Resources' Process, Fleet & Control (PFC) programme. It combines a structured ArchiMate repository with a suite of Claude-powered agents that help architects capture decisions, analyse capabilities, generate compliance reports, and keep the wiki consistent — all through a conversational chat interface.

The workbench is not a replacement for architect judgment. Every agent output is staged for human review before it lands in the registry. The `/review` flow is the human gate.

## Quick Start

1. Launch: `uv run chainlit run src/ea_workbench/chat/app.py`
2. Open `http://localhost:8000` in your browser
3. Type `/help` to see all available commands
4. Start a session: paste a transcript → `/run transcript-classifier <path>` → `/triage`

## Documentation

| Page | Contents |
|------|----------|
| [COMMANDS.md](COMMANDS.md) | Complete slash-command reference |
| [AGENTS.md](AGENTS.md) | Agent catalogue — use cases, inputs, outputs |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Schema overview, staging pipeline, key concepts |
| [WORKFLOWS.md](WORKFLOWS.md) | End-to-end workflow guides |

## Workspace Layout

```
stanmore-pfc/
├── .agents/         Agent configuration, prompts, and pipelines
│   ├── config.yaml  Agent registry (model, prompt, tools per agent)
│   ├── prompts/     System prompts (.md, one per agent)
│   ├── pipelines/   Pipeline trigger definitions
│   └── runs/        Agent run manifests (JSON)
├── .staging/        Pending items awaiting human review
│   ├── entities/    Staged ArchiMate elements (YAML)
│   ├── sessions/    Session records
│   └── approved/    Reviewed and accepted items
├── architecture/    EA practice artefacts (principles, ADRs, standards, NFRs)
├── output/          Agent output files (reports, exports, specs)
└── registry.db      SQLite element registry (Option C schema)
```
