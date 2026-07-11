# Library AI Agent — IBM watsonx.ai Studio

An intelligent AI-powered library assistant that helps students find, discover, and access learning resources using **IBM watsonx.ai Studio**, **IBM Watson NLU**, and **IBM Cloud** services.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                  Student Web Interface                   │
│          (Chat · Catalogue · Recommendations)            │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/REST
┌────────────────────────▼────────────────────────────────┐
│                  Flask REST API Layer                     │
│    /api/agent  /api/books  /api/students  /api/admin     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│               Library AI Agent (Orchestrator)            │
│                                                          │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────┐  │
│  │ NLP Processor│  │ Recommendation  │  │  Library   │  │
│  │ (Watson NLU) │  │     Engine      │  │ Repository │  │
│  └──────┬───────┘  └────────┬────────┘  └─────┬──────┘  │
│         │                   │                 │          │
│  ┌──────▼───────────────────▼─────────────────▼──────┐  │
│  │              IBM watsonx.ai Client                 │  │
│  │         (Granite Foundation Models)                │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  IBM Cloud Data Layer                     │
│   IBM Cloud PostgreSQL   │  IBM Cloudant NoSQL           │
│   (Books, Loans,         │  (Student Profiles,           │
│    Reservations)         │   Preferences)                │
└─────────────────────────────────────────────────────────┘
```

## IBM Cloud Services Used

| Service | Purpose |
|---------|---------|
| **IBM watsonx.ai Studio** | Foundation model (Granite) for natural language generation, recommendations, availability responses |
| **IBM Watson NLU** | Query intent classification, entity extraction, keyword analysis |
| **IBM Cloud Databases (PostgreSQL)** | Books, loans, reservations, interaction logs |
| **IBM Cloudant** | Student profiles, reading history, preferences (NoSQL) |
| **IBM Cloud Functions** | Overdue notifications, waitlist processing, demand score recalculation |
| **IBM Code Engine** | Containerised deployment of the agent API |

---

## Features

- 🤖 **Natural Language Understanding** — parses free-text queries into intents and entities
- 📚 **Personalised Recommendations** — blends query relevance, student profile, and popularity
- ✅ **Real-time Availability** — shows copies available, location, and waitlist count
- 📌 **Reservations & Waitlist** — create holds, track queue position
- 🔄 **Loan Renewal** — extend loans up to the configured limit
- 📊 **Analytics Dashboard** — live stats, top books, service health
- 🔄 **Graceful Fallback** — runs fully offline in demo mode with SQLite + rule-based AI

---

## Quick Start (Demo Mode)

```bash
# 1. Clone and enter the project
cd library-agent

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template (demo mode works without IBM credentials)
cp .env.example .env

# 5. Start the server
python main.py
```

Open **http://localhost:5000** in your browser.

---

## Production Setup (IBM Cloud)

```bash
# 1. Create an IBM Cloud account (Lite tier is free)
#    https://cloud.ibm.com/registration

# 2. Provision required services:
#    - watsonx.ai Studio  → https://cloud.ibm.com/catalog/services/watson-studio
#    - Watson NLU         → https://cloud.ibm.com/catalog/services/natural-language-understanding
#    - Databases for PostgreSQL → https://cloud.ibm.com/catalog/services/databases-for-postgresql

# 3. Fill in .env with your service credentials
cp .env.example .env
# Edit .env: set DEMO_MODE=false and fill in API keys / DB host

# 4. Run with gunicorn
pip install gunicorn
gunicorn "wsgi:create_app()" --config gunicorn.conf.py

# OR deploy to IBM Code Engine:
ibmcloud ce application create \
  --name library-ai-agent \
  --image us.icr.io/your-namespace/library-agent:latest \
  --env-from-secret library-agent-secrets \
  --port 5000
```

---

## API Reference

### Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/agent/query` | Process a natural language query |
| `POST` | `/api/agent/feedback` | Submit rating for an interaction |
| `GET`  | `/api/agent/trending` | Get trending books |

### Books
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/books/search` | Search catalogue (`?q=&subject=&available_only=`) |
| `GET`  | `/api/books/{id}` | Get book details + similar books |
| `GET`  | `/api/books/{id}/availability` | Real-time availability check |
| `POST` | `/api/books/{id}/reserve` | Reserve a book |

### Students
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/students/{id}/profile` | Full profile + active loans |
| `GET`  | `/api/students/{id}/loans` | Active loans |
| `POST` | `/api/students/{id}/loans/{loan_id}/renew` | Renew a loan |
| `GET`  | `/api/students/{id}/recommendations` | Personalised recommendations |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/admin/stats` | Library statistics |
| `GET`  | `/api/admin/interactions` | Recent AI agent interactions |
| `GET`  | `/api/health` | Service health check |

---

## Project Structure

```
library-agent/
├── main.py                    # Entry point
├── wsgi.py                    # Gunicorn WSGI shim
├── gunicorn.conf.py           # Production server config
├── Dockerfile                 # Container image
├── Procfile                   # Cloud Foundry / Heroku
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
│
├── config/
│   ├── __init__.py
│   └── settings.py            # All config (watsonx, NLU, DB, app)
│
├── database/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy ORM models
│   ├── connection.py          # Engine, session, health check
│   └── seed.py                # Demo data (15 books, 3 students)
│
├── ai_engine/
│   ├── __init__.py
│   ├── agent.py               # Core orchestrator
│   ├── nlp_processor.py       # Intent/entity extraction (Watson NLU / rules)
│   ├── watsonx_client.py      # watsonx.ai foundation model client
│   ├── recommendation_engine.py # 4-dimension scoring recommender
│   └── library_repository.py  # All DB queries
│
├── api/
│   ├── __init__.py
│   ├── app.py                 # Flask app factory
│   └── routes/
│       ├── agent_routes.py    # /api/agent/*
│       ├── books_routes.py    # /api/books/*
│       ├── student_routes.py  # /api/students/*
│       └── admin_routes.py    # /api/admin/*
│
└── frontend/
    └── index.html             # Single-page web application
```

---

## IBM watsonx.ai Models Used

| Model | Use Case |
|-------|---------|
| `ibm/granite-13b-instruct-v2` | Recommendation narratives, general responses |
| `ibm/granite-13b-chat-v2` | Conversational chat, multi-turn dialogue |
| `ibm/slate-125m-english-rtrvr` | Semantic embedding for similarity search |

---

## License

MIT — free to use for educational and research purposes.
