# Waywo NEXT - Ambitious Feature Roadmap

> These features build on everything completed in PLAN.md and push the project into truly next-level territory. The focus: **agentic AI**, deep integration with **Nemotron models**, and creative ways to showcase and promote the incredible projects people are building.

---

## Feature 1: AI-Generated Landing Pages for Projects

**Goal**: For projects that have no website (or have a dead/broken URL), use an agentic code-generation pipeline to create a custom single-page landing site - fully designed, deployable, and beautiful.

### Why This Is Exciting
Many HN "What are you working on?" projects are ideas or early-stage work with no web presence. This feature literally builds them a website, showcasing what agentic AI can do with just a text description.

### Architecture
```
Project Data + Description
  | Nemotron Super (script the page content, structure, copy)
  v
Page Blueprint (JSON: sections, headlines, features, CTAs)
  | Nemotron Super (generate full HTML/Tailwind/Vue code)
  v
Single-Page Site (HTML + CSS + JS)
  | Flux Model (generate hero images, feature illustrations, OG images)
  v
Styled Landing Page with AI-Generated Visuals
  | Playwright (capture screenshot of generated page)
  v
Preview + Deploy (serve as static page at /showcase/{project_id})
```

### Key Components
- **Page Planner Agent**: Analyzes project description, hashtags, and any scraped content to determine page structure (hero, features, pricing, about, CTA)
- **Code Generator Agent**: Produces clean HTML + Tailwind CSS. Uses Nemotron Super 49B for higher-quality code generation
- **Image Generator**: Calls Flux model API to generate hero images, logos, and feature illustrations based on project context
- **Preview & Deploy**: Serve generated pages as static files at `/showcase/{project_id}`, capture screenshots for the project gallery

### Files to Create
| File | Purpose |
|------|---------|
| `src/agents/website_generator.py` | Multi-step agent orchestrating the full pipeline |
| `src/clients/flux.py` | Client for Flux image generation API |
| `src/routes/showcase.py` | Serve generated landing pages |
| `frontend/app/pages/projects/[id]/showcase.vue` | Preview and launch button on project detail |
| `media/showcase/{project_id}/` | Generated HTML, images, assets |

### Tasks
- [ ] Design page template system (3-4 layout variants based on project type)
- [ ] Build page planner agent (Nemotron Super for content strategy)
- [ ] Build code generator agent (Nemotron Super for HTML/Tailwind generation)
- [ ] Integrate Flux model for hero images and illustrations
- [ ] Add static file serving for generated pages
- [ ] Add "Generate Website" button on project detail page
- [ ] Capture and display screenshot of generated page
- [ ] Add `/showcase` gallery page showing all generated sites

---

## Feature 2: Autonomous Project Research Agent

**Goal**: An agentic system that goes far beyond scraping a URL - it autonomously researches a project across the web, synthesizing a comprehensive research report.

### Why This Is Exciting
This is a true agentic AI demo. The agent makes its own decisions about what to investigate, follows leads, and assembles a report no human would have the patience to compile manually.

### Agent Capabilities
1. **GitHub Deep-Dive**: If a GitHub URL exists, fetch repo stats (stars, forks, contributors, language breakdown, recent activity, open issues)
2. **Social Signal Scan**: Search for the project on Twitter/X, Reddit, Product Hunt, and other platforms for mentions and sentiment
3. **Competitor Analysis**: Use semantic search over the existing project corpus to find similar projects, then compare features
4. **Tech Stack Detection**: Analyze scraped content, GitHub repo, and screenshots to identify the full technology stack
5. **Trend Positioning**: Where does this project sit in the broader landscape? Is it riding a trend or creating one?

