---
seo:
  title: Waywo Docs
  description: Documentation for waywo — an intelligent searchable index of "What are you working on?" projects from Hacker News.
---

::u-page-hero
#title
Waywo Documentation

#description
An intelligent searchable index of "What are you working on?" projects from Hacker News.

Waywo scrapes monthly HN threads, uses AI to extract and analyze projects, and provides semantic search and a RAG chatbot to explore them.

#links
  :::u-button
  ---
  color: neutral
  size: xl
  to: /getting-started/introduction
  trailing-icon: i-lucide-arrow-right
  ---
  Get Started
  :::

  :::u-button
  ---
  color: neutral
  icon: simple-icons-github
  size: xl
  to: https://github.com/your-username/waywo
  variant: outline
  ---
  GitHub
  :::
::

::u-page-section
#title
What's inside

#features
  :::u-page-feature
  ---
  icon: i-lucide-database
  to: /pipeline/overview
  ---
  #title
  [Data Pipeline]{.text-primary}

  #description
  Automated collection from Hacker News, LLM-powered project extraction, validation, scoring, and embedding generation.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-brain
  to: /ai-models/overview
  ---
  #title
  [NVIDIA Nemotron Models]{.text-primary}

  #description
  Three-model AI stack: Nemotron-3-Nano-30B for reasoning, llama-embed-nemotron-8b for embeddings, and llama-nemotron-rerank-1b for reranking.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-search
  to: /search-and-rag/overview
  ---
  #title
  [Semantic Search & RAG]{.text-primary}

  #description
  Vector similarity search over 4096-dimensional embeddings, plus a RAG chatbot with reranking for conversational project discovery.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-layout-dashboard
  to: /frontend/overview
  ---
  #title
  [Nuxt 4 Frontend]{.text-primary}

  #description
  Modern SPA with 11 pages built on Nuxt 4, shadcn/ui, and Tailwind CSS. Browse, filter, search, and chat with your project data.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-server
  to: /api/overview
  ---
  #title
  [REST API]{.text-primary}

  #description
  45+ endpoints covering posts, comments, projects, semantic search, chatbot, admin operations, and workflow inspection.
  :::

  :::u-page-feature
  ---
  icon: i-lucide-container
  to: /operations/docker-deployment
  ---
  #title
  [Docker Deployment]{.text-primary}

  #description
  Full Docker Compose stack with backend, Celery workers, Redis, Flower monitoring, Phoenix tracing, and Jupyter Lab.
  :::
::
