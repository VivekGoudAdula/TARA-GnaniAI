# TARA Architecture

## Overview

```
CSV import → Scoring + product matching → Campaign builder → Voice configuration
         → Communication API → Provider adapter (Gnani voice) → Voice session
Voice session events → outcome / transcript / extractions → Interaction History
```

## Module boundaries (non-negotiable)

| Module | Can import | Cannot import |
|---|---|---|
| `campaign/` | `scoring/`, `providers/` via Communication API | `providers/` directly |
| `communication/` | `providers/` | `campaign/` |
| `providers/gnani_*.py` | External Gnani API | Any app business logic |

**Rule**: All Gnani-specific field names, URLs, and response parsing live ONLY in
`backend/providers/gnani_*.py`. No other file references Gnani field names.

## Phase 1 – Scaffold

```
tara-gnani/
  backend/
    app/
      main.py           FastAPI app factory; includes dev router when DEV_ENDPOINTS=true
      routers/
        health.py       GET /api/health
        dev.py          POST /api/dev/stt, POST /api/dev/tts (dev-only)
    providers/
      gnani_client.py   GnaniClient: stt_transcribe(), tts_synthesize()
    scripts/
      smoke_stt.py      CLI: transcribe an audio file
      smoke_tts.py      CLI: synthesise EN/HI/TE, save to scripts/out/
      out/              .gitignored output directory
    tests/
      test_gnani_client.py  Unit tests (mocked HTTP) + live tests (skipped)
    requirements.txt
    pyproject.toml
  frontend/
    src/
      components/VoiceCheck.jsx   Mic recorder + TTS player
      App.jsx
    index.html, vite.config.js, tailwind.config.js, package.json
  docs/
    GNANI_NOTES.md      All Gnani API facts + measured latencies
    ARCHITECTURE.md     This file
  .env.example
  .gitignore
  README.md
```

## Security rules
- `tenant_id` comes ONLY from authenticated JWT (Phase 2+). Never from frontend.
- Cross-tenant access returns 404.
- API key never logged.
- Dev endpoints guarded by `DEV_ENDPOINTS=true` env flag.

## Data rules
- Scoring NEVER deletes/hides records; eligibility is a filter.
- One lead → many product match rows (score + explanation per product).
- Compliance enforced at dispatch in code (not prompts): consent, DND, calling window, frequency cap, duplicate check, audit log.
- Voice/LLM receives only: first name, bank name, product, language, prompt text. Never income, scores, or sensitive fields.

## Future phases
- **Phase 2**: Auth (JWT), tenant model, SQLite schema, CSV import
- **Phase 3**: Scoring engine (synthetic data, labelled)
- **Phase 4**: Campaign builder UI
- **Phase 5**: Voice agent (Groq LLM + Gnani STT/TTS real-time loop)
- **Phase 6**: Dashboard + interaction history
- **Phase 7**: Polish, compliance hardening, demo video