### Architecture
```
Trigger: "Deep Research" button on project detail
  |
  v
Research Planner (Nemotron Super)
  - Decides which research tasks to run based on available data
  - Generates a research plan (list of tool calls)
  |
  v
Parallel Research Agents (Celery tasks)
  ├── GitHub Agent → repo stats, activity, contributors
  ├── Web Mentions Agent → Firecrawl search for project name across sites
  ├── Competitor Agent → semantic search + LLM comparison
  ├── Tech Stack Agent → VL analysis of screenshots + code analysis
  └── Trend Agent → analyze tags, descriptions across time periods
  |
  v
Synthesis Agent (Nemotron Super)
  - Combines all research into a structured report
  - Generates key insights and recommendations
  |
  v
Research Report (stored in DB, rendered in UI)
```

### Research Report Structure
```json
{
  "executive_summary": "2-3 sentence overview",
  "github_analysis": { "stars": 142, "trend": "growing", "last_commit": "2 days ago", ... },
  "web_presence": { "mentions": 7, "sentiment": "positive", "platforms": [...] },
  "competitors": [{ "project_id": 45, "similarity": 0.87, "differentiators": [...] }],
  "tech_stack": { "frontend": ["React", "Tailwind"], "backend": ["Python", "FastAPI"], ... },
  "trend_analysis": { "category_growth": "+23%", "positioning": "early mover" },
  "key_insights": ["...", "...", "..."],
  "overall_assessment": "High potential project in a growing space..."
}
```

### Tasks
- [ ] Build research planner agent (decides what to investigate)
- [ ] Build GitHub research sub-agent (repo stats via GitHub API)
- [ ] Build web mentions sub-agent (Firecrawl + search)
- [ ] Build competitor analysis sub-agent (semantic search + LLM comparison)
- [ ] Build tech stack detection sub-agent (VL model + code analysis)
- [ ] Build synthesis agent (combines all research into report)
- [ ] Add research report DB model and storage
- [ ] Build research report UI on project detail page
- [ ] Add "Deep Research" button to trigger the pipeline
- [ ] Add Celery task for async research execution

---

## Feature 3: Promotional Video Generator

**Goal**: Generate a polished promotional video showcasing the top projects, with AI-narrated voiceover, animated transitions, and per-project highlight segments.

### Why This Is Exciting
This directly supports the goal of creating a video to promote the project. Instead of manually editing a video, the system assembles one programmatically from project data, screenshots, and AI-generated narration.

### Video Assembly Pipeline
```
1. Script Generation (Nemotron Super)
   - Intro: "Welcome to Waywo - showcasing the best projects from HN..."
   - Per-project segments: title, description, what makes it interesting
   - Transitions between projects
   - Outro with call to action

2. Visual Asset Collection
   - Project screenshots (already captured)
   - AI-generated title cards (Flux model)
   - Animated transitions (template-based)
   - Stats overlays (scores, tags)

3. Audio Generation (TTS / Nemotron Speech)
   - Narrate the full script
   - Background music track (royalty-free, configurable)
   - Per-segment audio clips

4. Video Assembly (FFmpeg)
   - Combine screenshots with Ken Burns effect (pan/zoom)
   - Overlay title cards and stats
   - Sync narration audio
   - Add transitions between segments
   - Output as MP4

5. Thumbnail Generation (Flux)
   - YouTube-style thumbnail with top project highlights
```

### Video Segment Structure (per project)
```
[0.0s - 0.5s]  Transition animation
[0.5s - 2.0s]  Title card with project name + tagline
[2.0s - 8.0s]  Screenshot with slow zoom, narration overlay
[8.0s - 10.0s] Stats overlay (scores, tags, URL)
[10.0s - 10.5s] Transition to next project
```

### Customization Options
- **Curated vs Auto**: Hand-pick projects or auto-select top N by idea score
- **Theme**: Light/dark, color scheme
- **Duration**: Short (60s highlights) / Medium (3-5 min) / Full (10+ min)
- **Format**: YouTube (16:9), Instagram Reel (9:16), Twitter/X (1:1)
- **Music**: Choose from templates or provide custom track
- **Narration Voice**: Multiple TTS voices available

