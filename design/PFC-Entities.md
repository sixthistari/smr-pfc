# PFC Entity Reference

**Stanmore Resources** | Technology — Enterprise Systems

| | |
|---|---|
| **Document Owner** | Justin Hume — Enterprise Architect, AI & Advanced Analytics |
| **Status** | Ready for Technical Review |
| **Date** | March 2026 |
| **Parent** | PFC Schema Extension Brief v2 (Option C) |
| **Purpose** | Field-level reference for extraction agents, Pydantic models, and human architects. Every table, every field, when to use it, when not to. |

---

## How This Document Works

Each entity section covers: what the table is, which ArchiMate types it holds, field instructions per subtype, concerns and gotchas, and worked examples. The extraction agents (UC-1) and the Claude Code build session use this as their canonical reference for "where does this concept go and what fields are required."

**Notation:**

- **Required** — must be populated for any row of this type
- **Subtype-required** — required only when `archimate_type` matches the specified subtype
- **Optional** — populate if known, leave NULL if not
- **Computed** — populated by the system, not by humans or agents

**Cross-table references** use the polymorphic `(target_table, target_id)` pattern or direct FKs. Application-level validation enforces referential integrity where SQLite can't.

---

## 1. domains

### What It Is

First-class entity representing a bounded context in the enterprise. Not a text field — a governed partition with its own autonomy ceiling, track default, and ownership. Every concern table references `domains(id)`.

### ArchiMate Mapping

Domains are not ArchiMate elements. They are an organisational overlay — the federated structure that partitions the enterprise architecture into governable units. In ArchiMate terms, a domain maps loosely to a Grouping element, but the PFC treats it as a structural primitive, not an ArchiMate type.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | Short slug: `dom-safety`, `dom-geology`, `dom-maintenance`, `dom-operations`, `dom-finance`, `dom-projects`, `dom-enterprise` (cross-cutting) |
| `name` | **Required** | Human-readable: "Safety", "Geology & Resource", "Maintenance & Reliability" |
| `description` | Optional | What this domain covers, its boundaries, key stakeholders |
| `priority` | Optional | Integer for roadmap sequencing. Lower = higher priority. Safety = 1, Geology = 2, etc. |
| `maturity` | Optional | `initial` \| `defined` \| `managed` \| `optimised`. Most Stanmore domains start at `initial`. |
| `autonomy_ceiling` | **Required** | Maximum agent autonomy permitted in this domain. `L0`–`L5`. Safety = `L2` (Track 1). Geology = `L3`. |
| `track_default` | **Required** | Default track for new processes in this domain. `Track1` (formal/governed) or `Track2` (informal/ad-hoc). |
| `spec_coverage` | Optional | Qualitative or percentage. How much of this domain is covered by wiki specifications. |
| `owner_role` | Optional | Who owns this domain. Role, not person — "Safety Manager", "Head of Geology". |

### Concerns

- **The `dom-enterprise` domain** is for genuinely cross-cutting elements (org structure, site locations, shared identity). Don't use it as a dumping ground for "I don't know which domain this belongs to" — that's what staging_items is for.
- **Autonomy ceiling is a governance constraint, not a suggestion.** An agent deployed in the Safety domain at L3 when the ceiling is L2 is a governance violation. The `governance_controls` table should have a control binding this ceiling to each domain's processes.
- **Domains are seeded, not extracted.** These are created by the architect during setup, not discovered by agents. The initial set comes from the domain partitioning in the Enterprise Knowledge Layers document.

### Example Rows

```
id: dom-safety
name: Safety
priority: 1
maturity: initial
autonomy_ceiling: L2
track_default: Track1
owner_role: Safety Manager

id: dom-geology
name: Geology & Resource
priority: 2
maturity: initial
autonomy_ceiling: L3
track_default: Track2
owner_role: Head of Geology
```

---

## 2. motivation

### What It Is

The ArchiMate Motivation layer — complete. Holds stakeholders, drivers, assessments, goals, outcomes, requirements, and constraints. These are the "why" of the architecture: who cares, what pressures exist, what we aspire to, and what the solution must satisfy.

### ArchiMate Types (CHECK constraint)

`stakeholder` | `driver` | `assessment` | `goal` | `outcome` | `requirement` | `constraint` | `meaning` | `value`

### The Motivation Chain

The chain is modelled via `relationships` (not parent_id):

```
Stakeholder → (association) → Driver → (association) → Assessment → (influence) → Goal
                                                                                   ↓ (realization)
                                                                         Business Requirement
                                                                                   ↓ (realization)
                                                                         Solution Requirement
                                                                                   ↓ (realization)
                                                                              Element (in any concern table)
```

Each link is a row in `relationships`. The chain is discovered by traversal, not by hierarchy.

### Field Instructions — Common Fields

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | Prefix by type: `STKH-001`, `DRV-001`, `ASSESS-001`, `GOAL-001`, `BREQ-001`, `SREQ-001`, `CON-001` |
| `name` | **Required** | Short descriptive name. "Safety Manager", "Regulatory compliance pressure", "Retrieval accuracy ≥85% precision@5" |
| `archimate_type` | **Required** | One of the CHECK values above |
| `domain_id` | **Required** | FK to domains. Enterprise-wide stakeholders use `dom-enterprise`. |
| `status` | **Required** | `active` \| `draft` \| `superseded` \| `deprecated` |
| `description` | **Required** | Full description. For requirements, this is the requirement statement. |
| `source_spec` | Optional | Wiki page path or document reference where this was defined |
| `confidence` | Computed | 0.0–1.0. Set by extraction agent. Human review may adjust. Default 1.0 for manually created. |
| `created_by` | Computed | `architect` \| `agent:<agent-id>` \| `import:<source>` |
| `engagement_ref` | Optional | FK to `engagements`. Links this motivation element to the workshop/interview where it was first articulated. |

### Field Instructions — Subtype: stakeholder

| Field | Subtype-required | Notes |
|---|---|---|
| `role` | **Required** | Organisational role: "Safety Manager", "CFO", "Head of Technology", "Mine Superintendent" |
| `influence_level` | Optional | `high` \| `medium` \| `low`. How much this stakeholder can affect architectural decisions. |

**Irrelevant fields (must be NULL):** threshold, target, acceptance_criteria, requirement_type, category, solution_id, driver_category, evidence, impact, horizon.

### Field Instructions — Subtype: driver

| Field | Subtype-required | Notes |
|---|---|---|
| `driver_category` | **Required** | `internal` \| `external` \| `regulatory`. "Need to reduce manual document search time" = internal. "MSHA compliance requirements" = regulatory. |

### Field Instructions — Subtype: assessment

| Field | Subtype-required | Notes |
|---|---|---|
| `evidence` | **Required** | The analytical observation. "40% of retrieved procedures are superseded versions, creating compliance risk." |
| `impact` | Optional | `high` \| `medium` \| `low`. How significant is this finding. |

