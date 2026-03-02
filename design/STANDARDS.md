# EA Workbench — Coding Standards

These standards govern all Python code in the EA Workbench. Claude Code must follow these when implementing.

---

## Python Standards

### Version and Tooling

- **Python**: 3.12+
- **Package manager**: `uv` (not pip, not poetry)
- **Formatter**: `ruff format`
- **Linter**: `ruff check`
- **Type checking**: `pyright` in strict mode
- **Testing**: `pytest` with `pytest-asyncio` for async tests

### Project Structure

```
ea-workbench/
├── pyproject.toml              # uv project config
├── .python-version             # 3.12
├── src/
│   └── ea_workbench/
│       ├── __init__.py
│       ├── chat/               # Chainlit app and chat agent logic
│       │   ├── app.py          # Chainlit entry point
│       │   ├── handlers.py     # Message and MCP handlers
│       │   └── commands.py     # Slash command implementations
│       ├── agents/             # Batch agent implementations
│       │   ├── base.py         # Common agent runner contract
│       │   ├── runner.py       # Agent execution and manifest writing
│       │   ├── adr_generator.py
│       │   ├── wiki_integrity.py
│       │   ├── design_guardrail.py
│       │   ├── spec_decomposition.py
│       │   ├── transcript_classifier.py
│       │   └── ...             # One module per agent
│       ├── extraction/         # Entity extraction protocol
│       │   ├── extractor.py    # Staging file writer
│       │   ├── schemas.py      # Pydantic models for entities/relationships
│       │   ├── export.py       # ArchiMate XML generator
│       │   └── review.py       # Staging approval workflow helpers
│       ├── registry/           # Element registry (SQLite)
│       │   ├── db.py           # Database connection and migrations
│       │   ├── queries.py      # Common query functions
│       │   └── mcp_server.py   # Custom MCP server wrapping registry
│       ├── models/             # Pydantic models (shared)
│       │   ├── elements.py
│       │   ├── capabilities.py
│       │   ├── manifests.py
│       │   └── config.py
│       └── utils/
│           ├── yaml_loader.py  # Safe YAML loading for capability model, glossary
│           ├── git.py          # Git operations (diff, commit, push)
│           └── archimate.py    # ArchiMate XML generation utilities
├── tests/
│   ├── test_agents/
│   ├── test_extraction/
│   ├── test_registry/
│   └── fixtures/               # Sample specs, transcripts, etc.
├── .chainlit/
│   └── config.toml
└── chainlit.md                 # Welcome message
```

### Code Style

- **Async-first**: All I/O operations (LLM calls, file reads, DB queries, MCP calls) must be async. Use `asyncio` and `aiofiles`.
- **Type hints everywhere**: All function signatures must have full type annotations. Use `str | None` not `Optional[str]`.
- **Pydantic for data models**: All structured data (manifests, entities, relationships, config) must be Pydantic BaseModel subclasses. Use Pydantic v2.
- **No classes where functions suffice**: Don't create classes for agents. Agents are async functions that accept typed config and return typed results. The `base.py` module defines the contract as a Protocol, not an abstract base class.
- **Docstrings**: Google style. Required on all public functions. Not required on private helpers if the name is self-explanatory.
- **Error handling**: Never bare `except`. Always catch specific exceptions. LLM call failures must be caught and recorded in the run manifest (status: "failed", error: description).
- **No print statements**: Use `logging` module. Structured logging (JSON) for batch agents. Chainlit's built-in logging for chat.

### Naming Conventions

