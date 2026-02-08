# Frontend (frontend/) - Agent Guide

## Purpose

Next.js 14 application providing four user-facing surfaces: Knowledge Wiki generation, Web Crawler, Save & Research (Instapaper-style), and Readings browser. Designed as a PWA with Android Share Target support.

## Architecture

```mermaid
flowchart TD
    subgraph Pages
        HOME[/ - Home + Wiki Generator]
        WIKI[/wiki/:id - Wiki Viewer]
        PROJECTS[/wiki/projects - Project List]
        CRAWLER[/crawler - Web Crawler UI]
        SAVE[/save - Share Target Receiver]
        READINGS[/readings - Reading List]
        DETAIL[/readings/:id - Reading Detail]
    end

    subgraph Components
        TREE[WikiTreeView]
        ASK[AskPanel]
        MD[Markdown]
        MERMAID[MermaidDiagram]
        CARD[CrawlJobCard]
        THEME[ThemeToggle]
    end

    subgraph API_Routes["API Routes (Next.js)"]
        WIKI_API[/api/wiki/*]
        INGEST_API[/api/ingest/*]
        READINGS_API[/api/readings/*]
    end

    subgraph Backend["FastAPI Backend"]
        BE[localhost:8000]
    end

    HOME --> WIKI
    HOME --> CRAWLER
    HOME --> SAVE
    SAVE --> READINGS
    WIKI --> TREE
    WIKI --> ASK
    WIKI --> MD
    MD --> MERMAID
    CRAWLER --> CARD

    WIKI_API --> BE
    INGEST_API --> BE
    READINGS_API --> BE
```

## Component Map

| Component | Purpose | Key Props |
|-----------|---------|-----------|
| `WikiTreeView` | Collapsible section/page sidebar | `wikiStructure`, `currentPageId`, `onPageSelect` |
| `AskPanel` | Chat interface with streaming responses | `wikiTitle`, `wikiContext` |
| `Markdown` | Rich markdown with Mermaid + syntax highlighting | `content` |
| `MermaidDiagram` | Dynamic Mermaid chart renderer | `chart` |
| `CrawlJobCard` | Live crawl job status with polling | `job`, `onRefresh` |
| `ThemeToggle` | Light/dark mode (Japanese aesthetic) | — |

## Page Responsibilities

| Page | File | Key Behaviour |
|------|------|---------------|
| Home | `app/page.tsx` | Wiki title input, generate button, project cards |
| Wiki Viewer | `app/wiki/[id]/page.tsx` | Sidebar + streaming page content + Ask modal + export |
| Crawler | `app/crawler/page.tsx` | URL input, config panel, job monitoring |
| Save | `app/save/page.tsx` | Share Target receiver, auto-save, YouTube cards |
| Readings | `app/readings/page.tsx` | Reading list with thumbnails, tags, domains |
| Reading Detail | `app/readings/[id]/page.tsx` | YouTube embed, summary, key points, related links |

## PWA & Android Share Target

The `public/manifest.json` declares a `share_target`:

```json
{
  "action": "/save",
  "method": "GET",
  "params": { "title": "title", "text": "text", "url": "url" }
}
```

When installed via "Add to Home Screen" on Android Chrome, the app appears in the system share sheet. Shared URLs are received as query parameters on `/save`.

## Durable Lessons

1. **API routes are proxies.** Every `app/api/` route handler forwards to the FastAPI backend. This avoids CORS issues and lets the frontend deploy independently. Keep route handlers thin — just `fetch()` + forward.

2. **Streaming is through the proxy.** Wiki page generation and chat forward `Response.body` as a `ReadableStream`. The frontend reads chunks via `reader.read()` and updates state progressively.

3. **Session storage for state transfer.** Wiki structures are stored in `sessionStorage` after generation, then read by the wiki viewer page. This avoids re-generating on navigation.

4. **YouTube detection is UI-aware.** When `result.media_type === "youtube"`, the save page shows a thumbnail card with play button, the readings list shows video thumbnails, and the detail page embeds an iframe player.

5. **CrawlJobCard polls until terminal.** It polls `/api/ingest/jobs/:id` every 3 seconds while status is `queued` or `started`, then stops. The polling state is managed with `useEffect` cleanup.

6. **Theme uses CSS custom properties.** Colors like `--accent-primary`, `--card-bg`, `--border-color` are set on `:root` and `[data-theme="dark"]`. Tailwind classes reference these via `var()`. No Tailwind dark: prefix needed.

7. **Standalone output for Docker.** `next.config.mjs` sets `output: "standalone"` which produces a self-contained Node.js server. The Dockerfile copies `.next/standalone` + `.next/static` for a minimal production image.
