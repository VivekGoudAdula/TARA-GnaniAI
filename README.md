# TARA — Targeted Acquisition & Reach Agent

> Voice-first outreach platform for banks/lenders in India.  
> Built for the **Gnani AI "Great Indian AI Internship Challenge"** (deadline: Nov 10 2026).

## What it does
- Scores customers/leads for product fit (synthetic data, clearly labelled)
- Campaign builder selects the audience
- Voice AI agent calls selected people in **Hindi, Telugu or English**
- Uses **Gnani Prisma v3.0** (STT) and **Gnani Timbre v2.5** (TTS)

## Phase 1 — Scaffold + Voice Verification ✅

### Run the backend
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp ../.env.example ../.env   # fill in GNANI_API_KEY
uvicorn app.main:app --reload --port 8000
```

### Run the frontend
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### Required .env values for Phase 1
| Variable | Required | Description |
|---|---|---|
| `GNANI_API_KEY` | **YES** | From https://platform.gnani.ai |
| `DEV_ENDPOINTS` | YES (set `true`) | Enables /api/dev/stt and /api/dev/tts |

### Run smoke tests
```bash
cd backend
# Generate TTS audio first, then round-trip to STT
python scripts/smoke_tts.py            # saves out/en.wav, out/hi.wav, out/te.wav
python scripts/smoke_stt.py out/en.wav # transcribe English
python scripts/smoke_stt.py out/hi.wav # transcribe Hindi
python scripts/smoke_stt.py out/te.wav # transcribe Telugu
```

### Run unit tests
```bash
cd backend
pytest tests/ -v
```

## Architecture
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Gnani API notes
See [docs/GNANI_NOTES.md](docs/GNANI_NOTES.md)

