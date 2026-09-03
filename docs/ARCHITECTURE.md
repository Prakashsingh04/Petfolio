# Architecture & Tech Stack — Adopt-a-Pet

**Related docs:** [PRD.md](PRD.md) · [DATABASE.md](DATABASE.md) · [API.md](API.md) · [ROADMAP.md](ROADMAP.md)

---

## 1. The Stack at a Glance

| Layer | Choice | Version |
|---|---|---|
| Frontend | Next.js (App Router) + React + TypeScript | Next 15 / React 19 |
| Styling | Tailwind CSS | v4 |
| Backend | FastAPI + Pydantic v2 | Python 3.12 |
| ORM / Migrations | SQLAlchemy 2.0 + Alembic | |
| Database | PostgreSQL | 16 |
| Image storage | Cloudinary | Free tier |
| Email | Resend | Free tier |
| Frontend hosting | Vercel | Hobby |
| Backend + DB hosting | Render | Starter |
| Error tracking | Sentry | Free tier |

---

## 2. System Diagram

```mermaid
flowchart TD
    User([User's browser])

    subgraph Vercel
        Next[Next.js App Router<br/>Server Components + Client Components]
    end

    subgraph Render
        API[FastAPI<br/>routers → services → models]
        PG[(PostgreSQL 16)]
    end

    subgraph External
        CLD[Cloudinary<br/>image storage + CDN]
        MAIL[Resend<br/>transactional email]
        SEN[Sentry]
    end

    User -->|HTTPS| Next
    Next -->|JSON over HTTPS<br/>cookies forwarded| API
    User -->|direct signed upload| CLD
    User -->|<img src> via CDN| CLD
    API --> PG
    API -->|signature generation<br/>+ image deletion| CLD
    API -->|send| MAIL
    MAIL -->|delivers| User
    API --> SEN
    Next --> SEN
```

**Three things to notice:**

1. **Images never traverse the API.** The browser uploads directly to Cloudinary with a short-lived signature the API generates, and reads back through Cloudinary's CDN. The API only stores URLs and issues deletes. This keeps the Render instance free of large multipart bodies and file buffering.
2. **The frontend is the only client.** No public API consumers in v1, so the API is shaped for exactly the screens in the PRD rather than for generic reuse.
3. **The browser talks to the API directly for authenticated actions.** Server Components fetch public data (listing grid, pet detail) for SEO; the cookies live in the browser and are sent straight to the API for everything that mutates state.

---

## 3. Backend Framework: FastAPI vs Django + DRF

| Dimension | FastAPI | Django + DRF |
|---|---|---|
| **Shape of the fit** | A pure JSON API. Nothing in the framework assumes it renders HTML. | A full web framework where DRF is a layer bolted onto a template-oriented core. |
| **API docs** | OpenAPI/Swagger generated automatically from Pydantic models — always accurate because it *is* the validation layer. | Needs `drf-spectacular` and annotations; drifts from reality unless maintained. |
| **Validation** | Pydantic v2 (Rust core). One model defines validation, serialization, and the docs. | DRF serializers. More boilerplate, and a separate concept from the model layer. |
| **Async** | Native `async def` throughout. Matters here for the Cloudinary and Resend calls, which are I/O with no CPU work. | Async support exists but is partial; the ORM and much of the middleware stack are sync-first. |
| **Admin panel** | **None.** You build any admin surface yourself. | **Free, and genuinely good.** Moderating users and listings is a checkbox. |
| **Auth** | Assemble it: `python-jose` for JWT, `passlib`/`argon2-cffi` for hashing, your own dependency for the current user. Roughly 150 lines. | `django.contrib.auth` gives users, hashing, permissions, and password reset out of the box. |
| **Migrations** | Alembic — powerful, but autogenerate needs hand-editing (enums, generated columns, partial indexes). | Django migrations — more automatic, better at detecting model changes. |
| **Boilerplate to first endpoint** | Very little. | Settings module, app registration, URL conf, serializer, viewset. |
| **Performance** | Higher throughput on I/O-bound work (Starlette + uvicorn). | Adequate; not the bottleneck at our scale either way. |
| **Learning curve** | Small surface, but you make more decisions. | Large surface, but the decisions are made for you. |

### Decision: FastAPI

The frontend is Next.js and owns 100% of the UI. Django's biggest advantages — templates, forms, the ORM's tight coupling to views, the admin — are mostly aimed at a world where Django renders pages. We would be paying Django's weight and using a slice of it.

Concretely:

