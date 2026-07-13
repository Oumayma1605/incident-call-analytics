# Power BI Dashboard — Build Guide

This folder doesn't contain a `.pbix` file — Power BI's file format is a proprietary
binary that has to be built inside Power BI Desktop itself, which isn't available in
this environment. What's here instead is everything needed to build the exact
dashboard in about 20–30 minutes: the clean data model, the DAX measures, and the
page-by-page layout.

![Dashboard preview](../visuals/00_dashboard_preview_mockup.png)
*(mockup — built in matplotlib to show the target layout; the real thing will look
sharper and be fully interactive)*

## 1. Get the data in

Open Power BI Desktop → **Get Data → Text/CSV**, and import, one at a time:

| File | Role |
|---|---|
| `data/processed/incidents_for_dashboard.csv` | Fact table — one row per ticket |
| `data/processed/calls_for_dashboard.csv` | Fact table — one row per call |
| `data/processed/dim_date.csv` | Date dimension |

On import, set data types explicitly: `opened_at` / `resolved_at` → Date/Time,
`first_call_resolution` → True/False, `reopen_count` / `reassignment_count` → Whole Number.

## 2. Build the model (Model view)

Create these relationships:

- `dim_date[date]` (1) → `Incidents[opened_at]` (many) — mark `dim_date` as a **Date Table**
- `dim_date[date]` (1) → `Calls[opened_at]` (many) — second relationship, set to **inactive**
  (Power BI only allows one active relationship at a time between two tables using the
  same date column; use `USERELATIONSHIP()` in a measure if you need to force it)
- `Incidents[ticket_id]` (1) → `Calls[linked_incident]` (many)

## 3. Add the measures

Open **Modeling → New Measure** and paste each formula from `measures.dax`.

## 4. Build the pages

**Page 1 — Overview**
- 4 KPI cards across the top: `Total Incidents`, `First Call Resolution Rate`,
  `Reopen Rate`, `Median Resolution Time (hours)`
- Clustered column chart: incidents & calls by month (`dim_date[month]` on axis)
- Horizontal bar chart: `Total Incidents` by `category`, top 10
- Donut chart: `First Call Resolution Rate` breakdown
- Slicers: `month`, `company`, `assignment_group`

**Page 2 — Resolution performance**
- Box-and-whisker or clustered bar: `Median Resolution Time (hours)` split by
  `first_call_resolution`
- Bar chart: `Avg Resolution Time (hours)` by `category`
- Scatter or bar: `Avg Resolution Time (hours)` by `reassignment_count`
- Table: `assignment_group` x `Total Incidents`, `First Call Resolution Rate`,
  `Median Resolution Time (hours)` — sortable, this is the operational drill-down view

**Page 3 — Calls**
- KPI cards: `Total Calls`, `Outbound Call Share`, `Calls per Incident`
- Pie chart: calls by `call_reason`
- Bar chart: calls by `call_direction`
- Line chart: calls by day (`dim_date[date]`) to see daily rhythm

## 5. Publish & share

**File → Publish → Publish to Power BI** (needs a Power BI account, free tier works
for personal workspaces). Once published, **File → Embed report → Publish to web**
(only for non-confidential data — since this dataset is already anonymized and stripped
of any direct identifiers, that's fine here) gives you a public link you can drop
straight into the README or share with anyone without them needing a Power BI license.
