# Phase 9 Handoff: PDF Report Export

## 1. Overview & Objectives

Phase 9 delivers a print-ready, multi-page, deterministic PDF export engine for any completed backtest run in the EquiTest NSE framework. The generation pipeline executes completely server-side in Python using WeasyPrint, Jinja2, and matplotlib (Agg backend). Reports render institutional-grade analytics featuring exact A4 pagination, running headers/footers with dynamic page counters (`Page X / Y`), repeated table headers across page splits, audit trail reproducibility provenance, customizable branding, and zero client-side canvas dependencies.

All changes are strictly additive: no existing endpoints, models, metric calculation algorithms, or routes from Phases 0–8 were modified.

---

## 2. Repository State & Baseline Commit

- **Base Git SHA**: `a88c52954164c669ce70734cbe5820fcbd273e52`
- **Branch**: `main`
- **Authoritative Reference Documents**:
  - `TRACEABILITY.md` (Updated with REQ-9.1 through REQ-9.7 and PDF endpoints)
  - `docs/ASSUMPTIONS.md` (Binding constraints and methodology rules)
  - `docs/ARCHITECTURE.md` (System topology and subsystem interactions)
  - `docs/STRATEGY.md` (Strategy parameters, universe definitions, and indicators)

---

## 3. Test Verification & Quality Gates

The entire test suite passes 100% cleanly across all tiers:

| Test Suite | Commands Executed | Result | Details |
| :--- | :--- | :--- | :--- |
| **Backend Unit & Integration** | `pytest backend/tests` | ✅ Passed | 147 passed, 0 failed; **88.42% line coverage** (gate >= 80%) |
| **Frontend Vitest** | `npm --prefix frontend test` | ✅ Passed | 11 test files, 30 tests passed, 0 failed |
| **Playwright E2E** | `npx playwright test` | ✅ Passed | 18 tests passed, 0 failed across all workflows |
| **Code Formatting & Linting** | `make lint` | ✅ Passed | Ruff (0 errors), Black (clean), ESLint (0 errors, 0 warnings), TypeScript strict (0 errors) |
| **OpenAPI Contract Sync** | `make openapi` | ✅ Passed | Synchronized `frontend/openapi.json` and `frontend/lib/schema.d.ts` |

---

## 4. Requirements Traceability (Phase 9)

| Req ID | Requirement | Implementation Artifacts | Test & Verification Evidence | Status |
| :--- | :--- | :--- | :--- | :--- |
| **REQ-9.1** | PDF Report Export | `backend/app/reports/pdf.py`, `backend/app/api/v1/reports.py`, `backend/app/reports/templates/` | `backend/tests/test_reports_pdf.py::test_generate_pdf_fixture_run`, `test_export_pdf_small_run_streams_pdf`, `frontend/tests/export.test.tsx`, `e2e/pdf_export.spec.ts` | ✅ Verified |
| **REQ-9.2** | PDF Template Configurability | `backend/app/core/branding.py`, `backend/app/reports/templates/report.html.j2`, `backend/app/reports/templates/report.css` | `backend/tests/test_reports_pdf.py::test_pdf_branding_config_override` | ✅ Verified |
| **REQ-9.3** | Server-Side Chart Rendering | `backend/app/reports/charts.py` | `backend/tests/test_reports_pdf.py::test_render_equity_curve_produces_png`, `test_render_drawdown_produces_png`, `test_render_monthly_heatmap_produces_png`, `test_charts_are_deterministic` | ✅ Verified |
| **REQ-9.4** | Async PDF Job for Large Runs | `backend/app/reports/jobs.py`, `backend/app/api/v1/reports.py` (`/jobs/{job_id}`, `/jobs/{job_id}/download`, `/export/pdf/async`) | `backend/tests/test_reports_pdf.py::test_export_pdf_large_run_returns_202`, `test_job_status_lifecycle`, `test_pdf_job_manager_cleanup_expired`, `frontend/tests/export.test.tsx`, `e2e/pdf_export.spec.ts` | ✅ Verified |
| **REQ-9.5** | Deterministic PDF Output | `backend/app/reports/pdf.py` (`include_creation_date=False`), `charts.py` | `backend/tests/test_reports_pdf.py::test_pdf_is_deterministic`, `test_charts_are_deterministic` | ✅ Verified |
| **REQ-9.6** | Docker Runtime Dependencies | `backend/Dockerfile`, `backend/pyproject.toml` | Multi-stage build stages, WeasyPrint C-libraries (`libpango-1.0-0`, `libcairo2`, `fonts-dejavu-core`), smoke test | ✅ Verified |
| **REQ-9.7** | CLI Wrapper for PDF Generation | `backend/app/reports/__main__.py`, `backend/app/reports/pdf.py` | `backend/tests/test_reports_pdf.py::test_cli_pdf_generation` | ✅ Verified |

