# Word Cloud Feature Plan

A tag/word cloud visualization page for waywo projects using [VueWordCloud](https://github.com/SeregPie/VueWordCloud).

---

## Milestone 1: Foundation — Basic Word Cloud with Live Data

**Goal:** Install VueWordCloud, create a new API endpoint that returns tag frequencies, build a minimal `/word-cloud` page that renders a working word cloud from real project hashtags.

### Backend

- **New DB function `get_hashtag_counts()`** in `src/db/projects.py`
  - Query all `waywo_projects.hashtags` JSON arrays
  - Count occurrences of each tag across all valid projects
  - Return `list[dict]` with `{"tag": str, "count": int}`, sorted by count descending
  - Optional filters: `source` (hn / nemo_data_designer), `min_count` (exclude rare tags)

- **New API endpoint `GET /api/waywo-projects/hashtag-counts`** in `src/routes/projects.py`
  - Returns `{ "tags": [{"tag": "ai", "count": 142}, ...], "total_unique": N, "total_usage": N }`
  - Query params: `source`, `min_count`, `limit` (default 200, cap the cloud size)

### Frontend

- **Install VueWordCloud**: `npm install vuewordcloud` in `frontend/`
- **Register as Nuxt plugin** (client-only, since it uses canvas/workers):
  - Create `frontend/app/plugins/vue-word-cloud.client.ts`
  - Register `VueWordCloud` component globally
- **New page `frontend/app/pages/word-cloud.vue`**:
  - Fetch tag data from `/api/waywo-projects/hashtag-counts`
  - Transform `[{tag, count}]` into VueWordCloud's `words` format: `[[tag, count], ...]`
  - Render full-viewport word cloud with sensible defaults
  - Loading state while data fetches
  - Basic color function: weight-based coloring (high-count = bold color, low-count = muted)
- **Add "Word Cloud" link** to navigation in `frontend/app/layouts/default.vue` (desktop + mobile)

### Acceptance Criteria
- [ ] Word cloud renders with real hashtag data from the database
- [ ] Tags are sized proportionally to their frequency
- [ ] Page loads without errors, cloud is responsive to container size
- [ ] Navigation link works

---

## Milestone 2: Settings Panel — Control Colors, Fonts, and Layout

**Goal:** Add a slide-out Sheet panel (right side) with controls to customize the word cloud appearance in real-time. Use the existing shadcn-vue Sheet component.

### Controls Panel (Sheet)

- **Toggle button** in the page header (gear/settings icon) to open/close the Sheet
- **Color scheme picker** — choose from preset palettes:
  - "Vibrant" (rainbow/multi-hue)
  - "Cool" (blues/greens/purples)
  - "Warm" (reds/oranges/yellows)
  - "Monochrome" (shades of a single hue, user picks the base color)
  - "Theme" (uses CSS variables from the current light/dark theme)
- **Font family** — dropdown to pick from 4-5 web-safe or Google Fonts options
  - e.g. Inter, Roboto, Playfair Display, Fira Code, system default
- **Font weight** — slider or select: normal / bold / black
- **Spacing** — slider (0 to 1, maps to VueWordCloud `spacing` prop)
- **Rotation** — preset options:
  - "None" (all horizontal)
  - "Mixed" (random between -15deg and +15deg)
  - "Right angles" (0 or 90deg)
  - "Full random" (-90 to 90deg)
- **Font size ratio** — slider (0 to 5, controls min/max size spread)
- **Max words** — slider (25 to 500) to control density

### Implementation Notes

- Use `Sheet` + `SheetContent` from `~/app/components/ui/sheet/` (side="right")
- All controls bind to reactive refs, word cloud re-renders reactively
- Persist settings to `localStorage` so they survive page refreshes
- Show a "Reset to defaults" button at the bottom of the panel

### Acceptance Criteria
- [ ] Sheet opens/closes smoothly from right side
- [ ] Each control updates the word cloud in real time
- [ ] Settings persist across page refreshes via localStorage
- [ ] Reset button restores all defaults

---

## Milestone 3: Animations and Polish

**Goal:** Add smooth animations, visual polish, and delightful touches.

### Animations

- **Enter animation** — words fade/scale in when cloud renders
  - Use VueWordCloud's `enter-animation` prop with CSS transitions
- **Animation duration** — slider in settings panel (200ms to 2000ms)
- **Animation overlap** — slider (0 = sequential, 1 = simultaneous)
- **Animation easing** — dropdown: ease, ease-in-out, linear, spring-like

### Visual Polish

- **Dark/light mode** — color palettes automatically adapt to current theme
- **Responsive sizing** — cloud fills available viewport height (minus nav/header)
- **Empty state** — friendly message when no tags match current filters
- **Tag count badge** — show total unique tags and total tag usages in the page header
- **"Regenerate" button** — re-randomize the layout (useful since VueWordCloud placement has randomness)

### Acceptance Criteria
- [ ] Smooth entry animations on initial render and when settings change
- [ ] Animation controls in settings panel work correctly
- [ ] Cloud looks good in both light and dark mode
- [ ] Responsive: looks good on desktop and tablets

---

## Technical Notes

### VueWordCloud Props We'll Use

| Prop | Our Usage |
|------|-----------|
| `words` | `[[tag, count], ...]` from API |
| `color` | Function based on selected palette + weight |
| `font-family` | From settings panel |
| `font-weight` | From settings panel |
| `font-size-ratio` | From settings panel slider |
| `spacing` | From settings panel slider |
| `rotation` | Function based on rotation preset |
| `rotation-unit` | `'deg'` |
| `animation-duration` | From settings panel |
| `animation-easing` | From settings panel |
| `animation-overlap` | From settings panel |
| `enter-animation` | CSS fade+scale effect |

### File Changes Summary

| File | Change |
|------|--------|
| `frontend/package.json` | Add `vuewordcloud` dependency |
| `frontend/app/plugins/vue-word-cloud.client.ts` | **New** — register component (client-only) |
| `frontend/app/pages/word-cloud.vue` | **New** — main page |
| `frontend/app/layouts/default.vue` | Add nav link |
| `src/db/projects.py` | Add `get_hashtag_counts()` |
| `src/db/client.py` | Export new DB functions |
| `src/routes/projects.py` | Add `/hashtag-counts` endpoint |

### API Design

```
GET /api/waywo-projects/hashtag-counts
  ?source=hn|nemo_data_designer    # filter by project source
  &min_count=3                      # exclude rare tags
  &limit=200                        # max tags to return
Response:
{
  "tags": [
    {"tag": "ai", "count": 142},
    {"tag": "python", "count": 98},
    ...
  ],
  "total_unique": 350,
  "total_usage": 4200
}
```

---

## Future Work

These milestones are deferred for later implementation.

### Filtering and Interactivity

- **Minimum count slider** — hide tags below a threshold (e.g. show only tags used 3+ times)
- **Source filter** — toggle between "All", "Hacker News only", "AI-Generated only"
  - Calls API with `source` param, re-fetches tag counts
- **Exclude tags** — multi-select input to manually remove specific tags from the cloud
  - Useful for removing overly generic tags like "software", "web", "app"
- **Click on a tag** → navigate to `/projects?tags=<clicked-tag>` to see matching projects
- **Hover tooltip** — show tag name and exact count on hover (using VueWordCloud's slot template)
- **Progress indicator** — show VueWordCloud's `update:progress` event during rendering

### Advanced Features

- **Co-occurrence view** — click a tag to pivot the cloud to show tags that co-occur with it
  - New DB function `get_tag_co_occurrences(tag)` + API param `related_to=<tag>`
  - Breadcrumb trail to navigate back
- **Time-based view** — year selector to filter tag counts by source post year
  - New API param `year` on hashtag-counts endpoint
- **Export** — "Download as PNG" button + "Copy tag list" to clipboard
