# AI Use-Case Submission — Automated Safety Audit Report Generator

**Submission Date:** 2026-02-20
**Submitted By:** Marcus Chen, Engineering Lead
**Domain:** Safety Management
**Priority:** High

## Use-Case Description

Automatically generate monthly safety audit reports from incident data, safety case records,
and hazard register entries. The AI system will summarise trends, flag unresolved hazards,
and produce a draft report for safety managers to review and sign off.

## Business Value

- Reduces report preparation time from 3 days to 2 hours per month
- Consistent format and coverage — no items missed
- Enables trend analysis across multiple periods
- Frees safety managers to focus on remediation rather than report writing

## Data Sources

- Incident Reporting System (IRS) — structured incident records (JSON API)
- Safety Case Repository — safety case status records (REST API, available)
- Hazard Register — YAML export (manual refresh, weekly)

## Feasibility

The core capability is text summarisation and structured report generation — well within
current AI capability. Data access requires API integration work (~2 weeks engineering).

## Risk Assessment

- **Privacy**: Incident data may include personal details — PII handling required
- **Accuracy**: AI-generated summaries must be reviewed by a qualified safety manager before sign-off
- **Compliance**: AS/NZS 4360 compliance — human-in-the-loop mandatory

## Strategic Alignment

Directly supports the Safety Management Platform initiative (Q1 2026 roadmap item).
Aligns with AI CoE priority: operational efficiency through intelligent document generation.

## Dependencies

- Safety Case Repository service must be live (Q2 2026)
- IRS API must expose audit-relevant endpoints
- PII handling policy sign-off from Legal