### Files to Create
| File | Purpose |
|------|---------|
| `src/agents/video_generator.py` | Main video generation orchestrator |
| `src/clients/tts.py` | Text-to-speech client for narration |
| `src/video/script_writer.py` | LLM-powered script generation |
| `src/video/asset_builder.py` | Visual asset preparation (title cards, overlays) |
| `src/video/assembler.py` | FFmpeg-based video assembly |
| `frontend/app/pages/video.vue` | Video generation UI and preview |
| `media/videos/` | Generated video storage |

### Tasks
- [ ] Build script generation agent (Nemotron Super writes compelling narration)
- [ ] Build title card generator (Flux model for styled project cards)
- [ ] Integrate TTS for narration audio (Nemotron Speech models)
- [ ] Build FFmpeg video assembler with Ken Burns effect on screenshots
- [ ] Create video generation Celery task (long-running, async)
- [ ] Build video configuration UI (select projects, theme, duration, format)
- [ ] Add progress tracking for video generation
- [ ] Generate YouTube-style thumbnail
- [ ] Add video preview and download page

---

## Feature 4: Multi-Agent Project Review Board

**Goal**: A panel of specialized AI agents that each review a project from a different expert perspective, then debate and synthesize a comprehensive evaluation.

### Why This Is Exciting
This showcases multi-agent collaboration - agents with different "personalities" and expertise areas evaluate the same project, disagree, and reach consensus. It's like having a virtual advisory board for every single project.

### The Review Board Agents

| Agent | Persona | Evaluates |
|-------|---------|-----------|
| **Market Analyst** | Investor mindset, market-aware | Market size, competition, timing, monetization potential |
| **Technical Architect** | Senior engineer, pragmatic | Tech stack choices, scalability, complexity vs. value |
| **UX Critic** | Design-focused, user-centric | Landing page quality, user experience, clarity of value prop |
| **Innovation Scout** | Trend-aware, novelty-seeking | Originality, creative use of technology, wow factor |
| **Devil's Advocate** | Skeptical, finds weaknesses | What could go wrong, missing pieces, red flags |

### Review Process
```
Phase 1: Independent Review (Parallel)
  Each agent reviews the project independently:
  - Reads project data, description, scraped content
  - VL agent analyzes the screenshot
  - Produces a structured review with score and reasoning

Phase 2: Cross-Review (Sequential)
  Each agent reads the other agents' reviews and:
  - Agrees or disagrees with specific points
  - Raises concerns the others missed
  - Adjusts their assessment based on new perspectives

Phase 3: Synthesis (Nemotron Super)
  A moderator agent:
  - Identifies points of consensus and disagreement
  - Produces a final unified assessment
  - Highlights the most interesting/controversial findings
  - Generates an overall "Review Board Score" (1-100)
```

### Output Format
```json
{
  "review_board_score": 78,
  "consensus": "A technically solid project with strong market timing...",
  "individual_reviews": {
    "market_analyst": { "score": 8, "summary": "...", "key_points": [...] },
    "tech_architect": { "score": 7, "summary": "...", "key_points": [...] },
    "ux_critic": { "score": 6, "summary": "...", "key_points": [...] },
    "innovation_scout": { "score": 9, "summary": "...", "key_points": [...] },
    "devils_advocate": { "score": 5, "concerns": [...] }
  },
  "debate_highlights": [
    { "topic": "Scalability", "for": "tech_architect", "against": "devils_advocate", "resolution": "..." }
  ],
  "recommendations": ["...", "...", "..."]
}
```

### Tasks
- [ ] Design agent personas with system prompts for each reviewer
- [ ] Build independent review step (parallel Celery tasks)
- [ ] Build cross-review step (agents read and respond to each other)
- [ ] Build synthesis/moderator agent
- [ ] Integrate VL model for screenshot-based UX review
- [ ] Store review results in DB
- [ ] Build review board UI on project detail page (tabbed agent views)
- [ ] Add "Request Review" button on project detail
- [ ] Display debate highlights and consensus

---

## Feature 5: Interactive Project Knowledge Graph