---

## 5. Architectural Implementation Details

### 5.1 Server-Side Chart Rendering (`backend/app/reports/charts.py`)
- Configured matplotlib Agg backend (`matplotlib.use("Agg")`). Never calls `plt.show()`.
- Generates 1200x600 resolution images at 150 DPI.
- Pure functions accepting pandas DataFrames only (no disk reads except optional branding logos):
  - `render_equity_curve(equity_df, out_path, ...)`
  - `render_drawdown(equity_df, out_path, ...)`
  - `render_monthly_heatmap(monthly_df, out_path, ...)`
- Strips PNG metadata chunks (`Software`, `Creation Time`) via Pillow save options and `png.write(..., pnginfo=...)` to ensure deterministic SHA-256 byte hashes.

### 5.2 Multi-Page Report Template (`backend/app/reports/templates/`)
- **`report.html.j2`** Jinja2 template containing 6 ordered sections:
  1. **Cover Page**: Firm name, optional logo, "Backtest Report — <Strategy Name>", run ID, generation date, period (start–end), symbol count, disclaimer.
  2. **Executive Summary**: 6 KPI cards (Final Capital, Total Return %, Number of Trades, Average Profit, Average Loss, Win %), advanced metrics table (CAGR, Sharpe, Sortino, Max Drawdown, Calmar, Profit Factor, Expectancy, Avg Days Held), and dynamic narrative paragraph.
  3. **Configuration**: Serialized `StrategyConfig` table, data snapshot hash, Git commit SHA.
  4. **Performance Charts**: Full-width Equity Curve, Underwater Drawdown chart, Monthly Returns Heatmap.
  5. **Trade Log**: Paginated table (`symbol`, `entry_date`, `entry_price`, `qty`, `exit_date`, `exit_price`, `pnl_inr`, `pnl_pct`, `days_held`, `exit_reason`). P&L columns colored green for profit, red for loss. Rows capped at 5,000 in PDF with export disclaimer if exceeded.
  6. **Appendix**: Full contents of `docs/ASSUMPTIONS.md` rendered to HTML; audit panel with Git SHA, data snapshot hash, Python library versions, config hash.
- **`report.css`**:
  - `@page` A4 size with 20mm margins.
  - Running header: firm name and run ID (suppressed on cover page).
  - Running footer: dynamic page counter in `Page X / Y` format via CSS counters `counter(page)` and `counter(pages)`.
  - Repeated table headers: `thead { display: table-header-group; }`.
  - Non-breaking table rows: `tr { page-break-inside: avoid; }`.
  - Pure self-contained inline CSS; zero external network or web font dependencies.

### 5.3 Deterministic PDF Engine (`backend/app/reports/pdf.py`)
- `generate_pdf(run_id: str, include_creation_date: bool = True, output_dir: Path | None = None) -> Path`:
  - Reuses existing repositories (`_load_run_and_result`, `load_run_audit`). Does not re-query or duplicate metrics logic.
  - Embedded charts are passed as base64 data URIs (`data:image/png;base64,...`) to eliminate temporary filesystem path leakage into WeasyPrint image XObject identifiers.
  - Fixes `SOURCE_DATE_EPOCH="0"` in environment during rendering to normalize font subset timestamps.
  - When `include_creation_date=False`, strips `/CreationDate`, `/ModDate`, and `/ID` trailer entries with `pypdf`, guaranteeing 100% bit-for-bit SHA-256 byte determinism.
- Raises custom `PdfGenerationError(Exception)` wrapping any underlying failure.