**What an assessment is:** The analytical bridge between a driver and a goal. Without it, the model jumps from "pressure exists" to "we want outcome" with no recorded reasoning. This is where architectural judgement lives. Example: Driver = "Regulatory compliance pressure on safety procedures." Assessment = "Current manual process can't keep up with regulatory change frequency — 40% of retrieved procedures are superseded." Goal = "Self-service knowledge platform enabling any employee to find authoritative information within 30 seconds."

### Field Instructions — Subtype: goal

| Field | Subtype-required | Notes |
|---|---|---|
| `horizon` | **Required** | `H1` (0–12 months) \| `H2` (12–36 months) \| `H3` (36+ months). Goals are deliberately aspirational and span horizons. |

### Field Instructions — Subtype: requirement

| Field | Subtype-required | Notes |
|---|---|---|
| `requirement_type` | **Required** | `business` \| `solution` \| `nfr` |
| `category` | Optional | For NFRs: `performance` \| `security` \| `reliability` \| `usability` \| `maintainability` \| `governance`. For business reqs: `functional` \| `operational` \| `compliance`. |
| `threshold` | Optional | Minimum acceptable value. "85%" |
| `target` | Optional | Desired value. "95%" |
| `acceptance_criteria` | Optional | JSON array of testable criteria: `[{"criterion": "precision@5 ≥ 0.85", "test_method": "eval query set"}]` |
| `solution_id` | Optional | FK to `solutions`. Only for solution requirements — binds the requirement to a specific solution. Business requirements are solution-independent and should NOT have this set. |

**Business vs Solution Requirements:** A business requirement survives regardless of implementation. "I need to find the current version of a safety procedure quickly." A solution requirement is testable against a specific implementation. "RAG pipeline shall return authoritative document with ≥85% precision@5." If the solution changes, the solution requirement may change. The business requirement endures.

### Field Instructions — Subtype: constraint

Constraints are restrictions on the architecture — "must use Azure-native services", "must comply with ISO 27001", "budget ceiling of $X". They constrain goals and requirements via `influence-relationship` in the relationships table.

### Concerns

- **Don't confuse stakeholders with business actors.** A stakeholder has *interests* in the architecture. A business actor *does work* in processes. The Safety Manager is a stakeholder (cares about safety outcomes) AND a business actor (performs incident investigation). Two different rows, two different tables, linked by a relationship.
- **Assessment is the most commonly missed entity.** Extraction agents tend to jump from driver to goal. Train them to look for "because", "this means", "the impact is", "analysis shows" — these signal assessments.
- **Requirements need the `requirement_type` field populated.** An extraction agent that creates a requirement row without specifying business vs solution has created an ambiguous entity. Default to `business` if unclear — solution requirements should only be created when a specific solution context exists.
- **The `nfr_ref` field** (if present) links a solution requirement to its parent NFR in `practice_artefacts`. This creates the traceability: NFR standard → solution requirement → tested against → quality evaluation.

---

## 3. strategy

### What It Is

The ArchiMate Strategy layer — complete. Holds capabilities (hierarchical), value streams (with stages), resources, and courses of action. These are the "what we can do" and "how we plan to get there" of the architecture.

### ArchiMate Types (CHECK constraint)

`capability` | `value-stream` | `resource` | `course-of-action`

### Field Instructions — Common Fields

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | Prefix by type: `CAP-001`, `VS-001`, `RES-001`, `COA-001` |
| `name` | **Required** | "Enterprise Knowledge Retrieval", "Safety Information Value Stream", "Azure AI Search Capacity" |
| `archimate_type` | **Required** | One of the CHECK values above |
| `domain_id` | **Required** | FK to domains. Capabilities may be cross-domain (`dom-enterprise`). |
| `status` | **Required** | `current` \| `target` \| `planned` \| `deprecated` |
| `description` | **Required** | What this capability/stream/resource enables |
| `confidence` | Computed | Agent-set confidence |

### Field Instructions — Subtype: capability

| Field | Subtype-required | Notes |
|---|---|---|
| `parent_id` | Optional | FK self-reference for hierarchy. Root capabilities have NULL parent_id. |
| `level` | Computed | Depth in hierarchy. 0 = root. Computed from parent_id chain. |
| `maturity` | Optional | `none` \| `initial` \| `developing` \| `defined` \| `managed` \| `optimised`. Current maturity of this capability. |

**Capability hierarchy:** Capabilities form a tree. "Enterprise Knowledge Management" (L0) → "Document Retrieval" (L1) → "Authority-Aware Retrieval" (L2). The hierarchy is structural, not the motivation chain. Functions *realise* capabilities (via relationships), not the other way around.

### Field Instructions — Subtype: value-stream

| Field | Subtype-required | Notes |
|---|---|---|
| `stages` | **Required** | JSON array of ordered stages: `[{"name": "Capture", "description": "...", "capabilities": ["CAP-001"]}, {"name": "Enrich", ...}]` |
| `value_proposition` | Optional | What value this stream delivers to its consumer |

**Value streams are explicitly in the JD accountabilities.** "Identify and map enterprise value chains and value streams." A value stream is sequential — each stage transforms value. Cross-references to capabilities and domains are in the `relationships` table.

### Field Instructions — Subtype: course-of-action

| Field | Subtype-required | Notes |
|---|---|---|
| `horizon` | **Required** | `H1` \| `H2` \| `H3`. Same horizon model as goals. |
| `traces_to_goal` | **Required** | FK to `motivation` (goal). Which goal this course of action addresses. |

**Course of action vs ADR:** A course of action is a strategic direction: "Invest in federated knowledge platform to address document retrieval deficiencies." An ADR is an implementation decision: "Use Neo4j with n10s for the enterprise knowledge graph." The course of action lives in strategy. The ADR lives in practice_artefacts. The course of action *informs* ADRs; an ADR *implements* a course of action.

### Concerns

- **Don't create capabilities below L2 depth too early.** The capability model should stabilise at L0/L1 before decomposing further. L2+ capabilities should emerge from business architecture analysis, not from speculative decomposition.
- **Value stream stages are JSON now.** If stage-level queries become necessary (e.g., "which capabilities are consumed at stage 3 of this value stream"), the stages field would need to become a child table. Flag this in the Claude Code review.
- **Resources are underused.** Most architectural work focuses on capabilities and value streams. Resources (budget, people, infrastructure capacity) matter for course-of-action feasibility. Don't forget to model them.

---

## 4. business_architecture

### What It Is

The ArchiMate Business layer. Holds actors, roles, functions, processes, services, objects, and events. This is where the enterprise operates — who does what, how work flows, what things are produced and consumed.

### ArchiMate Types (CHECK constraint)

`business-actor` | `business-role` | `business-process` | `business-function` | `business-service` | `business-object` | `business-event` | `contract` | `product`