**Goal**: Build a dynamic, interactive visualization that maps relationships between all projects - shared technologies, similar goals, common authors, and evolution over time.

### Why This Is Exciting
This transforms the flat list of projects into an explorable universe. Users can visually discover clusters, spot trends, and find connections they'd never find through search alone.

### Graph Structure

**Nodes**:
- Projects (sized by idea score, colored by category)
- Technologies (extracted from tags and tech stack detection)
- Authors (HN usernames)
- Time periods (monthly HN threads)

**Edges**:
- `project --uses--> technology` (extracted from tags, descriptions, VL analysis)
- `project --similar_to--> project` (embedding similarity > threshold)
- `project --by--> author`
- `project --from--> time_period`
- `technology --related_to--> technology` (co-occurrence)

### Visualization Features
- **Force-directed layout**: Projects cluster naturally by similarity
- **Zoom levels**: Overview (clusters) -> Category (tech groupings) -> Detail (individual projects)
- **Time slider**: Animate the graph over months to see how the ecosystem evolves
- **Click to explore**: Click any node to see details, neighbors, and paths
- **Cluster detection**: Automatically identify and label project clusters ("AI Tools", "Dev Infrastructure", "Consumer Apps")
- **Search integration**: Highlight projects matching a semantic search query

### Technical Approach
- **Backend**: Generate graph data from embeddings (similarity matrix), tags (co-occurrence), and metadata
- **Frontend**: D3.js or vis-network for interactive graph rendering
- **LLM Integration**: Nemotron Super generates cluster labels and descriptions
- **Embedding Clustering**: Run k-means or HDBSCAN on project embeddings to find natural groupings

### Files to Create
| File | Purpose |
|------|---------|
| `src/graph/builder.py` | Constructs graph from project data and embeddings |
| `src/graph/clustering.py` | Cluster detection and labeling |
| `src/routes/graph.py` | Graph data API endpoints |
| `frontend/app/pages/explore.vue` | Interactive graph visualization page |
| `frontend/app/components/waywo/ProjectGraph.vue` | D3.js graph component |

### API Endpoints
```
GET /api/graph/data
    Query params: min_similarity=0.7, min_score=5
    Response: { nodes: [...], edges: [...], clusters: [...] }

GET /api/graph/clusters
    Response: { clusters: [{ id, label, description, project_count, top_tags }] }

GET /api/graph/project/{id}/neighborhood
    Response: { center: {...}, neighbors: [...], paths: [...] }
```

### Tasks
- [ ] Build graph data structure from embeddings and metadata
- [ ] Implement similarity threshold for edge creation
- [ ] Run clustering algorithm on embeddings
- [ ] Generate cluster labels with Nemotron Super
- [ ] Build graph data API endpoints
- [ ] Implement D3.js force-directed graph visualization
- [ ] Add time slider for temporal exploration
- [ ] Add zoom levels and click-to-explore
- [ ] Add search highlight integration
- [ ] Create `/explore` page with the interactive graph

---

## Feature 6: Automated Weekly Digest & Newsletter

**Goal**: A fully automated content pipeline that curates the most interesting projects each week, writes editorial-quality analysis, and publishes it as a newsletter and web page.

### Why This Is Exciting
This turns raw project data into polished, human-readable content automatically. The LLM doesn't just summarize - it writes like a tech journalist, finding narrative threads and insights across projects.

### Content Pipeline
```
1. Project Curation (Automated)
   - Select top projects by idea score from the past week/month
   - Identify trending tags/categories
   - Find surprising or underappreciated projects (high quality, low visibility)

2. Editorial Analysis (Nemotron Super)
   - Write an opening editorial identifying the week's themes
   - Per-project write-ups (not just descriptions - analysis, context, why it matters)
   - "Trend Watch" section analyzing emerging patterns
   - "Hidden Gem" spotlight for underappreciated projects
   - Closing thoughts and what to watch for next week

3. Visual Design
   - Generate header image (Flux model)
   - Include project screenshots
   - Create infographic-style stats (trending tags, score distributions)

4. Publishing
   - Render as styled web page at /digest/{date}
   - Generate email-friendly HTML version
   - Create RSS feed for subscribers
   - Archive of past digests
```

