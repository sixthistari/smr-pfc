# Stanmore PFC — Design Specification

These files define the requirements, standards, and architecture for the Stanmore PFC (Pre-Frontal Cortex) — the Enterprise Architect's operational layer for the Stanmore Intelligence System (SIS Brain).

## Files

| File | Purpose | Read Order |
|---|---|---|
| `BUILD-INSTRUCTIONS.md` | **Start here.** How to approach building. Step-by-step build order. | 1 |
| `REQUIREMENTS.md` | Full requirements specification. What to build, in detail. | 2 |
| `ARCHITECTURE-DECISIONS.md` | Constraints and design choices. Why things are the way they are. | 3 |
| `STANDARDS.md` | Coding standards, project structure, testing requirements. | 4 |
| `SYSTEM-PROMPT.md` | Draft system prompt for the chat agent. Domain context for the LLM. | 5 |

## How to Use

1. Copy these files into the `/design` folder of the PFC project
2. Point Claude Code at the project root
3. Tell Claude Code: "Read all files in /design/ before starting. Build Phase 0 following BUILD-INSTRUCTIONS.md."
4. Review and iterate

## Key Architecture Decisions

- **Chat = Anthropic Messages API + Chainlit + MCP** (not Agent SDK)
- **Batch = Claude Agent SDK** (file in, file out, pipeline triggered)
- **PFC repo = source of truth** (git-native: wiki + YAML + SQLite)
- **Orbus iServer = system of record** (receives syndicated ArchiMate XML; PFC → Orbus, never reverse)
- **Entity extraction = cross-cutting concern** (every agent extracts, not a separate job)
- **ArchiMate Motivation layer for needs/requirements** (not JTBD — use native ArchiMate types)
- **Provenance-first staging** (every structured output carries conversation context)
- **Practice artefacts are first-class** (principles, standards, decisions, NFRs, ideas, strategies in the EA repo)
- **No framework abstractions** (no LangChain, no LlamaIndex — direct API calls)

## Owner

Justin Hume — Enterprise Architect, AI & Advanced Analytics
Stanmore Resources | Technology — Enterprise Systems