### Field Instructions — Common Fields

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | Prefix: `BA-001` (actor), `BR-001` (role), `BP-001` (process), `BF-001` (function), `BS-001` (service), `BO-001` (object), `BE-001` (event) |
| `name` | **Required** | "Safety Manager" (actor), "Procedure Reviewer" (role), "Incident Investigation" (process), "Safety Management" (function), "Safety Advisory Service" (service), "Incident Report" (object) |
| `archimate_type` | **Required** | One of the CHECK values above |
| `domain_id` | **Required** | FK to domains |
| `parent_id` | Optional | Self-reference for hierarchy. Processes can contain sub-processes. Functions can contain sub-functions. |

### Field Instructions — Subtype: business-actor

| Field | Subtype-required | Notes |
|---|---|---|
| `actor_type` | **Required** | `person` \| `team` \| `org-unit` \| `agent` |

**Agent as actor — the Autonomy Policy Gateway:** `actor_type = 'agent'` is NOT a default classification. An AI agent is an `application-component` in `solution_architecture` by default. It only becomes a business-actor when ALL of these conditions are met:

1. Operating at **L3 or above** (Execute in Sandbox or higher)
2. Assigned to a **defined process step** with `step_type = 'agent'`
3. Has a **formal role assignment** (holds a `business-role`)
4. Approved through **AI CoE architectural sign-off** (documented as ADR in practice_artefacts)

If you're creating a business-actor with `actor_type = 'agent'`, you must be able to point to the ADR that approved the promotion. The corresponding `solution_architecture` row should have `promoted_to_actor = 1`.

### Field Instructions — Subtype: business-role

| Field | Subtype-required | Notes |
|---|---|---|
| `agent_augmented` | Optional | `0` \| `1`. Is this role augmented by an AI agent? |
| `augmentation_level` | Optional | `L0`–`L5`. At what autonomy level is the agent augmenting this role? Only meaningful when `agent_augmented = 1`. |

**Actors vs Roles:** An actor *is* someone (Safety Manager). A role is the *hat they wear* in a context (Procedure Reviewer). The Safety Manager acts as "Procedure Reviewer" during document governance and as "Incident Investigator" during incident response. Actors are assigned to roles via `assignment-relationship` in the relationships table. Roles are the attachment point for agent augmentation — you augment the *role*, not the person.

### Field Instructions — Subtype: business-process

| Field | Subtype-required | Notes |
|---|---|---|
| `track` | **Required** | `Track1` \| `Track2`. Critical governance classification. Track 1 = formally governed, auditable, compliance-dependent. Track 2 = ad-hoc, exploratory, judgment-driven. |
| `governance_level` | Optional | `high` \| `medium` \| `low`. How tightly governed this process is. Track 1 processes are typically high. |
| `trigger_event` | Optional | What triggers this process. FK to a business-event or description. |
| `process_owner_id` | Optional | FK to a business-role that owns this process. |

**Processes are the primary unit of agent deployment.** An agent's autonomy level is set per process step, not globally. A Safety Compliance Agent might operate at L2 in Track 1 safety processes (recommend only) but at L4 in Track 2 ad-hoc queries (execute with guardrails). The `process_steps` table decomposes processes into steps where this granularity is captured.

### Field Instructions — Subtype: business-function

No subtype-specific fields beyond the common set. Functions *realise* capabilities (via relationships). They group related behaviour by competency — "Safety Management", "Production Planning". Functions are stable — they change when the org restructures, not when processes change.

### Field Instructions — Subtype: business-service

| Field | Subtype-required | Notes |
|---|---|---|
| `service_type` | Optional | `internal` \| `external`. Internal services serve other business units. External services serve customers or regulators. |
| `consumer` | Optional | Who consumes this service. Role or actor reference. |

**In portfolio context,** a business service is the gateway to a solution. The Safety Advisory Service (business-service) is realised by the Safety Knowledge Solution (solutions), which is composed of AI Search, Foundry Agent, Copilot Studio (solution_architecture components).

### Field Instructions — Subtype: business-object

| Field | Subtype-required | Notes |
|---|---|---|
| `has_authority_scoring` | Optional | `0` \| `1`. Does this object type have document authority scoring? Safety Procedure = yes. Ad-hoc email = no. |
| `classification` | Optional | Data classification: `public` \| `internal` \| `confidential` \| `restricted` |

**Business objects are what agents read, create, transform, and validate.** An Incident Report, a Safety Procedure, a Work Order, a Geological Survey. These are primary candidates for document authority scoring in the knowledge layer. When `has_authority_scoring = 1`, the object should have corresponding authority rules in the knowledge store configuration.

### Concerns

- **Don't model every person as a business-actor.** Model *roles* generously, actors selectively. "Mine Superintendent" is a role many people fill. Create one role, not one actor per superintendent.
- **Track classification is non-negotiable for processes.** Every process must be Track 1 or Track 2. This drives agent governance, autonomy ceilings, and audit requirements. If you're unsure, default to Track 1 — it's safer to over-govern than under-govern.
- **Business events are triggers, not log entries.** "Incident Reported" is a business event. "John logged into the system at 3pm" is not.

---

## 5. process_steps

### What It Is

Ordered decomposition of a business process into executable steps. Each step has a type (human, agent, system, decision, gateway), an optional agent assignment, and governance flags. This is where the dual-track model and autonomy levels materialise at the operational level.

### Not an ArchiMate Element

Process steps are a supporting structure, not an ArchiMate type. They decompose `business-process` rows from `business_architecture` into granular steps. In ArchiMate terms, they're an internal decomposition — the ArchiMate export represents the process as a single element, with steps as annotations.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | `PS-<process-id>-<seq>`: `PS-BP-001-01`, `PS-BP-001-02` |
| `process_id` | **Required** | FK to `business_architecture` where `archimate_type = 'business-process'` |
| `sequence` | **Required** | Integer ordering. Gaps allowed (10, 20, 30) for later insertion. |
| `name` | **Required** | "Receive incident report", "Classify severity", "Assign investigator" |
| `step_type` | **Required** | `human` \| `agent` \| `system` \| `decision` \| `gateway` |
| `role_id` | Optional | FK to `business_architecture` (business-role). Who performs this step. |
| `agent_id` | Optional | FK to `solution_architecture` (where `is_agent = 1`). Which agent is assigned. Only meaningful when `step_type = 'agent'`. |
| `agent_autonomy` | Optional | `L0`–`L5`. Overrides the agent's `default_autonomy` for this specific step. |
| `description` | Optional | What happens at this step |
| `input_objects` | Optional | JSON array of business-object IDs consumed: `["BO-incident-report"]` |
| `output_objects` | Optional | JSON array of business-object IDs produced: `["BO-investigation-plan"]` |
| `approval_required` | **Required** | `0` \| `1`. Must a human approve the agent's output before it takes effect? **Required for any step where `agent_autonomy` is L2.** |
| `track_crossing` | **Required** | `0` \| `1`. Does the output of this step enter a formal (Track 1) process? If `1`, provenance tagging and human review gate are mandatory. |

