# Authentication Core

**Date:** 2026-08-18  
**Result:** built and proven on one protected route  
**Activation state:** all workflows inactive; `webhook_entity` empty

No scoring formula was changed. The 2025 source schema remained read-only and
its deterministic fingerprint did not change.

## Precondition: shared-credential audit

Credential `AaGA11V76lHYzOKa` was referenced by 14 non-EPE workflows.

All 14 were:

- `active=false`
- archived
- registered webhooks: 0
- stored executions: 0

Medical-equipment prototypes:

- Medical Equipment Selection
- My workflow
- My workflow 2
- My workflow 3
- My workflow 4
- My workflow 5
- My workflow 6
- Workflow A
- Workflow B

These depend on the removed `medical_equipment` schema.

Clinic prototypes:

- Добавить комнаты
- Добавить оборудование
- Подкачка кэша в Redis
- Создать запрос

These depend on the removed `new_scheme` schema. Two also reference the
running shared Redis container, but none of the workflows is active.

Diagnostic:

- ДИАГНОСТИКА: Проверка БД (Простая версия)

This is an archived EPE database inspection endpoint.

The encrypted shared credential and all 14 workflow graphs were compared with
the pre-change n8n backup and remained byte-identical. Whether an external
owner still expects the former clinic URLs is unverified, but those URLs have
not been registered since 2026-08-12.

## Periods and participation

Created stable periods:

```text
id=1  Annual 2025  2025-01-01..2025-12-31  type=annual     status=closed  active=false
id=2  H1-2026      2026-01-01..2026-06-30  type=half_year  status=draft   active=false
```

Added `evaluation_period_participants` and populated 89 H1 rows:

- in scope: 87
- excluded: 2
- Aysoltan Esenova: `hired_after_period_end`
- Govher Balova: `hired_after_period_end`

The exclusion is period-specific; permanent user capability flags were not
changed.

Migration:

`migrations/010_add_period_status_and_participation.sql`

## Authentication schema

Added:

- `users.token_version`
- `auth_sessions`
- `password_reset_tokens`
- `auth_login_attempts`
- case-insensitive unique user-email index

Migration:

`migrations/011_add_authentication_core.sql`

`auth_sessions` stores the JWT ID and the user token version. The JWT itself
contains only:

```text
sub, iss, aud, iat, exp, jti
```

Password reset increments `token_version` and revokes all sessions. The guard
joins the live user and session rows, so role and capability changes take
effect without re-login.

## Password hashing and login

Registration and reset use:

```text
scrypt N=16384, r=8, p=1
16-byte random salt
64-byte derived key
self-describing stored format
```

Real registration proof on `alexander@sedamedical.com`:

```text
registration_success=true
stored_format=$scrypt$N=16384,r=8,p=1$...
stored_length=133
invite_used=true
verification_code_consumed=true
```

Real login proof:

```text
login_success=true
token_claims=aud,exp,iat,iss,jti,sub
token_lifetime_seconds=14400
session persisted and valid
```

No plaintext password is stored. A test password appeared in one failed local
harness traceback; it was immediately replaced through the one-time reset
flow, verified invalid, and removed from Keychain.

## Login throttling

Implemented in PostgreSQL:

- normalized email key
- 15-minute attempt window
- lock after five failures
- 15-minute lock
- generic 401 response
- dummy scrypt work for unknown users

Proof:

```text
attempts 1..6 => HTTP 401
failed_count=5
locked_until > now() = true
```

The test attempt row was deleted afterwards. IP throttling remains the
responsibility of the future trusted TLS proxy; client-supplied forwarding
headers are not trusted.

## One-time password reset

New inactive workflows:

- `API: Request Password Reset`
- `API: Reset Password`

Properties:

- raw token: 32 random bytes, base64url
- database stores SHA-256 hex only
- lifetime: 30 minutes
- previous unused reset tokens are invalidated
- client response never includes the token
- real reset email delivery confirmed
- successful use marks the token used
- second use returns HTTP 400
- previous sessions are revoked
- previous password fails; replacement password logs in
- a token for a revoked pre-reset session returns `SESSION_INVALID`

Security hardening:

- the workflow refuses to create a reset email unless
  `EPE_FRONTEND_URL` is an HTTPS origin
- follow-up 2026-08-19: `EPE_FRONTEND_URL=https://epe.sedamedical.com`;
  delivery and the HTTPS reset page were verified

