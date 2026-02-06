# Waywo Documentation Plan

> From zero to production-ready documentation site using [Docus](https://docus.dev)

---

## Overview

This plan covers building a comprehensive documentation site for waywo — an intelligent searchable index of "What are you working on?" projects from Hacker News. The docs site will live in `/docs` within the monorepo and be built with Docus (Nuxt-based documentation framework).

### Approach

- **Breadth first** — Cover all sections at a useful level before going deep on any one area
- **Keep it simple** — Scannable pages with clear headers, tables, and code examples where they help
- **Examples where helpful** — Real code snippets from the codebase, not every line documented
- **Hand-written API docs** — With references to the auto-generated Swagger/ReDoc for full schemas
- **Flexible ordering** — Docus directory prefixes (10, 20, 30...) use gaps so new sections can be inserted without renumbering

### Content Directory Numbering

Sections use **increments of 10** so new sections can slot in between without renumbering anything:

```
content/
├── index.md                    (landing page)
├── 10.getting-started/
├── 20.architecture/
├── 30.pipeline/
├── 40.ai-models/
├── 50.search-and-rag/
├── 60.api/
├── 70.frontend/
├── 80.development/
└── 90.operations/
```

Within each section, pages use **increments of 1** (1, 2, 3...) since page reordering within a section is rare.

---

## Milestone 1: Scaffolding & Configuration

**Goal**: Set up the Docus project, configure branding, navigation, and dev workflow.

### Tasks
- [ ] Initialize Docus project in `/docs` via `npx create-docus docs`
- [ ] Configure `app.config.ts` — site name, color scheme, social links (GitHub repo)
- [ ] Configure `nuxt.config.ts` — SEO defaults, title template (`%s - Waywo Docs`)
- [ ] Set up custom theme in `assets/css/main.css` — color tokens
- [ ] Create landing page (`content/index.md`) with hero: tagline, quick links to key sections
- [ ] Add to `docker-compose.yml` as optional service (port 3001)
- [ ] Add `docs` script targets to root-level Makefile
- [ ] Verify local dev server runs at `http://localhost:3001`

### Deliverable
A running Docus site with branded landing page, navigation shell, and local dev workflow.

---

## Milestone 2: Getting Started Guide

**Goal**: Get a new developer from zero to running waywo locally.

### Pages
- [ ] **`10.getting-started/1.introduction.md`** — What is waywo, problem it solves, solution overview
- [ ] **`10.getting-started/2.prerequisites.md`** — Required software, environment variables table
- [ ] **`10.getting-started/3.quickstart.md`** — Clone → `docker compose up` → open browser. Service URLs table
- [ ] **`10.getting-started/4.manual-setup.md`** — Running without Docker for hot-reload development
- [ ] **`10.getting-started/5.first-run.md`** — Guided tour: process posts → extract projects → search → chat

### Deliverable
A newcomer can go from `git clone` to a fully working local instance.

---

## Milestone 3: Architecture & Concepts

**Goal**: Explain how waywo works at a conceptual level.

### Pages
- [ ] **`20.architecture/1.overview.md`** — High-level data flow diagram: HN → comments → projects → embeddings → search/chat
- [ ] **`20.architecture/2.data-model.md`** — Three core entities (`WaywoPost`, `WaywoComment`, `WaywoProject`), relationships, key fields
- [ ] **`20.architecture/3.tech-stack.md`** — Technology inventory table grouped by layer
- [ ] **`20.architecture/4.service-map.md`** — Docker services table: name, port, purpose, health endpoint

### Deliverable
A developer understands the system architecture, data model, and technology choices.

---

## Milestone 4: Data Pipeline Documentation

**Goal**: Document how data flows from Hacker News to stored, searchable projects.

### Pages
- [ ] **`30.pipeline/1.overview.md`** — Four stages: Post Collection → Comment Extraction → Project Processing → Embedding. Flow diagram
- [ ] **`30.pipeline/2.post-collection.md`** — `waywo.yml` format, HN Firebase API, how posts are fetched and stored
- [ ] **`30.pipeline/3.comment-extraction.md`** — How comments are fetched, filtering, status tracking
- [ ] **`30.pipeline/4.project-workflow.md`** — The LlamaIndex workflow: 8 steps with a brief description of each. Example input/output for the overall workflow
- [ ] **`30.pipeline/5.celery-tasks.md`** — Task list, queue config, how to trigger manually, Flower monitoring

### Deliverable
A developer understands the data pipeline and can trigger or debug it.

---

## Milestone 5: AI & Nemotron Models

**Goal**: Document the NVIDIA Nemotron model integrations.

### Pages
- [ ] **`40.ai-models/1.overview.md`** — Three-model architecture table: LLM, Embedder, Reranker — what each does
- [ ] **`40.ai-models/2.nemotron-llm.md`** — Model access (OpenAI-compatible API), config options, two temperature modes
- [ ] **`40.ai-models/3.embedding-service.md`** — Service API, 4096-dim vectors, client config (retries, timeout)
- [ ] **`40.ai-models/4.rerank-service.md`** — Service API, how reranking differs from similarity, fallback behavior
- [ ] **`40.ai-models/5.prompts.md`** — Summary table of all prompts used and their purpose. Key examples where instructive

### Deliverable
A developer understands each AI model's role and how to configure them.

---

## Milestone 6: Semantic Search & RAG

**Goal**: Document the vector search and RAG chatbot systems.

### Pages
- [ ] **`50.search-and-rag/1.overview.md`** — Two retrieval modes: semantic search vs RAG chatbot. When to use each
- [ ] **`50.search-and-rag/2.vector-storage.md`** — sqlite-vector setup, embedding storage format, index building
- [ ] **`50.search-and-rag/3.semantic-search.md`** — End-to-end flow: query → embed → similarity → results
- [ ] **`50.search-and-rag/4.rag-chatbot.md`** — Chatbot workflow: embed → retrieve → rerank → generate. Source attribution
- [ ] **`50.search-and-rag/5.tuning.md`** — Practical tips: top_k, reranker thresholds, prompt adjustments

### Deliverable
A developer can understand and tune the search and RAG systems.

---

## Milestone 7: API Reference

**Goal**: Hand-written reference for all REST API endpoints. Link to Swagger UI for full schemas.

### Pages
- [ ] **`60.api/1.overview.md`** — Base URL, response conventions, pagination, error format. Links to `/docs` (Swagger) and `/redoc`
- [ ] **`60.api/2.posts.md`** — Post endpoints with example responses
- [ ] **`60.api/3.comments.md`** — Comment endpoints with example responses
- [ ] **`60.api/4.projects.md`** — Project endpoints, filter parameters table, example responses
- [ ] **`60.api/5.search-and-chat.md`** — Search and chatbot endpoints with example request/response
- [ ] **`60.api/6.admin.md`** — Admin endpoints with destructive operation warnings
- [ ] **`60.api/7.workflows.md`** — Workflow inspection and visualization endpoints

### Deliverable
Every endpoint documented with method, path, parameters, and example. Full schemas available via Swagger link.

---

## Milestone 8: Frontend Documentation

**Goal**: Document the Nuxt 4 frontend application.

### Pages
- [ ] **`70.frontend/1.overview.md`** — Stack summary, project structure, routing
- [ ] **`70.frontend/2.pages.md`** — Each page: purpose, key features, notable interactions
- [ ] **`70.frontend/3.components.md`** — Component organization, shadcn/ui patterns
- [ ] **`70.frontend/4.configuration.md`** — `nuxt.config.ts`, runtime config, environment variables
- [ ] **`70.frontend/5.styling.md`** — Tailwind setup, color mode, responsive approach

### Deliverable
A frontend developer can understand and extend the UI.

---

## Milestone 9: Development Guide

**Goal**: Everything a contributor needs to develop, test, and debug.

### Pages
- [ ] **`80.development/1.project-structure.md`** — Annotated directory tree
- [ ] **`80.development/2.dev-environment.md`** — IDE setup, virtualenv, Node setup, .env template
- [ ] **`80.development/3.testing.md`** — pytest setup, running tests, writing new tests
- [ ] **`80.development/4.debugging.md`** — Debug tools: Flower, Phoenix, Redis Insights, Jupyter Lab
- [ ] **`80.development/5.code-style.md`** — Black, ESLint, Makefile commands
- [ ] **`80.development/6.adding-features.md`** — Patterns: new endpoint, new workflow step, new frontend page

### Deliverable
A contributor has a complete development guide.

---

## Milestone 10: Operations & Deployment

**Goal**: Deployment, monitoring, and maintenance documentation.

### Pages
- [ ] **`90.operations/1.docker-deployment.md`** — `docker-compose.yml` walkthrough, environment variables, volumes
- [ ] **`90.operations/2.monitoring.md`** — Monitoring tools table, health endpoints, what to watch
- [ ] **`90.operations/3.database.md`** — SQLite location, backups, index rebuilding, reset operations
- [ ] **`90.operations/4.scaling.md`** — Worker scaling, throughput, rate limits, SQLite concurrency
- [ ] **`90.operations/5.troubleshooting.md`** — Common issues with symptoms → diagnosis → fix format

### Deliverable
An operator can deploy, monitor, and troubleshoot a waywo instance.

---

## Milestone 11: Polish & Production Readiness

**Goal**: Final pass for cross-linking, SEO, and deployment of the docs site itself.

### Tasks
- [ ] Cross-link all pages where concepts reference each other
- [ ] Configure GitHub integration (`github.url`, `github.branch`)
- [ ] Write SEO descriptions for every page
- [ ] Consistency review: tone, formatting, depth
- [ ] Add a FAQ page
- [ ] Verify code examples are accurate
- [ ] Deploy docs site (Vercel, Netlify, or GitHub Pages)
- [ ] Add docs URL to main project README

### Deliverable
A polished, deployed documentation site.

---

## Site Navigation Structure

```
Waywo Docs
├── Home (landing page)
├── Getting Started
│   ├── Introduction
│   ├── Prerequisites
│   ├── Quickstart (Docker)
│   ├── Manual Setup
│   └── First Run Guide
├── Architecture
│   ├── Overview
│   ├── Data Model
│   ├── Tech Stack
│   └── Service Map
├── Data Pipeline
│   ├── Overview
│   ├── Post Collection
│   ├── Comment Extraction
│   ├── Project Workflow
│   └── Celery Tasks
├── AI & Nemotron Models
│   ├── Overview
│   ├── Nemotron LLM
│   ├── Embedding Service
│   ├── Rerank Service
│   └── Prompts
├── Search & RAG
│   ├── Overview
│   ├── Vector Storage
│   ├── Semantic Search
│   ├── RAG Chatbot
│   └── Tuning
├── API Reference
│   ├── Overview
│   ├── Posts API
│   ├── Comments API
│   ├── Projects API
│   ├── Search & Chat API
│   ├── Admin API
│   └── Workflows API
├── Frontend
│   ├── Overview
│   ├── Pages
│   ├── Components
│   ├── Configuration
│   └── Styling
├── Development
│   ├── Project Structure
│   ├── Dev Environment
│   ├── Testing
│   ├── Debugging
│   ├── Code Style
│   └── Adding Features
└── Operations
    ├── Docker Deployment
    ├── Monitoring
    ├── Database
    ├── Scaling
    └── Troubleshooting
```

---

## Page Count Summary

| Section | Pages |
|---------|-------|
| Landing Page | 1 |
| Getting Started | 5 |
| Architecture | 4 |
| Data Pipeline | 5 |
| AI & Nemotron Models | 5 |
| Search & RAG | 5 |
| API Reference | 7 |
| Frontend | 5 |
| Development | 6 |
| Operations | 5 |
| **Total** | **48 pages** |

---

## Principles

1. **Breadth first** — Cover every section at a useful level; go deeper later as needed
2. **Keep it simple** — Scannable pages with headers, tables, and code blocks. No over-documenting
3. **Examples where helpful** — Real code from the codebase, included when they clarify, omitted when obvious
4. **Hand-written + auto-gen** — API docs are hand-written for readability; link to Swagger/ReDoc for full schemas
5. **Flexible structure** — Section numbering uses gaps (10, 20, 30...) so new sections slot in without renumbering
6. **Monorepo-native** — Docs live alongside code and should be updated with code changes
