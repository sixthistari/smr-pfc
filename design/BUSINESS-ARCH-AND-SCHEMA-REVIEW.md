# PFC Schema Extension Brief — Business Architecture, Portfolio, and Motivation Layer

**Stanmore Resources** | Technology — Enterprise Systems

| | |
|---|---|
| **Document Owner** | Justin Hume — Enterprise Architect, AI & Advanced Analytics |
| **Status** | Ready for Technical Review |
| **Date** | March 2026 |
| **Parent** | PFC REQUIREMENTS.md, Section 3 (Data Model) |
| **Supersedes** | Earlier brief version (pre-schema-review) |
| **Inputs** | PFC Schema Review — ArchiMate Metamodel Alignment (Option C adopted) |

---

## 1. Problem Statement

The PFC Phase 0 schema covers extraction and staging well but has three structural problems identified in the schema review:

**Double-booking risk.** The hybrid approach (generic `elements` table + dedicated tables for stakeholders, drivers, needs, etc.) allows the same concept to exist in two places with no constraint preventing it. Two agents or two humans writing to the same database will create duplicates.

**No layer-specific attributes.** A Business Process has attributes a Technology Node doesn't — trigger type, process owner, track classification, automation level. The generic `elements` table can't capture these without a JSON blob, which defeats the relational schema.

**No metamodel enforcement.** ArchiMate defines which relationship types are valid between which element types. The current schema allows any element to relate to any other. Agents will create invalid relationships, discovered only at Orbus import time.

Beyond these structural issues, the schema has no Business Architecture layer — and Justin will be engaging business stakeholders within weeks. Every conversation surfaces processes, functions, actors, roles, and services. Without schema support, extracted entities get shoehorned into the wrong types or lost. The spec-driven approach only works if the spec can receive what the business gives you.

---

## 2. Adopted Schema Structure — Option C (Tables Per Concern)

Based on the schema review, the PFC adopts **Option C: tables grouped by architectural concern**, not by individual ArchiMate element type and not as a single generic bag.

### 2.1 Table Architecture

| Table | What It Holds | ArchiMate Coverage |
|---|---|---|
| `motivation` | Stakeholders, Drivers, Assessments, Goals, Outcomes, Principles, Constraints | Motivation layer (complete) |
| `strategy` | Capabilities (hierarchical), Value Streams (with stages), Resources, Courses of Action | Strategy layer (complete) |
| `business_architecture` | Processes, Functions, Services, Actors, Roles, Objects, Events | Business layer |
| `solution_architecture` | Application Components, Services, Interfaces, Data Objects, Technology Nodes, Artifacts, Agent deployments | Application + Technology layers (merged) |
| `implementation` | Work Packages, Deliverables, Plateaus, Gaps | Implementation & Migration layer |
| `domains` | Domain definitions with governance attributes | Cross-cutting (first-class entity, not a text field) |
| `relationships` | All cross-element relationships with metamodel validation | All ArchiMate relationship types |
| `practice_artefacts` | ADRs, NFR register, standards, ideas | Non-ArchiMate EA practice management |
| `engagements` | Workshops, interviews, reviews | Non-ArchiMate provenance/audit |
| `solutions` | Solution portfolio — groups components into delivery units | Cross-layer (portfolio management) |
| `staging_items` | Agent-extracted entities awaiting human review | Pipeline management |
| `agent_runs` / `sessions` | Operational metadata | Tool management |

### 2.2 Common Fields on All Concern Tables

Every concern table (motivation, strategy, business_architecture, solution_architecture, implementation) shares a common field set:

```sql
id TEXT PRIMARY KEY,
name TEXT NOT NULL,
archimate_type TEXT NOT NULL,       -- constrained to valid types for this table
domain_id TEXT REFERENCES domains(id),
status TEXT,
description TEXT,
source_spec TEXT,                   -- wiki page path where defined
confidence REAL DEFAULT 1.0,        -- 1.0 manual, <1.0 agent-extracted
created_by TEXT,
created_at TEXT DEFAULT CURRENT_TIMESTAMP,
updated_at TEXT DEFAULT CURRENT_TIMESTAMP
```

Layer-specific fields are additional columns, nullable where not all element types in that table need them. A `CHECK` constraint on `archimate_type` restricts each table to its valid ArchiMate types.

### 2.3 Eliminating Double-Booking

The dedicated tables from Phase 0 (`stakeholders`, `drivers`, `needs`, `requirements`, `capabilities`, `elements`) are **replaced**, not supplemented. Migration is mechanical:

- `stakeholders` → rows in `motivation` with `archimate_type = 'stakeholder'`
- `drivers` → rows in `motivation` with `archimate_type = 'driver'`
- `needs` → rows in `motivation` with `archimate_type = 'goal'` (renamed — see Section 3)
- `requirements` → rows in `motivation` with `archimate_type = 'requirement'`
- `capabilities` → rows in `strategy` with `archimate_type = 'capability'`
- `elements` → split by `archimate_type` into the appropriate concern table
- `element_capabilities` → rows in `relationships` with `archimate_type = 'realization-relationship'`

No concept lives in two places. One table per concern. One row per entity.

---

## 3. Motivation Layer — Revised Chain

### 3.1 Full Chain

```
Stakeholder ──association──► Driver ──association──► Assessment ──association──► Goal
                                                                                  │
                                                                      realization │
                                                                                  ▼
                                                                   Business Requirement
                                                                          │
                                                                realization │
                                                                          ▼
                                                              Solution Requirement
                                                                     │
                                                           realization │
                                                                     ▼
                                                              Element (any layer)
```

### 3.2 Concept Definitions

**Driver**: An internal or external condition that creates pressure or opportunity. Observable facts. "Multiple versions of safety procedures exist across SharePoint sites." "MSHA regulatory change frequency is increasing."

