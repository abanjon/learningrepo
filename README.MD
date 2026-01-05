# Integrated Data Engineering Learning Plan

![Python](https://img.shields.io/badge/Python-Advanced-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Advanced-blue)
![Spark](https://img.shields.io/badge/Apache%20Spark-Intermediate-orange)
![Airflow](https://img.shields.io/badge/Airflow-Intermediate-orange)


---

## Overview

This repository documents an **intentional, structured upskilling project** focused on modern **Data Engineering fundamentals and production patterns**.

Rather than isolated tutorials, this project follows a **single evolving system** that grows in complexity over 12 weeks — mirroring how real-world data platforms are built, scaled, and operated.

**Goal:**
Demonstrate hands-on proficiency across the full data engineering lifecycle:
- Data ingestion
- Validation & transformation
- Relational modeling
- Distributed processing
- Orchestration
- Testing, performance tuning, and production readiness

---

## Core Philosophy

> **Learn tools together, not in isolation.**

Each week builds directly on prior work. Concepts like Python OOP, SQL modeling, Spark, and Airflow are applied **together**, reinforcing how they interact in real systems.

This project emphasizes:
- Production-minded design
- Explicit data modeling decisions
- Performance and scalability tradeoffs
- Observability, testing, and failure handling

---

## The Project

**What’s being built:**
A **production-style CRM data platform** that evolves through three phases:

### Phase 1 — Foundation (Weeks 1–4)
Local development & core pipeline
- Python + PostgreSQL ETL
- Schema design & validation
- OOP & data structures
- Testing with `pytest`
- Dockerized local environment

### Phase 2 — Scale & Optimize (Weeks 5–8)
Distributed processing & analytics
- Apache Spark (batch + streaming)
- Performance optimization
- Spark ↔ PostgreSQL integration
- Airflow orchestration of Spark jobs

### Phase 3 — Production Patterns (Weeks 9–12)
*(Planned / in progress)*
- Data warehouse modeling (star schema, SCD Type 2)
- Incremental loads & materialized views
- Backfills, retries, monitoring
- Production-style orchestration & scheduling

---

## Tech Stack

- **Languages:** Python, SQL
- **Databases:** PostgreSQL
- **Processing:** Pandas, PySpark
- **Orchestration:** Apache Airflow
- **Infrastructure:** Docker
- **Testing:** pytest
- **Data Formats:** CSV, JSON, Parquet

---

## Why This Exists

This repository exists as:
	•	A portfolio-grade upskilling project
	•	A learning log for advanced data engineering concepts
	•	Evidence of hands-on, production-oriented thinking

It is not a course solution, tutorial dump, or copy-paste demo.
