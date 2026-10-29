# AccessResQ Technical Documentation

**Version:** 1.0.0  
**Purpose:** Competition demonstration prototype for community flood-related reporting and preparedness in Bangladesh.

## 1. Architecture

- **Frontend:** Semantic HTML, CSS, vanilla JavaScript, Leaflet map library and OpenStreetMap tiles.
- **Backend:** FastAPI REST API served by Uvicorn.
- **Database:** SQLite with parameterized SQL queries and foreign-key constraints.
- **Private file storage:** Server-side upload directory; file metadata is linked to a user record in SQLite.
- **Authentication:** PBKDF2-HMAC-SHA256 password hashes, signed timed session cookies, `HttpOnly`, `SameSite=Strict`, and `Secure` cookies on HTTPS requests.

Request flow: browser UI → same-origin `/api/*` endpoints → validation and authorization → SQLite/private file storage. The frontend never receives the admin token or password hash.

## 2. Data model

### users

`id`, `name`, `email` (unique, case-insensitive), `phone`, `password_hash`, `created_at`.

### reports

`id`, `public_id`, optional `user_id`, `title`, `category`, `urgency`, `status`, `verification`, `description`, `area`, `lat`, `lng`, `people_affected`, `children_count`, `mobility_support`, `needs`, private `contact`, `created_at`, `updated_at`.

- `status`: `needed`, `in_progress`, `delivered`, `closed`.
- `verification`: `pending`, `verified`, `rejected`, or `sample` for seeded demo records.
- `urgency`: `critical`, `high`, `moderate`, `low`.
- Public report serializers intentionally omit `contact` and `user_id`.

### documents

`id`, random `public_id`, `user_id`, `original_name`, random `stored_name`, `mime_type`, `size_bytes`, `created_at`. Each list/download/delete query includes the current user's ID to enforce ownership.

### shelters

`id`, `name`, `address`, `lat`, `lng`, optional `contact`, `verification`, `source`, `created_at`. New shelter entries start as `pending`; only verified entries are returned by the verified-only endpoint.

## 3. Validation and security controls

- Pydantic validation for input lengths, category/status enumerations, numeric ranges and Bangladesh map coordinate bounds.
- Parameterized SQL for user input.
- Password hashing with PBKDF2-HMAC-SHA256 (310,000 iterations, random 16-byte salt).
- Signed session cookies expire after 14 days and are `HttpOnly` and `SameSite=Strict`.
- Reviewer-only state changes compare the `X-Admin-Token` value using constant-time comparison.
- Document upload requires an authenticated session, accepts only PDF/JPEG/PNG/WEBP, limits files to 10 MB, checks basic file signatures and stores files under random server filenames.
- Document download/delete is scoped to the authenticated user's ownership.
- Download responses set `X-Content-Type-Options: nosniff` and `Cache-Control: private, no-store`.
- Private contact data is omitted from public report list/detail responses.

## 4. Operational security gaps before a real pilot

This is not a production emergency platform. Before real personal data or rescue operations:

1. Use a strong random `ACCESSRESQ_SECRET_KEY` and a separate reviewer token; rotate them securely.
2. Enforce HTTPS and configure trusted proxy handling correctly.
3. Add rate limiting, account lockout/abuse detection, email verification, password reset, stronger session revocation and CSRF protections appropriate to the deployment.
4. Replace shared reviewer token with named reviewer accounts, roles and a tamper-evident audit log.
5. Move documents to private managed object storage with encryption at rest, least-privilege access, malware scanning, retention controls and tested backups.
6. Establish privacy consent, data minimization, retention/deletion procedures and local legal review.
7. Configure persistent storage, backup/restore drills, monitoring, alerting and incident response.
8. Conduct independent security testing and accessibility testing.

## 5. Flood and shelter data integrity

The prototype does not infer flood depth or predict where water will rise first. Map markers reflect community submissions and clearly labelled demo records. A community report is not automatically a confirmed incident. Safe places are not seeded with invented real-world locations; the verified directory is empty by default and depends on an authorised review workflow. Safe routes are not computed or guaranteed.

A future flood intelligence module should ingest official Bangladesh Water Development Board/Flood Forecasting and Warning Centre data where permitted, preserve source timestamps and geographic coverage, display freshness and confidence, and clearly distinguish official warnings from crowdsourced reports. Shelter listings should be validated with local authorities or trusted humanitarian partners and periodically re-confirmed.

## 6. Deployment configuration

Set environment variables in the hosting provider. Use a persistent disk and set both `ACCESSRESQ_DB_PATH` and `ACCESSRESQ_UPLOAD_DIR` to directories on that disk. Keep secrets out of source control. Do not expose the reviewer token in HTML, JavaScript, query parameters or public repository files.

## 7. Test strategy

Automated tests cover health status, clearly marked demo data, public privacy filtering, report creation and coordinate validation, account creation, password authentication, document upload/download access control and shelter verification defaults. These tests do not substitute for production penetration testing, high-load testing or real-world pilot validation.