**Assessment** (new): The analytical bridge between a driver and a response. Evaluates a driver in organisational context. "Our current manual process can't keep up with regulatory change frequency — 40% of retrieved procedures are superseded versions, creating compliance risk." This is where architectural judgement lives. Without it, the model jumps from "pressure exists" to "we want this outcome" with no recorded reasoning.

**Goal** (new): A longer-term aspiration spanning planning horizons. "Stanmore has a self-service knowledge platform enabling any employee to find authoritative information within 30 seconds." Goals feed into vision and horizons (H1: 0–12 months, H2: 12–36 months, H3: 36+). Deliberately aspirational — they set direction, may never be fully achieved.

**Business Requirement** (renamed from Need): What the stakeholder requires, in business terms, solution-independent. "I need to find the current version of a safety procedure quickly." Survives regardless of implementation. If the entire tech stack changed tomorrow, the business requirement persists.

**Solution Requirement** (renamed from Requirement): A testable attribute of a specific solution. "The RAG pipeline shall return the authoritative document version with >85% precision@5." Changes when the solution changes. Has acceptance criteria.

**Principle**: Kept in `practice_artefacts` table, not in the motivation chain. Principles are normative statements that constrain the architecture broadly ("Specifications, not code, are the primary asset"). Where a principle constrains a specific requirement, model the relationship in the `relationships` table.

### 3.3 Motivation Table Schema

```sql
CREATE TABLE motivation (
    -- Common fields
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL CHECK (archimate_type IN (
        'stakeholder', 'driver', 'assessment', 'goal', 'outcome',
        'requirement', 'constraint', 'meaning', 'value'
    )),
    domain_id TEXT REFERENCES domains(id),
    status TEXT,
    description TEXT,
    source_spec TEXT,
    confidence REAL DEFAULT 1.0,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Stakeholder-specific
    role TEXT,                               -- stakeholder role/title
    influence_level TEXT,                    -- high | medium | low

    -- Driver-specific
    driver_category TEXT,                   -- internal | external | regulatory

    -- Assessment-specific
    evidence TEXT,                           -- data/observations supporting the assessment
    impact TEXT,                             -- what happens if unaddressed

    -- Goal-specific
    horizon TEXT,                            -- H1 | H2 | H3

    -- Requirement-specific (business and solution)
    requirement_type TEXT,                  -- business | solution | non-functional
    category TEXT,                          -- performance | security | usability | etc
    threshold TEXT,                         -- minimum acceptable
    target TEXT,                            -- desired level
    acceptance_criteria TEXT,               -- JSON array
    solution_id TEXT,                        -- FK to solutions (solution reqs only)
    nfr_ref TEXT,                            -- link to NFR in practice_artefacts

    -- Engagement provenance
    engagement_ref TEXT REFERENCES engagements(id)
);
```

Nullable layer-specific columns. Not every row uses every column. The `archimate_type` discriminator tells you which fields are relevant. Simple, queryable, no double-booking.

---

## 4. Business Architecture Layer

### 4.1 Why Now

Agent governance depends on process context. The dual-track model and autonomy levels (L0–L5) are defined in terms of business processes. An agent's autonomy ceiling is set by the process it operates within. Without processes in the model, agent governance is a policy document rather than an enforceable architectural constraint.

### 4.2 Business Architecture Table Schema

```sql
CREATE TABLE business_architecture (
    -- Common fields
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL CHECK (archimate_type IN (
        'business-actor', 'business-role', 'business-collaboration',
        'business-interface', 'business-process', 'business-function',
        'business-interaction', 'business-event', 'business-service',
        'business-object', 'contract', 'representation', 'product'
    )),
    domain_id TEXT REFERENCES domains(id),
    status TEXT,
    description TEXT,
    source_spec TEXT,
    confidence REAL DEFAULT 1.0,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Hierarchy (actors, functions, processes can nest)
    parent_id TEXT REFERENCES business_architecture(id),

    -- Actor-specific
    actor_type TEXT,                         -- person | team | org-unit | agent
    -- NOTE: actor_type = 'agent' only under Autonomy Policy conditions (see Section 5)

    -- Role-specific
    agent_augmented INTEGER DEFAULT 0,      -- 1 if an agent augments this role
    augmentation_level TEXT,                -- L0-L5 when augmented

    -- Process-specific
    track TEXT,                             -- Track1 | Track2
    governance_level TEXT,                  -- formal | standard | lightweight
    trigger_event TEXT,                     -- what initiates this process
    process_owner_id TEXT,                  -- FK to a business-role row in this table

    -- Service-specific
    service_type TEXT,                      -- internal | external
    consumer TEXT,                          -- who uses this service
    sla TEXT,

    -- Object-specific
    has_authority_scoring INTEGER DEFAULT 0, -- 1 if document authority applies
    classification TEXT                     -- sensitivity/handling classification
);
```

### 4.3 Process Steps (Dedicated Table)

Process steps need their own table because they are ordered sequences within a process, not standalone architectural elements. They reference business_architecture rows but have step-specific attributes:

```sql
CREATE TABLE process_steps (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL REFERENCES business_architecture(id),
    sequence INTEGER NOT NULL,
    name TEXT NOT NULL,
    step_type TEXT NOT NULL,                -- human | agent | system | decision | gateway
    role_id TEXT,                            -- FK to business-role in business_architecture
    agent_id TEXT,                           -- FK to agent in solution_architecture (if step_type = 'agent')
    agent_autonomy TEXT,                    -- L0-L5, only if step_type includes agent involvement
    description TEXT,
    input_objects TEXT,                      -- JSON array of business-object IDs
    output_objects TEXT,                     -- JSON array of business-object IDs
    approval_required INTEGER DEFAULT 0,    -- 1 if human approval gate
    track_crossing INTEGER DEFAULT 0        -- 1 if output may enter a formal process
);
```

