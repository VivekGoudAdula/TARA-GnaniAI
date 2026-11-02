# Gnani AI API Notes
_Last updated: 2026-11-02. All items marked (from docs) are sourced from docs.gnani.ai.
Items marked (verified by real call) were run against the live API._

---

## Base URL & Auth

| Item | Value | Source |
|---|---|---|
| Base URL | `https://api.vachana.ai` | from docs |
| Auth header | `X-API-Key-ID: <key>` (every request) | from docs |
| API key source | env var `GNANI_API_KEY` – never logged | project rule |

---

## STT – Prisma v3.0

### Endpoint
```
POST https://api.vachana.ai/stt/v3
Content-Type: multipart/form-data
```
_(from docs)_

### Request fields
| Field | Type | Required | Notes |
|---|---|---|---|
| `audio_file` | file | YES | WAV, MP3, OGG, FLAC, AAC, M4A (from docs) |
| `model` | string | YES | `prisma-v3.0` for multilingual + auto-detect (from docs) |
| `language_code` | string | YES | `indic-auto`, `hi-IN`, `te-IN`, `en-IN`, etc. (from docs) |
| `format` | string | no | `transcribe` (optional, from docs) |

### Audio limits
- **Max duration**: 30 seconds (from docs) – we auto-stop at 25s in frontend
- **Sample rates**: 8 kHz – 44.1 kHz (from docs)
- **Formats**: WAV, MP3, OGG, FLAC, AAC, M4A (from docs)

### Response shape (200 OK)
```json
{
  "success": true,
  "request_id": "req-xxxxxxxx",
  "transcript": "Hello, this is a test.",
  "model": "prisma-v3.0",
  "detected_language_code": "en-IN"
}
```
_(from docs)_

### Language codes supported
| Language | Code |
|---|---|
| Auto-detect (Indic) | `indic-auto` |
| Hindi | `hi-IN` |
| English (Indian) | `en-IN` |
| Telugu | `te-IN` |
| Tamil | `ta-IN` |
| Kannada | `kn-IN` |
| Malayalam | `ml-IN` |
| Marathi | `mr-IN` |
| Punjabi | `pa-IN` |
| Bengali | `bn-IN` |
| Gujarati | `gu-IN` |

_(from docs)_

---

## TTS – Timbre v2.5

### Endpoints available
| Mode | URL | Notes |
|---|---|---|
| REST (batch) | `POST https://api.vachana.ai/api/v1/tts/inference` | Full audio in one response (from docs) |
| SSE streaming | `POST https://api.vachana.ai/api/v1/tts/sse` | Chunked audio via Server-Sent Events (from docs) |
| WebSocket realtime | `WSS wss://api.vachana.ai/api/v1/tts` | Lowest latency (from docs) |

**Phase 1 uses the REST endpoint only.**

### Request body (JSON)
```json
{
  "text": "Hello!",
  "model": "timbre-v2.5",
  "voice": "Nalini",
  "language": "en-IN",
  "speed": 1.0,
  "audio_config": {
    "sample_rate": 48000,
    "encoding": "linear_pcm",
    "container": "wav"
  }
}
```
_(from docs)_

### Request fields
| Field | Type | Required | Notes |
|---|---|---|---|
| `text` | string | YES | Text to synthesise (from docs) |
| `model` | string | YES | `timbre-v2.5` (from docs) |
| `voice` | string | YES | Voice name from catalog (from docs) |
| `language` | string | YES | BCP-47 language code (from docs) |
| `speed` | float | no | Speech rate multiplier, default `1.0` (from docs) |
| `audio_config` | object | no | See sub-fields below (from docs) |

### audio_config fields
| Field | Default | Options |
|---|---|---|
| `sample_rate` | `48000` | `8000`, `16000`, `22050`, `24000`, `44100`, `48000` (from docs) |
| `container` | `wav` | `wav`, `raw`, `mp3`, `ogg`, `mulaw`, `alaw` (from docs) |
| `encoding` | `linear_pcm` | `linear_pcm`, `pcm_s16le`, `pcm_mulaw`, `pcm_alaw`, `oggopus` (from docs) |
| `num_channels` | `1` | Mono = 1 (from docs) |
| `sample_width` | `2` | 16-bit = 2 (from docs) |
| `bitrate` | `128k` | `32k`, `64k`, `96k`, `128k`, `192k` – MP3 only (from docs) |

### Response
- **200 OK**: Raw binary audio bytes in the requested format (from docs)
- `Content-Type` header matches container (e.g. `audio/wav`, `audio/mpeg`) (from docs)

### Supported languages (Timbre v2.5)
Same 10 Indian languages + English as STT above. (from docs)

### Voice catalog (Timbre v2.5)
Timbre v2.5 has **42 voices** (from docs). Key voices used in Phase 1:

| Voice | Notes |
|---|---|
| `Nalini` | Female; default in our code; works across languages (from docs) |
| `Kaveri` | Female, Confident/Bright (from docs) |
| `Deepak` | Male, Grounded/Conversational (from docs) |

> **Note**: Voice names are case-sensitive. Voices are model-specific – `timbre-v2.5` voices cannot be used with `timbre-v3.0`. (from docs)

---

## Error Reference

| HTTP Code | error_code | Meaning | Action |
|---|---|---|---|
| `401` | `MISSING_API_KEY` | Header absent or empty (from docs) | Add `X-API-Key-ID` |
| `401` | `INVALID_API_KEY` | Key invalid/revoked (from docs) | Check key |
| `402` | — | Insufficient credits (from docs) | Top up, no retry |
| `403` | `SCOPE_NOT_ALLOWED` | Key lacks scope for this API (from docs) | Check key permissions |
| `429` | `RATE_LIMITED` | Concurrent request limit hit (from docs) | Exponential backoff |
| `5xx` | — | Transient server error | Retry once |

Error response shape:
```json
{
  "detail": {
    "error_code": "RATE_LIMITED",
    "message": "Only 1 active request is allowed at a time...",
    "status_code": 429
  }
}
```
_(from docs)_

---

## Live Call Results – Phase 1

> _Fill in after running smoke_tts.py and smoke_stt.py_

### TTS latencies (verified by real call)

| Language | Voice | Text length | Latency (ms) | File size | Status |
|---|---|---|---|---|---|
| en-IN | Nalini | ~65 chars | TBD | TBD | pending |
| hi-IN | Nalini | ~45 chars | TBD | TBD | pending |
| te-IN | Nalini | ~42 chars | TBD | TBD | pending |

### STT latencies & indic-auto detection (verified by real call)

| Audio | Language sent | Detected language | Transcript | Latency (ms) | Status |
|---|---|---|---|---|---|
| en.wav (from TTS) | indic-auto | TBD | TBD | TBD | pending |
| hi.wav (from TTS) | indic-auto | TBD | TBD | TBD | pending |
| te.wav (from TTS) | indic-auto | TBD | TBD | TBD | pending |

### What did NOT work / caveats

- TBD after live runs. Will update here.

---

## Realtime / WebSocket (not used in Phase 1)

### STT WebSocket
- URL: `WSS wss://api.vachana.ai/stt/v3/stream` (from docs – to be verified)
- Sends raw audio frames; receives partial and final transcripts
- Phase 3+ will implement for live call agent

### TTS WebSocket
- URL: `WSS wss://api.vachana.ai/api/v1/tts` (from docs)
- Lowest latency; suitable for real-time agent responses
- Phase 3+ will implement

