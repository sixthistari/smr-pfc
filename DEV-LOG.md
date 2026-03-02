# EA Workbench — Development Log

## Status: Scaffold / Stub — Needs Real Work

This codebase is a **working scaffold**. All modules, models, tests, and wiring are in place, but significant domain-specific work is required before production use.

---

## What is Done (scaffold quality)

| Area | Status | Notes |
|------|--------|-------|
| Phase 0 — core framework | ✅ Complete | Models, registry, extraction, chat, aiosqlite, Chainlit |
| Phase 1 — foundational agents | ✅ Scaffolded | wiki-integrity, guardrail, spec-decomposition, ArchiMate export |
| Phase 2 — specialist agents (12) | ✅ Scaffolded | All 12 agents wired up, run() methods callable, manifests written |
| Option C schema (21 tables) | ✅ Scaffolded | Tables created, views in place, valid_relationships seeded |
| Pydantic models (5 concern layers) | ✅ Scaffolded | All field definitions, no business logic yet |
| Migration utility | ✅ Scaffolded | Routes Phase 0 rows to concern tables |
| Test suite (252 tests) | ✅ Passing | All unit tests pass with mocked SDK |
| End-user docs | ✅ Draft | docs/ — commands, agents, architecture, workflows |

---

## What Needs Real Work

### Agent Prompts (`stanmore-pfc/.agents/prompts/*.md`)
All 16 prompt files are **template stubs**. Each needs:
- Concrete few-shot examples drawn from real PFC meetings and decisions
- Domain-specific context (PFC programme terminology, NHS digital standards, ArchiMate usage conventions for the programme)
- Output format constraints tightened to the actual registry schema field names
- Guardrail thresholds calibrated against real risk tolerance

### Capability Model (`stanmore-pfc/capabilities/*.yaml`)
No real capability data exists. The capability model files need to be populated with actual PFC programme capabilities before `transcript-classifier` and `capability-intelligence` agents can produce useful output.

### Element Registry (`stanmore-pfc/registry.db`)
Database is empty. Needs seeding with:
- Domain definitions (safety, patient flow, clinical records, etc.)
- Baseline architecture elements from existing PFC programme documents
- Initial stakeholder and driver records from programme governance docs

### Valid Relationships (`valid_relationships` table)
Seeded with ~45 ArchiMate 3.2 pairs at init. Needs review against the specific ArchiMate types actually used in this programme — some permitted pairs may be irrelevant; missing pairs may need adding.

### Assessment Criteria (`stanmore-pfc/specs/_assessment-criteria.md`)
Referenced by `use-case-assessment` agent. File does not exist — the agent falls back to an embedded default. The real AI CoE assessment template needs to be authored and placed here.

### NFR Baseline (`stanmore-pfc/specs/_nfr_index.yaml`)
Referenced by `nfr-compliance` agent. Not yet created. Needs the programme's actual NFR thresholds (availability, response time, data residency, etc.).

### Standards Register (`stanmore-pfc/specs/standards/`)
Referenced by `standards-enforcer` agent. No standards pages exist yet. Needs content from the NHS digital, Azure, and programme-specific standards that should be enforced.

### Orbus / Work Items Integration
`orbus-sync` agent reads from a YAML work-items export. The actual export format from the Orbus tool (or whatever replaces it) needs to be validated against the agent's expected schema.

### Authentication
Chainlit is running without any auth. For anything beyond a local workstation, add password auth or SSO via `@cl.password_auth_callback` or OAuth.

### `/triage` Approval Flow
The approve/reject UI is implemented as `cl.Action` buttons, but the routing in `approve_staging_item()` needs end-to-end testing with real staged entities from a live agent run.

### Session Persistence
`sessions` table is defined but `SessionRecord` is not being written automatically at session end. The `/wrap` command writes it manually — needs auto-persist on session close.

---

## Known Gaps / Tech Debt

- `business_architecture` types are **skipped** in `migrate_phase0_to_option_c()` — the generic `Element` model doesn't carry enough fields to reconstruct a `BusinessArchElement` cleanly. A separate migration path for these is needed when real BA data exists.
- `element_registry_view` unions the legacy `elements` table alongside the 5 concern tables. Once all elements are in concern tables, the legacy join should be removed.
- Agent `run()` functions catch bare `Exception` and return `status="failed"` — specific error types should be surfaced differently (auth errors vs timeout vs content policy).
- No retry logic on SDK calls.
- MCP server (`ea_workbench.registry.mcp_server`) has only basic read tools; write tools needed for agentic update workflows.

---

## Next Milestones

1. **Populate capability model** — minimum viable set of ~20 capabilities for transcript-classifier to be useful
2. **Author assessment criteria** — real AI CoE template in `specs/_assessment-criteria.md`
3. **Seed 3–5 domains** — run `/migrate` after to populate concern tables
4. **Run transcript-classifier on a real meeting** — validate staged entity YAML schema against actual output
5. **Triage first batch** — end-to-end: transcript → staging → /triage → registry
6. **Add auth** — before sharing with anyone outside localhost

---

_Last updated: 2026-03-02_
