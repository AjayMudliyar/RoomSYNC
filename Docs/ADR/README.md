# RoomSync Architecture Decision Records (ADRs)

**Status:** Reconciled Phase 0 Baseline (`DEC-01`–`DEC-10` & Owner Decisions `OD-U1`–`OD-U8`)  
**Related Documents:**
- [OPEN_DECISIONS.md](../engineering/OPEN_DECISIONS.md) — Approved decisions (`DEC-01`–`DEC-10`, `OD-U1`–`OD-U8`), remaining proposed/prod-prep gates, and `PRD.md`/`TDD.md` sync edits.
- [QUESTIONNAIRE_CATALOG_V1.md](../QUESTIONNAIRE_CATALOG_V1.md) — **PROPOSED** 20-question `v1` lifestyle catalog & deal-breaker rules *(pending separate review before Milestone 3)*.
- [IMPLEMENTATION_PLAN.md](../engineering/IMPLEMENTATION_PLAN.md) — Final Milestone 0 checklist, Milestones 1–10 exit gates, and Post-MVP backlog.
- [API_CONVENTIONS.md](../API_CONVENTIONS.md) — Shared public `/api/v1/` and internal `/internal/v1/` HTTP contracts.
- [REPOSITORY_ASSESSMENT.md](../REPOSITORY_ASSESSMENT.md) — Phase 0 reconnaissance findings.

---

## ADR Index

| ADR ID | Title | Status | Decisions Covered | Blocking Before |
|---|---|---|---|---|
| [ADR-001](./ADR-001-platform-architecture-and-boundaries.md) | Platform Architecture, Monorepo Boundaries, MVP Scope, UX Structure & Operations | Accepted | `DEC-01`, `DEC-04`, `DEC-08`–`10`, `OD-U3`, `OD-U4`, `OD-U5`, `OD-U7` | Milestone 0 |
| [ADR-002](./ADR-002-compatibility-engine-and-weights.md) | Deterministic 8-Dimension Compatibility Engine, 20-Q Policy & Scoring Semantics | Accepted *(Catalog Proposed)* | `DEC-02`, `OD-U2` | Milestone 3 |
| [ADR-003](./ADR-003-design-system-token-reconciliation.md) | Canonical Warm Tech Harmony Design System & WCAG 2.1 AA Reconciliation | Accepted | `DEC-03` | Milestone 0 / Milestone 7 |
| [ADR-004](./ADR-004-auth-sessions-locations-and-privacy.md) | Authentication Staged Policy, Dual-Client Sessions, 5-City Locations & Privacy-by-Design | Accepted | `DEC-05`–`07`, `OD-U1`, `OD-U6`, `OD-U7`, `OD-U8` | Milestone 1 / Milestone 2 |

