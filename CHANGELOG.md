# Changelog

## 2026-07-02

### Backend

- **Switched RNA folding to DNA folding.** `backend/main.py` now loads
  `ViennaRNA-master/misc/dna_mathews2004.par` on import via
  `RNA.params_load(...)`, and all three `RNA.fold(...)` call sites pass DNA
  sequences directly (no more `T → U` conversion). This aligns folding output
  with the ML model, which was trained on DNA structures. MFE values shift
  from the RNA range (~−8 kcal/mol on the test seq) to the DNA range
  (~−3 kcal/mol) — expected.
- **Log throttling.** Added `_should_log_now(job_id, key, interval=1.0)` helper
  that time-throttles per-batch and per-tick log lines using an in-job
  `_log_ts` dict. Applied to the combined batch summary log (constraint /
  ML / RNA-folding merged into one line), progress-update logs (both
  exhaustive and random paths), ETA logs, and mid-run `save_job_to_db`
  "Processing" saves. Terminal-state DB saves and errors are unchanged.
  Result: ~27 log lines per full-run job instead of hundreds.
- **Refactor: extracted helpers to `backend/utils/`.** New package with
  `config.py` (constants), `constraints.py` (GC/repeat checks + regex
  patterns), `sequence_utils.py` (prefix/suffix helpers), `schemas.py`
  (`InputData` Pydantic model + its validators), `results_queue.py`
  (`BoundedResultsQueue`). `main.py` dropped from 1717 → 1565 lines with
  no behavior change. Anything that touches `active_jobs`, `_should_log_now`,
  or the RNA thread pool stayed in `main.py` intentionally.

### Frontend — multi-page restructure

- **New site structure.**
  - `app/page.tsx` — new home page (hero + module grid).
  - `app/predict/page.tsx` — the original prediction UI (moved from
    `app/page.tsx`, renamed "Aptamer Designer" in the UI).
  - `app/faq/`, `app/instructions/`, `app/members/`, `app/license/`,
    `app/contact/` — new subpages, each backed by a data file.
  - `app/results/[jobId]/` — unchanged route, still bookmarkable.
- **Shared layout.** `app/layout.tsx` now wraps every page with a
  `Header` and `Footer`. Header reads its links from `app/content/nav.ts`
  and highlights the active route via `usePathname`.
- **Content-in-data-files pattern.** All text lives in `app/content/*.ts`
  (`site.ts`, `nav.ts`, `modules.ts`, `faq.ts`, `instructions.ts`,
  `members.ts`). Adding an FAQ item / nav link / module = editing an
  object literal, not touching JSX.
- **Reusable components.** `app/components/Header.tsx`,
  `Footer.tsx`, `ModuleCard.tsx`.

### Frontend — Aptamer Designer improvements

- **"Start New Task" button** in the results panel. Resets every form and
  job-related state field, and rewrites the URL back to `/predict` via
  `history.replaceState` so the address bar reflects a fresh form (not
  `/results/<jobId>`).
- **D3 + Fornac load ordering.** Old code loaded d3 with
  `strategy="beforeInteractive"` inside a page — silently ignored in
  Next 15 App Router outside the root layout, so d3 sometimes never
  loaded, and Fornac's `t.fornac = e(t.d3)` UMD wrapper captured
  `undefined` → "Cannot read properties of undefined (reading 'select')".
  Fix: extracted `app/components/AptamerVizScripts.tsx` — d3 loads via
  `afterInteractive`, and Fornac's `<Script>` is conditionally rendered
  only after d3's `onLoad` fires. Reused from both
  `app/predict/layout.tsx` and `app/results/layout.tsx` so
  `/results/<jobId>` gets the same viz libs.
- **Fixed results-URL regression.** `app/results/[jobId]/page.tsx` was
  importing `Home` from `../../page` — which after the restructure is
  the module grid, not the prediction UI. Import changed to
  `../../predict/page`. Bookmarked results URLs work again.

### Frontend — polish

- **Input text colour on dark-mode devices.** `globals.css` had a
  `@media (prefers-color-scheme: dark)` block that flipped body colour
  to `#ededed`, but every panel is hardcoded `bg-white`, so form input
  values were near-invisible on Windows-dark-mode Chrome. Removed the
  dark-mode block (the app doesn't actually support dark mode) and
  added explicit `input, textarea, select { color: #171717; }` plus
  placeholder colour rules.

### Known dev-mode gotcha

- After moving `app/page.tsx` (old prediction UI) → `app/predict/page.tsx`
  and creating a new `app/page.tsx`, the Next dev server's chunk registry
  can go stale — the manifest lists `static/chunks/app/page.js` but the
  file is never emitted. Symptom: `ChunkLoadError` when navigating to
  home from another route. Fix: stop `next dev`, `rm -rf .next`,
  restart `npm run dev`. Not a code bug — just Next dev cache.

### Backups on disk

- `backend/main.py.bak_before_dna_fold`
- `backend/main.py.bak_before_refactor`
- `frontend/app/page.tsx.bak_before_restructure`
- `frontend/app/layout.tsx.bak_before_restructure`