### Concerns

- **`approval_required = 1` is mandatory at L2.** L2 means "Recommend Actions" — the agent proposes, the human approves. If there's no approval gate, the agent is effectively at L4 (Execute with Guardrails). This is a governance violation in Track 1 processes.
- **`track_crossing = 1` triggers review.** When an agent's output in a Track 2 process enters a Track 1 context (e.g., an ad-hoc analysis appears in a board pack), the track crossing protocol activates. This flag is the trigger.
- **Decision steps don't have agents.** `step_type = 'decision'` means a human decision point. The decision may be *informed* by an agent (prior step), but the decision itself is human.
- **Gateway steps** are BPMN constructs — parallel split, exclusive choice, synchronisation. Include them if the process has non-trivial flow control. Skip them for simple linear processes.

---

## 6. solution_architecture

### What It Is

The ArchiMate Application and Technology layers, merged. Holds application components, services, interfaces, data objects, technology nodes, artifacts, and agent deployments. Also holds knowledge stores as a specialisation.

### ArchiMate Types (CHECK constraint)

`application-component` | `application-collaboration` | `application-interface` | `application-function` | `application-interaction` | `application-event` | `application-service` | `data-object` | `node` | `device` | `system-software` | `technology-collaboration` | `technology-interface` | `technology-function` | `technology-process` | `technology-interaction` | `technology-event` | `technology-service` | `artifact` | `equipment` | `facility` | `distribution-network` | `material`

### Field Instructions — Common Fields

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | Descriptive slug: `comp-foundry-agent`, `tech-ai-search`, `data-safety-index`, `art-safety-owl` |
| `name` | **Required** | "Foundry Agent Service", "Azure AI Search", "Safety Vector Index", "Safety Ontology Extension" |
| `archimate_type` | **Required** | One of the CHECK values above |
| `domain_id` | **Required** | FK to domains |
| `status` | **Required** | `current` \| `target` \| `planned` \| `deprecated` \| `retired` |
| `deployment_status` | Optional | `planned` \| `dev` \| `staging` \| `production`. Operational status, not architectural status. |

### Field Instructions — Subtype: Agent (is_agent = 1)

| Field | Subtype-required | Notes |
|---|---|---|
| `is_agent` | Set to `1` | Flags this as an AI agent |
| `default_autonomy` | **Required** | `L0`–`L5`. Default autonomy level. Can be overridden per process step in `process_steps.agent_autonomy`. |
| `default_track` | **Required** | `Track1` \| `Track2`. Default track. |
| `knowledge_base_ref` | Optional | FK to another solution_architecture element that is the agent's knowledge base |
| `model_ref` | Optional | LLM identifier: `gpt-4o`, `claude-sonnet-4-5`, `granite-3.1-8b-instruct` |
| `promoted_to_actor` | Computed | `0` \| `1`. Set to `1` when agent graduates to business-actor via CoE sign-off. Do not set manually — this is the output of the Autonomy Policy Gateway process. |

### Field Instructions — Subtype: Knowledge Store (is_knowledge_store = 1)

| Field | Subtype-required | Notes |
|---|---|---|
| `is_knowledge_store` | Set to `1` | Flags this as a knowledge store |
| `store_type` | **Required** | `vector` \| `graph` \| `document` \| `hybrid` |
| `config_path` | Optional | Path to configuration in the repo: `/domains/safety/store-config.yaml` |
| `fallback_ref` | Optional | FK to another solution_architecture element — the fallback store if this one is unavailable. Implements the Fabric IQ fallback chain pattern. |
| `ingestion_pipeline_ref` | Optional | FK to the pipeline element that feeds this store |

### Field Instructions — Subtype: Technology Service / Node

| Field | Subtype-required | Notes |
|---|---|---|
| `platform` | Optional | `Azure AI Search` \| `Azure OpenAI` \| `Fabric` \| `Neo4j` \| etc. |
| `environment` | Optional | `dev` \| `test` \| `staging` \| `prod` |
| `provider` | Optional | `Azure` \| `on-premises` \| `hybrid` |
| `region` | Optional | Azure region: `australiaeast` |
| `ga_status` | **Required for technology-service and node** | `ga` \| `preview` \| `deprecated` \| `retired`. Critical for the Fabric IQ/Foundry IQ fallback assessment pattern — architecture decisions depend on knowing which services are GA vs preview. |

### Concerns

- **`ga_status` is architecture-critical.** The Fabric IQ fallback assessment is entirely driven by whether a service is GA or preview. When a preview service moves to GA, update this field and review any governance controls or ADRs that referenced its preview status.
- **An agent is NOT a knowledge store.** A Safety Compliance Agent (`is_agent = 1`) *uses* the Safety Knowledge Store (`is_knowledge_store = 1`). They're separate rows, linked by `knowledge_base_ref` on the agent row. Don't collapse them.
- **The `fallback_ref` chain** enables multi-level fallback: Fabric IQ Ontology → Foundry IQ Knowledge Base → Azure AI Search + AI Foundry → Blob Storage + AI Search. Each element's `fallback_ref` points to the next in the chain. Query the chain with recursive traversal.
- **Application + Technology merge works today.** If a future requirement demands separate governance of application vs technology layers (e.g., different change approval processes), split the table by `archimate_type` prefix. The data is already partitioned by type — the split is mechanical.

---

## 7. implementation

### What It Is

