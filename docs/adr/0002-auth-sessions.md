# ADR 0002: Database-backed sessions instead of JWT

- **Status:** Accepted
- **Date:** 2026-11-17

## Context

The helpdesk SPA and API are served from the same origin. Roles can change at runtime, and admins must be able to revoke access immediately. The frontend must not store long-lived credentials in JavaScript-accessible storage.

## Decision

Use opaque session tokens stored hashed in a `sessions` table.

- On login, generate a random token, store its SHA-256 hash, and set the raw token in an `HttpOnly`, `SameSite=Lax` cookie (plus `Secure` in production).
- Load the user and role from the database on every authenticated request.
- Revoke sessions on logout, password change, role change, and deactivation.
- Reject state-changing requests whose `Origin` does not match `APP_BASE_URL`.
- Hash passwords with Argon2id.

## Consequences

Positive:

- Immediate revocation and role freshness.
- No access/refresh token rotation or client-side token storage.
- Simple to explain and test in an interview.

Negative:

- One indexed database lookup per authenticated request. Acceptable at this scale.
- Requires a sessions table and cleanup of expired rows.
- Cookie-based auth requires CSRF/origin discipline.

## Alternatives considered

- **JWT access token in `localStorage`:** simpler stateless verification, but vulnerable to XSS and hard to revoke.
- **JWT access + refresh rotation:** supports revocation indirectly, but adds significant complexity for a single-origin SPA.
- **FastAPI `SessionMiddleware` signed cookies:** client-side state cannot be revoked before expiry.
