# EA Workbench — Agent Catalogue

All agents are configured in `stanmore-pfc/.agents/config.yaml`.
Run any agent with: `/run <agent-id> [input-path]`

## Agent Reference

| ID | Name | Use Case | Input | Output | Model Tier |
|----|------|----------|-------|--------|------------|
| `adr-generator` | ADR Generator | Decision capture | Decision description (text) | `architecture/decisions/ADR-*.md` | Authoring |
| `wiki-integrity` | Wiki Integrity Checker | UC-7 | Workspace path | Integrity report + violation list | Extraction |
| `guardrail` | Guardrail Agent | Risk gate | Spec/decision text | Risk assessment (pass/flag) | Judgment |
| `spec-decomposition` | Spec Decomposer | Requirements | Parent spec path | Child spec files | Authoring |
| `transcript-classifier` | Transcript → ArchiMate | UC-1 | Transcript file path | Staged entities YAML + report | Extraction |
| `weekly-summary` | Weekly Summary | Cadence | Workspace path | `output/weekly-summaries/week-*.md` | Authoring |
| `use-case-assessment` | Use-Case Assessor | UC-2 | Submission markdown | `output/assessments/*-assessment.md` | Judgment |
| `capability-intelligence` | Capability Intelligence | UC-4 | Work items YAML | `output/intelligence/capability-report-*.md` | Judgment |
| `multi-format-export` | Multi-Format Export | UC-14 | Spec file path | 5 formats in `output/exports/{slug}/` | Authoring |
| `stakeholder-comms` | Stakeholder Comms | UC-5 | Spec file path | 3 variants in `output/communications/{slug}/` | Authoring |
| `domain-knowledge-spec` | Domain Knowledge Spec | UC-11 | Domain brief (text) | `output/specs/dk-{slug}.md` | Authoring |
| `nfr-compliance` | NFR Compliance Report | UC-10 | Solution spec path | `output/compliance/nfr-{date}.md` | Extraction |
| `architecture-review` | Architecture Review Gate | UC-3 | PR diff / spec path | `output/reviews/arch-review-{id}.md` | Judgment |
| `spec-code-alignment` | Spec-to-Code Alignment | UC-8 | `diff::spec` paths | `output/reviews/alignment-{id}.md` | Judgment |
| `orbus-sync` | Orbus Sync Intelligence | UC-9 | Work items YAML | `output/orbus-sync/changeset-{date}.yaml` | Judgment |
| `standards-enforcer` | Standards Enforcer | UC-15 | New/changed spec | `output/reviews/standards-{id}.md` | Judgment |

## Model Tiers

| Tier | Resolved Model | Used For |
|------|----------------|----------|
| Extraction | `claude-haiku-4-5` (configurable) | Entity extraction, data aggregation |
| Judgment | `claude-sonnet-4-6` | Architecture decisions, assessments |
| Authoring | `claude-sonnet-4-6` | Narrative writing, spec generation |

Model assignments are in `config.yaml` under `defaults.extraction_model`, `defaults.judgment_model`, `defaults.authoring_model`.

## Output Directories

```
stanmore-pfc/output/
├── assessments/      use-case-assessment
├── communications/   stakeholder-comms
├── compliance/       nfr-compliance
├── exports/          multi-format-export
├── intelligence/     capability-intelligence
├── reviews/          architecture-review, spec-code-alignment, standards-enforcer
├── specs/            domain-knowledge-spec, spec-decomposition
├── weekly-summaries/ weekly-summary
└── orbus-sync/       orbus-sync
```
