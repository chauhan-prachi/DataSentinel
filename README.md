<div align="center">

# 🛡️ DataSentinel

### Data Reliability & Quality Monitoring Platform

<p>
  <strong>
    A Django-based data reliability platform for ingesting, validating,
    monitoring, and diagnosing data pipelines.
  </strong>
</p>

<br>

<a href="https://github.com/chauhan-prachi/DataSentinel">
  <img src="https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github" alt="GitHub Repository">
</a>

<br><br>


</div>

---

## 📌 Overview

**DataSentinel** is a data reliability platform built with **Python, Django, PostgreSQL, and Pandas**.

It processes datasets through an end-to-end reliability workflow:

```text
Data Source
     ↓
Ingestion
     ↓
Profiling & Schema Detection
     ↓
Quality Checks
     ↓
Schema Drift + Anomaly Detection
     ↓
Pipeline Run
     ↓
Reliability Score
     ↓
RCA + Alerts
     ↓
Observability Dashboard
```

The project focuses on detecting data problems early and turning raw failures into **structured, explainable reliability signals**.

---

## ✨ Key Features

| Feature                        | Description                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------ |
| 📥 **Multi-Format Ingestion**  | CSV, JSON, Excel, Parquet, TSV, XML, PostgreSQL and remote CSV                 |
| 🔍 **Dataset Profiling**       | Row counts, data types, nulls, uniqueness and duplicates                       |
| 🧠 **Schema Detection**        | Identifies identifiers, emails, numerics, dates, booleans and categorical data |
| ⚙️ **Automatic Rules**         | Suggests quality checks based on detected column characteristics               |
| ✅ **Data Quality Engine**      | NOT NULL, UNIQUE, EMAIL, DATE, NUMERIC, RANGE and DUPLICATE checks             |
| 🔄 **Schema Drift**            | Detects added, removed and changed columns/data types                          |
| 📊 **Anomaly Detection**       | Monitors row count, null rates and numeric mean changes                        |
| 🚀 **Pipeline Execution**      | Orchestrates ingestion, validation, detection and persistence                  |
| 📈 **Reliability Scoring**     | Combines quality, schema, anomaly and pipeline signals                         |
| 🔎 **Automated RCA**           | Generates structured findings, evidence, impact and recommendations            |
| 🚨 **Alerts**                  | Detects quality failures, anomalies, schema drift and pipeline failures        |
| 📊 **Observability Dashboard** | Tracks reliability, quality trends, incidents and pipeline history             |

---

## 🧪 Data Quality Engine

Current validation checks:

```text
NOT_NULL
UNIQUE
VALID_EMAIL
VALID_DATE
NUMERIC_VALIDITY
RANGE
DUPLICATE
```

Each check produces structured results:

```text
Check
├── PASS / FAIL
├── Rows Checked
├── Rows Passed
├── Rows Failed
└── Diagnostic Details
```

---

## 📊 Reliability Engine

DataSentinel calculates pipeline reliability using multiple signals:

```text
Quality Score      → 50%
Schema Stability   → 20%
Anomaly Health     → 20%
Pipeline Status    → 10%
```

The resulting score is converted into a reliability grade:

```text
A → 90+
B → 80–89
C → 70–79
D → 60–69
F → <60
```

The scoring model is intentionally **transparent and deterministic** in v1.

---

## 🔎 Automated Root Cause Analysis

When reliability problems occur, DataSentinel analyzes signals from:

* Quality failures
* Schema drift
* Data anomalies
* Pipeline failures

It produces structured findings containing:

```text
Severity
Root Cause
Evidence
Impact
Recommendation
```

The current RCA engine is **rule-based**, providing a foundation for future ML/LLM-assisted investigation.

---

## 🏗️ Architecture

```text
                         DataSentinel
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
          Ingestion       Profiling       PostgreSQL
              │               │
              └───────┬───────┘
                      ▼
              Quality Engine
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Quality     Schema      Anomaly
       Checks      Drift      Detection
          │           │           │
          └───────────┼───────────┘
                      ▼
                 Pipeline Run
                      │
              ┌───────┼───────┐
              ▼       ▼       ▼
           Score     RCA    Alerts
              │
              ▼
         Dashboard
```

---

## 🛠️ Technology Stack

| Category            | Technologies                    |
| ------------------- | ------------------------------- |
| **Backend**         | Python, Django                  |
| **Database**        | PostgreSQL, psycopg             |
| **Data Processing** | Pandas, NumPy, PyArrow          |
| **File Processing** | OpenPyXL, lxml                  |
| **Frontend**        | HTML, CSS, JavaScript, Chart.js |
| **Server**          | Gunicorn                        |
| **Static Files**    | WhiteNoise                      |
| **Development**     | Git, GitHub, VS Code            |

---

## 📁 Project Structure

```text
DataSentinel/
│
├── accounts/
├── config/
│
├── core/
│   ├── models.py
│   ├── views.py
│   │
│   └── services/
│       ├── pipeline.py
│       ├── ingestion/
│       ├── quality/
│       ├── schema/
│       ├── anomaly/
│       ├── reliability/
│       ├── rca/
│       └── alerts/
│
├── templates/
├── static/
├── data/
├── manage.py
├── requirements.txt
└── README.md
```

---

## ⚙️ Run Locally

```powershell
git clone https://github.com/chauhan-prachi/DataSentinel.git
cd DataSentinel

python -m venv venv
venv\Scripts\Activate.ps1

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver --noreload
```

Open:

```text
http://127.0.0.1:8000/
```

Configure database and secret settings through environment variables. Never commit `.env` or credentials.

---

## ✅ Verification

```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

Current project verification:

```text
Django System Check       ✓
Migration Check           ✓
Project Verification      ✓
```

---

## 🚀 Roadmap

* [ ] Historical anomaly baselines
* [ ] Semantic data drift detection
* [ ] Advanced statistical/ML anomaly detection
* [ ] Incident correlation
* [ ] Data lineage
* [ ] Airflow orchestration
* [ ] PySpark large-scale processing
* [ ] Cloud data sources
* [ ] ML/LLM-assisted RCA
* [ ] Production-grade alert routing

---

## 👩‍💻 About

**Prachi Chauhan**

MCA | Python | SQL | Data Engineering | Backend | Data Reliability

DataSentinel is being developed as a practical exploration of **data engineering, data quality, pipeline observability, and reliable data systems**.

<br>

<a href="https://github.com/chauhan-prachi">
  <img src="https://img.shields.io/badge/GitHub-Profile-181717?style=for-the-badge&logo=github" alt="GitHub">
</a>

 

<a href="https://www.linkedin.com/in/prachi-chauhan-79a446226">
  <img src="https://img.shields.io/badge/LinkedIn-Profile-0A66C2?style=for-the-badge&logo=linkedin" alt="LinkedIn">
</a>

</div>
