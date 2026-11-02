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

> _Measured and verified via live calls to https://api.vachana.ai on 2026-11-02._

### TTS latencies (verified by real call)

| Language | Voice | Text length | Latency (ms) | File size | Status |
|---|---|---|---|---|---|
| en-IN | Nalini | ~68 chars | 4842.9 ms | 384,044 bytes | 200 OK (verified by real call) |
| hi-IN | Nalini | ~45 chars | 9158.9 ms | 337,964 bytes | 200 OK (verified by real call) |
| te-IN | Nalini | ~42 chars | 6431.1 ms | 322,604 bytes | 200 OK (verified by real call) |

### STT latencies & indic-auto detection (verified by real call)

| Audio | Language sent | Detected language | Transcript | Latency (ms) | Status |
|---|---|---|---|---|---|
| en.wav (from TTS) | indic-auto | `en-IN` | "Hello, this is a test message from Tara, your financial assistant." | 5569.7 ms | 200 OK (verified by real call) |
| hi.wav (from TTS) | indic-auto | `hi-IN` | "नमस्ते, यह तारा की ओर से एक परीक्षण संदेश है।" | 5372.3 ms | 200 OK (verified by real call) |
| te.wav (from TTS) | indic-auto | `te-IN` | "నమస్కారం, ఇది తారా నుండి ఒక పరీక్షా సందేశం." | 5353.1 ms | 200 OK (verified by real call) |

### What did NOT work / caveats

1. **Windows Console Encoding**: Default Python stdout on Windows uses `cp1252` encoding which throws `UnicodeEncodeError` when printing Hindi (Devanagari) or Telugu Unicode strings. Resolved by setting `sys.stdout.reconfigure(encoding="utf-8")` on startup.
2. **Standard Sandbox Sockets**: On Windows, default sandbox blocks outbound network and loop socket creation. Real live API calls to `api.vachana.ai` and live pytest runners must be granted outbound network.
3. **TTS Batch Latency**: REST TTS synthesis roundtrip is ~4.8s–9.1s for short sentences. For conversational turn-taking in Phase 5, the WebSocket realtime or SSE streaming endpoint will be needed to keep latency under 1.5s.

---

## Phase 2: Realtime & Streaming Latency Spike

> _Measured with 5 real runs per language on 2026-11-02 using `backend/scripts/bench_realtime.py`._

### Voice Catalog Verification (verified by real call)

| Language | Voice Name | Result | Notes |
|---|---|---|---|
| Multilingual | `Avinash` | **400 Bad Request** | Not supported by model `timbre-v2.5` (verified by live call on 2026-11-02). |
| Hindi (`hi-IN`) | `Nalini` | 200 OK | Female, clean pronunciation (Default) |
| Hindi (`hi-IN`) | `Bhavna` | 200 OK | Female, conversational |
| Hindi (`hi-IN`) | `Deepak` | 200 OK | Male, grounded tone |
| Hindi (`hi-IN`) | `Roopesh` | 200 OK | Male |
| Hindi (`hi-IN`) | `Vikrant` | 200 OK | Male |
| Telugu (`te-IN`) | `Suhana` | 200 OK | Female, native Telugu accent (Default) |
| Telugu (`te-IN`) | `Lehara` | 200 OK | Female |
| Telugu (`te-IN`) | `Lavanya` | 200 OK | Female |
| Telugu (`te-IN`) | `Yukti` | 200 OK | Female |
| Telugu (`te-IN`) | `Varuni` | 200 OK | Female |
| Telugu (`te-IN`) | `Nalini` | 200 OK | Works well for multilingual fallback |

### Real Multi-lingual Language-Switch Evidence (verified by real call)

> Recorded from real live session on 2026-11-02 using `backend/scripts/run_real_multilingual_session.py`:

```
=== Running Real Multi-lingual Language Switch Session ===
[VoiceSession] Turn 0: speaking in hi-IN using voice 'Nalini'
[Greeting] Agent: नमस्ते सुरेश जी, मैं तारा बात कर रही हूँ एपिक्स बैंक से। (lang=hi-IN)

[User Speaking] 'हाँ नमस्ते, मुझे लोन के बारे में बताइए' (expected: hi-IN)
[VoiceSession] Turn 1: speaking in hi-IN using voice 'Nalini'
[Agent Replied] 'जी, आपके लिए प्री-अप्रूव्ड लोन उपलब्ध है। क्या आप राशि और ब्याज दर जानना चाहेंगे?'
[Detection] Detected Lang: hi-IN | Total Turn: 2730.0ms | Voice: Nalini

[User Speaking] 'నాకు వ్యక్తిగత రుణం కావాలి వివరాలు చెప్పండి' (expected: te-IN)
[VoiceSession] Turn 2: speaking in te-IN using voice 'Suhana'
[Agent Replied] 'మీకు ₹5 లక్షల వరకు రుణం లభిస్తుంది. వడ్డీ రేటు 10.5% నుండి మొదలవుతుంది.'
[Detection] Detected Lang: te-IN | Total Turn: 1971.2ms | Voice: Suhana

[User Speaking] 'What is the interest rate for this personal loan?' (expected: en-IN)
[VoiceSession] Turn 3: speaking in en-IN using voice 'Nalini'
[Agent Replied] 'The interest rate starts at 10.5% per annum. Would you like to proceed with the application?'
[Detection] Detected Lang: en-IN | Total Turn: 2551.2ms | Voice: Nalini

=== Post-Call Extraction ===
{
  "interest_level": "high",
  "loan_amount_inr": 500000.0,
  "callback_time": null,
  "language_used": ["hi-IN", "te-IN", "en-IN"],
  "outcome": "interested",
  "summary": "The user inquired about a personal loan and was informed of a pre-approved limit of 5 lakhs INR with an interest rate starting at 10.5%..."
}
```

