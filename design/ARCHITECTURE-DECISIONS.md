# EA Workbench — Architecture Decisions

Decisions made during design that constrain implementation. Claude Code should treat these as fixed unless the architect explicitly changes them.

---

## ADR-001: Chainlit for Chat UI, Not Custom Frontend

**Context**: Need a chat interface for interactive EA work. Options: custom React/Vue app, Streamlit, Gradio, Chainlit, Open WebUI.

**Decision**: Use Chainlit.

**Rationale**:
- Python-native (matches Agent SDK and backend stack)
- Native MCP support (ADO wiki integration via stdio transport)
- Built-in step visualisation (shows tool calls without custom UI work)
- Chat-first design (not a data app framework bolted to chat)
- < 300 lines of application code to get a working chat agent
- Apache 2.0 licensed

**Consequences**:
- Community-maintained (original team stepped back May 2025). Releases still shipping (2.9.6 Jan 2026). Accept the risk for a prototype; keep backend logic decoupled so UI framework is replaceable.
- Limited dashboard capabilities. Observability views may need to be wiki-generated pages rather than Chainlit native.
- No persistent chat history out of the box — requires SQLAlchemy data layer configuration.

**Alternatives rejected**:
- Custom React/Vue: 3-4 weeks frontend work for no architectural benefit
- Streamlit: Not chat-first; bolts chat onto a data app framework
- Open WebUI: Heavier than needed; designed for multi-model multi-user deployment
- Helix fork: Wrong stack (Vue.js), wrong purpose (visual editor vs chat agent), maintenance burden

---

## ADR-002: Anthropic Messages API for Chat, Agent SDK for Batch

**Context**: Two execution modes needed — interactive chat and batch file processing. Both could use Agent SDK or Messages API.

**Decision**: Chat uses Messages API with tool calling. Batch uses Agent SDK with filesystem tools.

**Rationale**:
- Chat needs MCP tool access (wiki, registry) and multi-turn conversation. Messages API + tool calling is the right abstraction. No need for filesystem access in chat.
- Batch needs filesystem access (read specs, write outputs, run bash commands). Agent SDK provides this natively.
- Mixing them (Agent SDK for chat) creates unnecessary security surface — giving the chat agent bash access when it only needs MCP tools.
- The dual-track governance model supports this split: chat is Track 2 (informal), batch agents are Track 1-adjacent (auditable).

**Consequences**:
- Two different LLM calling patterns in the codebase. Acceptable — they serve genuinely different purposes.
- Model routing is handled differently: Messages API client specifies model directly; Agent SDK uses environment config.

---

## ADR-003: SQLite for Element Registry, Not PostgreSQL

**Context**: Need a relational store for architectural elements, relationships, and capabilities. Options: SQLite, PostgreSQL, JSON files, Cosmos DB.

**Decision**: SQLite (single file in git repo).

**Rationale**:
- Single-user prototype (one architect). No concurrent write pressure.
- Git-native: the DB file is committed and versioned alongside specs. History is free.
- Agent-friendly: Agent SDK agents can query via bash (`sqlite3`) or Python (`aiosqlite`).
- Zero infrastructure: no server to provision, no connection strings to manage.
- Portable: if the contract ends, the entire EA knowledge base (wiki + DB) is a git clone.