### Digest Structure
```markdown
# Waywo Weekly - February 7, 2026

## This Week's Theme: The Rise of Local AI Tools
[Editorial paragraph about the trend...]

## Top Projects

### 1. ProjectName - One-line hook
[2-3 paragraph analysis: what it does, why it's interesting, how it fits the landscape]
Score: 9/10 | Tags: #ai #local-first | [Visit Project →]

### 2. ...

## Trend Watch
- **Local-first AI** appeared in 34% of projects this month, up from 12% last month
- **Rust** continues its climb as the #2 backend language after Python
- New category emerging: "AI-powered developer tools"

## Hidden Gem: ProjectName
[Spotlight on an underappreciated project with high quality but low visibility]

## By the Numbers
- 47 new projects processed this week
- Average idea score: 6.8 (up from 6.2 last month)
- Most popular tag: #saas (18 projects)
```

### Tasks
- [ ] Build project curation logic (scoring, trend detection, hidden gem selection)
- [ ] Create editorial writing agent (Nemotron Super with journalist persona)
- [ ] Create trend analysis module (tag frequency over time, category growth)
- [ ] Generate header images with Flux model
- [ ] Build digest rendering as styled HTML page
- [ ] Create email-friendly HTML template
- [ ] Build RSS feed generator
- [ ] Add Celery beat scheduled task for weekly generation
- [ ] Create `/digest` archive page and individual digest pages
- [ ] Add subscriber notification system (optional: email integration)

---

## Feature 7: Project Evolution Tracker

**Goal**: Continuously monitor projects over time, detecting changes, growth, and milestones. Build a timeline of each project's journey from HN comment to whatever it becomes.

### Why This Is Exciting
Most project showcases are a snapshot in time. This feature tells the *story* of a project - when it launched, when it got its first GitHub stars, when the website changed, when it was mentioned on other platforms. It's a living history.

### What Gets Tracked
- **URL Health**: Is the site still up? Has the content changed significantly?
- **GitHub Activity**: Star count over time, commit frequency, new releases
- **Visual Changes**: Periodic screenshot comparison (detect major redesigns)
- **Web Mentions**: New articles, social media posts, Product Hunt launches
- **Author Updates**: If the author posts in a later "What are you working on?" thread

### Architecture
```
Celery Beat (Weekly/Monthly)
  |
  v
For each tracked project:
  ├── URL Health Check → Store status (up/down/changed)
  ├── Screenshot Comparison → Capture new screenshot, compare with VL model
  ├── GitHub Stats Fetch → Stars, forks, commits (if GitHub URL exists)
  ├── Web Mention Scan → Firecrawl search for project name
  └── Author Comment Scan → Check if author posted updates in newer threads
  |
  v
Change Detection Agent (Nemotron Super)
  - Analyze what changed since last check
  - Classify change: "major redesign", "steady growth", "abandoned", "launched v2"
  - Generate timeline entry
  |
  v
Timeline Entry → Stored in DB, displayed in UI
```

### Timeline Entry Types
| Type | Icon | Description |
|------|------|-------------|
| `first_seen` | Star | Project first extracted from HN comment |
| `screenshot_change` | Camera | Significant visual change detected |
| `github_milestone` | Trophy | Reached stars milestone (100, 500, 1K, 5K) |
| `new_release` | Package | New GitHub release detected |
| `web_mention` | Globe | Mentioned on another platform |
| `author_update` | Person | Author posted an update in a later HN thread |
| `site_down` | Warning | Project URL is no longer accessible |
| `major_update` | Rocket | Major redesign or feature launch |

