# EA Workbench — Common Workflows

## 1. Capture from a Meeting

Turn a stakeholder meeting transcript into staged ArchiMate entities.

1. Save the transcript as a text file, e.g. `stanmore-pfc/.staging/meetings/2026-03-01-safety-workshop.txt`
2. Run the classifier:
   ```
   /run transcript-classifier stanmore-pfc/.staging/meetings/2026-03-01-safety-workshop.txt
   ```
3. The agent extracts entities (drivers, goals, requirements, capabilities) and writes them to `.staging/entities/transcript-classifier-{run_id}.yaml`
4. Review the staged file:
   ```
   /triage
   ```
5. Approve each file — entities are routed to the correct concern table in `registry.db`
6. Check results:
   ```
   /staging
   ```

**Tip**: Run `/status` to see the agent run manifest with extraction counts before triaging.

---

## 2. Draft an Architecture Decision Record

Record a significant decision and get a structured ADR in the wiki.

1. Describe the decision in the chat (or use `/run` directly):
   ```
   /run adr-generator "We will use Azure AI Search with semantic ranking for the Safety Knowledge Store, replacing the keyword-only SharePoint search."
   ```
2. The agent writes a draft ADR to `stanmore-pfc/architecture/decisions/ADR-*.md`
3. Open the file, review and edit the consequences and alternatives sections
4. Move status from `Proposed` to `Accepted` when ready
5. Optionally run the guardrail:
   ```
   /run guardrail stanmore-pfc/architecture/decisions/ADR-NNN.md
   ```

---

## 3. Weekly Rhythm

Synthesise the week's activity into a planning document every Monday.

1. Ensure sessions have been wrapped during the week with `/wrap`
2. Run the weekly summary agent:
   ```
   /run weekly-summary .
   ```
3. The agent reads recent session records and agent runs, then writes:
   `stanmore-pfc/output/weekly-summaries/week-{YYYYMMDD}.md`
4. The summary includes: Key Decisions, Items Staged, Agents Run, Open Questions, Recommended Next Steps
5. Share the markdown in your team channel or paste into confluence
6. Review practice artefact trends:
   ```
   /analytics
   ```

---

## 4. Onboard a New Domain

Bring a new domain (e.g. "Fleet Management") into the architecture.

1. Write a short domain brief (2–3 paragraphs covering scope, key stakeholders, main capabilities)
2. Generate a domain knowledge spec:
   ```
   /run domain-knowledge-spec "Fleet Management oversees all light and heavy vehicle operations..."
   ```
3. Review the draft spec at `stanmore-pfc/output/specs/dk-fleet-management.md`
4. Run an assessment for any use cases in the domain:
   ```
   /run use-case-assessment stanmore-pfc/.staging/submissions/fleet-tracking-uc.md
   ```
5. Once the spec is approved, triage any extracted entities:
   ```
   /triage
   ```
6. Export an ArchiMate-compatible snapshot:
   ```
   /run multi-format-export stanmore-pfc/specs/fleet-management.md
   ```
   Outputs land in `stanmore-pfc/output/exports/fleet-management/` in five formats.