- **Auto-generated OpenAPI is worth a lot on a two-surface project.** `/docs` becomes the live contract between the Next.js work and the Python work — no hand-written API docs to fall out of date.
- **Pydantic v2 models are the single source of truth** for validation, response shapes, and documentation. The `UserPublic` / `UserPrivate` / `UserContact` split in [API.md §2](API.md#2-shared-response-objects) is three small classes and impossible to leak past.
- **The 41 endpoints in [API.md](API.md) are simple CRUD plus one interesting transaction.** Neither framework struggles; FastAPI just expresses them with less ceremony.

### What we give up, and how we cover it

| Loss | Mitigation |
|---|---|
| No admin panel for moderating users and listings | Not needed in v1 — no moderation feature is in scope. When it is, either build a small admin surface in Next.js against admin-scoped endpoints, or point a generic tool (Retool, Metabase) at the database. Noted as a v1.5 item in [ROADMAP.md](ROADMAP.md). |
| No built-in auth | Implemented once in Phase 1 and never touched again. The design is fully specified in [API.md §1.6](API.md#16-auth-cookies). |
| Alembic autogenerate misses things | Documented rule in [DATABASE.md §8](DATABASE.md#8-migrations-alembic): always read and edit generated migrations. |

**When Django would have been the right call:** if we wanted the admin on day one, if the team already knew Django, or if the product needed server-rendered pages from Python.

---

## 4. Hosting: Vercel vs Railway vs Render

### The three platforms compared

| Dimension | Vercel | Railway | Render |
|---|---|---|---|
| **Built for** | Next.js — it's the same company | Any container, any language | Any container, any language |
| **Python support** | Serverless functions only; not a good home for a long-lived FastAPI app with pooled DB connections | First class | First class |
| **Managed Postgres** | Only via partner integrations (Neon, Supabase) | Yes, included | Yes, included |
| **Free tier** | Generous and permanent for hobby projects | **No true free tier** — trial credit, then usage-based (~$5/mo minimum) | Free web service + free Postgres (Postgres expires after 30 days; free services sleep) |
| **Cold starts** | None for static/edge; functions warm fast | Paid instances stay warm | **Free tier sleeps after 15 min idle → 30–60 s first request.** Paid Starter ($7/mo) stays warm |
| **Deploy DX** | Best in class: push to Git, preview URL per PR | Excellent, very fast builds, nice logs | Good; builds are slower than Railway |
| **Preview environments** | Automatic per PR | Per-environment, manual setup | Per PR on paid plans |
| **Pricing model** | Per-seat + usage | Pure usage (CPU/RAM/egress) — cheap when idle, harder to predict | Flat per-service — predictable, pay even when idle |
| **Edge CDN for the frontend** | Yes, global, automatic | No | Static sites yes; not Next.js-native |
| **Next.js features** | All of them: ISR, image optimization, streaming, middleware | Works, but you self-host Next in a container and lose the managed edge behavior | Same caveat |

### Decision: Vercel for the frontend, Render for the backend and database

```mermaid
flowchart LR
    subgraph V[Vercel]
        FE[Next.js frontend<br/>adopt-a-pet.vercel.app]
    end
    subgraph R[Render]
        BE[FastAPI web service<br/>api.adopt-a-pet.onrender.com]
        DB[(Render Postgres)]
    end
    FE -->|NEXT_PUBLIC_API_URL| BE
    BE -->|DATABASE_URL, private network| DB
```

**Why split rather than run everything on one platform:**

Next.js on Vercel is meaningfully better than Next.js anywhere else — image optimization, ISR, edge caching, and per-PR preview deployments all work with zero configuration, and the free tier covers a project of this size indefinitely. Putting the frontend on Render to gain "one dashboard" trades away real capability for a small convenience.

**Why Render over Railway for the backend:**

| Reason | Detail |
|---|---|
| Predictable cost | $7/mo Starter web service + $7/mo Postgres, flat. Railway's usage billing is cheaper when idle but harder to forecast, and has no free tier at all. |
| Free tier for development | Render's free web service and free Postgres let the whole staging environment cost $0 while we build. Only production needs paid instances. |
| Postgres backups on the paid tier | Daily automated backups included. |
| Native health checks | `GET /health` from [API.md §10](API.md#10-meta-endpoints) plugs straight into Render's health check config. |

**Railway is the better choice if** deploy speed and DX matter more than a free tier, or if the app is bursty enough that usage billing wins. It is a genuinely close call — the deploy configuration is nearly identical either way, so switching later is a day of work, not a rewrite.

**The one real Render caveat:** free-tier services sleep after 15 minutes of inactivity, and the first request afterwards takes 30–60 seconds. Acceptable for staging. **Production must be on the paid Starter plan** — a 45-second cold start on the landing page would sink the product.

---

## 5. Image Storage: Cloudinary vs S3 + CloudFront

| Dimension | Cloudinary | S3 + CloudFront |
|---|---|---|
| Setup | One account, one SDK, done | Bucket + IAM policy + CloudFront distribution + OAI + cache behaviors |
| Transformations | URL-based, on the fly: `w_400,h_300,c_fill,f_auto,q_auto` | Build your own with Lambda@Edge or a resizing service |
| Direct browser upload | Signed uploads built in | Presigned PUT URLs, then your own post-processing |
| CDN | Included | CloudFront, configured separately |
| Free tier | 25 credits/mo ≈ 25 GB storage + bandwidth — well beyond our needs | Pay from the first byte, though pennies at this scale |
| Cost at scale | Gets expensive past the free tier | Cheaper at high volume |
| Lock-in | URLs contain the Cloudinary domain; migrating means rewriting stored URLs | Portable |

### Decision: Cloudinary

Pet photos are the product. Cloudinary's URL transformations mean one uploaded image serves every context — a 400×300 card thumbnail, a 1200px gallery image, a WebP or AVIF variant per browser — without a resizing pipeline, a background worker, or extra storage:

```
.../upload/w_400,h_300,c_fill,g_auto,f_auto,q_auto/adopt-a-pet/pets/x1.jpg   → card
.../upload/w_1200,c_limit,f_auto,q_auto/adopt-a-pet/pets/x1.jpg              → gallery
```

`g_auto` (content-aware cropping) keeps the animal centered in the 4:3 card crop, which is exactly the kind of thing that would otherwise need manual work on every listing. Building the S3 equivalent is a multi-day detour for a product that needs zero images beyond pet photos and avatars.

**Folders:** `adopt-a-pet/pets/` and `adopt-a-pet/avatars/`.

---

## 6. Email: Resend vs SendGrid vs SES

| Dimension | Resend | SendGrid | Amazon SES |
|---|---|---|---|
| Setup | API key, verify a domain, send | Account review, sender auth, API key | IAM, domain verification, **sandbox escape request** |
| Free tier | 3,000/mo, 100/day | 100/day | 62,000/mo from EC2; otherwise $0.10/1,000 |
| DX | Excellent — clean SDK, React Email templates, good logs | Dated API, heavy dashboard | Raw and low-level |
| Deliverability | Good | Very good, long track record | Very good |
| Templates | React Email components, versioned in the repo | Dashboard-based template editor | None — you build the MIME |
| Time to first email | Minutes | ~an hour | A day, waiting on sandbox approval |

### Decision: Resend

Six transactional emails ([PRD.md §7](PRD.md#7-email-notification-matrix)), low volume, and templates that should live in the repository next to the code that sends them. Resend's free tier covers us many times over, and React Email keeps the templates reviewable in pull requests instead of stranded in a vendor dashboard.

SES becomes correct at high volume or if the rest of the infrastructure moves to AWS. SendGrid is the safe default with the least pleasant developer experience.

---

## 7. Repository Layout

A monorepo — one repository, two deployables. The frontend and backend change together constantly in early development, and a single PR that touches an endpoint and its consumer is much easier to review than two coordinated PRs.

```
adopt-a-pet/
├─ README.md
├─ docs/
│  ├─ PRD.md
│  ├─ DATABASE.md
│  ├─ API.md
│  ├─ ARCHITECTURE.md
│  └─ ROADMAP.md
│
├─ backend/
│  ├─ app/
│  │  ├─ main.py                  # FastAPI app, CORS, router registration, exception handlers
│  │  ├─ config.py                # Pydantic Settings, reads env vars
│  │  ├─ database.py              # engine, session factory, get_db dependency
│  │  ├─ models/                  # SQLAlchemy models, one file per table group
│  │  │  ├─ user.py               # User, RefreshToken, EmailToken
│  │  │  ├─ pet.py                # Pet, PetImage
│  │  │  ├─ application.py        # AdoptionApplication, Favorite
│  │  │  └─ notification.py
│  │  ├─ schemas/                 # Pydantic request/response models
│  │  │  ├─ auth.py  user.py  pet.py  application.py  common.py
│  │  ├─ routers/                 # HTTP layer only: parse, authorize, delegate
│  │  │  ├─ auth.py  users.py  pets.py  images.py
│  │  │  ├─ favorites.py  applications.py  notifications.py  meta.py
│  │  ├─ services/                # business logic, the only layer that writes
│  │  │  ├─ auth_service.py  pet_service.py  application_service.py
│  │  │  ├─ image_service.py  notification_service.py
│  │  ├─ core/
│  │  │  ├─ security.py           # hashing, JWT encode/decode, token generation
│  │  │  ├─ dependencies.py       # get_current_user, require_verified, require_owner
│  │  │  ├─ exceptions.py         # AppError subclasses → the error envelope
│  │  │  └─ rate_limit.py
│  │  └─ integrations/
│  │     ├─ cloudinary_client.py
│  │     └─ email_client.py       # Resend + template rendering
│  ├─ alembic/
│  ├─ scripts/seed.py
│  ├─ tests/
│  ├─ pyproject.toml
│  └─ Dockerfile
│
└─ frontend/
   ├─ src/
   │  ├─ app/
   │  │  ├─ layout.tsx  page.tsx           # landing
   │  │  ├─ (auth)/login  register  verify-email  forgot-password  reset-password
   │  │  ├─ pets/page.tsx                  # browse
   │  │  ├─ pets/[id]/page.tsx             # detail
   │  │  ├─ pets/[id]/applications/page.tsx
   │  │  ├─ pets/new  pets/[id]/edit
   │  │  ├─ dashboard/listings  applications  favorites  profile
   │  │  └─ users/[id]/page.tsx
   │  ├─ components/
   │  │  ├─ ui/                            # Button, Input, Badge, Modal, Skeleton
   │  │  ├─ pets/                          # PetCard, PetGrid, FilterBar, PetGallery, PetForm
   │  │  ├─ applications/                  # ApplicationCard, ApplicationForm
   │  │  └─ layout/                        # Header, Footer, NotificationBell
   │  ├─ lib/
   │  │  ├─ api.ts                         # fetch wrapper: credentials, refresh-on-401, error envelope
   │  │  ├─ auth.ts                        # session context
   │  │  ├─ cloudinary.ts                  # signed upload helper
   │  │  └─ types.ts                       # TS types mirroring the API schemas
   │  └─ hooks/                            # usePets, useFavorites, useApplications
   ├─ tailwind.config.ts
   ├─ next.config.ts
   └─ package.json
```

### Backend layering rule

```
router  →  service  →  model/session
```

| Layer | Does | Never does |
|---|---|---|
| **Router** | Declares the path, request/response schemas, and auth dependency. Calls one service function. | Contains business logic or touches the session directly |
| **Service** | All business rules, all transactions, all side effects (email, Cloudinary). Raises typed `AppError`s. | Knows about HTTP, `Request`, or status codes |
| **Model** | Table definition and relationships. | Contains logic |

The payoff is that the accept-application transaction lives in exactly one function, and a router is short enough to read in full:

```python
@router.post("/{application_id}/accept", response_model=ApplicationDetail)
async def accept_application(
    application_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return application_service.accept(db, application_id, user)
```

### Frontend data-fetching rule

| Page type | Strategy | Why |
|---|---|---|
| Landing, browse, pet detail, public profile | **Server Components**, fetched on the server | These pages must be crawlable — a pet listing that Google can index is a real acquisition channel |
| Favorite toggle, forms, dashboards, notifications | **Client Components** calling the API from the browser | Needs the auth cookies and interactive state |
| Filter changes on browse | URL search params → server re-render | Makes filter state shareable and back-button correct, per FR-DISC-6 |

No TanStack Query in v1. The mutation surface is small; a shared `lib/api.ts` wrapper plus React state covers it without another dependency to configure.

---

## 8. Authentication Flow

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Next.js (browser)
    participant API as FastAPI
    participant DB as Postgres

    Note over U,DB: Login
    U->>FE: email + password
    FE->>API: POST /auth/login (credentials: include)
    API->>DB: Look up user by email
    DB-->>API: user row
    API->>API: argon2.verify(password, hash)
    API->>DB: INSERT refresh_tokens (sha256 of token)
    API-->>FE: Set-Cookie access_token (15m) + refresh_token (7d)
    FE-->>U: Redirect to /pets

    Note over U,DB: Normal request
    FE->>API: GET /users/me/favorites (cookie sent automatically)
    API->>API: Decode JWT, load user
    API-->>FE: 200 data

    Note over U,DB: Access token expired
    FE->>API: POST /pets/{id}/favorite
    API-->>FE: 401 TOKEN_EXPIRED
    FE->>API: POST /auth/refresh
    API->>DB: Look up hash, check not revoked/expired
    API->>DB: Revoke old, INSERT new (rotation)
    API-->>FE: New cookie pair
    FE->>API: Retry POST /pets/{id}/favorite
    API-->>FE: 201

    Note over U,DB: Refresh also invalid
    FE->>API: POST /auth/refresh
    API-->>FE: 401 REFRESH_INVALID
    FE-->>U: Clear state, redirect to /login
```

| Parameter | Value | Reasoning |
|---|---|---|
| Password hash | Argon2id | Current recommended algorithm; memory-hard, unlike bcrypt |
| Access token | JWT, 15 min | Short enough that a leaked token expires quickly; stateless so no DB read per request |
| Refresh token | Opaque random 32 bytes, 7 days | Opaque, not a JWT — it must be revocable, and revocability requires a DB lookup anyway |
| Storage | httpOnly cookies | Immune to XSS token theft, unlike `localStorage` |
| Rotation | Every refresh issues a new pair and revokes the old | Shrinks the window a stolen refresh token is useful |
| Password reset | Revokes **all** of that user's refresh tokens | "Change your password" must actually end other sessions |
| Verification token | SHA-256 hashed in `email_tokens`, single-use | A database leak must not yield usable links |

### Security checklist

| Concern | Handling |
|---|---|
| CORS | Explicit allowlist: the Vercel production domain, preview domains, and `localhost:3000`. `allow_credentials=True`. Never `*` — a wildcard is invalid with credentials anyway. |
| CSRF | `SameSite=Lax` cookies plus non-GET for every mutation. The refresh cookie is additionally path-scoped to `/api/v1/auth`. |
| IDOR | Every owner-scoped endpoint re-checks ownership from the database in the service layer — never from a client-supplied ID. Applications return `404` (not `403`) to non-parties so a third party learns nothing. |
| PII exposure | Enforced by response schema, not by convention: `UserPublic` has no `email` or `phone` field, so it cannot leak one. `UserContact` is used only after acceptance. |
| Input validation | Pydantic at the boundary — max lengths, enum membership, positive integers, email format. Nothing untyped reaches a service. |
| SQL injection | SQLAlchemy parameterized queries throughout. No string-built SQL, including in the full-text search. |
| Rate limiting | Per [API.md §1.7](API.md#17-rate-limits), strictest on the auth and email-sending endpoints. |
| Secrets | Environment variables only. `.env` is gitignored; `.env.example` documents the keys with placeholder values. |
| Error leakage | Unhandled exceptions return a generic 500 with a correlation ID; the real trace goes to Sentry and structured logs. |
| Cloudinary signatures | Expire in 1 hour, scoped to a fixed folder, and only issued to authenticated users. |

---

## 9. Background Work

Three things must not block an HTTP response:

| Job | Trigger | Mechanism |
|---|---|---|
| Send an email | Registration, reset, application events | `BackgroundTasks` — FastAPI runs it after the response is returned |
| Delete Cloudinary assets | Image or listing deleted | `BackgroundTasks` |
| Sentry reporting | Unhandled exception | Sentry SDK, async |

**No Celery, no Redis, no worker process in v1.** FastAPI's `BackgroundTasks` runs in the same process after the response is sent, which is exactly right for a handful of fire-and-forget I/O calls. The tradeoff is honest: if the process restarts mid-task, the email is lost. For a verification email that the user can resend, that is an acceptable failure — and adding a real queue later is a contained change because every side effect already goes through `email_client` or `cloudinary_client`.

**Emails are always queued after the database commit**, never inside the transaction — see [DATABASE.md §7](DATABASE.md#7-the-accept-transaction).

---

## 10. Environments

| Environment | Frontend | Backend | Database |
|---|---|---|---|
| **Local** | `localhost:3000` | `localhost:8000` (uvicorn `--reload`) | Docker Postgres on `localhost:5432` |
| **Staging** | Vercel preview (auto per PR) | Render free service | Render free Postgres |
| **Production** | Vercel production | Render Starter ($7/mo, no sleep) | Render Starter Postgres ($7/mo, daily backups) |

Local Postgres via `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: adopt
      POSTGRES_PASSWORD: adopt
      POSTGRES_DB: adopt_a_pet
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
volumes:
  pgdata:
```

---

## 11. Environment Variables

### Backend (`backend/.env`)

| Variable | Example | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://adopt:adopt@localhost:5432/adopt_a_pet` | Postgres connection |
| `JWT_SECRET` | 64 random hex chars | Signs access tokens. **Different per environment.** |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_MINUTES` | `15` | |
| `REFRESH_TOKEN_DAYS` | `7` | |
| `FRONTEND_URL` | `https://adopt-a-pet.vercel.app` | Builds absolute links in emails |
| `CORS_ORIGINS` | `https://adopt-a-pet.vercel.app,http://localhost:3000` | Comma-separated allowlist |
| `CLOUDINARY_CLOUD_NAME` | `adopt-a-pet` | |
| `CLOUDINARY_API_KEY` | | |
| `CLOUDINARY_API_SECRET` | | **Backend only.** Never exposed to the browser. |
| `RESEND_API_KEY` | | |
| `EMAIL_FROM` | `Adopt-a-Pet <hello@adopt-a-pet.com>` | |
| `SENTRY_DSN` | | Optional locally |
| `ENVIRONMENT` | `local` \| `staging` \| `production` | Gates debug behavior and cookie `Secure` flag |

### Frontend (`frontend/.env.local`)

| Variable | Example | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://adopt-a-pet-api.onrender.com/api/v1` | API base — public by necessity |
| `NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME` | `adopt-a-pet` | Builds transformation URLs |
| `NEXT_PUBLIC_SENTRY_DSN` | | |

> Anything prefixed `NEXT_PUBLIC_` is shipped to the browser in the JS bundle. The Cloudinary **API secret** must never carry that prefix, and never appear in the frontend at all.

---

## 12. Deployment

### Backend on Render

`render.yaml` at the repository root:

```yaml
services:
  - type: web
    name: adopt-a-pet-api
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/v1/health
    envVars:
      - key: DATABASE_URL
        fromDatabase: { name: adopt-a-pet-db, property: connectionString }
      - key: JWT_SECRET
        generateValue: true
      - key: ENVIRONMENT
        value: production

databases:
  - name: adopt-a-pet-db
    databaseName: adopt_a_pet
    plan: starter
```

Migrations run in `startCommand`, so the schema is always ahead of the code that needs it. Remaining secrets are set in the Render dashboard, not committed.

### Frontend on Vercel

Import the repository, set **Root Directory** to `frontend`. Everything else is detected. Environment variables are set per scope (Production / Preview / Development) in the dashboard. Add `res.cloudinary.com` to `next.config.ts` `images.remotePatterns` so `next/image` will serve pet photos.

### CI (GitHub Actions)

`.github/workflows/ci.yml`, on every pull request:

| Job | Steps |
|---|---|
| `backend` | ruff → mypy → pytest against a Postgres service container |
| `frontend` | eslint → `tsc --noEmit` → `next build` |

Both platforms deploy automatically on merge to `main`. Vercel additionally builds a preview per PR.

---

## 13. Observability

| Signal | Tool | Detail |
|---|---|---|
| Errors | Sentry | Both surfaces. Release tagging on deploy; PII scrubbing on. |
| Logs | Render's log stream | Structured JSON: timestamp, level, request ID, path, status, duration |
| Uptime | Render health checks | `GET /api/v1/health` verifies the database connection, not just that the process is alive |
| Frontend performance | Vercel Analytics | Core Web Vitals on real traffic |

Every request gets an `X-Request-ID` (generated if absent) that appears in the log line, the Sentry event, and the 500 response — so a user-reported "it broke" can be traced to a specific request.

---

## 14. Decision Summary

| Decision | Choice | One-line reason |
|---|---|---|
| Backend framework | FastAPI | Pure JSON API with auto-generated docs; Django's admin and templates aren't earning their weight here |
| ORM | SQLAlchemy 2.0 + Alembic | Typed models, explicit control over the transaction in FR-APP-6 |
| Frontend hosting | Vercel | Next.js works best where Next.js is made |
| Backend hosting | Render | Predictable flat pricing, free tier for staging, native health checks |
| Database hosting | Render Postgres | Same platform as the API — private networking, one bill |
| Images | Cloudinary | URL transformations replace an entire resizing pipeline |
| Email | Resend | Templates live in the repo; free tier covers 6 emails many times over |
| Repo | Monorepo | Frontend and backend change together during the whole build |
| Background jobs | `BackgroundTasks` | Six fire-and-forget emails do not justify Celery and Redis |
| Auth | Custom JWT in httpOnly cookies | No vendor, XSS-safe storage, revocable sessions |