### Tasks
- [ ] Create timeline data model and DB schema
- [ ] Build URL health checker (periodic ping + content hash)
- [ ] Build screenshot comparator (VL model diff analysis)
- [ ] Build GitHub stats tracker (API integration)
- [ ] Build web mention scanner (Firecrawl-based search)
- [ ] Build change detection agent (classifies and narrates changes)
- [ ] Create Celery beat task for periodic monitoring
- [ ] Build timeline UI component on project detail page
- [ ] Add project status badges (active, growing, dormant, abandoned)
- [ ] Create `/trending` page showing projects with most recent activity

---

## Feature 8: AI-Powered Project Pitch Deck Generator

**Goal**: Automatically generate a presentation-style pitch deck for any project, suitable for sharing, embedding, or even presenting.

### Why This Is Exciting
Imagine clicking a button on any project and getting a polished 8-slide pitch deck generated in seconds. It's a showcase of how well the AI understands each project and can repackage it for different audiences.

### Slide Structure
```
Slide 1: Title + Hero Image
  - Project name, tagline, AI-generated hero visual

Slide 2: The Problem
  - What problem does this project solve?
  - Generated from description + web content analysis

Slide 3: The Solution
  - How the project addresses the problem
  - Key features and approach

Slide 4: How It Works
  - Technical architecture or user flow
  - Simplified diagram generated by the LLM

Slide 5: Screenshot / Demo
  - Project screenshot with annotations
  - Key UI elements highlighted

Slide 6: Technology Stack
  - Detected technologies (from VL analysis + description)
  - Why these choices matter

Slide 7: Market & Competition
  - Similar projects (from semantic search)
  - Key differentiators

Slide 8: Key Metrics & Links
  - Idea score, complexity score
  - Project URLs, HN thread link
  - QR code for quick access
```

### Output Formats
- **Web slides**: HTML/CSS reveal.js presentation at `/pitch/{project_id}`
- **PDF export**: Downloadable pitch deck
- **Image export**: Individual slide images for social sharing

### Generation Pipeline
```
Project Data → Nemotron Super (content strategy per slide)
  → Flux (hero image, slide backgrounds)
  → Template Engine (reveal.js or HTML)
  → Playwright (capture slide images for PDF/sharing)
```

### Tasks
- [ ] Design slide templates (3-4 visual themes)
- [ ] Build content generation agent (Nemotron Super writes slide content)
- [ ] Generate hero images and backgrounds with Flux
- [ ] Build reveal.js presentation renderer
- [ ] Add PDF export via Playwright
- [ ] Add individual slide image export
- [ ] Create "Generate Pitch Deck" button on project detail page
- [ ] Build pitch deck gallery page
- [ ] Add social sharing for individual slides

---

## Feature 9: Conversational Project Discovery Agent

**Goal**: A sophisticated conversational AI that goes beyond simple Q&A - it actively helps users discover projects through guided exploration, comparisons, and personalized recommendations.

### Why This Is Exciting
The current chatbot answers questions about projects. This feature turns it into a proactive discovery assistant that understands what you're looking for, asks clarifying questions, remembers your preferences, and guides you through the project universe.

### Conversation Capabilities

**1. Guided Discovery**
```
User: "I want to build something with AI"
Agent: "I found 47 AI-related projects. To help narrow it down:
        - Are you looking for developer tools, end-user products, or infrastructure?
        - Any particular AI domain? (NLP, vision, agents, etc.)
        - Solo project or looking for something with a team?"
User: "Developer tools, specifically for code generation"
Agent: "Great! Here are the top 5 code generation tools, ranked by relevance:
        1. [Project A] - VS Code extension for... (Score: 9/10)
        2. ..."
```

**2. Comparison Mode**
```
User: "Compare projects 42 and 67"
Agent: "Here's a detailed comparison:
        | Aspect | Project 42 | Project 67 |
        | Focus  | ...        | ...        |
        | Stack  | ...        | ...        |
        Key differences: Project 42 focuses on... while Project 67..."
```

