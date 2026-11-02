# TARA on Gnani: Project Context and Rules

## What we are building
TARA (Targeted Acquisition & Reach Agent): a voice-first outreach platform for
banks/lenders in India. It scores customers and leads for product fit, lets an
employee build a campaign from the scored audience, and a voice AI agent talks to
the selected people in Hindi, Telugu or English. Call outcomes flow back to a dashboard.

Built for the Gnani AI "Great Indian AI Internship Challenge".
Deadline: Nov 10, 2026, 11:59 PM IST. Everything must be built on Gnani AI models/APIs.

## Hard requirements from the challenge
- Voice stack MUST use Gnani: Prisma v3.0 (STT) and Timbre v2.5 (TTS).
- The Gnani Agent Builder is OUT OF SCOPE. Use only the API platform.
- Synthetic data ONLY. No real phone numbers, Aadhaar, PAN, account numbers, or recorded calls.
- Must be a working application, demonstrable in a public video.
- Never claim anything works unless it was actually run and verified.

## Gnani API facts (verified from docs.gnani.ai)
- Base URL: https://api.vachana.ai
- Auth header on every request: X-API-Key-ID: <key>   (key from env var GNANI_API_KEY)
- STT REST: POST /stt/v3, multipart form: audio_file, model=prisma-v3.0,
  language_code=indic-auto (auto detect) or e.g. hi-IN, te-IN, en-IN.
  Audio max 30 seconds. Formats: WAV, MP3, OGG, FLAC, AAC, M4A. 8-44.1 kHz.
  Response includes: success, request_id, transcript, model, detected_language_code.
- TTS: Timbre v2.5 (REST, SSE streaming, WebSocket realtime). STT also has WebSocket realtime.
- ALWAYS read https://docs.gnani.ai/llms.txt and the relevant doc pages BEFORE
  writing any Gnani call. NEVER guess an endpoint, parameter, voice name, or
  response field. If the docs don't say, test it with a real call and record the finding
  in docs/GNANI_NOTES.md.

## Architecture (non-negotiable)
CSV import -> Scoring + product matching -> Campaign builder -> Voice configuration
 -> Communication API -> Provider adapter (Gnani voice) -> Voice session
Voice session events -> outcome/transcript/extractions -> Interaction History

Rules:
1. Campaign module NEVER imports provider code. Communication module NEVER imports
   campaign code. They talk only through the Communication API contract.
2. All Gnani-specific field names, URLs and parsing live ONLY in backend/providers/gnani_*.py
3. Multi-tenant: tenant_id comes ONLY from the authenticated JWT. Never accept it from the
   frontend. Cross-tenant access returns 404.
4. Scoring NEVER deletes or hides records. Eligibility is a FILTER, not a deletion.
5. One lead/customer maps to MANY products (separate match rows with score + explanation).
6. Compliance is enforced at dispatch in code, not in prompts: consent required,
   DND flag, calling window (09:00-21:00 IST default), contact-frequency cap,
   duplicate in-flight check, TEST_MODE allowlist, audit log entry for every attempt.
7. No product, prompt, or message content is hardcoded in provider/communication code.
   It comes from stored campaign configuration.
8. The voice/LLM stack receives only: first name, bank name, product, language, prompt text.
   Never income, scores, or other sensitive fields.

## Tech stack
- Backend: Python 3.11+, FastAPI, Pydantic, SQLite via SQLModel (single file DB, easy to run
  for judges), pytest
- Frontend: React + Vite + Tailwind. Clean, light, professional fintech look. No wave/animated backgrounds.
- LLM for the agent: provider-pluggable interface; default Groq (env GROQ_API_KEY).
  Evon (Gnani open weights) is optional and NOT required.
- Config via .env (never commit). Provide .env.example.

## Engineering rules
- Inspect the repo before editing. Reuse what exists. No duplicate logic.
- Keep every file under 250 lines. Few folders. No speculative abstractions.
- Small, readable code with type hints and short docstrings.
- Write tests for every rule in "Architecture". Run them. Show results.
- Commit at the end of each phase with a clear message.
- Do not build features from future phases. Stop at the phase boundary.
- If a requirement is ambiguous, pick the simplest option, state the assumption in
  the report, and continue. Only stop to ask if you are blocked.

## Honesty rules for UI, README and demo
- Say "test calls to verified testers", never "conversion".
- Scoring models are trained on synthetic data: label this wherever metrics appear.
- WhatsApp/SMS/Email are NOT built. Do not show them as working. Mark as "roadmap".

## Required report at the end of every phase
1. What was built  2. Files created/changed  3. How to run it
4. Tests run + actual results  5. What is proven vs not proven
6. Deviations/assumptions  7. Suggested next phase notes
Do not claim something works unless you ran it.