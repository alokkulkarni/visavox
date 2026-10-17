# ADR-004: Aurora PostgreSQL with row-level security

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-17 |
| Requirements | TEN-03, TEN-07, AVA-06, CON-03 |
| DAG node | C1 |

## Context
All tenants homed in a cell share one regional database. Tenant isolation must be provable (TEN-03). Consent records and audit events need immutable, versioned storage (CON-03, TEN-07).

## Decision
Use **Aurora PostgreSQL** in each cell with:
- `tenant_id` on every tenant table;
- **row-level security policies** keyed on a per-transaction `app.tenant_id` setting;
- a non-owner application role that cannot bypass RLS;
- append-only, hash-chained tables for audit and consent history.

Migrations use Alembic.

## Consequences
- Isolation holds even if a query forgets a filter. The isolation test suite must cover every table.
- Connection pooling must reset tenant context per transaction.

## Alternatives considered
- **Database per tenant.** Strongest isolation, but the operational cost grows with tenant count.
- **DynamoDB.** Weaker relational integrity for consent and versioning, and isolation would have to be enforced in code.
