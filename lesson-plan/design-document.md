# SoundStream Learning System -- Design Document

Saved from the original brainstorming session so future phases can be written consistently.

---

## Student Profile
- **Skill Level:** Early-intermediate Python and SQL
- **Background:** Completed prior CRM project with OOP, ETL pipelines, PostgreSQL, Docker
- **Learning Style:** Learns by doing, prefers concise explanations, rated previous sessions 3/10 difficulty
- **Pace:** Tends to finish sessions faster than estimated
- **Goal:** Startup generalist -- practical breadth over academic depth

## System Architecture

### Core Components
1. **`progress.md`** -- Single source of truth for all learning state
2. **`lesson-plan/`** -- All lesson content organized by week/session
3. **`.opencode/commands/lesson.md`** -- `/lesson` slash command triggers sessions
4. **`.opencode/agents/tutor.md`** -- Custom tutor agent (Gemini 3 Flash, temp 0.3)
5. **`AGENTS.md`** -- LLM behavioral rules

### Git Structure
- `main` branch: lesson plans, system files, progress tracking
- `cumulative` branch: running SoundStream project (session 5 work)
- `week-X-session-Y` branches: individual session work, kept for reference

### Model Choice
- **All agents:** Gemini 3 Flash ($0.50/$3.00 per 1M tokens)
- **Estimated cost:** ~$1-2/month at 5 sessions/week

---

## Session Structure

### Sessions 1-4: Independent (~45-60 min)
| Phase | Time | Description |
|-------|------|-------------|
| Setup | 2 min | Create branch `week-X-session-Y` from main |
| Follow-Along | 15-20 min | LLM guides through mini-project, outputs code with inline comments |
| Independent Addition | 15-20 min | Requirements only, NO code from LLM |
| Code Review | 5 min | Student runs code, LLM reviews output and grades |
| Quiz | 10 min | 10 questions, 8/10 to pass, strict grading |
| Wrap-up | 2 min | Update progress.md |

### Session 5: Cumulative Project (~45-60 min)
| Phase | Time | Description |
|-------|------|-------------|
| Setup | 2 min | Checkout `cumulative` branch |
| Brief | 5 min | What to add this week, acceptance criteria |
| Build | 30-40 min | Requirements only, NO code from LLM |
| Review | 10 min | Verify acceptance criteria by running commands |
| Wrap-up | 3 min | Update progress.md, commit |

### Quiz Rules
- 8/10 (80%) to pass
- Strict grading, no partial credit
- On fail: status set to `awaiting_quiz_retry`, next `/lesson` serves remediation
- Remediation uses different examples and quiz questions from the 15+ question bank
- No retry limit

### No-Code Rule (Independent Phase)
The LLM may:
- Reference code from the follow-along ("look at how we did X in step 3")
- Show error messages and explain them
- Describe algorithms in plain English prose
- Answer conceptual questions

The LLM must NOT:
- Write code blocks, function signatures, SQL queries
- Write pseudocode that is essentially the answer
- If student is stuck: give progressively more specific hints, still in prose

---

## 16-Week Curriculum

### Phase 1: Foundation (Weeks 1-4)
**Technologies:** Python, SQL/PostgreSQL, Docker, pytest, FastAPI

**Week 1: Python + SQL Basics**
- S1: Environment setup (Docker, PostgreSQL, uv, project structure) -- Weather station data
- S2: Tables, inserts, basic SELECT queries -- Bookstore inventory
- S3: Python classes, file I/O, CSV loading -- Fitness tracker logs
- S4: Data validation & error handling -- Restaurant health inspections
- S5: SoundStream -- Create schema (artists, tracks, albums), load seed data, basic queries

**Week 2: Relational Design + Testing**
- S1: Foreign keys, JOINs, normalization -- University course enrollment
- S2: Python generators, chunked processing -- Server access logs
- S3: pytest fundamentals (fixtures, assertions) -- E-commerce order processing
- S4: Integration testing with test databases -- Library book lending
- S5: SoundStream -- Add users, streams, playlists tables; streaming event ETL with dedup

