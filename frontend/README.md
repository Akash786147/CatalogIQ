# CatalogIQ — Frontend

The reviewer surface. React 19 + TypeScript + Vite.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # typecheck + production bundle
```

It runs standalone with no backend — see *Connecting the backend* below.

## What each screen is for

| Route | Screen | The point it makes |
|---|---|---|
| `/` | **Run overview** | Fill rate shown *next to* accuracy, provenance breakdown, confidence distribution, cost, analyst-hours saved |
| `/review` | **Review queue** | Ranked by doubt, not row number. "918 clean, 82 need you." |
| `/review/:rowId` | **Product detail** | Every value with its evidence — and the correction that propagates |
| `/search` | **Search proof** | Same query, raw vs enriched. The 30-second commercial case. |

The detail screen is the one that matters. Hovering a value highlights **the exact
characters of `Part_Desc` it was read from**, so provenance is something a judge
can see rather than something we assert. Correcting a field submits a *rule*
scoped to the distributor, and the response reports its blast radius —
*"applied to 55 rows, 3 now need re-review."*

## Connecting the backend

Every component talks to [`src/lib/api.ts`](src/lib/api.ts) and nothing else.
That is the only file that knows a network exists.

It calls the FastAPI backend directly — there is no mock layer.

In development, start FastAPI on `:8000`. `vite.config.ts` proxies `/api` there, so no CORS
setup is needed in development. When deployed, set `VITE_API_BASE` to the
backend's URL and add that origin to `CATALOGIQ_CORS_ORIGINS` on the backend.

The endpoints `api.ts` expects:

| Method | Path | Returns |
|---|---|---|
| `GET` | `/api/runs/latest` | `RunStats` |
| `GET` | `/api/rows?search=&manufacturer=&flag=` | `EnrichedRow[]` |
| `GET` | `/api/rows/:rowId` | `EnrichedRow` |
| `POST` | `/api/corrections` | `PropagationResult` |
| `GET` | `/api/search?q=` | `SearchComparison` |

`src/lib/types.ts` mirrors `backend/app/core/cell.py`. **If you change one,
change the other** — that pairing is the contract between the two halves.

## Theme

Brand tokens in [`src/styles/theme.css`](src/styles/theme.css) are lifted from
unilogcorp.com's own stylesheets so this reads as a Unilog product:

| Token | Value | Use |
|---|---|---|
| navy | `#0C2A4D` | sidebar, primary buttons |
| amber | `#FF9D00` | the signature accent — active nav, primary CTA |
| blue | `#009EFF` | interactive secondary, focus rings |
| type | Avenir → Nunito Sans fallback | their brand face, with a loaded substitute |

Dark mode is a **selected** palette, not an inverted one. Both modes were
validated with the dataviz validator — lightness band, chroma floor, CVD
separation, normal-vision floor and contrast all pass. Provenance colors are
never the only signal: every chip carries its label, and chart segments carry
direct value labels plus a legend.

## Conventions

- No component fetches directly — always through `api`.
- A `Cell` with `state: null` is an **honest gap** and renders as explanatory
  italic text, never as an em-dash or a zero. That distinction is the product.
- Confidence is never color-alone; the percentage is always printed.
