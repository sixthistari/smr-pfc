# EA Workbench — Architecture Reference

## Option C Schema (21 Tables)

The registry uses **Option C: Tables Per Concern** — each ArchiMate layer gets its own table with layer-specific columns. This eliminates the double-booking and generic `domain` text field problems of the original 4-table schema.

### Concern Layer Map

```
┌─────────────────────────────────────────────────┐
│                   DOMAINS                        │
│  Bounded contexts — every concern table FK's here│
└─────────────────────────────────────────────────┘
         │           │           │           │
         ▼           ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│MOTIVATION│ │STRATEGY  │ │BUSINESS  │ │SOLUTION  │
│          │ │          │ │ARCH      │ │ARCH      │
│stakeholder│ │capability│ │actor     │ │component │
│driver    │ │value-    │ │role      │ │service   │
│assessment│ │ stream   │ │process   │ │data-obj  │
│goal      │ │resource  │ │function  │ │node      │
│requirement│ │course-of-│ │service   │ │tech-svc  │
│constraint│ │ action   │ │object    │ │artifact  │
└──────────┘ └──────────┘ │event     │ └──────────┘
                           └──────────┘
                                │
                                ▼
                          ┌──────────┐
                          │IMPLEMENTA│
                          │TION      │
                          │work-pkg  │
                          │deliverable│
                          │plateau   │
                          │gap       │
                          └──────────┘

Supporting tables:
  process_steps       Steps within a business process
  relationships       Cross-table ArchiMate relationships
  valid_relationships ArchiMate metamodel permitted pairs (seeded)
  solutions           Portfolio: grouped components
  solution_components Solution → element links
  solution_diagrams   Diagrams per solution
  deployment_targets  Infrastructure targets (dev/test/prod)
  solution_deployments Solution → target deployment status
  practice_artefacts  EA practice artefact index (ADRs, principles, NFRs)
  engagements         Stakeholder engagement sessions
  governance_controls Compliance controls per element
  staging_items       Items awaiting human review
  quality_evaluations Performance/quality evaluation records
  agent_runs          Agent run provenance
  sessions            Chat session records
```

## Staging Pipeline

```
Chat / Agent
    │
    │ Writes YAML to .staging/entities/
    ▼
staging_items table  ──────────────────────────┐
    │                                           │
    │ /triage presents staged files             │
    ▼                                           │
Human Review                                    │
  Approve ──► Routes to concern table           │
  Reject  ──► Deleted                           │
              │                                 │
              ▼                                 │
   motivation | strategy | business_architecture│
   solution_architecture | implementation        │
              │                                 │
              └─────── element_registry_view ───┘
                         (unified search)
```

## Key Concepts

### Domains
First-class entities with `autonomy_ceiling` (max AI autonomy level L0–L5) and `track_default` (Track1 = human-in-loop, Track2 = supervised autonomy). Every concern element belongs to a domain.

### Dual-Track Model
- **Track 1**: Human makes decision; agent assists and drafts. All outputs reviewed before action.
- **Track 2**: Agent acts within defined guardrails; human is notified and can override.

Autonomy levels L0 (fully manual) → L5 (fully autonomous). The PFC programme currently targets L2–L3 for most operational domains.

### ArchiMate Metamodel Enforcement
The `valid_relationships` table is seeded with permitted source/target/type triples from ArchiMate 3.2 Appendix B. The `validate_relationship()` query function checks new relationships before insertion.

### Element Registry View
`element_registry_view` unions all 5 concern tables into a single searchable surface:
```sql
SELECT id, name, archimate_type, domain_id AS domain, status, description, source_table
FROM motivation UNION ALL ...
```

## Where Data Lives

| Data | Location |
|------|----------|
| Agent prompts | `stanmore-pfc/.agents/prompts/*.md` |
| Agent config | `stanmore-pfc/.agents/config.yaml` |
| Capability model | `stanmore-pfc/capabilities/*.yaml` |
| Element registry | `stanmore-pfc/registry.db` (SQLite) |
| Staged entities | `stanmore-pfc/.staging/entities/*.yaml` |
| Agent outputs | `stanmore-pfc/output/{category}/*.md` |
| EA practice artefacts | `stanmore-pfc/architecture/{type}/*.md` |
| Wiki specs | `stanmore-pfc/specs/**/*.md` |
