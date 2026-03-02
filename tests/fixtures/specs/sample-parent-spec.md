---
parent: index
title: Identity and Access Management
domain: security
tier: 1
---

# Identity and Access Management

## Background

The Stanmore Resources Identity and Access Management (IAM) capability governs how
users, systems, and services authenticate and are authorised to access enterprise
resources. This encompasses on-premises Active Directory, Azure AD (Entra ID), and
federated access for partner systems.

## Problem Statement

The organisation currently operates fragmented identity stores across multiple systems
with inconsistent access review processes. This creates risk of excessive privilege
accumulation and limits our ability to enforce least-privilege principles.

## Scope

This spec covers the following sub-domains:
- Directory services and synchronisation
- Multi-factor authentication
- Privileged access management
- Application access provisioning
- Identity governance and access reviews

## Goals

1. Establish a unified identity fabric across cloud and on-premises systems
2. Enforce least-privilege access with automated provisioning and de-provisioning
3. Achieve Conditional Access coverage for all critical applications
4. Enable self-service access request and approval workflows

## Constraints

- Must integrate with existing SAP and Oracle HR systems for lifecycle events
- Must comply with Australian Privacy Act 1988 requirements for data access logging
- Cannot break existing partner federation arrangements

## Open Questions

- Should PAM tooling (CyberArk vs Azure PIM) be rationalised?
- What is the target state for non-human identity management?