**Consequences**:
- Concurrent writes will cause issues if multiple agents run simultaneously. Mitigate with single-writer pattern (queue agent runs, don't parallelise).
- Phase 1 (team deployment) may require migration to PostgreSQL if Mahtab or other team members need concurrent access. Schema is designed to be portable (standard SQL, no SQLite-specific features).

---

## ADR-004: Git as the Knowledge Base, Not Orbus

**Context**: EA knowledge needs a canonical store. Orbus iServer is the official EA repository. ADO Wiki is git-backed markdown.

**Decision**: Git (wiki repo + companion EA repo) is the canonical source of truth. Orbus is a downstream rendering consumer.

**Rationale**:
- Orbus integration is expensive, slow, and fragile. The REST API has limited documentation and the team has limited Orbus expertise.
- Wiki specs are the working documents where architecture decisions actually live. Orbus models are derived views created after the fact.
- Agents can read/write git natively. They cannot interact with Orbus without significant integration work.
- If the contract ends, a git repo is portable. An Orbus instance is not.
- The entity extraction protocol captures structured facts from agent work. Periodic ArchiMate XML export provides the bridge to Orbus when needed.

**Consequences**:
- Orbus will lag behind the wiki. This is acceptable — Orbus is for formal presentations and governance artifacts, not for working architecture.
- The ArchiMate export script must produce valid Open Exchange XML that Orbus can import cleanly.
- The capability model, element registry, and vocabulary must be maintained in git with discipline. Without Orbus enforcing schema, the EA knowledge base relies on agent validation and architect review.

---

## ADR-005: Entity Extraction as Cross-Cutting Concern, Not Separate Agent

**Context**: Need to build a structured representation of the architecture (entities, relationships) from wiki content. Options: dedicated extraction agent that scans all content, or extraction embedded in every agent.

**Decision**: Every agent that touches architectural content extracts entities and relationships as a side effect. No dedicated extraction agent.

**Rationale**:
- Agents are already reading and reasoning about architectural content. The marginal cost of also writing a structured record is near zero (a system prompt suffix + output file).
- A dedicated extraction agent would need to re-read everything the other agents already processed — redundant work.
- Extraction quality is higher when it's a side effect of a focused task (e.g., spec decomposition agent understands the document deeply) than when it's a generic scan.
- The staging area accumulates naturally as agents do real work. The architecture model builds itself.

**Consequences**:
- Every agent system prompt includes the extraction protocol suffix. Prompt maintenance is slightly higher.
- Extraction format must be consistent across all agents. Pydantic schema validation at write time enforces this.
- Some agents don't extract (use-case assessment, NFR compliance, stakeholder comms). This is fine — they're flagged as `extracts_entities: false` in config.

---

## ADR-006: YAML for Configuration, Not TOML or JSON

**Context**: Need configuration files for capability model, glossary, agent registry, staging files.

**Decision**: YAML for all human-edited configuration. JSON for machine-generated outputs (manifests, API responses).

**Rationale**:
- YAML supports comments (JSON doesn't). Configuration files need annotations explaining choices.
- YAML handles multi-line strings naturally (system prompts, descriptions).
- YAML is the standard for infrastructure-as-code (Bicep parameters, pipeline definitions, K8s manifests) — consistent with the team's existing patterns.
- JSON is used only for run manifests and structured outputs where comments aren't needed and machine parsing is the primary use case.

**Consequences**:
- Must use safe YAML loading (`yaml.safe_load`) everywhere. Never `yaml.load` with untrusted input.
- TOML is used only for Chainlit's own config (`.chainlit/config.toml`) because Chainlit requires it.

---

## ADR-007: Model Routing is Configuration, Not Code

**Context**: Different agents benefit from different models (Claude for judgment, Gemini for extraction). Need to route model selection per agent.

**Decision**: Model assignment is declared per agent in `.agents/config.yaml`. The runner reads the config and sets the model. No model-selection logic in agent code.

**Rationale**:
- Model selection is an operational decision (cost, quality, availability) that changes independently of agent logic.
- New models become available frequently. Changing assignment should be a config edit, not a code change.
- A/B testing models (Claude vs Gemini on the same extraction task) is trivial with config-based routing — run the agent twice with different config.

**Consequences**:
- The agent runner must support multiple model backends (Anthropic API, Azure AI Foundry with different model deployments).
- Config validation must check that specified models are available in the Azure AI Foundry deployment.

---

## ADR-008: No LangChain, No Framework Abstractions

**Context**: LangChain, LlamaIndex, Semantic Kernel, and similar frameworks offer agent orchestration abstractions.

**Decision**: Direct API calls only. No agent framework abstractions.

**Rationale**:
- The Agent SDK IS the agent framework for batch agents. Adding LangChain on top adds a layer with its own opinions, breaking changes, and debugging complexity.
- The Messages API is 20 lines of code for a tool-calling conversation. LangChain doesn't simplify this — it obscures it.
- Framework abstractions make debugging harder. When a batch agent produces wrong output, you need to see exactly what prompt was sent and what response came back. Direct API calls make this transparent.
- Dependency minimisation. Every framework is a dependency that can break, have security issues, or change APIs. Direct calls to stable APIs (Anthropic, Azure OpenAI) have the smallest attack surface.

**Consequences**:
- Some boilerplate in the chat handler for tool call processing. Acceptable — it's explicit and debuggable.
- If a future use case genuinely needs multi-agent orchestration (not just sequential agent runs), reconsider LangGraph or Semantic Kernel Process Framework at that point. Not needed for the current 15 use cases.

---

## ADR-009: PFC as Source of Truth, Orbus as System of Record

**Context**: Stanmore has both a git-native PFC repo where the architect works and Orbus iServer as the formal enterprise architecture tool. Need to establish clear data ownership.

**Decision**: The PFC git repository is the source of truth for all EA knowledge. Orbus iServer is the system of record that receives syndicated content. Data flow is always PFC → Orbus, never the reverse.

**Rationale**:
- The architect works daily in the PFC — it must be the authoritative source to avoid split-brain problems.
- Git provides version history, branching, merge review, and CI/CD integration that Orbus cannot match for iterative authoring.
- Agents operate on git-native files. Making Orbus the source of truth would require live API integration for every agent read operation, introducing latency and a hard dependency.
- Orbus serves a different audience (enterprise-wide EA stakeholders) with different needs (views, reports, cross-portfolio analysis). It should receive a curated, reviewed subset — not the architect's working state.
- If Orbus is unavailable or deprioritised, no EA work stops. The PFC is self-sufficient.

**Consequences**:
- The ArchiMate export pipeline must be maintained as the syndication mechanism.
- Orbus import format validation is needed to catch drift.
- Two-way sync is explicitly out of scope — manual reconciliation if Orbus content diverges.
- Practice artefacts without ArchiMate equivalents (decisions, ideas, standards) live only in the PFC repo unless manually published.

---

## ADR-010: Provenance-First Staging

**Context**: AI conversations generate structured artefacts (entities, work items, decisions) but the reasoning behind them is lost if only the structured record is kept. A DevOps work item saying "Investigate Purview label coverage" is actionable but misses the 20-minute conversation where the coverage gap was discovered and implications analysed.

**Decision**: Every staged or authored artefact must carry a provenance block containing: session ID, semantic conversation summary, trigger message, key exchanges, session link, and related artefact references. The summary is a dense paragraph capturing reasoning, not just the conclusion.

**Rationale**:
- Structured outputs are lossy without provenance. The reasoning is the actual value; the structured record is just the conclusion.
- Chat sessions can be long (2+ hours, 15+ staged items across 6 topics). Linking to "whole chat" doesn't provide useful context.
- Session links may break (Chainlit instance restarts). The semantic summary is durable.
- DevOps consumers (including future team members) need context without replaying entire transcripts.

**Consequences**:
- Provenance generation adds ~200 tokens of overhead per staged item. Acceptable for the value it provides.
- System prompt must include provenance capture instructions.
- Session persistence (SQLAlchemy backend) required from Phase 0 to support stable session URLs.
- Work items pushed to DevOps embed the conversation summary in the description field.

---

## ADR-011: ArchiMate Motivation Layer for Needs and Requirements

**Context**: The PFC needs to capture stakeholder needs and solution requirements with clear separation and traceability. JTBD (Jobs To Be Done) was considered as the framing but adds a parallel vocabulary.

**Decision**: Use ArchiMate Motivation layer elements directly. Needs map to `goal`, requirements map to `requirement`, stakeholder concerns map to `driver`, desired results map to `outcome`, and architectural principles map to `principle`. No JTBD overlay.

**Rationale**:
- ArchiMate already has the vocabulary. Adding JTBD creates two naming systems for the same concepts.
- The entity extraction protocol already handles ArchiMate types. Motivation layer elements participate in the same extraction → staging → Orbus export pipeline with no additional tooling.
- The key insight (separate needs from requirements) is captured by the ArchiMate distinction between `goal` (solution-independent) and `requirement` (solution-specific). This separation is the important thing, not which framework names it.
- Orbus iServer speaks ArchiMate natively. Motivation layer elements syndicate through the standard export pipeline.

**Consequences**:
- Needs are captured as ArchiMate `goal` elements in `needs/by-domain/`. Requirements as ArchiMate `requirement` elements in `requirements/by-domain/`.
- Engagement records (`needs/engagements/`) don't have a direct ArchiMate mapping — they are EA practice records, not model elements.
- The traceability chain (Stakeholder → Driver → Goal → Requirement → Element → Capability) is fully expressible in ArchiMate relationships.
- `course-of-action` (Strategy layer) is used for strategies rather than creating a custom type.