**3. Inspiration Mode**
```
User: "Show me something surprising"
Agent: "Here's an unexpected find - [Project X] combines blockchain with
        bird watching. Despite sounding niche, it scored 8/10 for innovation
        and has a beautifully designed app. The creator also built..."
```

**4. Trend Exploration**
```
User: "What's trending this month?"
Agent: "Three interesting trends I'm seeing:
        1. Surge in local-first AI tools (12 projects, up 200%)
        2. Rust is becoming the go-to for CLI tools
        3. Several projects combining LLMs with home automation
        Want me to dive deeper into any of these?"
```

### Agent Architecture
```
User Message
  |
  v
Intent Classifier (Nemotron)
  ├── Discovery → Guided exploration flow
  ├── Comparison → Side-by-side analysis
  ├── Inspiration → Surprise/random mode
  ├── Trend → Temporal analysis
  ├── Specific → Direct RAG query
  └── Follow-up → Continue previous thread
  |
  v
Tool Selection
  ├── semantic_search(query, filters)
  ├── get_similar_projects(id)
  ├── get_trend_data(category, timeframe)
  ├── compare_projects(id1, id2)
  └── get_random_high_quality(min_score)
  |
  v
Response Generation (Nemotron Super)
  - Rich markdown with project cards
  - Follow-up suggestions
  - Conversation memory
```

### Conversation Memory
- Track user preferences across the session (e.g., "interested in Rust projects")
- Remember what projects have already been shown (avoid repetition)
- Build a preference profile to improve recommendations

### Tasks
- [ ] Build intent classification system
- [ ] Implement guided discovery flow with clarifying questions
- [ ] Build comparison mode with structured side-by-side output
- [ ] Build inspiration/surprise mode
- [ ] Build trend exploration with temporal analysis
- [ ] Add conversation memory and preference tracking
- [ ] Create tool-use framework (agent selects and calls backend tools)
- [ ] Upgrade chat UI with rich project cards inline
- [ ] Add conversation starters and suggested questions
- [ ] Add "Share this conversation" feature

---

## Feature 10: Real-Time HN Thread Live Processing & Dashboard

**Goal**: When a new "What are you working on?" thread goes live on HN, automatically detect it and process comments in real-time with a live dashboard showing projects appearing as they're extracted.

### Why This Is Exciting
Instead of batch processing after the fact, this creates a live event experience. Users can watch the dashboard as new projects stream in, get real-time stats, and see the thread evolve. It turns a monthly HN post into a live event.

### Live Processing Pipeline
```
HN API Polling (every 60 seconds)
  |
  v
New Comment Detected
  |
  v
Processing Queue (Celery with priority)
  |
  v
LlamaIndex Workflow (extract, validate, enrich)
  |
  v
WebSocket Broadcast → Connected Clients
  |
  v
Live Dashboard Updates
```

### Live Dashboard Features

**Real-Time Feed**
- Projects appear as they're extracted (animated entry)
- Live processing indicator ("Processing comment #847...")
- "New!" badges on recently extracted projects

**Live Stats Panel**
- Total comments processed / remaining
- Projects extracted (valid vs filtered)
- Average scores updating in real-time
- Tag cloud growing as new tags appear
- Processing speed (projects/minute)

**Live Leaderboard**
- Top projects by idea score (updates as new ones come in)
- Most common tags this thread
- Author spotlight (prolific commenters)

**Activity Timeline**
- Scrolling timeline of processing events
- "Comment #847 → 2 projects extracted → AI Dashboard, CLI Tool"
- Live workflow status indicators

### Architecture
```
Backend:
  - HN API poller (Celery Beat, every 60s during active thread)
  - Comment deduplication and ordering
  - Priority queue for new comments
  - WebSocket server (FastAPI WebSocket endpoint)
  - Broadcast channel for live events

Frontend:
  - WebSocket connection to backend
  - Animated project card entry
  - Real-time chart updates (Chart.js / D3)
  - Sound notification for high-scoring projects (optional)
  - Auto-scroll feed with pause on hover
```

