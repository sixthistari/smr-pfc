# Stanmore PFC — Claude Code Instructions

## Before Writing Any Code

Read ALL files in `/design/` first. They are the specification for this project.

- `BUILD-INSTRUCTIONS.md` — **Start here.** Step-by-step build order.
- `REQUIREMENTS.md` — Full requirements specification. What to build.
- `ARCHITECTURE-DECISIONS.md` — Why things are the way they are.
- `STANDARDS.md` — Coding standards, module dependency rules, violations list.
- `SYSTEM-PROMPT.md` — Draft system prompt for the chat agent.

## Key Rules

- **Australian English** spelling throughout (organisation, colour, behaviour).
- **Module dependency DAG** is strictly enforced. See STANDARDS.md § Module Dependency Rules.
- **Pydantic v2** only. `model_dump()` not `.dict()`. `model_validate()` not `.parse_obj()`.
- **No framework abstractions.** No LangChain, LlamaIndex, or Semantic Kernel.
- **No ORM.** Use aiosqlite with raw SQL. No SQLAlchemy.
- **Async-first.** All I/O operations must be async.
- **Files are the interface.** Agents read and write files. The filesystem is the integration layer.
- **System prompts are configuration.** They live in `.agents/prompts/*.md`, not in code.
- **Schema validation at boundaries.** All outputs validate against Pydantic models before disk write.
- **Run tests after every change.** `uv run pytest tests/` must pass before moving on.

## Build Order

Follow BUILD-INSTRUCTIONS.md Phase 0, steps 1-11 in exact order.
Each step must work before moving to the next.

## Project Layout

- `src/ea_workbench/` — Application code
- `tests/` — Pytest test suite
- `design/` — Specification documents (read-only reference)
- `stanmore-pfc/` — EA knowledge base (the PFC repo content — capabilities, elements, specs, staging)