### 4.4 Key Business Layer Concepts

**Business Actor**: Who does the work. Safety Manager, Maintenance Planner, Geology Team, AI Centre of Excellence. Concrete — exists on an org chart. Distinguished from Motivation-layer Stakeholders: a Stakeholder has interests, a Business Actor performs functions.

**Business Role**: The hat an actor wears in a specific context. A Safety Manager acts as "Procedure Reviewer" during document governance and "Incident Investigator" during incident response. Roles are the attachment point for agent augmentation — "the Safety Agent augments the Incident Investigator role at L2."

**Business Function**: A grouping of work by competency. Safety Management, Production Planning, Maintenance Management. Functions realise capabilities. Relatively stable — change when the organisation restructures, not when processes change.

**Business Process**: How work flows, with steps, decisions, inputs, outputs. The dual-track model materialises here. Track 1 processes are formally governed. Track 2 processes are loosely defined. Processes are the primary unit of agent deployment — autonomy level is set per process step, not globally.

**Business Service**: What the organisation offers to consumers. "Safety Advisory Service," "Knowledge Retrieval Service." In the portfolio, a service is the gateway to an agentic application. Business users consume services; solutions deliver them.

**Business Object**: Things that flow through processes. Safety Procedure, Work Order, Incident Report, Geological Survey. What agents read, create, transform, validate. Primary candidates for document authority scoring.

---

## 5. Agent Identity in the Business Layer — The Autonomy Policy Gateway

### 5.1 The Question

Should agents be modelled as business actors (they perform work) or as technology components assigned to process steps (they are tools used by human actors)?

### 5.2 The Answer: Conditional, Governed by Autonomy Policy

Agents do not automatically belong in the business layer. An agent is, by default, an application-component in `solution_architecture`. It is a tool. A human actor uses it within a process step, the way a human uses a spreadsheet or a database.

An agent **graduates to the business layer** — modelled as a `business-actor` with `actor_type = 'agent'` — only when it meets specific conditions defined in the Autonomy Policy:

| Condition | Rationale |
|---|---|
| Operating at **L3 or above** (Execute in Sandbox or higher) | Below L3, the agent suggests or drafts. A human executes. The agent has no independent action that requires identity governance. At L3+, the agent takes actions — even sandboxed ones — that need traceability to an identity. |
| Assigned to a **defined process step** with `step_type = 'agent'` | Free agents (Track 2, ad-hoc usage) don't need actor status. They're tools. An agent that occupies a process step has a role in a workflow, and that role needs the same governance as a human role: authorisations, controls, audit trail. |
| Has a **formal role assignment** in `business_architecture` | If the agent has a business-role (e.g., "Automated Compliance Checker"), it needs actor status to hold that role. The role brings authorisations and constraints — the same way a human actor holding the "Incident Investigator" role has defined authorities. |
| Approved through **AI CoE architectural sign-off** | No agent self-promotes. The decision to elevate an agent to actor status is a governance decision made by the AI Centre of Excellence, documented as an ADR in `practice_artefacts`. |

### 5.3 What Actor Status Gives an Agent

When an agent is modelled as a business-actor:

- **Identity**: It has a named identity in the architecture. "Safety Compliance Agent" is not just a component — it's an actor that participates in processes, holds roles, and has authorisations.
- **Role assignment**: It can be assigned to business-roles via `relationships`. The role defines what it can do, just as it does for a human.
- **Authorisation scope**: The role carries authorisation boundaries — what data it can access, what actions it can perform, what systems it can write to.
- **Audit trail**: Actions taken by the agent are attributable to a named actor, not just a generic "system" entry in a log.
- **Process participation**: It appears in process step diagrams as a named participant, not an anonymous tool call.

### 5.4 What This Means for the Dual-Track Model

**Track 1 processes** (formal, governed): An agent in a Track 1 process step is almost certainly at L2 (Recommend Actions) with a human approval gate before any external effect. It may hold a business-role but does not need actor status at L2 — it's augmenting a human actor, not replacing one. If a Track 1 agent reaches L3+ (sandbox execution with promotion gate), it needs actor status because it's taking independent action within a governed workflow. This requires a formal safety case.

**Track 2 processes** (informal, ad-hoc): An agent in Track 2 at L3–L4 is more autonomous but less governed. It may not need actor status if it's a free agent performing ad-hoc tasks — the Knowledge & Research Agent at L4, for example, is a tool the architect uses, not an actor in a process. However, if a Track 2 agent's output routinely crosses into Track 1 territory (the track crossing protocol), that pattern should trigger a review of whether the agent needs actor status and formal process step assignment.

**The boundary**: Actor status is not about capability — it's about accountability. An agent gets actor status when the architecture needs to hold it accountable as a participant in governed work, not just traceable as a tool that was invoked.

### 5.5 Autonomy Policy Update Required

The existing L0–L5 autonomy level definitions should be extended with a governance metadata section:

```yaml
# Addition to autonomy policy
agent_identity_governance:
  actor_threshold: "L3"             # minimum level for business-actor eligibility
  requires_process_assignment: true # must be in a defined process step
  requires_role_assignment: true    # must hold a business-role
  requires_coe_signoff: true        # AI CoE must approve via ADR
  review_triggers:
    - "Agent output enters Track 1 process more than 3 times in 30 days"
    - "Agent autonomy level promoted above L2"
    - "New process step created with step_type = 'agent'"
```

---

## 6. Strategy Layer

### 6.1 Schema