**Week 3: FastAPI + Docker Compose**
- S1: FastAPI basics (routes, Pydantic models, path/query params) -- Todo list API
- S2: Database-backed API endpoints (CRUD) -- Recipe collection API
- S3: Docker Compose (multi-container: app + database) -- Blog platform
- S4: API testing & request validation -- Inventory management API
- S5: SoundStream -- API layer for top tracks, artist stats, user listening history

**Week 4: Advanced SQL + Performance**
- S1: Window functions, CTEs, subqueries -- Employee salary analytics
- S2: Indexes, EXPLAIN ANALYZE, query optimization -- E-commerce product search
- S3: Materialized views & aggregate tables -- Social media engagement metrics
- S4: Database migrations & schema versioning -- Hotel reservation system
- S5: SoundStream -- Analytics: trending tracks, listener retention, revenue reports

### Phase 2: Modern Data Stack (Weeks 5-8)
**Technologies:** dbt, DuckDB, PySpark, Airflow

**Week 5: dbt (Transform Layer)**
- S1: dbt setup, models, sources -- Retail sales pipeline
- S2: dbt tests & documentation -- Healthcare patient records
- S3: Incremental models & snapshots -- Stock market daily prices
- S4: dbt macros & Jinja templating -- Multi-tenant SaaS metrics
- S5: SoundStream -- dbt transform layer (staging -> intermediate -> marts)

**Week 6: DuckDB + Data Formats**
- S1: DuckDB basics, analytical queries -- Census demographic data
- S2: Parquet, CSV, JSON format comparison -- IoT sensor readings
- S3: DuckDB + Python integration -- Flight delay analysis
- S4: Data lake patterns (partitioning by date) -- Web clickstream data
- S5: SoundStream -- DuckDB analytics, Parquet exports, fast local analytics

**Week 7: PySpark (Concepts)**
- S1: Spark basics, DataFrames, transformations -- NYC taxi trip data
- S2: Spark SQL & aggregations -- Movie ratings analysis
- S3: Spark + PostgreSQL/Parquet I/O -- Real estate transactions
- S4: Spark performance (partitions, caching, broadcast joins) -- Ad click attribution
- S5: SoundStream -- Batch process historical data, artist royalty calculations

**Week 8: Airflow (Orchestration)**
- S1: Airflow setup, first DAG -- File processing pipeline
- S2: Task dependencies, XComs, parallel execution -- Multi-source data merge
- S3: Error handling, retries, alerting -- Payment processing pipeline
- S4: Scheduling, backfills, sensors -- Weather data collection
- S5: SoundStream -- Orchestrate: DAGs for daily ETL, weekly reports, dbt, quality checks

### Phase 3: Warehouse + Visualization (Weeks 9-12)
**Technologies:** Star schema, data quality, Streamlit, CI/CD

**Week 9: Star Schema Design**
- S1: Fact vs dimension tables, surrogate keys -- Retail point-of-sale
- S2: SCD Type 1 & Type 2 -- Customer address tracking
- S3: ETL from source to warehouse -- Hospital admissions
- S4: OLAP queries & rollups -- Advertising campaign performance
- S5: SoundStream -- Warehouse: dim_artist, dim_track, dim_user, dim_date, fact_streams, fact_revenue

**Week 10: Data Quality + Monitoring**
- S1: Data quality checks (completeness, freshness, accuracy) -- Financial transaction audit
- S2: Great Expectations or custom validation framework -- Insurance claims processing
- S3: Logging, metrics, health endpoints -- API monitoring dashboard
- S4: Alerting patterns (pipeline failure detection) -- Supply chain tracking
- S5: SoundStream -- Quality layer: automated checks, alerting, quality dashboard