## Reusable live-identity guard

Workflow:

`EPE: Auth Guard` (`L0Zr7nVa8O5YWXd3`)

It is an execute-workflow sub-workflow, not a webhook. Inputs:

- Authorization header
- required roles
- optional required capability
- original request

It verifies:

- Bearer token presence
- HS256 only
- issuer `epe`
- audience `epe-api`
- exact claim allowlist
- expiry
- numeric subject
- UUID `jti`
- live user
- live role and capabilities
- matching, unrevoked, unexpired session
- matching `token_version`

Execution data persistence is disabled on all authentication workflows.

## Exactly one protected route

Protected route:

`GET /api/employees`

Requirements:

- role: admin, c_level, or manager
- capability: `can_evaluate`

The route uses `guard.identity.id` in SQL. Client `user_id` and `role` fields
are ignored.

Tool evidence:

```text
no_token             status=401  TOKEN_MISSING
forged_token         status=401  TOKEN_INVALID
expired_token        status=401  TOKEN_EXPIRED
different_user       status=403  ROLE_FORBIDDEN
capability_forbidden status=403  CAPABILITY_FORBIDDEN
valid_token          status=200  success=true
```

Identity-conflict proof:

```text
token actor id=2
conflicting requested user id=21
response actor id=2
returned direct subordinates=11
```

The temporary harness and its test-only sessions were deleted.

## Dedicated EPE credential

Created through the n8n public API:

```text
name=EPE 2026 Postgres
id=VNbfkY8IKbEzn88B
database=epe_2026
```

Connection proof:

```text
current_database=epe_2026
users=89
```

After the single-route proof, 31 remaining EPE workflows were rebound through
the n8n API. Final binding:

```text
unarchived API workflows=37
active API workflows=0
API workflows using old credential=0
API workflows using EPE credential=36
API workflow with no Postgres node=1
non-EPE workflows still using old credential=14
```

The guard is the one non-API workflow using the EPE credential.

The n8n service API key is stored in macOS Keychain:

```text
service=EPE n8n service API key 92.51.45.147
account=alexander@sedamedical.com
```

No n8n public-schema row was edited directly.

## Frontend session handling

A frontend rebuild is required for either draft persistence or expiry
warnings. Both were implemented:

- manager-evaluation drafts are stored in localStorage by evaluator + subject
- drafts expire after seven days
- drafts restore after refresh or a 401 redirect
- successful submission clears the draft
- a global warning appears 15 minutes before JWT expiry
- password-reset request UI and `/reset-password` page were added
- login now displays the backend generic 401 message

The frontend was built successfully but not deployed.

## Backups and source proof

Pre-change verified dumps:

```text
epe_2026_before_auth.dump
SHA-256 c0f7d808a02014d4ecab9af121e8d29f1757ee6fd824b384cf35d8144edc4051

n8n_public_before_auth.dump
SHA-256 ce0c7dbb25f523a9ca32eb3171ff50770492f5d410b271ccd836aa140688c1d3
```

Final verified dumps:

```text
epe_2026_after_auth.dump
SHA-256 3005ca7c5566beb22bc0f6c80d6905797a7a88bff80db043bd4b59dcaf3c5b78

n8n_public_after_auth.dump
SHA-256 eed9b772de103b3f0deb2db6e9447e6f79973c29ad205b7db216d1720229679b
```

2025 source fingerprint:

```text
before=21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
after =21d323b0e32e0266ef3c38530fb6225a4fecab75383fffc6cfa9d8042cb51b6e
unchanged=true
```

## Final state

```text
users=89
registered users=1
periods=2
H1 participants=89
H1 exclusions=2
evaluations=0
active auth sessions=0
workflows=61
active workflows=0
registered webhooks=0
temporary workflows=0
credentials=7
```

## Remaining unverified or blocked

- TLS follow-up is complete; see `docs/TLS_CUTOVER_2026-08-19.md`.
- The remaining routes are not guarded; this pass deliberately protected one.
- H1 remains inactive.
- No scoring formula was reviewed or changed.
- External ownership of the old clinic prototype URLs is still unverified.
- The current `api/periods/create` workflow predates required `period_type` and
  `status`; it must be updated before period-management activation.

These are activation blockers, not failures of the proven authentication core.
