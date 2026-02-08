# SoundStream: 16-Week Data Engineering Curriculum

## Overview
Build a music/content data platform from scratch. 5 sessions per week, 80 sessions total.
- **Sessions 1-4:** Independent mini-projects on varied domains (weather, e-commerce, IoT, etc.)
- **Session 5:** Cumulative build on the SoundStream platform using that week's concepts

## Tech Stack Progression
| Phase | Weeks | Technologies |
|-------|-------|-------------|
| Foundation | 1-4 | Python, SQL/PostgreSQL, Docker, pytest, FastAPI |
| Modern Data Stack | 5-8 | dbt, DuckDB, PySpark, Airflow |
| Warehouse + Viz | 9-12 | Star schema, data quality, Streamlit, CI/CD |
| Cloud + Capstone | 13-16 | AWS/GCP, Terraform, deployment, capstone |

---

## Phase 1: Foundation (Weeks 1-4)

### Week 1: Python + SQL Basics
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Environment setup (Docker, PostgreSQL, uv, project structure) | Weather station data |
| 2 | Tables, inserts, basic SELECT queries | Bookstore inventory |
| 3 | Python classes, file I/O, CSV loading | Fitness tracker logs |
| 4 | Data validation & error handling | Restaurant health inspections |
| 5 | **SoundStream:** Create schema (artists, tracks, albums), load seed data, basic queries |

### Week 2: Relational Design + Testing
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Foreign keys, JOINs, normalization | University course enrollment |
| 2 | Python generators, chunked processing | Server access logs |
| 3 | pytest fundamentals (fixtures, assertions) | E-commerce order processing |
| 4 | Integration testing with test databases | Library book lending |
| 5 | **SoundStream:** Add users, streams, playlists tables; build streaming event ETL with dedup |

### Week 3: FastAPI + Docker Compose
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | FastAPI basics (routes, Pydantic models, path/query params) | Todo list API |
| 2 | Database-backed API endpoints (CRUD) | Recipe collection API |
| 3 | Docker Compose (multi-container: app + database) | Blog platform |
| 4 | API testing & request validation | Inventory management API |
| 5 | **SoundStream:** Add API layer -- endpoints for top tracks, artist stats, user listening history |

### Week 4: Advanced SQL + Performance
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Window functions, CTEs, subqueries | Employee salary analytics |
| 2 | Indexes, EXPLAIN ANALYZE, query optimization | E-commerce product search |
| 3 | Materialized views & aggregate tables | Social media engagement metrics |
| 4 | Database migrations & schema versioning | Hotel reservation system |
| 5 | **SoundStream:** Add analytics -- trending tracks, listener retention, revenue reports |

---

## Phase 2: Modern Data Stack (Weeks 5-8)

### Week 5: dbt (Transform Layer)
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | dbt setup, models, sources | Retail sales pipeline |
| 2 | dbt tests & documentation | Healthcare patient records |
| 3 | Incremental models & snapshots | Stock market daily prices |
| 4 | dbt macros & Jinja templating | Multi-tenant SaaS metrics |
| 5 | **SoundStream:** dbt transform layer -- staging, intermediate, mart models for streaming data |

### Week 6: DuckDB + Data Formats
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | DuckDB basics, analytical queries | Census demographic data |
| 2 | Parquet, CSV, JSON -- format comparison | IoT sensor readings |
| 3 | DuckDB + Python integration | Flight delay analysis |
| 4 | Data lake patterns (partitioning by date) | Web clickstream data |
| 5 | **SoundStream:** DuckDB analytics layer -- process Parquet exports, build fast local analytics |

### Week 7: PySpark (Concepts)
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Spark basics, DataFrames, transformations | NYC taxi trip data |
| 2 | Spark SQL & aggregations | Movie ratings analysis |
| 3 | Spark + PostgreSQL/Parquet I/O | Real estate transactions |
| 4 | Spark performance (partitions, caching, broadcast joins) | Ad click attribution |
| 5 | **SoundStream:** Batch process historical streaming data, artist royalty calculations |

### Week 8: Airflow (Orchestration)
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Airflow setup, first DAG | File processing pipeline |
| 2 | Task dependencies, XComs, parallel execution | Multi-source data merge |
| 3 | Error handling, retries, alerting | Payment processing pipeline |
| 4 | Scheduling, backfills, sensors | Weather data collection |
| 5 | **SoundStream:** Orchestrate -- DAGs for daily ETL, weekly reports, dbt runs, quality checks |

---

