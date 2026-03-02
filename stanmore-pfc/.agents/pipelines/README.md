# ADO Pipeline Templates

This directory contains Azure DevOps pipeline YAML templates for the Stanmore PFC agent
automation. These are documentation artefacts — configure them in your ADO project before
running.

---

## Pipelines

### `wiki-integrity-pipeline.yaml`

**Purpose**: Weekly automated wiki structure integrity check (UC-13).

**Trigger**: Scheduled — every Monday at 06:00 UTC.

**Agent**: `wiki-integrity`

**What it does**:
1. Scans `stanmore-pfc/specs/**/*.md` for structural violations
2. Checks for missing parent links, orphan specs, oversized pages, and broken `[[Links]]`
3. Publishes a JSON manifest to `.agents/runs/` as a build artefact

**Configuration in ADO**:
1. Import the pipeline YAML into your ADO project under Pipelines → New Pipeline → Azure Repos Git
2. Create a variable group named `pfc-secrets` with variable `ANTHROPIC_API_KEY`
3. Set the `PFC_WORKSPACE` variable to the correct workspace path for your agent
4. Enable the weekly schedule

**Environment variables required**:
| Variable | Source | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Variable group `pfc-secrets` | API key for Claude |
| `PFC_WORKSPACE` | Pipeline variable | Absolute path to stanmore-pfc/ |

---

### `guardrail-pipeline.yaml`

**Purpose**: Automated design-time guardrail check on spec changes (UC-7).

**Trigger**: On push/commit to any branch when files in `stanmore-pfc/specs/**/*.md` are modified.

**Agent**: `guardrail`

**What it does**:
1. Identifies changed spec files in the commit diff
2. Runs the guardrail agent against each changed file
3. Produces a review comment markdown file in `.staging/work/`
4. Publishes review files as build artefacts

**Configuration in ADO**:
1. Import the pipeline YAML under Pipelines → New Pipeline
2. Configure it to trigger on your wiki repository
3. Set the path filter to `stanmore-pfc/specs/**/*.md`
4. Add the `pfc-secrets` variable group
5. Optionally: configure the pipeline to post review comments back to PRs using the
   ADO REST API or a comment task

**Environment variables required**:
| Variable | Source | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Variable group `pfc-secrets` | API key for Claude |
| `PFC_WORKSPACE` | Pipeline variable | Absolute path to stanmore-pfc/ |

**Note**: The guardrail is advisory only — it does not block merges. Configure branch
policies separately if blocking is required.

---

## Common Setup

### Variable Group: `pfc-secrets`

Create this variable group in ADO under Pipelines → Library:

| Name | Value | Secret |
|---|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Yes |
| `AZURE_AI_FOUNDRY_ENDPOINT` | Azure AI Foundry endpoint URL (optional) | Yes |

### Agent Pool

Both pipelines use `ubuntu-latest` (Microsoft-hosted). For self-hosted agents,
replace `vmImage: ubuntu-latest` with your agent pool configuration.

### Python Version

Python 3.12 is required. The pipelines use `UsePythonVersion@0` to pin the version.

---

## Running Locally

To run an agent pipeline step locally without ADO:

```bash
# Wiki integrity
PFC_WORKSPACE=./stanmore-pfc uv run python -m ea_workbench.agents.wiki_integrity

# Guardrail (provide the spec file path)
PFC_WORKSPACE=./stanmore-pfc uv run python -m ea_workbench.agents.guardrail specs/tier1/iam.md
```
