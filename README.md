# Petfolio

A web portal that connects people who need to rehome a pet with people who want to adopt one.

An owner creates a listing with photos and details. Adopters browse the catalog, filter by animal type, save favorites, and submit an adoption application. The owner reviews applications in one inbox, accepts one adopter, and marks the pet adopted. Both sides get email notifications at each step.

**Status:** Design complete, build not started.

---

## Documentation

Read in this order.

| Document                                     | What's in it                                                                                                                                                                      |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [docs/PRD.md](docs/PRD.md)                   | Executive summary, problem statement, personas, feature list, numbered functional requirements, user flows, UX/design direction, email matrix                                     |
| [docs/DATABASE.md](docs/DATABASE.md)         | ERD, table-by-table schema with DDL, enums, indexes, the accept transaction, migration and seed strategy                                                                          |
| [docs/API.md](docs/API.md)                   | All 41 REST endpoints with request/response shapes, error codes, pagination, auth cookie design, rate limits                                                                      |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System diagram, stack tradeoff tables (FastAPI vs Django, Vercel vs Railway vs Render, Cloudinary vs S3, email providers), repo layout, auth flow, security checklist, deployment |
| [docs/ROADMAP.md](docs/ROADMAP.md)           | Ten build phases with deliverables, requirement coverage, and "done when" checklists                                                                                              |

---

## Stack

| Layer            | Choice                                                            |
| ---------------- | ----------------------------------------------------------------- |
| Frontend         | Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS v4 |
| Backend          | FastAPI · Python 3.12 · Pydantic v2                               |
| ORM / Migrations | SQLAlchemy 2.0 · Alembic                                          |
| Database         | PostgreSQL 16                                                     |
| Images           | Cloudinary (signed direct-from-browser upload)                    |
| Email            | Resend                                                            |
| Auth             | Custom JWT in httpOnly cookies, Argon2id hashing                  |
| Hosting          | Vercel (frontend) · Render (API + Postgres)                       |

Reasoning for each choice is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Scope

**In v1:** authentication with email verification · user profiles · pet listing CRUD with multiple photos · browse with filters, search, sort, and pagination · favorites · adoption applications with accept/reject · mark as adopted · six transactional emails · landing page.

**Not in v1:** in-app messaging · shelter accounts · payments · map/radius search · admin dashboard · mobile apps · multi-language. Post-v1 candidates are listed in [docs/ROADMAP.md §2](docs/ROADMAP.md#2-beyond-v1).

---

## Repository Layout (planned)

```
adopt-a-pet/
├─ docs/          # this documentation set
├─ backend/       # FastAPI: routers → services → models
└─ frontend/      # Next.js App Router
```

Full breakdown in [docs/ARCHITECTURE.md §7](docs/ARCHITECTURE.md#7-repository-layout).

---

## Getting Started

Nothing is implemented yet. Begin with [Phase 0 — Foundation](docs/ROADMAP.md#phase-0--foundation), which sets up the repository, Docker Postgres, Alembic migrations, the deployed skeleton on Vercel and Render, and CI.