**Week 11: Streamlit Dashboards**
- S1: Streamlit basics (layout, charts, tables) -- COVID data explorer
- S2: Database-connected dashboards -- Sales performance tracker
- S3: Interactive filters & drill-downs -- Student grade analytics
- S4: Dashboard deployment & caching -- Real-time crypto tracker
- S5: SoundStream -- Interactive dashboard: trends, top artists, revenue, engagement

**Week 12: CI/CD + Code Quality**
- S1: GitHub Actions basics -- Open source library
- S2: Automated testing pipelines -- Microservice test suite
- S3: Linting, type hints, pre-commit hooks -- Legacy code cleanup
- S4: Docker build & deployment automation -- Container registry pipeline
- S5: SoundStream -- CI/CD: automated tests, linting, dbt checks, Docker builds

### Phase 4: Cloud + Capstone (Weeks 13-16)
**Technologies:** AWS/GCP, Terraform, deployment, capstone

**Week 13: Cloud Basics (AWS/GCP)**
- S1: Cloud concepts, S3/GCS buckets -- Document storage system
- S2: Managed databases (RDS/Cloud SQL) -- Multi-region user data
- S3: Serverless functions (Lambda/Cloud Functions) -- Webhook processor
- S4: IAM, secrets management, security basics -- Secure API gateway
- S5: SoundStream -- Migrate data storage to cloud, connect pipelines

**Week 14: Cloud Deployment**
- S1: Infrastructure as Code (Terraform basics) -- VPC + subnet setup
- S2: Container registries & cloud deployment -- Microservice deployment
- S3: Cloud monitoring & cost management -- Budget alert system
- S4: Environment management (dev/staging/prod) -- Feature flag service
- S5: SoundStream -- Deploy to cloud: database, API, Airflow

**Week 15: Integration + Polish**
- S1: API authentication & rate limiting -- Public API gateway
- S2: Caching strategies (Redis basics) -- Session management
- S3: Async processing patterns -- Email notification system
- S4: Documentation & runbooks -- Operations handbook
- S5: SoundStream -- End-to-end integration in cloud

**Week 16: Capstone**
- S1-5: Build a complete mini data platform from scratch. New domain (e-commerce). This is the final exam.

---

## Lesson File Format

Each lesson file (session-X.md) should contain these sections:

```
# Week X, Session Y: [Topic]
**Domain:** [varied domain name]
**Concepts:** [list of concepts covered]
**Prerequisites:** [what should already be set up]

## FOLLOW-ALONG
[Step-by-step guided project with complete code blocks and inline comments]

## INDEPENDENT
[Requirements, expected behavior, files to create/modify -- NO code]

## REVIEW CHECKLIST
[What to look for when grading the student's independent addition]

## QUIZ
[15+ questions -- use 10 per attempt, reserve extras for retries]
[Mix of: multiple choice, code output prediction, spot the bug, short answer]
[Include answer key at the bottom]
```

For Session 5 files:
```
# Week X, Session 5: SoundStream -- [Feature]
**Branch:** cumulative
**Builds on:** [previous session 5 work]
**Concepts applied:** [concepts from sessions 1-4 this week]

## BRIEF
[What the student will add to SoundStream]

## REQUIREMENTS
[Detailed requirements with expected behavior]

## ACCEPTANCE CRITERIA
[Specific commands to run and expected outputs to verify success]
```

---

## Known Design Tradeoffs

1. **Quiz integrity is honor-system.** Student could read quiz questions ahead of time. Accepted because this is self-directed learning.
2. **No-code rule is hard to enforce perfectly.** LLM might drift toward giving too much help. AGENTS.md has explicit rules but relies on model compliance.
3. **Lesson files written in phases.** Allows adaptation but means Phases 2-4 don't exist yet when Phase 1 starts.
4. **Simple branches instead of worktrees.** Less isolation but simpler to manage.
5. **Session numbers track progress, not calendar dates.** Gaps between sessions are normal and expected.