The ArchiMate Implementation and Migration layer. Holds work packages, deliverables, plateaus (target architecture states), and gaps (what's missing between current and target). This is the roadmap layer.

### ArchiMate Types (CHECK constraint)

`work-package` | `deliverable` | `implementation-event` | `plateau` | `gap`

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | Prefix: `WP-001`, `DEL-001`, `PLT-001`, `GAP-001` |
| `name` | **Required** | "Phase 1 Medallion Pipeline Build", "Safety Domain MVP Deliverable", "Phase 2 Target State" |
| `archimate_type` | **Required** | One of the CHECK values above |
| `domain_id` | Optional | Some work packages span domains |
| `solution_id` | Optional | FK to `solutions`. Work packages deliver solutions. |
| `phase` | Optional | `Phase 0` \| `Phase 1` \| `Phase 2` \| `Phase 3`. Aligns with the Knowledge Platform MVP phase progression. |
| `target_date` | Optional | For work packages: when it should be complete |
| `plateau_description` | Optional | For plateaus: what the architecture looks like at this state |

### Concerns

- **Every gap should have a work package addressing it.** PFC governance agents can check this: `SELECT g.* FROM implementation g LEFT JOIN relationships r ON g.id = r.source_id AND r.archimate_type = 'realization-relationship' WHERE g.archimate_type = 'gap' AND r.id IS NULL` → unaddressed gaps.
- **Plateaus describe states, not actions.** "The knowledge layer has two domain stores (Safety, Maintenance) with automated ingestion and retrieval quality ≥85% precision@5" is a plateau. "Build the maintenance knowledge store" is a work package.

---

## 8. relationships

### What It Is

All cross-element relationships in the architecture. Every link between any two elements in any concern table is a row here. The `source_table` / `target_table` fields identify which tables the elements live in. The `archimate_type` field specifies the ArchiMate relationship type.

### Relationship Types (Common)

`composition-relationship` | `aggregation-relationship` | `assignment-relationship` | `realization-relationship` | `serving-relationship` | `access-relationship` | `influence-relationship` | `triggering-relationship` | `flow-relationship` | `specialization-relationship` | `association-relationship`

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | `rel-<source>-<target>-<type>` or generated UUID |
| `source_table` | **Required** | Table name: `motivation`, `strategy`, `business_architecture`, `solution_architecture`, `implementation` |
| `source_id` | **Required** | FK to the source element |
| `target_table` | **Required** | Table name of the target element |
| `target_id` | **Required** | FK to the target element |
| `archimate_type` | **Required** | ArchiMate relationship type |
| `description` | Optional | Human-readable description of the relationship |
| `evidence` | Optional | Quote or section reference supporting this relationship |
| `confidence` | Computed | Agent-set. 0.0–1.0. |

### The UNIQUE Constraint

`UNIQUE(source_id, target_id, archimate_type)` — you can't have two identical relationships. But you CAN have multiple *different* relationship types between the same elements (e.g., an actor is both `assigned-to` a role and `associated-with` a stakeholder).

### Metamodel Validation

Every INSERT is validated against `valid_relationships`. If the combination of `source_archimate_type`, `target_archimate_type`, and `relationship_type` doesn't exist in the lookup table, the relationship is flagged. **Soft warning during extraction, hard fail on Orbus export.**

### Concerns

- **Relationships are directional.** Source → Target has meaning. A business-function *realises* a capability, not the reverse. Get the direction right — the ArchiMate specification defines this.
- **Don't create relationships between entities you're not confident about.** A low-confidence entity linked by a high-confidence relationship creates false precision. If the entity confidence is below 0.5, defer the relationship until the entity is validated.
- **Cross-table joins** require knowing both `source_table` and `target_table`. Query pattern: `SELECT r.*, m.name as source_name FROM relationships r JOIN motivation m ON r.source_id = m.id WHERE r.source_table = 'motivation'`.

---

## 9. valid_relationships

### What It Is

Lookup table seeded from the ArchiMate 3.2 specification's relationship matrix. Defines which relationship types are valid between which element types. Used for metamodel validation on every relationship INSERT.

### Seeding

This table is seeded once during schema initialisation and updated only when the ArchiMate specification changes. The seed data comes from the ArchiMate 3.2 specification Appendix B (Relationship Matrix). Claude Code generates the seed SQL from the specification.

### Concerns

- **This is a reference table, not a managed entity.** Don't extract rows into this table from conversations. Don't modify it during normal operation.
- **Stanmore may need custom extensions.** If the architecture uses relationship types not in the ArchiMate spec (e.g., `fallback-relationship` for knowledge store chains), add them to this table with a `custom` flag. But prefer using ArchiMate-standard types where possible.

---

## 10. governance_controls

### What It Is

The operational binding between a standard (in `practice_artefacts`) and the architecture element it governs. Standards say *what* the governance requires. Controls say *where and how* it's applied, and whether it's currently compliant.

### Not an ArchiMate Element

Governance controls are a PFC management construct, not an ArchiMate type. They don't export to Orbus. They serve the internal governance function of the EA practice.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | `ctrl-<standard-shortcode>-<target-shortcode>`: `ctrl-tcp-bp-incident`, `ctrl-l2ceiling-dom-safety` |
| `name` | **Required** | Human-readable: "Track Crossing Protocol on Incident Investigation" |
| `target_table` | **Required** | CHECK constrained: `business_architecture` \| `solution_architecture` \| `process_steps` \| `strategy` \| `motivation` \| `implementation` |
| `target_id` | **Required** | FK to the governed element |
| `standard_id` | **Required** | FK to `practice_artefacts`. The standard, principle, or NFR that mandates this control. |
| `constraint_id` | Optional | FK to `motivation` (archimate_type = 'constraint'). If the control implements an ArchiMate constraint. |
| `enforcement_type` | **Required** | `automated` \| `manual-audit` \| `self-assessment` \| `approval-gate` |
| `enforcement_mechanism` | Optional | Description of how enforcement works |
| `assessment_frequency` | Optional | `continuous` \| `daily` \| `weekly` \| `monthly` \| `quarterly` \| `annual` |
| `last_assessed` | Computed | Timestamp of last compliance check |
| `compliance_status` | **Required** | `compliant` \| `non-compliant` \| `partially-compliant` \| `not-assessed` \| `exempt` |
| `scope` | Optional | `enterprise` \| `domain` \| `process` \| `step` |
| `domain_id` | **Required** | FK to domains |

### Concerns

- **`target_table` + `target_id` is validated by CHECK constraint on the table name but NOT on the target_id.** Application-level validation must confirm the target_id actually exists in the specified table. Flag for the Claude Code review.
- **Every domain should have at least one control binding its autonomy ceiling.** If `domains.autonomy_ceiling = 'L2'` for Safety, there should be a governance_controls row binding the autonomy ceiling standard to that domain.
- **Compliance status is a point-in-time assertion.** `compliant` today doesn't mean compliant tomorrow. The `assessment_frequency` field defines how often the status should be refreshed. A governance agent (scheduled, UC-10 NFR Compliance Report) can update these.

### Example Row

```
id: ctrl-tcp-bp-incident
name: Track Crossing Protocol on Incident Investigation
target_table: business_architecture
target_id: BP-incident-investigation
standard_id: STD-007
enforcement_type: automated
enforcement_mechanism: process_steps.track_crossing flag triggers provenance tagging and human review gate
assessment_frequency: continuous
compliance_status: compliant
scope: process
domain_id: dom-safety
```

---

## 11. solutions

### What It Is

Portfolio management. A solution groups application components, technology services, and agent deployments to realise business requirements through business services. It bridges "what the business needs" and "what technology delivers."

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | `sol-<domain>-<name>`: `sol-safety-knowledge`, `sol-maintenance-advisor` |
| `name` | **Required** | "Safety Knowledge Platform", "Maintenance Advisory Service" |
| `domain_id` | **Required** | FK to domains |
| `solution_type` | **Required** | `agent-service` \| `platform` \| `integration` |
| `status` | **Required** | `proposed` \| `in-build` \| `deployed` \| `retired` |
| `portfolio_product` | Optional | Product grouping if solutions are grouped into products |
| `business_service_id` | Optional | FK to `business_architecture` (business-service). Which business service this solution delivers. |
| `owner` | Optional | Solution owner role |

### Concerns

- **UML diagrams belong to solutions.** Component, sequence, deployment, class diagrams are solution-level artefacts stored in `solution_diagrams`. No "system-wide component diagram" — each solution owns its own.
- **Deployment chain:** Solution → `solution_deployments` → `deployment_targets` → IaC template path. When a solution changes, PFC governance agents can flag that the corresponding Bicep template may need updating.

---

## 12. solution_components

### What It Is

Junction table linking solutions to their constituent elements in `solution_architecture`. Many-to-many: an Azure AI Search instance can serve multiple solutions; a solution comprises multiple components.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `solution_id` | **Required** | FK to `solutions` |
| `element_id` | **Required** | FK to `solution_architecture` |
| `role_in_solution` | Optional | What role this component plays: `agent-runtime`, `knowledge-base`, `vector-index`, `embedding-service`, `orchestrator`, `frontend` |

### Concerns

- **PK is composite:** `(solution_id, element_id)`. One element can only appear once per solution.

---

## 13. solution_diagrams

### What It Is

UML and architecture diagrams belonging to a specific solution. File references — the actual diagram lives in the repo or wiki.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | `diag-<solution>-<type>`: `diag-sol-safety-component` |
| `solution_id` | **Required** | FK to `solutions` |
| `diagram_type` | **Required** | `component` \| `sequence` \| `deployment` \| `class` \| `activity` |
| `title` | **Required** | "Safety Knowledge Platform — Component Diagram" |
| `file_path` | **Required** | Path to the diagram file in the repo or wiki |
| `notation` | Optional | `UML` \| `ArchiMate` \| `Mermaid` \| `custom` |

---

## 14. deployment_targets

### What It Is

Infrastructure environments where solutions are deployed. Azure subscriptions, resource groups, regions.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | `dt-<env>-<region>`: `dt-prod-aue`, `dt-dev-aue` |
| `name` | **Required** | "Production — Australia East", "Development — Australia East" |
| `environment` | **Required** | `dev` \| `test` \| `staging` \| `prod` |
| `region` | Optional | Azure region: `australiaeast` |
| `subscription` | Optional | Azure subscription identifier |

---

## 15. solution_deployments

### What It Is

Junction table linking solutions to deployment targets. Tracks IaC template paths and deployment status.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `solution_id` | **Required** | FK to `solutions` |
| `target_id` | **Required** | FK to `deployment_targets` |
| `iac_path` | Optional | Path to Bicep/ARM template: `infra/domains/safety/main.bicep` |
| `status` | **Required** | `planned` \| `provisioned` \| `active` \| `decommissioned` |

---

## 16. practice_artefacts

### What It Is

EA practice management artefacts that don't map cleanly to ArchiMate elements. ADRs, NFRs, standards, principles, ideas, strategies. These are the governance instruments — the rules, decisions, and aspirations that constrain and guide the architecture.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | Prefix by type: `PRI-001` (principle), `ADR-001` (decision), `STD-001` (standard), `NFR-001` (nfr), `IDEA-001` (idea) |
| `title` | **Required** | "Specification Imperative", "Use Neo4j for Enterprise Knowledge Graph", "Agent Track Crossing Protocol" |
| `type` | **Required** | `principle` \| `standard` \| `decision` \| `nfr` \| `idea` \| `strategy` |
| `archimate_type` | Optional | Some artefacts map to ArchiMate: principles → `principle`, constraints → `constraint`. Many don't. NULL is fine. |
| `status` | **Required** | `active` \| `draft` \| `superseded` \| `rejected` \| `deferred` |
| `domain_id` | Optional | FK to domains. Enterprise-wide standards use NULL or `dom-enterprise`. |
| `file_path` | Optional | Wiki page or repo path for the full document |
| `summary` | Optional | Brief description |
| `supersedes` | Optional | Self-reference to the artefact this one replaces |

### Concerns

- **Standards vs Principles:** A principle is aspirational and directional ("Specification quality is the bottleneck, not implementation speed"). A standard is prescriptive and enforceable ("Agents at L3+ require CoE sign-off"). Standards get governance controls; principles generally don't (unless they're operationalised via standards).
- **ADRs are decisions, not standards.** "Use Neo4j with n10s" is a decision (ADR). "All knowledge graph implementations must support OWL/SHACL" is a standard. The ADR implements the standard.
- **Ideas are provisional.** `type = 'idea'` is for captured concepts that haven't been assessed yet — "meta-agent definition pattern that spawns new agent types from specifications." Ideas that survive assessment become ADRs, standards, or courses of action.
- **Governance controls bind standards to targets.** Don't put enforcement details in the practice_artefacts row. The standard says "what." The governance_controls row says "where, how, and whether it's compliant."