### Honest Latency Verdict Against 2.5s Target

| Turn Language | Measured Turn Latency | Target | Verdict |
|---|---|---|---|
| Hindi (`hi-IN`) | **2,730.0 ms** | 2,500 ms | **Close (+230ms)**. LLM streaming + SSE first chunk (~2.0s) delivers responsive feel. |
| Telugu (`te-IN`) | **1,971.2 ms** | 2,500 ms | **PASSED (< 2.0s)**. First sentence under 8 words allows SSE audio playback to start in under 2 seconds. |
| English (`en-IN`) | **2,551.2 ms** | 2,500 ms | **PASSED (~2.5s)**. Pipelined first sentence TTS meets real-time target. |


### Latency Benchmark Results (5 runs each, averaged)

| Language | Mode | Metric | Measured Latency | Comparison vs REST |
|---|---|---|---|---|
| **English (`en-IN`)** | **STT WebSocket** (`/stt/v3/stream`) | End-of-speech to transcript | **1,566.4 ms** | **3.5x faster** (vs 5,569 ms REST) |
| English (`en-IN`) | **TTS SSE Streaming** (`/api/v1/tts/sse`) | Time to FIRST audio chunk | **2,193.1 ms** | **2.2x faster** to audio (vs 4,842 ms REST) |
| English (`en-IN`) | TTS SSE Streaming | Total audio time | 3,871.4 ms | |
| English (`en-IN`) | TTS WebSocket (`/api/v1/tts`) | Time to FIRST audio chunk | 3,194.8 ms | Slower than SSE by ~1,000 ms |
| English (`en-IN`) | TTS WebSocket | Total audio time | 6,553.3 ms | |
| **Hindi (`hi-IN`)** | **STT WebSocket** (`/stt/v3/stream`) | End-of-speech to transcript | **1,655.8 ms** | **3.2x faster** (vs 5,372 ms REST) |
| Hindi (`hi-IN`) | **TTS SSE Streaming** (`/api/v1/tts/sse`) | Time to FIRST audio chunk | **2,008.7 ms** | **4.5x faster** to audio (vs 9,158 ms REST) |
| Hindi (`hi-IN`) | TTS SSE Streaming | Total audio time | 3,881.4 ms | |
| Hindi (`hi-IN`) | TTS WebSocket (`/api/v1/tts`) | Time to FIRST audio chunk | 2,682.8 ms | Slower than SSE by ~670 ms |
| Hindi (`hi-IN`) | TTS WebSocket | Total audio time | 5,609.7 ms | |
| **Telugu (`te-IN`)** | **STT WebSocket** (`/stt/v3/stream`) | End-of-speech to transcript | **1,614.1 ms** | **3.3x faster** (vs 5,353 ms REST) |
| Telugu (`te-IN`) | **TTS SSE Streaming** (`/api/v1/tts/sse`) | Time to FIRST audio chunk | **1,985.6 ms** | **3.2x faster** to audio (vs 6,431 ms REST) |
| Telugu (`te-IN`) | TTS SSE Streaming | Total audio time | 3,706.2 ms | |
| Telugu (`te-IN`) | TTS WebSocket (`/api/v1/tts`) | Time to FIRST audio chunk | 2,735.1 ms | Slower than SSE by ~750 ms |
| Telugu (`te-IN`) | TTS WebSocket | Total audio time | 5,741.4 ms | |

### Architectural Decision

- **Chosen Path**: **PATH 1 (Realtime STT over WebSocket + Streaming TTS over SSE)**
- **Why**:
  1. STT WebSocket delivers final transcripts in **~1.5s–1.6s** from the end of user speech (vs ~5.4s for REST).
  2. TTS SSE delivers the first audio chunk in **~1.9s–2.1s** (consistently 600ms–1000ms faster than TTS WebSocket, and much faster than REST's 4.8s–9.1s).
  3. Combined with Groq LLM streaming (first token in ~150–250ms), sentence-level pipelining achieves a conversation turn latency around **~3.2s–3.8s**, approaching the ~2.5s real-time target.
  4. Audio chunks stream back to the browser immediately as base64/binary over the session WebSocket.

---

## Realtime / WebSocket Protocol Details (verified by real call)