```sql
CREATE TABLE strategy (
    -- Common fields
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL CHECK (archimate_type IN (
        'capability', 'value-stream', 'resource', 'course-of-action'
    )),
    domain_id TEXT REFERENCES domains(id),
    status TEXT,
    description TEXT,
    source_spec TEXT,
    confidence REAL DEFAULT 1.0,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Capability-specific (hierarchical)
    parent_id TEXT REFERENCES strategy(id),
    level INTEGER,                          -- depth in hierarchy (0 = root)
    maturity TEXT,                          -- initial | defined | managed | optimised

    -- Value-stream-specific
    stages TEXT,                             -- JSON array of stage definitions
    value_proposition TEXT,

    -- Course-of-action-specific
    horizon TEXT,                            -- H1 | H2 | H3
    traces_to_goal TEXT                     -- FK to motivation row (goal)
);
```

### 6.2 Value Streams

Value streams are explicitly called out in Justin's JD accountabilities: "Identify and map enterprise value chains and value streams." A value stream is not just a capability — it has sequential stages, each consuming and producing value. The `stages` JSON field stores the ordered stage definitions. Cross-references to capabilities and domains are modelled in the `relationships` table.

### 6.3 Course of Action

The strategic bridge between motivation ("why") and implementation ("how we'll get there"). "Invest in a federated knowledge platform to address document retrieval deficiencies" is a course of action. It links a goal to the capabilities and resources needed to achieve it. Distinct from ADRs (which are implementation decisions) — Course of Action is strategic direction.

---

## 7. Solution Architecture Layer

### 7.1 Schema

```sql
CREATE TABLE solution_architecture (
    -- Common fields
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL CHECK (archimate_type IN (
        'application-component', 'application-collaboration',
        'application-interface', 'application-function',
        'application-interaction', 'application-event',
        'application-service', 'data-object',
        'node', 'device', 'system-software',
        'technology-collaboration', 'technology-interface',
        'technology-function', 'technology-process',
        'technology-interaction', 'technology-event',
        'technology-service', 'artifact',
        'equipment', 'facility', 'distribution-network', 'material'
    )),
    domain_id TEXT REFERENCES domains(id),
    status TEXT,
    description TEXT,
    source_spec TEXT,
    confidence REAL DEFAULT 1.0,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Application-component-specific
    version TEXT,
    deployment_status TEXT,                 -- planned | dev | staging | production
    tier TEXT,                              -- presentation | logic | data

    -- Agent-specific (subset of application-component)
    is_agent INTEGER DEFAULT 0,             -- 1 if this is an AI agent
    default_autonomy TEXT,                  -- L0-L5 default (can be overridden per process step)
    default_track TEXT,                     -- Track1 | Track2 default
    knowledge_base_ref TEXT,                -- FK to knowledge base element
    model_ref TEXT,                         -- LLM model identifier
    promoted_to_actor INTEGER DEFAULT 0,    -- 1 if graduated to business-actor (see Section 5)

    -- Knowledge-store-specific (subset of data-object / application-component)
    is_knowledge_store INTEGER DEFAULT 0,   -- 1 if this is a knowledge store
    store_type TEXT,                         -- vector | graph | document | hybrid
    config_path TEXT,                        -- path to store configuration in repo
    fallback_ref TEXT,                       -- FK to fallback store element (fallback chain)
    ingestion_pipeline_ref TEXT,             -- FK to pipeline element that feeds this store

    -- Technology-specific
    platform TEXT,
    environment TEXT,                       -- dev | test | staging | prod
    provider TEXT,                          -- Azure | on-premises | hybrid
    region TEXT,
    ga_status TEXT,                          -- ga | preview | deprecated | retired

    -- Interface-specific
    protocol TEXT,
    sla TEXT
);
```

### 7.2 Application + Technology Merged

Stanmore doesn't need the distinction between Application and Technology as separate tables yet. The workload is Azure-native, the team is small, and the architectural questions are about solutions (which span both layers), not about application-vs-technology boundaries. The `archimate_type` field preserves the distinction for ArchiMate export and Orbus import. If the distinction becomes operationally important later, the table splits cleanly by `archimate_type` prefix.

### 7.3 Knowledge Store Specialisation

The SIS Brain knowledge layer is the primary thing being built. Knowledge stores — the Safety Knowledge Store, its ontology extension, its authority rules, the vector indexes, the graph store — are central architectural elements. They need attributes that generic application components don't: store type (vector vs graph vs document), configuration paths, fallback chains, ingestion pipeline references.

Rather than a separate `knowledge_stores` table (which would reintroduce the proliferation problem Option C solved), knowledge stores are modelled as `solution_architecture` rows with `is_knowledge_store = 1`. The knowledge-layer-specific columns are nullable on the table but validated by the Pydantic model for knowledge store entities. Same pattern as `is_agent` for agent-specific columns.

A Safety Knowledge Store is an `application-component` with `is_knowledge_store = 1`, `store_type = 'hybrid'` (vector + document), `config_path = '/domains/safety/store-config.yaml'`, `fallback_ref` pointing to the Blob Storage + AI Search fallback element (per the Fabric IQ fallback assessment). Its ontology extension is an `artifact` with a file path to the OWL/SHACL definitions. Both are grouped under the Safety Knowledge solution via `solution_components`.

Convenience view: `CREATE VIEW v_knowledge_stores AS SELECT * FROM solution_architecture WHERE is_knowledge_store = 1;`

### 7.4 Convenience Views for Type Safety

The wide-table nullable column pattern trades structural type safety for structural simplicity. The compensation mechanism is views and Pydantic validation:

```sql
-- Per-type views for query ergonomics
CREATE VIEW v_stakeholders AS SELECT * FROM motivation WHERE archimate_type = 'stakeholder';
CREATE VIEW v_drivers AS SELECT * FROM motivation WHERE archimate_type = 'driver';
CREATE VIEW v_assessments AS SELECT * FROM motivation WHERE archimate_type = 'assessment';
CREATE VIEW v_goals AS SELECT * FROM motivation WHERE archimate_type = 'goal';
CREATE VIEW v_business_requirements AS SELECT * FROM motivation WHERE archimate_type = 'requirement' AND requirement_type = 'business';
CREATE VIEW v_solution_requirements AS SELECT * FROM motivation WHERE archimate_type = 'requirement' AND requirement_type = 'solution';

CREATE VIEW v_capabilities AS SELECT * FROM strategy WHERE archimate_type = 'capability';
CREATE VIEW v_value_streams AS SELECT * FROM strategy WHERE archimate_type = 'value-stream';

CREATE VIEW v_processes AS SELECT * FROM business_architecture WHERE archimate_type = 'business-process';
CREATE VIEW v_actors AS SELECT * FROM business_architecture WHERE archimate_type = 'business-actor';
CREATE VIEW v_roles AS SELECT * FROM business_architecture WHERE archimate_type = 'business-role';
CREATE VIEW v_functions AS SELECT * FROM business_architecture WHERE archimate_type = 'business-function';
CREATE VIEW v_business_services AS SELECT * FROM business_architecture WHERE archimate_type = 'business-service';
CREATE VIEW v_business_objects AS SELECT * FROM business_architecture WHERE archimate_type = 'business-object';

CREATE VIEW v_agents AS SELECT * FROM solution_architecture WHERE is_agent = 1;
CREATE VIEW v_knowledge_stores AS SELECT * FROM solution_architecture WHERE is_knowledge_store = 1;
```

The database stores the union; Pydantic models enforce which fields are required, optional, or forbidden for each `archimate_type`; views provide the query convenience of dedicated tables. SQLite won't stop you writing a stakeholder row with a `threshold` value, but the MCP server's Pydantic validation layer will.

---

## 7A. Governance Controls in Business Architecture

### 7A.1 What Controls Are

A governance control is the operational binding between a standard (or principle, or constraint) and the business architecture element it governs. The Track Crossing Protocol is a standard in `practice_artefacts`. The Safety Incident Investigation process is a `business-process` in `business_architecture`. The control says: "the Track Crossing Protocol applies to this process, enforced via automated flag on track_crossing = 1 in process_steps, assessed quarterly."

Without explicit controls, governance is implicit — scattered across `autonomy_ceiling` on domains, `governance_level` on processes, `track` on process steps. You can't answer "which standards apply to this process?" or "which processes are non-compliant with this standard?" because the binding doesn't exist.

### 7A.2 Controls Are Not a Concern Table

Controls are not ArchiMate elements. They're a binding mechanism — the operational enforcement of a constraint or standard against a business architecture element. They live alongside `process_steps` as a supporting structure table, not as a sixth concern table.

### 7A.3 Schema

