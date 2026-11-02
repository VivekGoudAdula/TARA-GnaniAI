# TARA — Targeted Acquisition & Reach Agent

> Voice-first outreach platform for banks and lenders in India.  
> Built for the **Gnani AI "Great Indian AI Internship Challenge"**.

## Core Capabilities
- Multi-tenant banking platform with strict tenant isolation.
- Campaign builder with audience preview, snapshot immutability, and versioned voice configs.
- Explanatory product fit scoring (trained on synthetic data).
- Voice AI agent calling customers in **Hindi, Telugu, or English** with sub-3s turn latency.
- Powered by **Gnani Prisma v3.0** (STT), **Timbre v2.5** (TTS), and **Groq** LLMs.

---

## Database Setup (MongoDB)

TARA requires MongoDB for multi-tenant data, catalog management, and voice session persistence.
The application starts with only `.env` filled in.

### Option A: Local MongoDB (Installed Service)
If MongoDB is installed locally on your system, default `MONGO_URI=mongodb://127.0.0.1:27017` in `.env` connects immediately.

### Option B: Docker Compose
Run a lightweight MongoDB container:
```bash
docker compose up -d
```
Then configure in `.env`:
```env
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB_NAME=tara_gnani
```

### Option C: MongoDB Atlas (Cloud)
Paste your Atlas connection string directly into `.env`:
```env
MONGO_URI=mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=tara_gnani
```

---

## Quickstart

### 1. Backend
```bash
cd backend
python -m venv .venv
# Activate:
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -r requirements.txt
cp ../.env.example ../.env   # fill in GNANI_API_KEY, GROQ_API_KEY
python scripts/seed_data.py  # seeds Test Bank & Other Bank with synthetic data
uvicorn app.main:app --reload --port 8000
```

### 2. Demo Credentials (Synthetic Data Only)
The seed script initializes two isolated workspaces:
- **Test Bank**: `admin@testbank.com` / `password123` (4 products, 200 customers, 200 leads)
- **Other Bank**: `admin@otherbank.com` / `password123` (1 product, 10 customers)
> *All accounts and profiles are demo credentials operating strictly on synthetic data.*

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 4. Run Tests
```bash
python -m pytest backend/tests -v -m "not live"
```