- **Files**: `snake_case.py`
- **Functions**: `snake_case`
- **Classes** (Pydantic models only): `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Agent IDs**: `kebab-case` (matching config.yaml keys)

### Dependencies (Minimal)

Core:
- `chainlit` — chat UI
- `anthropic` — Messages API client
- `claude-agent-sdk` — batch agent execution
- `pydantic` >= 2.0 — data models
- `aiosqlite` — async SQLite access
- `pyyaml` — YAML loading
- `lxml` — ArchiMate XML generation

Avoid unless genuinely needed:
- `langchain`, `llamaindex`, `semantic-kernel` — unnecessary abstraction layers. Direct API calls only.
- `sqlalchemy` — overkill for SQLite with known schemas. Use raw SQL via aiosqlite.
- `pandas` — not needed. Use sqlite queries or list comprehensions.

---

## Design Principles

### 1. Files Are the Interface

Agents read files (markdown, YAML, JSON, SQLite) and write files. The filesystem is the integration layer. Don't build internal APIs between agents — they share a filesystem.

### 2. System Prompts Are Configuration, Not Code

System prompts live in `.agents/prompts/*.md` as editable markdown files. They are loaded at runtime. Changing agent behaviour should not require code changes — only prompt edits. The code handles execution mechanics (reading inputs, writing outputs, managing the agent loop). The prompt handles domain logic.

### 3. Schema Validation at Boundaries

All agent outputs (manifests, staged entities, staged relationships) must validate against Pydantic models before being written to disk. Invalid output is logged and the run status set to "partial" — not silently written.

### 4. Idempotent by Default

Running an agent twice on the same input should produce the same output. Staging files use deterministic naming (`{agent_id}_{run_id}.yaml`) so re-runs overwrite, not duplicate. The element registry uses UPSERT semantics.

### 5. Fail Loud, Recover Gracefully

- LLM call fails → log error, write manifest with status "failed", exit cleanly
- MCP connection fails → degrade (tell user wiki is unavailable), don't crash
- Schema validation fails → log the invalid output, write what's valid, set status "partial"
- File not found → clear error message naming the expected path

### 6. No Magic

- No auto-discovery of agents (they're listed in config.yaml)
- No dynamic import tricks (explicit imports in runner.py)
- No decorator-based registration patterns
- No dependency injection frameworks
- Configuration is YAML files, not environment-variable-driven feature flags

---

## Module Dependency Rules

The package dependency DAG is strictly enforced. Arrows mean "may import from."

```
models     ← (nothing — pure data contracts, no internal imports)
utils      ← models
registry   ← models, utils
extraction ← models, utils, registry
agents     ← models, utils, registry, extraction
chat       ← models, utils, registry, extraction, agents
```

**The rules:**

- `models/` imports nothing from `src/ea_workbench/`. It defines Pydantic models only.
- `registry/` never imports from `chat/`, `agents/`, or `extraction/`. It is a leaf module.
- `extraction/` may read the registry (for dedup checks) but never imports chat or agent code.
- `agents/` may use extraction and registry but never imports chat code.
- `chat/` is the top-level orchestrator — it may import from everything.
- Cross-module communication that doesn't fit this DAG goes through the filesystem (staging files, manifests, config.yaml).

---

## AI Development Protocol

**Before writing any code, Claude Code must:**

1. **Read the design files.** All files in `/design/` — especially REQUIREMENTS.md for the section being implemented and BUILD-INSTRUCTIONS.md for the current phase.
2. **Read relevant existing code.** Before adding a new agent, read an existing agent. Before modifying the chat handler, read the current handler. Pattern-match against what exists.
3. **Check the models first.** Every data structure has a Pydantic model in `models/`. If the model doesn't exist yet, create it before writing the code that uses it. Models are the contract.
4. **Run tests after every change.** Not at the end — after each meaningful change. `pytest tests/` must pass before moving to the next step.

---

## YAML Schema Conventions

All YAML files in the PFC repo follow these rules:

- **Field ordering**: `id` first, then `name`/`title`, then `type`/`status`, then descriptive fields, then relationships/references, then timestamps, then `provenance` last.
- **IDs are strings**, not integers. Format: `PREFIX-NNN` (e.g., `NEED-001`, `ADR-012`, `PRI-003`).
- **Enums are lowercase strings**: `status: "active"` not `status: "Active"`.
- **Dates are ISO 8601**: `"2026-03-02"` for dates, `"2026-03-02T10:45:00Z"` for timestamps.
- **Multi-line strings use `|`** (literal block scalar), not `>` (folded).
- **Lists of references use `ref:`** to distinguish from inline data: `- ref: "NEED-001"`.
- **Register files (`_index.yaml`)** are the machine-readable catalogue. Individual markdown files are the human-readable detail. Both must agree — the register is not optional.
- **No anchors or aliases** (`&`, `*`). Keep YAML flat and explicit. Agents parse these files — cleverness is the enemy.

---

## Agent Prompt Structure

All agent prompts in `.agents/prompts/` follow this section order:

1. **Role** — one paragraph: who the agent is and what it does
2. **Context** — loaded dynamically at runtime: `{{CAPABILITY_MODEL}}`, `{{GLOSSARY}}`, etc.
3. **Input** — what the agent receives (file paths, content types, expected format)
4. **Output** — exact output format with a concrete example (YAML/JSON/Markdown template)
5. **Constraints** — what the agent must NOT do (e.g., "Do not invent elements not present in the source document")
6. **Extraction Protocol** — entity/work artefact extraction instructions (if applicable)

The output section must include a complete example, not just a schema description. Claude produces better structured output when it can pattern-match against a concrete instance.

---

## Violations

These are patterns Claude Code must not produce. If found in review, fix immediately.

```
❌ Importing chat/ from agents/, extraction/, or registry/
❌ Importing agents/ from extraction/ or registry/
❌ Hardcoded file paths (use config.yaml or environment variables)
❌ Bare except: clauses (always catch specific exceptions)
❌ print() statements (use logging module)
❌ Creating classes for agents (agents are async functions with typed config)
❌ LangChain, LlamaIndex, or Semantic Kernel imports
❌ SQLAlchemy or any ORM (use aiosqlite with raw SQL)
❌ Pydantic v1 patterns (use v2: model_dump() not .dict(), model_validate() not .parse_obj())
❌ Writing to .staging/ without a provenance block
❌ Writing to wiki/repo without user confirmation (Wiki Write Protocol)
❌ Auto-discovering agents (they are listed explicitly in config.yaml)
❌ Dynamic imports or decorator-based registration
❌ YAML anchors/aliases in repo files
❌ Register (_index.yaml) and detail file (.md) out of sync after a write
```

---

## Configuration Management

- **All paths** resolve from a `WORKBENCH_ROOT` environment variable or config entry. Never `os.path.join("/home/user/stanmore-pfc/", ...)`.
- **All LLM endpoints** come from config.yaml or environment variables. Never hardcoded model names or API URLs in agent code.
- **MCP server URLs** are configured in Chainlit's config, not in handler code.
- **The config.yaml agent registry** is the single source of truth for which agents exist, which models they use, and which prompts they load. Adding an agent means adding a config entry, not modifying runner.py.

---

## Testing Standards

### Unit Tests

- Every Pydantic model must have tests for valid and invalid data
- Every SQL query function must have tests against an in-memory SQLite DB
- ArchiMate XML generation must validate against the Open Exchange XSD
- Entity extraction schema validation must test boundary cases (missing fields, invalid types, out-of-range confidence)

### Integration Tests

- Chat agent: mock the Anthropic API, verify MCP tool calls are made for wiki queries
- Batch agents: run against fixture files (sample specs, transcripts), verify output structure
- Staging pipeline: extract → approve → export → validate XML

### Test Fixtures

- `tests/fixtures/specs/` — sample wiki spec pages (3–5 covering different domains)
- `tests/fixtures/transcripts/` — sample interview transcripts
- `tests/fixtures/capabilities/` — sample capability model YAML
- `tests/fixtures/registry/` — pre-populated SQLite DB for query tests

---

## Git Conventions

- **Commits**: Conventional Commits format (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)
- **Branches**: `feature/{use-case-number}-{short-description}` (e.g., `feature/uc12-adr-generator`)
- **No generated files in git**: `.staging/exports/` is gitignored. Generated ArchiMate XML is an output, not source.
- **SQLite DB in git**: The element registry DB IS committed (it's the source of truth for known elements). Use small, frequent commits when the registry changes.