```sql
CREATE TABLE governance_controls (
    id TEXT PRIMARY KEY,                        -- e.g., 'ctrl-tcp-bp-incident'
    name TEXT NOT NULL,                         -- human-readable: "Track Crossing Protocol on Incident Investigation"
    description TEXT,

    -- What is being governed
    target_table TEXT NOT NULL CHECK (target_table IN (
        'business_architecture', 'solution_architecture', 'process_steps',
        'strategy', 'motivation', 'implementation'
    )),
    target_id TEXT NOT NULL,                     -- FK to the governed element

    -- What governs it
    standard_id TEXT REFERENCES practice_artefacts(id),  -- the standard, principle, or NFR
    constraint_id TEXT,                          -- optional FK to motivation (archimate_type = 'constraint')

    -- Enforcement
    enforcement_type TEXT NOT NULL,              -- automated | manual-audit | self-assessment | approval-gate
    enforcement_mechanism TEXT,                  -- description of how enforcement works
    assessment_frequency TEXT,                   -- continuous | daily | weekly | monthly | quarterly | annual
    last_assessed TEXT,                          -- timestamp of last assessment
    compliance_status TEXT DEFAULT 'not-assessed', -- compliant | non-compliant | partially-compliant | not-assessed | exempt

    -- Scope
    scope TEXT,                                  -- enterprise | domain | process | step
    domain_id TEXT REFERENCES domains(id),

    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 7A.4 How Controls Work in Practice

**Standard → Control → Process example:**

`practice_artefacts` row: STD-007 "Agent Track Crossing Protocol" — any agent output entering a Track 1 process must be identified, validated, and recorded.

`governance_controls` row: ctrl-tcp-bp-incident — STD-007 applies to BP-incident-investigation, enforcement_type = 'automated', enforcement_mechanism = "process_steps.track_crossing flag triggers provenance tagging and human review gate", assessment_frequency = 'continuous', compliance_status = 'compliant'.

**Compliance queries this enables:**

- "Which processes have no governance controls?" — LEFT JOIN business_architecture on governance_controls WHERE controls.id IS NULL
- "Which standards are not applied to any process?" — LEFT JOIN practice_artefacts on governance_controls WHERE controls.id IS NULL
- "Show me all non-compliant controls in the Safety domain" — straightforward WHERE clause
- "What's the compliance posture for this process?" — all controls where target_id = process_id

**For the AI CoE specifically:** The agent autonomy policy (L0–L5) becomes enforceable through controls. Each domain gets a control binding its autonomy ceiling standard to its processes. Agent actor promotion (Section 5) is itself a governed process with a control binding it to the CoE sign-off standard.

### 7A.5 Controls vs Practice Artefacts

Standards, principles, and NFRs live in `practice_artefacts`. They are *what* the governance says. Controls live in `governance_controls`. They are *where and how* the governance is applied. The standard is "agents at L3+ require CoE sign-off." The control is "this standard applies to the Safety domain's Compliance Agent, enforced via approval gate, assessed quarterly, currently compliant."

This separation means governance constraints don't need their own table — they stay as `practice_artefacts` entries. The `governance_controls` table handles the binding, enforcement, and compliance tracking.

---

## 8. Domains as First-Class Entities

The schema review identified that `domain` as a text field is insufficient. Domains need their own attributes.

```sql
CREATE TABLE domains (
    id TEXT PRIMARY KEY,                    -- e.g., 'dom-safety', 'dom-geology'
    name TEXT NOT NULL,
    description TEXT,
    priority INTEGER,                       -- domain priority for roadmap sequencing
    maturity TEXT,                          -- initial | defined | managed | optimised
    autonomy_ceiling TEXT,                 -- maximum agent autonomy permitted in this domain
    track_default TEXT,                    -- Track1 | Track2 default for new processes
    spec_coverage TEXT,                    -- percentage or qualitative assessment
    owner_role TEXT,                        -- who owns this domain
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

Every concern table references `domains(id)` instead of storing a free-text domain string. This enables domain-level governance queries: "show me all elements in domains where autonomy ceiling is L2 or below" or "which domains have no defined business processes."

---

## 9. Solutions Portfolio

### 9.1 What a Solution Is

A solution groups application components, technology services, and agent deployments to realise business requirements through business services. It is the bridge between "what the business needs" and "what technology delivers."

Agents at Stanmore don't live inside SAP or SharePoint. They operate above individual systems, at the business process layer, orchestrating across system boundaries, surfaced through portals and web applications. The solution is technically an application-layer concern but sits at the top of the solution stack — immediately below the business process it serves.

### 9.2 Schema

```sql
CREATE TABLE solutions (
    id TEXT PRIMARY KEY,                    -- e.g., 'sol-safety-knowledge'
    name TEXT NOT NULL,
    description TEXT,
    domain_id TEXT REFERENCES domains(id),
    solution_type TEXT,                     -- agent-service | platform | integration
    status TEXT DEFAULT 'proposed',         -- proposed | in-build | deployed | retired
    portfolio_product TEXT,                 -- which product this belongs to
    business_service_id TEXT,               -- FK to business_architecture (business-service)
    owner TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE solution_components (
    solution_id TEXT REFERENCES solutions(id),
    element_id TEXT NOT NULL,               -- FK to solution_architecture row
    element_table TEXT DEFAULT 'solution_architecture',
    role_in_solution TEXT,                  -- agent-runtime | knowledge-base | deployment-target | etc
    PRIMARY KEY (solution_id, element_id)
);

CREATE TABLE solution_diagrams (
    id TEXT PRIMARY KEY,
    solution_id TEXT NOT NULL REFERENCES solutions(id),
    diagram_type TEXT NOT NULL,             -- component | sequence | deployment | class
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,                -- path to diagram file in repo
    notation TEXT DEFAULT 'UML',            -- UML | ArchiMate | custom
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

UML diagrams belong to solutions. They don't exist outside the solution layer. There's no "system-wide component diagram" — each solution has its own. Enterprise-level views are ArchiMate viewpoints generated from the relationships table.

### 9.3 Deployment

```sql
CREATE TABLE deployment_targets (
    id TEXT PRIMARY KEY,                    -- e.g., 'dt-prod-aue'
    name TEXT NOT NULL,
    environment TEXT NOT NULL,              -- dev | test | staging | prod
    region TEXT,
    subscription TEXT,                      -- Azure subscription identifier
    description TEXT
);

CREATE TABLE solution_deployments (
    solution_id TEXT REFERENCES solutions(id),
    target_id TEXT REFERENCES deployment_targets(id),
    iac_path TEXT,                          -- path to Bicep/ARM template in repo
    status TEXT DEFAULT 'planned',          -- planned | provisioned | active | decommissioned
    deployed_at TEXT,
    PRIMARY KEY (solution_id, target_id)
);
```

The chain: Solution → Deployment Target → IaC Template. When a solution changes, PFC governance agents flag that the corresponding Bicep template may need updating.

---

## 10. Implementation & Migration Layer

```sql
CREATE TABLE implementation (
    -- Common fields
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL CHECK (archimate_type IN (
        'work-package', 'deliverable', 'implementation-event',
        'plateau', 'gap'
    )),
    domain_id TEXT REFERENCES domains(id),
    status TEXT,
    description TEXT,
    source_spec TEXT,
    confidence REAL DEFAULT 1.0,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

    -- Work-package-specific
    solution_id TEXT REFERENCES solutions(id),
    phase TEXT,                             -- Phase 0 | Phase 1 | Phase 2 | etc
    target_date TEXT,

    -- Plateau-specific
    plateau_description TEXT                -- what the architecture looks like at this state
);
```

This is the roadmap layer. Phase 0, Phase 1, Phase 2. Work packages deliver solutions. Plateaus describe target architecture states. Gaps identify what's missing between the current state and a plateau. Currently this lives in documents — putting it in the database lets PFC generate roadmap views and check that every gap has a work package addressing it.

---

## 11. Relationships with Metamodel Validation

```sql
CREATE TABLE relationships (
    id TEXT PRIMARY KEY,
    source_table TEXT NOT NULL,              -- which concern table
    source_id TEXT NOT NULL,
    target_table TEXT NOT NULL,
    target_id TEXT NOT NULL,
    archimate_type TEXT NOT NULL,            -- ArchiMate relationship type
    description TEXT,
    source_spec TEXT,
    evidence TEXT,                           -- quote or section reference
    confidence REAL DEFAULT 1.0,
    created_by TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, target_id, archimate_type)
);

