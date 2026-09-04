# 🐾 Pet Adoption Web Portal — Product & Engineering Guide

**Status:** Pre-development / planning locked
**Team size:** 2
**Repo model:** Monorepo (`/frontend` + `/backend`, single PR spans both)

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Personas & Core User Journey](#2-personas--core-user-journey)
3. [Feature Roadmap (MVP / V2 / V3)](#3-feature-roadmap-mvp--v2--v3)
4. [Tech Stack](#4-tech-stack)
5. [Data Model](#5-data-model)
6. [Trust & Security Design Rules](#6-trust--security-design-rules)
7. [Repo Structure](#7-repo-structure)
8. [API Surface](#8-api-surface)
9. [Modular Roadmap (Timeline)](#9-modular-roadmap-timeline)
10. [Git Workflow (2-Person Team)](#10-git-workflow-2-person-team)
11. [Deployment Notes](#11-deployment-notes)
12. [Open Decisions to Confirm](#12-open-decisions-to-confirm)

---

## 1. Project Vision

**One-liner:** "Airbnb for pet adoption" — pet owners/rescuers list pets, adopters browse and apply, owners choose who gets the pet.

### Primary Flow

1. A pet owner uploads information and images of a pet they want to give up for adoption.
2. Interested adopters browse available pets.
3. They apply to adopt.
4. The owner reviews requests and approves one adopter.

---

## 2. Personas & Core User Journey

| Persona                                                    | Needs                                                     | MVP?  |
| ---------------------------------------------------------- | --------------------------------------------------------- | ----- |
| **Lister** (owner giving up a pet, or independent rescuer) | Easy listing creation, control over who adopts            | ✅    |
| **Adopter**                                                | Trustworthy browsing, simple application, status tracking | ✅    |
| **Shelter/Org** (multi-pet, team)                          | Bulk listing, org profile, verification badge             | ⏭ V2 |
| **Admin/Moderator**                                        | Flag/remove listings, resolve disputes, verify orgs       | ⏭ V2 |

### Core User Journey

1. Sign up / log in
2. List a pet — wizard: basic info → photos → health/temperament → location → publish
3. Browse — grid/list with filters (species, breed, age, size, location)
4. View pet detail page
5. Apply to adopt — short form (living situation, experience, why this pet)
6. Owner reviews applications on a dashboard
7. Owner approves one applicant → system auto send the adopter mail
8. Listing marked `adopted` (archived, not deleted)

---

## 3. Feature Roadmap (MVP / V2 / V3)

| Feature                                                                 | MVP | V2  | V3  |
| ----------------------------------------------------------------------- | :-: | :-: | :-: |
| Auth (email + password)                                                 | ✅  |     |     |
| Pet listing CRUD + multi-image upload                                   | ✅  |     |     |
| Browse + basic filters (species/age/size/location text)                 | ✅  |     |     |
| Pet detail page                                                         | ✅  |     |     |
| Apply to adopt (form)                                                   | ✅  |     |     |
| Owner dashboard: review/approve/reject applicants                       | ✅  |     |     |
| Transactional email (Resend)                                            | ✅  |     |     |
| Responsive UI                                                           | ✅  |     |     |
| In-app messaging (owner ↔ applicant)                                    |     | ✅  |     |
| Favorites/saved pets                                                    |     | ✅  |     |
| Advanced filters (breed, distance radius, energy level, good-with-kids) |     | ✅  |     |
| Geo-based search (lat/lng radius)                                       |     | ✅  |     |
| Verified shelter/org accounts                                           |     | ✅  |     |
| Report/flag a listing                                                   |     | ✅  |     |
| Admin moderation dashboard                                              |     |     | ✅  |
| Adopter/lister ratings & trust score                                    |     |     | ✅  |
| Adoption success stories / social share                                 |     |     | ✅  |
| Map view                                                                |     |     | ✅  |
| Push notifications                                                      |     |     | ✅  |

**MVP scope is deliberately narrow:** no messaging, no payments, no geo — just enough to prove the core loop (list → apply → approve) works end to end.

---

## 4. Tech Stack

| Layer    | Choice                                                 | Notes                 |
| -------- | ------------------------------------------------------ | --------------------- |
| Frontend | Next.js 15 (App Router) + TypeScript + Tailwind CSS v4 |                       |
| Backend  | FastAPI + SQLAlchemy 2.0 (async) + Alembic             |                       |
| Database | PostgreSQL (Docker locally, Render for deploy)         | Real SQL, not SQLite  |
| Auth     | NextAuth.js v5 (credentials + email provider)          |                       |
| Images   | Cloudinary                                             |                       |
| Email    | Resend + React Email templates                         |                       |
| Deploy   | Vercel (frontend) + Render (backend)                   | Both free-tier viable |
| Repo     | Monorepo: `/frontend` + `/backend`                     | Single PR spans both  |

---

## 5. Data Model

### 5.1 Schema

```
User
 ├─ id, name, email, hashed_password
 ├─ phone, city (free text), avatar_url
 └─ created_at

PetListing
 ├─ id, owner_id (FK → User)
 ├─ name, species, breed, age, gender, size
 ├─ description, temperament_tags[], vaccinated, neutered
 ├─ city (free text)
 ├─ status: draft | published | pending_adoption | adopted | withdrawn
 ├─ adopted_via_application_id (FK → Application.id, nullable)   # proof of real adoption
 └─ created_at

PetImage
 ├─ id, pet_id (FK → PetListing), url, sort_order

Application
 ├─ id, pet_id (FK), applicant_id (FK → User)
 ├─ status: pending | approved | rejected | withdrawn
 ├─ message, living_situation, experience
 └─ submitted_at, decided_at

Notification
 ├─ id, user_id, type, payload_json, read_at, created_at
```

### 5.2 Key Design Decision: No `role` Field on `User`

**There is no `owner` vs. `adopter` role column.** A single account can list pets _and_ apply to adopt other pets — simultaneously, without switching modes. "Owner" and "adopter" are not identities; they're **contexts** derived from which table a `user.id` appears in as a foreign key:

- Appears as `PetListing.owner_id` → acting as an owner _for that pet_
- Appears as `Application.applicant_id` → acting as an adopter _for that application_

This mirrors Airbnb's `users` table, where a host and a guest are the same row — "host" just means "appears in `listings.host_id`."

**Why this beats an explicit role field:**

|                                   | Single role (chosen)                 | Explicit `role: owner \| adopter`     |
| --------------------------------- | ------------------------------------ | ------------------------------------- |
| Sign up once, do both immediately | ✅                                   | ❌ needs role-switch UX               |
| Adopter today → lister next month | ✅ free                              | ❌ requires migration/flow            |
| "Is this user an owner?"          | `EXISTS (... WHERE owner_id = :uid)` | `user.role == 'owner'` — can go stale |
| Matches Airbnb/OLX model          | ✅                                   | ❌                                    |

Roles/context are **computed on read**, never stored:

```python
async def get_user_dashboard_summary(db, user_id: int):
    listings = await db.execute(select(PetListing).where(PetListing.owner_id == user_id))
    applications = await db.execute(select(Application).where(Application.applicant_id == user_id))
    return {
        "is_lister": bool(listings),
        "is_adopter": bool(applications),
        "my_listings": listings,
        "my_applications": applications,
    }
```

Dashboard nav always shows both **"My Listings"** and **"My Applications"** tabs — no mode switch needed.

---

## 6. Repo Structure

```
pet-adoption-portal/
├── frontend/                          # Next.js 15 (App Router)
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── (main)/
│   │   │   ├── page.tsx               # Home / browse grid
│   │   │   ├── pets/
│   │   │   │   ├── [id]/page.tsx      # Pet detail
│   │   │   │   └── new/page.tsx       # Create-listing wizard
│   │   │   ├── dashboard/
│   │   │   │   ├── my-listings/page.tsx
│   │   │   │   ├── my-applications/page.tsx
│   │   │   │   └── applications/[petId]/page.tsx  # review applicants
│   │   │   └── profile/page.tsx
│   │   ├── api/
│   │   │   ├── auth/[...nextauth]/route.ts
│   │   │   └── uploadthing/route.ts
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/                        # Button, Card, Input, etc.
│   │   ├── pets/                      # PetCard, PetGrid, FilterBar
│   │   ├── applications/
│   │   └── layout/                    # Navbar, Footer
│   ├── lib/
│   │   ├── api-client.ts              # fetch wrapper → FastAPI
│   │   ├── auth.ts                    # NextAuth config
│   │   └── validators.ts              # zod schemas
│   ├── types/
│   ├── middleware.ts                  # route protection
│   ├── next.config.ts
│   └── package.json
│
├── backend/                           # FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py            # hashing, JWT
│   │   │   └── database.py            # async engine/session
│   │   ├── models/                    # SQLAlchemy models
│   │   │   ├── user.py / pet.py / application.py
│   │   ├── schemas/                   # Pydantic
│   │   ├── api/v1/
│   │   │   ├── routes_auth.py
│   │   │   ├── routes_pets.py
│   │   │   ├── routes_applications.py
│   │   │   ├── routes_users.py
│   │   │   └── router.py              # aggregator
│   │   ├── services/                  # business logic
│   │   │   ├── pet_service.py
│   │   │   ├── application_service.py
│   │   │   └── email_service.py       # Resend
│   │   ├── deps.py                    # get_db, get_current_user
│   │   └── utils/
│   ├── alembic/versions/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── docs/
│   ├── architecture.md
│   ├── api-spec.md
│   └── roadmap-v2.md                  # keeps V2/V3 scope out of MVP
├── .github/workflows/ci.yml
├── docker-compose.yml                 # local Postgres + backend
├── .env.example
└── README.md
```

---

## 7. API Surface

```
POST   /auth/register          POST /auth/login
GET    /users/me               PATCH /users/me

GET    /pets                   ?species=&size=&city=&status=
GET    /pets/{id}
POST   /pets                           (create draft)
PATCH  /pets/{id}                      (whitelist-limited transitions only, see §6.2)
DELETE /pets/{id}
POST   /pets/{id}/images

POST   /pets/{id}/applications
GET    /applications/mine
GET    /pets/{id}/applications         (owner only)
PATCH  /applications/{id}              (approve/reject → cascades: auto-reject others,
                                         mark pet adopted, trigger emails — see §6.2)
```

---

## 8. Modular Roadmap (Timeline)

| **Phase**                 | **Scope**                                                                                                                                                |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0 — Foundations**       | Repo scaffold, Docker Compose (Postgres), FastAPI health check, Next.js skeleton, Alembic init, CI, Vercel + Render wired to a "Hello World" deployment. |
| **1 — Auth**              | User model, FastAPI `/auth`, NextAuth credentials provider calling backend, session/middleware, profile page.                                            |
| **2 — Listings + Images** | Pet model + migrations, create/edit listing wizard, UploadThing integration, draft/publish states.                                                       |
| **3 — Browse & Discover** | Home grid, filters, pagination, pet detail page.                                                                                                         |
| **4 — Applications**      | Application model, apply form, owner review dashboard, approve/reject workflow (with status cascade rules).                                              |
| **5 — Notifications**     | Resend + React Email for application received, approved, rejected, and listing published emails.                                                         |
| **6 — Polish & Trust**    | Validation across forms, loading/empty/error states, responsive UI pass, report-a-listing stub, seed/demo data.                                          |
| **7 — Deploy & Launch**   | Production environment variables, custom domain, Sentry, Render Postgres backups, README, demo video, and final deployment.                              |

---

## 9. Deployment Notes

- **Local:** `docker-compose.yml` runs Postgres; backend via `uvicorn --reload`; frontend via `next dev`.
- **Backend (Render):** connect to Render Postgres, run Alembic migrations as a release/pre-deploy command.
- **Frontend (Vercel):** `NEXT_PUBLIC_API_URL` env var points at the Render backend URL.
- **Images:** Cloudinary
- **Email:** Resend API key lives in backend env only, never exposed to frontend.

---