---

## 17. engagements

### What It Is

Records of formal interactions — workshops, interviews, reviews, observations — that produced architectural knowledge. Provenance for motivation elements. "Where did we learn this?"

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | `ENG-001`, `ENG-002` |
| `title` | **Required** | "Safety Manager Workshop — Feb 2026", "Rob Luhrs Technology Review" |
| `date` | **Required** | ISO date |
| `type` | **Required** | `workshop` \| `interview` \| `review` \| `observation` |
| `context` | Optional | What was being discussed, who was present, key topics |
| `session_id` | Optional | FK to `sessions` if this engagement was captured via a PFC chat session |
| `conversation_summary` | Optional | AI-generated summary of the engagement |

### Concerns

- **Engagements are created by the architect, not by agents.** An agent might help write the summary, but the engagement record represents a real-world event that happened. It's not extracted — it's recorded.
- **Link to sessions when possible.** If a workshop was captured via a PFC chat session (Justin describes what happened, PFC extracts entities), the `session_id` field creates the traceability.

---

## 18. staging_items

### What It Is

The approval queue. Every entity extracted by an agent — whether from a chat conversation or a batch run — lands here first. Nothing goes directly into a concern table. The architect reviews, edits, approves, or rejects via `/triage`.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | Generated UUID |
| `entity_type` | **Required** | The ArchiMate type or PFC type being staged: `stakeholder`, `business-process`, `application-component`, etc. |
| `entity_data` | **Required** | JSON blob containing all the fields for the target table. This is the *proposed* row. |
| `target_table` | **Required** | Which concern table this entity belongs in: `motivation`, `strategy`, `business_architecture`, `solution_architecture`, `implementation` |
| `source_type` | **Required** | `chat` \| `batch-agent` |
| `source_id` | **Required** | FK to `sessions` (if chat) or `agent_runs` (if batch) |
| `trigger_message` | Optional | The user message or context that triggered this extraction |
| `confidence` | Computed | Agent's confidence in the extraction. 0.0–1.0. |
| `status` | **Required** | `staged` \| `approved` \| `rejected` \| `deferred` |
| `reviewed_at` | Computed | Timestamp when the architect made a decision |

### Concerns