-- Valid relationship combinations (lookup table for validation)
CREATE TABLE valid_relationships (
    source_archimate_type TEXT NOT NULL,
    target_archimate_type TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    PRIMARY KEY (source_archimate_type, target_archimate_type, relationship_type)
);
```

The `valid_relationships` table is seeded from the ArchiMate 3.2 specification's relationship matrix. Application-level validation (or a trigger in Postgres) checks every INSERT against this table. Invalid relationships are rejected or flagged for review rather than silently stored.

The `source_table` and `target_table` fields enable cross-table joins without a polymorphic ID problem. Query "all elements related to this business process" joins `relationships` to `solution_architecture` where `target_table = 'solution_architecture'`.

---

## 11A. Provenance — What the PFC Remembers About How Knowledge Arrived

### 11A.1 Where Chats Sit

Chat *content* doesn't live in PFC. Chainlit owns the conversation history — messages, turns, threading, the full transcript. PFC's job is to track what *came out of* chats: what was extracted, what was approved, what the session produced. The boundary is clean:

```
Chainlit (owns conversation)
  → sessions (PFC summary: when, counts, what happened)
    → staging_items (source_type='chat', source_id=session_id)
      → approved into concern tables (provenance trail back to session)
```

For batch agents, the chain is similar:

```
Agent execution (Claude Code, pipeline agent, scheduled scan)
  → agent_runs (what the agent did, metrics, model used)
    → staging_items (source_type='batch-agent', source_id=run_id)
      → approved into concern tables
```

For formal engagements (workshops, interviews), the chain routes through motivation:

```
Workshop happens → Justin captures via chat
  → engagements record created (date, participants, context)
    → motivation rows reference engagement_ref
      → traceability from a stakeholder need back to the workshop where it was first articulated
