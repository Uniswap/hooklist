# Hooklist Explorer UI Design

**Date:** 2026-02-27
**Status:** Approved

## Overview

A React SPA for browsing all Uniswap v4 hook deployments in the hooklist registry. Developer-focused, inspired by tokenlists.org's clean layout. Deployed via GitHub Pages from this repo.

## Tech Stack

- **React + TypeScript** via Vite
- **Tailwind CSS** for styling
- **No backend** — fetches `hooklist.json` at runtime, all filtering client-side
- **GitHub Pages** deployment from `site/dist/`

## Architecture

```
site/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── public/
│   └── (chain icons, favicon)
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── types.ts              # Hook, Flags, Properties types from schema
│   ├── hooks/
│   │   └── useHooks.ts       # Load + filter logic
│   ├── components/
│   │   ├── Header.tsx         # Logo, title, GitHub link
│   │   ├── SearchBar.tsx      # Text search input
│   │   ├── ChainFilter.tsx    # Chain pill/tab selector
│   │   ├── FlagFilter.tsx     # Flag toggle buttons
│   │   ├── PropertyFilter.tsx # dynamicFee/upgradeable/customSwapData toggles
│   │   ├── HookGrid.tsx       # Grid of hook cards
│   │   ├── HookCard.tsx       # Individual hook card
│   │   └── HookDetail.tsx     # Expanded detail view (modal or slide-over)
│   └── utils/
│       └── chains.ts          # Chain metadata (icons, explorer URLs, colors)
```

Data flow: `hooklist.json` → `useHooks` custom hook → filtered list → components.

## Layout

Split layout inspired by tokenlists.org:

- **Left side:** Hero section with title ("Hooklist — A registry of Uniswap v4 hook deployments"), description, and links (Submit a hook, GitHub, Docs)
- **Right side:** Search bar, chain filter pills, flag filter toggles, property filter toggles, result count, and a responsive card grid

**Responsive:** On mobile, hero collapses above the grid; filters become a collapsible panel.

## Hook Card

Each card shows at a glance:
- Chain badge (colored pill with chain name)
- Hook name
- Truncated description (1-2 lines)
- Verified source indicator
- Active flag count (e.g., "4 flags active")
- Property badges if true (dynamicFee, upgradeable)

## Hook Detail (Modal)

Slide-over from right (desktop) or bottom sheet (mobile):
- Full name, description
- Address (truncated with copy button)
- Link to block explorer
- All 14 flags in a grid (green check / gray X)
- Properties section
- Audit URL and deployer address if available

## Filtering

- **Search:** Text search across hook names and descriptions
- **Chain filter:** Pill toggles, multi-select, "All" default
- **Flag filter:** Toggle buttons for each of the 14 flags (show hooks that have flag enabled)
- **Property filter:** Toggle buttons for dynamicFee, upgradeable, requiresCustomSwapData
- **URL state:** Filter state encoded in URL search params for shareable links (`?chain=base&flags=beforeSwap`)

No pagination needed — 121 hooks is small enough for client-side filtering.

## Visual Design

- **Background:** White with light gray card hover
- **Text:** Dark gray primary, medium gray secondary
- **Accent:** Uniswap pink (#ff007a) for active states and links
- **Chain badges:** Per-chain colors (Base blue, Ethereum gray, Arbitrum blue, etc.)
- **Typography:** Inter / system font stack
- **Cards:** Rounded corners, subtle border, light hover shadow, chain-colored left border or top stripe
- **Filters:** Pill-shaped toggle buttons (filled active, outlined inactive)

## Data Loading

- `hooklist.json` fetched from same origin at runtime
- Loaded once on page mount
- All filtering/search is instant (client-side)

## CI Integration

- Extend `regenerate.yml` to rebuild the site when `hooklist.json` changes
- Add GitHub Pages deployment step publishing `site/dist/`