- **`target_table` prevents double-booking.** Each staged item knows exactly which concern table it belongs in. When approved, it's INSERTed into that table and only that table. There is no ambiguity about where a concept lives.
- **`entity_data` is the proposed row as JSON.** On approval, the data is validated against the target table's Pydantic model, then INSERTed. On edit, the architect modifies the JSON before approving.
- **Never bypass staging.** Even manually created entities should flow through staging (with confidence = 1.0 and source_type = 'chat') for audit trail consistency. The only exception is reference data (domains, valid_relationships) which is seeded directly.

---

## 19. agent_runs

### What It Is

Execution log for batch agents. What ran, when, how long, how many tokens, what it produced. Operational metadata, not architectural content.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `run_id` | **Required** | Generated UUID |
| `agent_id` | **Required** | Which agent ran. Matches `solution_architecture.id` where `is_agent = 1`. |
| `status` | **Required** | `running` \| `completed` \| `failed` |
| `input_path` | Optional | What was fed to the agent (file path, wiki page, etc.) |
| `output_path` | Optional | Where the agent's output was stored |
| `entities_extracted` | Computed | Count of staging_items produced by this run |
| `duration_ms` | Computed | Execution time |
| `tokens_used` | Computed | Total token consumption |
| `model_used` | Computed | Which LLM model: `claude-sonnet-4-5`, `gpt-4o` |
| `started_at` | Computed | Timestamp |
| `completed_at` | Computed | Timestamp |

---

## 20. sessions

### What It Is

Semantic summary of a Chainlit chat session. Enriched beyond Phase 0 to capture the architectural meaning of conversations — topics discussed, themes touched, decisions made or deferred, elements referenced. The bridge between raw transcripts (Chainlit) and discrete entities (staging_items).

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `session_id` | **Required** | Chainlit session identifier |
| `started_at` | Computed | Session start |
| `ended_at` | Computed | Session end |
| `entities_staged` | Computed | Count of staging_items produced |
| `items_approved` | Computed | Count approved during this session |
| `items_rejected` | Computed | Count rejected |
| `summary` | Computed | Wrap agent's prose summary. Human-readable narrative of what happened. |
| `topics` | Computed | JSON array of architectural topics: `["neo4j-vs-fabric-iq", "ontology-compliance", "phase-2-gate"]` |
| `architectural_themes` | Computed | JSON array of ArchiMate concerns touched: `["technology-service", "artifact", "gap"]` |
| `decisions_made` | Computed | JSON: `[{"decision": "Use Neo4j for KG", "rationale": "OWL/SHACL required", "ref": "ADR-008"}]` |
| `decisions_deferred` | Computed | JSON: `[{"topic": "Fabric IQ adoption", "lean": "defer", "reason": "preview only", "revisit_trigger": "Phase 2 gate"}]` |
| `elements_discussed` | Computed | JSON array of element IDs referenced or relevant to the conversation |
| `domain_ids` | Computed | JSON array of domain IDs this session touched |
| `engagement_ref` | Optional | FK to `engagements` if this session captures a formal meeting |
| `semantic_summary` | Computed | ~100-word summary optimised for embedding and vector search. Emphasises architectural concepts, element names, relationship types, decision context. Not the same as `summary`. |

### Who Owns This

The `/wrap` agent (UC: Session Wrap-up) runs at session end. It reads the Chainlit transcript and populates all computed fields. Entity extraction (UC-1) produces `staging_items`. The wrap agent produces the session record. Different outputs from the same raw conversation.

### Concerns

- **`semantic_summary` is for machines, `summary` is for humans.** The semantic summary is a dense paragraph written specifically for embedding and retrieval. When a future session asks "what did we discuss about the ontology layer?", the semantic_summary is what gets matched.
- **`decisions_deferred` is architecturally valuable.** A governance agent (scheduled) can scan for deferred decisions whose `revisit_trigger` condition has been met and surface them for review.
- **Don't over-extract topics.** The wrap agent should identify 3–7 substantive topics per session, not tag every noun. Topics should be findable and meaningful.

---

## 21. quality_evaluations

### What It Is

Structured measurement of how well architectural elements perform. Supports the phase-gating pattern: Phase 0 baseline → Phase 1 improvement threshold → Phase 2 comparative benchmark. Where T09 vs T11 results from the Knowledge Platform MVP live.

### Field Instructions

| Field | Type | Notes |
|---|---|---|
| `id` | **Required** | `eval-<domain>-<type>-<label>`: `eval-safety-retrieval-baseline`, `eval-safety-retrieval-di-chunking` |
| `name` | **Required** | "Safety Domain Retrieval Baseline — Phase 0" |
| `target_table` | **Required** | CHECK constrained. What was evaluated — typically `solution_architecture` or `solutions`. |
| `target_id` | **Required** | FK to the evaluated element |
| `domain_id` | **Required** | FK to domains |
| `evaluation_type` | **Required** | `retrieval` \| `generation` \| `end-to-end` \| `latency` \| `cost` |
| `phase` | **Required** | `Phase 0` \| `Phase 1` \| `Phase 2`. Which phase this evaluation belongs to. |
| `baseline_ref` | Optional | FK to a prior quality_evaluations row. Chains evaluations for trend tracking. Phase 1 eval references Phase 0 baseline. |
| `methodology` | Optional | Reference to the test protocol document. "Foundry IQ Retrieval Performance Evaluation — Section 3" |
| `metrics` | **Required** | JSON: `{"precision_at_5": 0.72, "latency_p50_ms": 340, "hallucination_rate": 0.05, "completeness": 0.68}` |
| `pass_fail` | **Required** | `pass` \| `fail` \| `inconclusive` |
| `summary` | Optional | Human-readable finding: "Baseline retrieval achieves 72% precision@5. Table-heavy documents underperform." |
| `decision_ref` | Optional | FK to `practice_artefacts`. If this evaluation drove an ADR. T20 in the MVP plan is an ADR driven by T09 vs T11 evaluation results. |
| `evaluated_by` | **Required** | Person or agent who ran the evaluation |
| `evaluated_at` | **Required** | When the evaluation was performed |

### Concerns

- **`baseline_ref` chaining is the trend mechanism.** Phase 0 eval has no baseline_ref. Phase 1 eval references Phase 0. Phase 2 eval references Phase 1. Query the chain to show improvement (or regression) across phases.
- **`pass_fail` is determined by the phase gate criteria.** The Knowledge Platform MVP defines: Phase 0 → baseline documented (pass if eval exists). Phase 1 → retrieval quality improvement >15% vs baseline (pass if metrics show >15% improvement). Phase 2 → Granite vs GPT-4o benchmark complete (pass if comparative metrics exist).
- **`metrics` is JSON because metrics vary by evaluation type.** Retrieval evaluations track precision, recall, latency, hallucination rate. Generation evaluations track groundedness, relevance, coherence. Cost evaluations track token consumption and dollar cost per query. Don't try to normalise these into columns.

### Example Row