## Phase 3: Warehouse + Visualization (Weeks 9-12)

### Week 9: Star Schema Design
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Fact vs dimension tables, surrogate keys | Retail point-of-sale |
| 2 | SCD Type 1 & Type 2 | Customer address tracking |
| 3 | ETL from source to warehouse | Hospital admissions |
| 4 | OLAP queries & rollups | Advertising campaign performance |
| 5 | **SoundStream:** Build warehouse -- dim_artist, dim_track, dim_user, dim_date, fact_streams, fact_revenue |

### Week 10: Data Quality + Monitoring
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Data quality checks (completeness, freshness, accuracy) | Financial transaction audit |
| 2 | Great Expectations or custom validation framework | Insurance claims processing |
| 3 | Logging, metrics, health endpoints | API monitoring dashboard |
| 4 | Alerting patterns (pipeline failure detection) | Supply chain tracking |
| 5 | **SoundStream:** Quality layer -- automated checks, alerting, data quality dashboard |

### Week 11: Streamlit Dashboards
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Streamlit basics (layout, charts, tables) | COVID data explorer |
| 2 | Database-connected dashboards | Sales performance tracker |
| 3 | Interactive filters & drill-downs | Student grade analytics |
| 4 | Dashboard deployment & caching | Real-time crypto tracker |
| 5 | **SoundStream:** Interactive dashboard -- trends, top artists, revenue, user engagement |

### Week 12: CI/CD + Code Quality
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | GitHub Actions basics | Open source library |
| 2 | Automated testing pipelines | Microservice test suite |
| 3 | Linting, type hints, pre-commit hooks | Legacy code cleanup |
| 4 | Docker build & deployment automation | Container registry pipeline |
| 5 | **SoundStream:** CI/CD -- automated tests, linting, dbt checks, Docker builds on push |

---

## Phase 4: Cloud + Capstone (Weeks 13-16)

### Week 13: Cloud Basics (AWS/GCP)
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Cloud concepts, S3/GCS buckets | Document storage system |
| 2 | Managed databases (RDS/Cloud SQL) | Multi-region user data |
| 3 | Serverless functions (Lambda/Cloud Functions) | Webhook processor |
| 4 | IAM, secrets management, security basics | Secure API gateway |
| 5 | **SoundStream:** Migrate data storage to cloud, connect pipelines to cloud resources |

### Week 14: Cloud Deployment
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | Infrastructure as Code (Terraform basics) | VPC + subnet setup |
| 2 | Container registries & cloud deployment | Microservice deployment |
| 3 | Cloud monitoring & cost management | Budget alert system |
| 4 | Environment management (dev/staging/prod) | Feature flag service |
| 5 | **SoundStream:** Deploy to cloud -- database, API, Airflow running in cloud |

### Week 15: Integration + Polish
| Session | Topic | Domain |
|---------|-------|--------|
| 1 | API authentication & rate limiting | Public API gateway |
| 2 | Caching strategies (Redis basics) | Session management |
| 3 | Async processing patterns | Email notification system |
| 4 | Documentation & runbooks | Operations handbook |
| 5 | **SoundStream:** End-to-end integration -- ingest, transform, warehouse, API, dashboard in cloud |

### Week 16: Capstone
| Session | Topic |
|---------|-------|
| 1-5 | Build a complete mini data platform from scratch in one week. New domain (e-commerce). Apply everything learned. This is the final exam. |

---

## Session Structure Reference

### Sessions 1-4 (~45-60 min)
1. **Setup** (2 min) -- Create branch, open files
2. **Follow-Along** (15-20 min) -- LLM guides, outputs code, student runs it
3. **Independent Addition** (15-20 min) -- Requirements only, no code from LLM
4. **Code Review** (5 min) -- Student runs code, LLM reviews output
5. **Quiz** (10 min) -- 10 questions, 8/10 to pass

### Session 5 (~45-60 min)
1. **Setup** (2 min) -- Checkout cumulative branch
2. **Brief** (5 min) -- What to build this week
3. **Build** (30-40 min) -- Requirements and acceptance criteria only
4. **Review** (10 min) -- Verify acceptance criteria pass
5. **Wrap-up** (3 min) -- Update progress, commit

## Lesson File Status
- [x] Phase 1 (Weeks 1-4): Written
- [ ] Phase 2 (Weeks 5-8): Write when approaching Week 5
- [ ] Phase 3 (Weeks 9-12): Write when approaching Week 9
- [ ] Phase 4 (Weeks 13-16): Write when approaching Week 13
