# Presidio Observer Frontend

The frontend is the local dashboard for Presidio Observer. It is built with Preact, Vite, and Carbon React components through Preact compatibility aliases.

## Role

The dashboard turns local analyzer metadata into an inspection and review workflow:

- view analyzer call volume and latency
- inspect recent analyzer events in a Carbon `DataTable`
- filter dashboard data by time range, language, entity type, and confidence flag
- enable optional polling-based auto-refresh
- open an event detail drawer without losing worklist context
- inspect summary metadata and entity-level metadata
- save, replace, and remove current-state evaluation labels
- report missed entities by type and count only

## Privacy Boundary

The frontend should not request, store, display, or cache raw text. It also should not display detected values, anonymized output, missed values, context words, regex patterns, tokens, lemmas, NLP artifacts, or allow-list values.

Allowed UI data includes analyzer metadata such as entity type, score, span offsets, span length, recognizer metadata, latency, language, confidence flag, and evaluation labels.

## Component Provider

Carbon React is the component provider. React packages are resolved to `preact/compat` through Vite aliases.

Current Carbon usage includes:

- `DataTable` for the Event Worklist
- `Tabs` for event detail sections
- `Tile`, `Grid`, and `Column` for dashboard layout
- `Select`, `TextInput`, `Checkbox`, `NumberInput`, and `Button` for controls
- `DataTableSkeleton` and `SkeletonText` for loading states
- `Toggletip` for targeted contextual help

Prefer Carbon primitives before adding custom UI controls.

## Dashboard Behavior

Filters are applied explicitly. Changing filter fields does not reload data until `Apply filters` is selected.

Auto-refresh is optional and disabled by default. When enabled, it uses the currently applied filters and prevents overlapping dashboard requests.

Saved labels are editable current evaluation state. Removing a saved label deletes only that label row through the backend API and does not delete analyzer events or metadata.

## Local Development

Install frontend dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Build static assets:

```bash
npm run build
```

Preview a local production build:

```bash
npm run preview
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## Docker Compose

The Docker image builds static assets with Node and serves them with Nginx. The Nginx config proxies `/api` to the `backend` service inside Docker Compose.

Run from the repository root:

```bash
docker compose up --build frontend
```

Default frontend URL:

```text
http://localhost:5173
```

## File Organization

- `src/app.jsx`: top-level dashboard orchestration and data refresh state
- `src/api/`: backend API clients
- `src/components/`: reusable Preact/Carbon components
- `src/lib/`: pure formatting and domain helpers
- `src/index.scss`: Carbon setup and local layout styles

## Contributing

Keep components focused and prefer top-level component definitions. Preserve independent parallel data fetches with `Promise.all` where endpoint results do not depend on each other.

Before proposing frontend changes, use the local development server for manual verification. Use the production build command when a packaging or bundling change is involved.

Useful commands:

```bash
npm run dev
npm run build
```