```
id: eval-safety-retrieval-baseline
name: Safety Domain Retrieval Baseline — Phase 0
target_table: solution_architecture
target_id: comp-safety-knowledge-store
domain_id: dom-safety
evaluation_type: retrieval
phase: Phase 0
baseline_ref: NULL
methodology: Foundry IQ Retrieval Performance Evaluation — Section 3.2
metrics: {"precision_at_5": 0.72, "latency_p50_ms": 340, "hallucination_rate": 0.05, "completeness": 0.68, "citation_accuracy": 0.81}
pass_fail: pass
summary: Baseline retrieval achieves 72% precision@5 with default Foundry IQ chunking. Table-heavy documents score 0.45 — significant underperformance vs text-only docs (0.88).
decision_ref: NULL
evaluated_by: architect
evaluated_at: 2026-03-15
```

---

## Appendix A: Recommended Convenience Views

```sql
-- Motivation subtypes
CREATE VIEW v_stakeholders AS SELECT id, name, role, influence_level, domain_id, status FROM motivation WHERE archimate_type = 'stakeholder';
CREATE VIEW v_drivers AS SELECT id, name, driver_category, domain_id, status FROM motivation WHERE archimate_type = 'driver';
CREATE VIEW v_assessments AS SELECT id, name, evidence, impact, domain_id, status FROM motivation WHERE archimate_type = 'assessment';
CREATE VIEW v_goals AS SELECT id, name, horizon, domain_id, status FROM motivation WHERE archimate_type = 'goal';
CREATE VIEW v_business_requirements AS SELECT id, name, category, description, domain_id, status FROM motivation WHERE archimate_type = 'requirement' AND requirement_type = 'business';
CREATE VIEW v_solution_requirements AS SELECT id, name, category, threshold, target, acceptance_criteria, solution_id, domain_id, status FROM motivation WHERE archimate_type = 'requirement' AND requirement_type = 'solution';
CREATE VIEW v_nfrs AS SELECT id, name, category, threshold, target, domain_id, status FROM motivation WHERE archimate_type = 'requirement' AND requirement_type = 'nfr';
CREATE VIEW v_constraints AS SELECT id, name, description, domain_id, status FROM motivation WHERE archimate_type = 'constraint';

-- Strategy subtypes
CREATE VIEW v_capabilities AS SELECT id, name, parent_id, level, maturity, domain_id, status FROM strategy WHERE archimate_type = 'capability';
CREATE VIEW v_value_streams AS SELECT id, name, stages, value_proposition, domain_id, status FROM strategy WHERE archimate_type = 'value-stream';
CREATE VIEW v_courses_of_action AS SELECT id, name, horizon, traces_to_goal, domain_id, status FROM strategy WHERE archimate_type = 'course-of-action';

-- Business architecture subtypes
CREATE VIEW v_actors AS SELECT id, name, actor_type, domain_id, status FROM business_architecture WHERE archimate_type = 'business-actor';
CREATE VIEW v_agent_actors AS SELECT id, name, domain_id, status FROM business_architecture WHERE archimate_type = 'business-actor' AND actor_type = 'agent';
CREATE VIEW v_roles AS SELECT id, name, agent_augmented, augmentation_level, domain_id, status FROM business_architecture WHERE archimate_type = 'business-role';
CREATE VIEW v_processes AS SELECT id, name, track, governance_level, trigger_event, process_owner_id, domain_id, status FROM business_architecture WHERE archimate_type = 'business-process';
CREATE VIEW v_functions AS SELECT id, name, parent_id, domain_id, status FROM business_architecture WHERE archimate_type = 'business-function';
CREATE VIEW v_business_services AS SELECT id, name, service_type, consumer, domain_id, status FROM business_architecture WHERE archimate_type = 'business-service';
CREATE VIEW v_business_objects AS SELECT id, name, has_authority_scoring, classification, domain_id, status FROM business_architecture WHERE archimate_type = 'business-object';

-- Solution architecture subtypes
CREATE VIEW v_agents AS SELECT id, name, default_autonomy, default_track, knowledge_base_ref, model_ref, promoted_to_actor, domain_id, status FROM solution_architecture WHERE is_agent = 1;
CREATE VIEW v_knowledge_stores AS SELECT id, name, store_type, config_path, fallback_ref, ingestion_pipeline_ref, domain_id, status FROM solution_architecture WHERE is_knowledge_store = 1;
CREATE VIEW v_technology_services AS SELECT id, name, platform, environment, provider, region, ga_status, domain_id, status FROM solution_architecture WHERE archimate_type = 'technology-service';

-- Governance
CREATE VIEW v_non_compliant_controls AS SELECT gc.*, pa.title as standard_name FROM governance_controls gc JOIN practice_artefacts pa ON gc.standard_id = pa.id WHERE gc.compliance_status = 'non-compliant';
CREATE VIEW v_uncontrolled_processes AS SELECT ba.id, ba.name, ba.track, ba.domain_id FROM business_architecture ba LEFT JOIN governance_controls gc ON gc.target_table = 'business_architecture' AND gc.target_id = ba.id WHERE ba.archimate_type = 'business-process' AND gc.id IS NULL;
```

---

## Appendix B: Pydantic Validation Rules Summary

The wide-table nullable pattern requires application-level validation. Each `archimate_type` value maps to a Pydantic model that enforces which fields are **required**, **optional**, or **forbidden** for that type.

| archimate_type | Required fields (beyond common) | Forbidden fields |
|---|---|---|
| `stakeholder` | role | threshold, target, acceptance_criteria, requirement_type, driver_category, evidence, impact, horizon |
| `driver` | driver_category | role, influence_level, threshold, target, acceptance_criteria, requirement_type, horizon |
| `assessment` | evidence | role, influence_level, threshold, target, acceptance_criteria, requirement_type, horizon |
| `goal` | horizon | role, influence_level, threshold, target, acceptance_criteria, requirement_type, driver_category, evidence |
| `requirement` (business) | requirement_type='business' | role, influence_level, driver_category, evidence, impact, horizon, solution_id |
| `requirement` (solution) | requirement_type='solution', acceptance_criteria | role, influence_level, driver_category, evidence, impact, horizon |
| `capability` | — | stages, value_proposition, traces_to_goal |
| `value-stream` | stages | parent_id, level, maturity, traces_to_goal |
| `course-of-action` | horizon, traces_to_goal | parent_id, level, maturity, stages |
| `business-actor` | actor_type | agent_augmented, track, governance_level, has_authority_scoring |
| `business-role` | — | actor_type, track, governance_level, has_authority_scoring |
| `business-process` | track | actor_type, agent_augmented, has_authority_scoring |
| `business-object` | — | actor_type, agent_augmented, track, governance_level |
| Agent (is_agent=1) | default_autonomy, default_track | store_type, config_path, fallback_ref |
| Knowledge store (is_knowledge_store=1) | store_type | default_autonomy, default_track, model_ref |

This table drives the Pydantic model generation in Claude Code. Each row becomes a discriminated union variant.

---

*Stanmore Resources | Technology — Enterprise Systems | March 2026*
*PFC Entity Reference — Ready for Technical Review*