### Event Types (WebSocket)
```json
{ "type": "new_comment", "comment_id": 847, "author": "..." }
{ "type": "processing_start", "comment_id": 847 }
{ "type": "project_extracted", "project": { "title": "...", "score": 8, ... } }
{ "type": "project_invalid", "reason": "Not a project (personal reflection)" }
{ "type": "stats_update", "total_projects": 142, "avg_score": 6.8, ... }
{ "type": "thread_complete", "summary": { ... } }
```

### Tasks
- [ ] Build HN API poller with new comment detection
- [ ] Add WebSocket endpoint for live event streaming
- [ ] Create priority processing queue for real-time extraction
- [ ] Build live dashboard page with WebSocket connection
- [ ] Add animated project card entry (CSS transitions)
- [ ] Build real-time stats panel with live updating charts
- [ ] Build live leaderboard component
- [ ] Build activity timeline feed
- [ ] Add thread detection (auto-detect new "WAYWO" posts)
- [ ] Add notification system for high-scoring projects
- [ ] Build thread summary generation when processing completes

---

## Implementation Priority

| Priority | Feature | Effort | Impact | Dependencies |
|----------|---------|--------|--------|--------------|
| 1 | **F3: Promotional Video Generator** | High | Very High | TTS service, FFmpeg |
| 2 | **F6: Automated Weekly Digest** | Medium | Very High | None (uses existing data) |
| 3 | **F10: Live Processing Dashboard** | Medium | High | WebSocket support |
| 4 | **F9: Conversational Discovery Agent** | Medium | High | Enhanced chatbot workflow |
| 5 | **F1: AI-Generated Landing Pages** | High | Very High | Flux model API |
| 6 | **F5: Interactive Knowledge Graph** | Medium | High | D3.js, clustering |
| 7 | **F4: Multi-Agent Review Board** | Medium | High | VL model for UX review |
| 8 | **F2: Autonomous Research Agent** | High | High | GitHub API, Firecrawl |
| 9 | **F7: Project Evolution Tracker** | Medium | Medium | Celery Beat, VL model |
| 10 | **F8: Pitch Deck Generator** | Medium | Medium | Flux model, reveal.js |

### Rationale
- **Video Generator first**: Directly supports the immediate goal of creating a promo video
- **Weekly Digest next**: High-impact, builds on existing data, creates shareable content
- **Live Dashboard**: Creates a compelling demo and real-time experience
- **Conversational Agent**: Upgrades the existing chatbot into something truly impressive
- **Landing Pages**: The most ambitious agentic feature - a real showstopper demo

---

## Model Requirements Summary

| Model | Features Using It |
|-------|-------------------|
| **Nemotron Super 49B** | F1 (code gen), F2 (research synthesis), F3 (scriptwriting), F4 (reviews), F5 (cluster labels), F6 (editorial), F7 (change analysis), F8 (slide content), F9 (conversation) |
| **Nemotron Nano VL** | F2 (tech stack detection), F4 (UX review), F7 (screenshot comparison) |
| **Nemotron Speech** | F3 (video narration) |
| **Nemotron Embed** | F5 (clustering), F9 (search), F10 (real-time embeddings) |
| **Nemotron Rerank** | F9 (discovery relevance) |
| **Flux** | F1 (hero images), F3 (title cards), F6 (header images), F8 (slide visuals) |

---

## Shared Infrastructure Needs

Before implementing features, these foundation pieces support multiple features:

1. **Flux Model Client** (`src/clients/flux.py`) - Used by F1, F3, F6, F8
2. **WebSocket Support** (`src/routes/websocket.py`) - Used by F10, potentially F9
3. **Agent Framework** (`src/agents/base.py`) - Used by F1, F2, F4, F7
4. **GitHub API Client** (`src/clients/github.py`) - Used by F2, F7
5. **FFmpeg Integration** (`src/video/`) - Used by F3
6. **Scheduled Monitoring Tasks** - Used by F7, F10