### 5.4 Async Job Lifecycle (`backend/app/reports/jobs.py` & API Endpoints)
- Handles large backtest runs (> 2000 trades) or explicit async requests:
  - `GET /api/v1/reports/{run_id}/export?format=pdf`:
    - Runs with <= 2000 trades generate synchronously and stream `application/pdf` with `Content-Disposition: attachment; filename="backtest_{sanitized_run_id}.pdf"`.
    - Runs with > 2000 trades return `202 Accepted` with `{ "job_id": "..." }` and a `Location: /api/v1/reports/jobs/{job_id}` header.
  - `POST /api/v1/reports/{run_id}/export/pdf/async`: Forces asynchronous generation regardless of trade count.
  - `GET /api/v1/reports/jobs/{job_id}`: Reports status (`pending`, `ready`, `failed`), file path, error, and timestamp. Automatically evicts jobs older than 1 hour.
  - `GET /api/v1/reports/jobs/{job_id}/download`: Streams the generated PDF once ready (`409 Conflict` if still pending, `410 Gone` if expired or failed).
  - `GET /api/v1/reports/{run_id}/preview.png`: Renders page 1 of the generated PDF as a PNG preview thumbnail.

### 5.5 Institutional Branding Configuration (`backend/app/core/branding.py`)
- Pydantic Settings reading dynamically from `backend/branding.json` if mounted, falling back to environment variables or institutional defaults:
  - `firm_name`: `"Backtesting Framework"`
  - `logo_path`: `None`
  - `disclaimer_text`: `"For research use only. Past performance does not guarantee future results."`
  - `primary_color`: `"#1f2937"`
  - `footer_note`: `""`
- Dynamic reload: edits to `branding.json` reflect immediately in subsequent PDF exports without server restart.

### 5.6 Frontend Component (`frontend/components/ExportButton.tsx`)
- TanStack Query mutation handling both synchronous 200 binary downloads and 202 async polling workflows (2-second interval polling hook).
- Integrates unobtrusive toast notifications for PDF generation progress, completion, and errors.
- Strict TypeScript with Zod response validation.
- Seamlessly placed on `/reports/[runId]` toolbar alongside existing CSV/XLSX/ZIP export buttons.

### 5.7 CLI Interface (`backend/app/reports/__main__.py`)
- CLI command: `python -m app.reports.pdf <run_id> <out_path>`
- Thin wrapper delegating to `generate_pdf()` for scriptable pipeline automation and scheduled reporting.

---

## 6. Locked Backend Interfaces

Future phases may import from these interfaces but MUST NOT modify their public signatures:

1. **`backend/app/reports/charts.py`**:
   - `render_equity_curve(equity_df: pd.DataFrame, out_path: Path, width: int = 1200, height: int = 600, dpi: int = 150) -> Path`
   - `render_drawdown(equity_df: pd.DataFrame, out_path: Path, width: int = 1200, height: int = 600, dpi: int = 150) -> Path`
   - `render_monthly_heatmap(monthly_df: pd.DataFrame, out_path: Path, width: int = 1200, height: int = 600, dpi: int = 150) -> Path`

2. **`backend/app/reports/pdf.py`**:
   - `generate_pdf(run_id: str, include_creation_date: bool = True, output_dir: Path | None = None) -> Path`
   - `PdfGenerationError(Exception)`

3. **`backend/app/core/branding.py`**:
   - `BrandingConfig` (Pydantic BaseSettings)
   - `get_branding_config() -> BrandingConfig`

4. **`backend/app/reports/jobs.py`**:
   - `pdf_job_manager: PdfJobManager`
   - `render_pdf_first_page_png(pdf_path: Path, out_path: Path) -> Path`

---

## 7. Locked Frontend Routes & Components

1. **`frontend/components/ExportButton.tsx`**:
   - Props: `format: "pdf" | "csv" | "xlsx"`, `runId: string`
   - Export toolbar on `/reports/[runId]`

---

## 8. Containerization & Dependencies

### Runtime System Packages (Debian / Dockerfile)
- `libpango-1.0-0`
- `libpangoft2-1.0-0`
- `libcairo2`
- `libgdk-pixbuf-2.0-0`
- `libffi-dev`
- `shared-mime-info`
- `fonts-dejavu-core`

### Python Libraries (`pyproject.toml`)
- `weasyprint>=62.0`
- `matplotlib>=3.9.0`
- `kaleido>=0.2.1`
- `jinja2>=3.1.4`
- `pypdf>=5.0.0`
- `markdown>=3.6.0`
- `pypdfium2>=4.30.0`
