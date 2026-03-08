# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Next.js frontend for **AIdea Platform** — SES job listing dashboard + engineer management + matching system + Supabase Auth.
Parent project CLAUDE.md (`../CLAUDE.md`) has full context including backend, deployment, and environment details.

- **Production URL**: `https://gmail-analyzer-nu.vercel.app`
- **Backend API**: `https://gmail-analyzer-api.onrender.com`

## Commands

```bash
npm run dev      # Start dev server (localhost:3000)
npm run build    # Production build (also runs TypeScript check)
npm run lint     # ESLint (flat config v9, next/core-web-vitals + typescript)
```

The backend must be running at `localhost:8000` for local development (or set `NEXT_PUBLIC_API_URL`).

## Architecture

### Tech Stack

- **Next.js 16** with App Router (`src/app/`)
- **React 19** — all pages are client components (`"use client"`)
- **TypeScript** (strict mode), path alias `@/*` → `./src/*`
- **Tailwind CSS v4** — configured via `@theme inline` in `globals.css`, no `tailwind.config.ts`
- **Recharts** — 4 chart components for data visualization
- **@supabase/supabase-js** — authentication (email+password login)

### Authentication

- **`src/lib/supabase.ts`** — Supabase client init. Returns `null` if env vars not set (auth disabled mode for local dev).
- **`src/components/AuthProvider.tsx`** — React context providing `useAuth()` hook: `{ user, loading, signOut }`. Fetches user profile from `/api/auth/me` after Supabase session established. Falls back to dummy admin when Supabase not configured.
- **`src/components/AppShell.tsx`** — Auth guard wrapper. Redirects unauthenticated users to `/login`. Controls Sidebar visibility (hidden on login page). Responsive layout with `lg:ml-56`.
- **`src/components/Sidebar.tsx`** — Role-based navigation: admin sees all 6 menu items, engineer sees only "My Profile". Displays user email + logout button.

### Pages (9 pages)

| Route | File | Purpose | Auth |
|-------|------|---------|------|
| `/login` | `login/page.tsx` | Login — email + password via Supabase Auth | Public |
| `/` | `page.tsx` | Dashboard — KPI cards + 4 charts + CollapsibleSection panels | Admin |
| `/search` | `search/page.tsx` | Job search — sidebar filters (AND/OR keyword, skills, area, price, date) + expandable results + CSV export | Admin |
| `/fetch` | `fetch/page.tsx` | Email fetch — pipeline controls, SSE progress, stats. 日時はJST変換。409重複は赤色表示 | Admin |
| `/settings` | `settings/page.tsx` | Settings — Gmail/Gemini/processing parameters | Admin |
| `/engineers` | `engineers/page.tsx` | Engineer management — CRUD, skills, pricing, area, processes, CSV import/export | Admin |
| `/matching` | `matching/page.tsx` | Matching — engineer↔listing proposals, score display, status management (2 tabs) | Admin |
| `/admin/users` | `admin/users/page.tsx` | User management — CRUD, role assignment, password reset, engineer linking | Admin |
| `/my-profile` | `my-profile/page.tsx` | My Profile — engineer's own info, skills, assignments (read-only) | Engineer |

### Key Modules

- **`src/lib/api.ts`** — Generic `fetchAPI<T>()` wrapper. `NEXT_PUBLIC_API_URL` env (falls back to `localhost:8000`). Auto-attaches Supabase Auth JWT as Bearer token. `no-store` cache. Error detail extraction from response body.
- **`src/lib/supabase.ts`** — Supabase client from `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **`src/types/index.ts`** — All TypeScript interfaces (50+). **Must stay in sync with backend `models/schemas.py`** and router response formats.
- **`src/components/Sidebar.tsx`** — Fixed dark sidebar with mobile hamburger menu. Brand: "AIdea Platform" v1.0.0.
- **`src/components/ProgressBar.tsx`** — SSE-based progress via EventSource.
- **`src/components/CollapsibleSection.tsx`** — Collapsible panels with default open/closed state.
- **`src/components/charts/`** — SkillBarChart, PriceHistogram, AreaPieChart, TrendLineChart.

### Styling

- CSS custom properties in `globals.css` `:root` — use `var(--card-bg)`, `var(--border)`, `var(--primary)` etc. via inline `style={{}}`.
- Tailwind classes for layout/spacing, CSS variables for theme colors.
- Geist Sans/Mono fonts loaded in `layout.tsx`.

### Data Fetching Pattern

All data fetching is client-side via `useEffect` + `useState`. No server components fetch data. Auth token automatically attached by `fetchAPI()`. Query params built with `buildParams()` pattern in search pages. SSE streaming via `getProgressURL(jobId)` → EventSource → `ProgressBar` component.

### Environment Variables

```
NEXT_PUBLIC_API_URL=             # Backend URL (default: http://localhost:8000)
NEXT_PUBLIC_SUPABASE_URL=        # https://xxx.supabase.co (omit for auth-disabled local dev)
NEXT_PUBLIC_SUPABASE_ANON_KEY=   # Supabase anon key
```