```

`engagements` stays in the Motivation group because it's provenance *for motivation elements specifically* — workshop where a driver was first voiced, interview where a requirement was first articulated. It's not a general-purpose audit record.

### 11A.2 Quality Evaluations

The knowledge platform MVP runs on a phase-gating pattern: Phase 0 baseline retrieval score → Phase 1 improvement threshold (>15% over baseline) → Phase 2 comparative benchmark (Granite vs GPT-4o). The Foundry IQ retrieval evaluation (project document) defines a structured test protocol with weighted metrics across five query categories.

These quality observations have no home in the current schema. They're not architectural elements (not in any concern table). They're not practice artefacts (not standards or decisions). They're operational measurements about how well the architecture is performing — closer in nature to `agent_runs` than to `solutions`.

```sql
CREATE TABLE quality_evaluations (
    id TEXT PRIMARY KEY,                         -- e.g., 'eval-safety-retrieval-baseline'
    name TEXT NOT NULL,                          -- "Safety Domain Retrieval Baseline — Phase 0"

    -- What was evaluated
    target_table TEXT NOT NULL CHECK (target_table IN (
        'solution_architecture', 'solutions', 'process_steps',
        'business_architecture', 'strategy'
    )),
    target_id TEXT NOT NULL,                      -- FK to the evaluated element
    domain_id TEXT REFERENCES domains(id),

    -- Evaluation context
    evaluation_type TEXT NOT NULL,                -- retrieval | generation | end-to-end | latency | cost
    phase TEXT,                                   -- Phase 0 | Phase 1 | Phase 2
    baseline_ref TEXT,                            -- FK to the prior evaluation this compares against
    methodology TEXT,                             -- reference to test protocol (e.g., Foundry IQ eval doc)

    -- Results
    metrics TEXT NOT NULL,                        -- JSON: {"precision_at_5": 0.72, "latency_p50_ms": 340, ...}
    pass_fail TEXT,                               -- pass | fail | inconclusive
    summary TEXT,                                 -- human-readable finding
    decision_ref TEXT,                            -- FK to practice_artefacts ADR if this evaluation drove a decision

    -- Metadata
    evaluated_by TEXT,                            -- person or agent
    evaluated_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**What this enables:**

- "Show me all quality evaluations for the Safety Knowledge Store" — WHERE target_id = 'comp-safety-knowledge-store'
- "Compare Phase 0 baseline to Phase 1 results" — JOIN on baseline_ref
- "Which evaluations drove architecture decisions?" — WHERE decision_ref IS NOT NULL
- "What's the retrieval quality trend across phases?" — ORDER BY phase, evaluated_at
- T09 vs T11 results from the MVP implementation plan are rows here, with `baseline_ref` linking them. The ADR in T20 references the evaluation that justified the chunking decision.

### 11A.3 Sessions — Enriched for Conversation Semantics

The Phase 0 `sessions` table was a bare summary record — start time, end time, counts. This is insufficient for a key requirement: *finding architectural meaning from past conversations*. A session where you discussed Neo4j vs Fabric IQ trade-offs, leaned Neo4j, deferred pending Phase 2 — that architectural reasoning needs to be findable later without searching raw transcripts.

The enriched `sessions` table adds structured fields that the `/wrap` agent populates at session end:

```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT,
    ended_at TEXT,

    -- Counts (carried from Phase 0)
    entities_staged INTEGER DEFAULT 0,
    items_approved INTEGER DEFAULT 0,
    items_rejected INTEGER DEFAULT 0,

    -- Conversation semantics (new)
    summary TEXT,                             -- wrap agent's prose summary
    topics TEXT,                              -- JSON array: ["neo4j-vs-fabric-iq", "ontology-compliance", "phase-2-gate"]
    architectural_themes TEXT,                -- JSON array of ArchiMate concerns touched: ["technology-service", "artifact", "gap"]
    decisions_made TEXT,                      -- JSON array: [{decision, rationale, ref}] — crystallised to ADR
    decisions_deferred TEXT,                  -- JSON array: [{topic, lean, reason_deferred, revisit_trigger}]
    elements_discussed TEXT,                  -- JSON array of element IDs referenced or relevant
    domain_ids TEXT,                          -- JSON array of domain IDs this session touched
    engagement_ref TEXT,                      -- FK to engagements if session captures a formal meeting
    semantic_summary TEXT                     -- wrap agent's ~100-word summary optimised for semantic search
);
```

**Who owns this mapping:** The `/wrap` agent (UC: Session Wrap-up) runs at session end, reads the Chainlit transcript, and populates these fields. Entity extraction (UC-1) produces `staging_items`. The wrap agent produces the session record. Different outputs from the same conversation:

- `staging_items` = discrete atoms (a stakeholder, a requirement, a capability)
- `sessions` = the semantic meaning of the conversation as a whole

**What `semantic_summary` is for:** A dense paragraph written by the wrap agent specifically for embedding and vector search. Not the same as `summary` (which is human-readable narrative). The semantic summary emphasises architectural concepts, element names, relationship types, and decision context — optimised for retrieval when a future conversation asks "what did we discuss about the ontology layer?"

**What `decisions_deferred` captures:** Architectural discussions that didn't crystallise into ADRs but have value. The JSON structure includes the topic, the current lean, why it was deferred, and the trigger condition for revisiting. When the trigger fires (e.g., "Phase 2 gate reached"), a governance agent can surface the deferred decision for review.

### 11A.4 The Provenance Group — Complete

The Provenance group now has four tables, each with a distinct role:

| Table | What It Records | Typical Source |
|---|---|---|
| `sessions` | Semantic summary of a Chainlit chat session — topics, themes, deferred decisions, element references | Wrap agent at session end |
| `agent_runs` | Execution record of a batch agent — duration, tokens, model, entity count | Agent framework post-run |
| `staging_items` | Individual extracted entities awaiting human review — the approval queue | Entity extraction agents |
| `quality_evaluations` | Structured measurement of how well architectural elements perform | Test protocols, eval scripts |

`sessions` and `agent_runs` are *how* things happened. `staging_items` is *what* was extracted. `quality_evaluations` is *how well* things work. `sessions.semantic_summary` bridges the gap between raw transcripts (Chainlit) and discrete entities (staging_items) — it captures the architectural *meaning* of conversations that may not have produced any entities at all.

---

## 12. Complete Table Count

| Category | Tables | Purpose |
|---|---|---|
| ArchiMate concern tables | 5 | motivation, strategy, business_architecture, solution_architecture, implementation |
| Supporting structures | 4 | domains, process_steps, valid_relationships, governance_controls |
| Portfolio | 4 | solutions, solution_components, solution_diagrams, solution_deployments |
| Infrastructure | 1 | deployment_targets |
| Cross-layer | 1 | relationships |
| EA practice | 2 | practice_artefacts, engagements |
| Provenance | 4 | staging_items, agent_runs, sessions, quality_evaluations |
| **Total** | **21** | |

21 tables. Up from 19 (pre-reconciliation review). The two additions — `governance_controls` and `quality_evaluations` — each address a specific gap identified in the cross-chat schema review: controls provide the operational binding between standards and the elements they govern; quality evaluations provide the phase-gating measurement framework the knowledge platform MVP depends on. Both have clear reasons to exist that aren't served by any other table.

---

## 13. Migration from Phase 0

| Phase 0 Table | Destination | Migration |
|---|---|---|
| `stakeholders` | `motivation` (archimate_type = 'stakeholder') | Row-level INSERT with type mapping |
| `drivers` | `motivation` (archimate_type = 'driver') | Row-level INSERT |
| `needs` | `motivation` (archimate_type = 'goal') | Rename concept to Business Requirement; archimate_type = 'goal' |
| `requirements` | `motivation` (archimate_type = 'requirement') | Row-level INSERT; add requirement_type = 'solution' |
| `capabilities` | `strategy` (archimate_type = 'capability') | Preserve parent_id hierarchy |
| `elements` | Split by archimate_type into solution_architecture or business_architecture | Mechanical split |
| `element_capabilities` | `relationships` (archimate_type = 'realization-relationship') | Join table becomes relationship row |
| `practice_artefacts` | Unchanged | Already correct shape |
| `engagements` | Unchanged | Already correct shape |
| `staging_items` | Unchanged | Already correct shape |
| `agent_runs` | Unchanged | Already correct shape |
| `sessions` | Enriched — add topics, architectural_themes, decisions_deferred, elements_discussed, semantic_summary | ALTER TABLE ADD COLUMN for each new field |

---

## 14. Open Questions

1. **Process notation**: Should process definitions in the wiki use BPMN-lite markdown (richer, harder to author) or structured YAML with steps (simpler, loses gateway semantics)? **Lean**: YAML steps now, BPMN rendering as a future visualisation consumer of the same data.

2. **Function-capability granularity**: At what level do functions map to capabilities? A function like "Safety Management" might map to multiple capabilities. Need to decide the canonical direction. **Lean**: Many-to-many via relationships table.

3. **Portfolio hierarchy**: Is product/service/solution sufficient, or does Stanmore need programme/project groupings? **Lean**: Sufficient for now. Programme-level grouping is an `implementation` table concern (work-packages grouped by phase).

4. **Metamodel strictness**: Should invalid relationships be rejected (hard fail) or flagged for review (soft warning)? **Lean**: Soft warning during extraction, hard fail on Orbus export.

5. **Value stream stages**: JSON array in a single column, or a `value_stream_stages` child table? **Lean**: JSON for now, child table if stage-level queries become necessary.

---

*Stanmore Resources | Technology — Enterprise Systems | March 2026*.  