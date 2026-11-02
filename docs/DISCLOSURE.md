# Prior Art & Challenge Rebuild Disclosure

> [!IMPORTANT]
> **Declaration of Original Work for the Gnani AI Internship Challenge 2026**

## 1. Project Heritage & Previous Concepts
- The high-level product concept of **TARA** (Targeted Acquisition & Reach Agent) was previously conceptualized and explored by the author in earlier academic or hackathon settings.
- Earlier conceptual explorations were prototyped on external, non-Gnani voice technology stacks [OWNER TO CONFIRM: specific historical prototypes and dates].

## 2. From-Scratch Implementation for this Challenge
- **This codebase is a ground-up implementation created specifically for the Gnani AI Internship Challenge.**
- As proven by the repository git commit history (starting from initial commit `038166c` on Nov 2, 2026), every module was constructed from scratch following the 7-phase build plan.
- [OWNER TO CONFIRM: whether any minor utility functions or schemas were inspired by earlier notes; repo git history confirms all files were newly authored].

## 3. What is Specifically New in this Build
1. **Direct Integration with Gnani AI Proprietary APIs**:
   - Built directly on **Gnani Prisma v3.0** (ASR / STT) with `indic-auto` language detection.
   - Built on **Gnani Timbre v2.5** (Streaming SSE & REST TTS) with curated Indic voices (`Nalini` for en-IN/hi-IN, `Suhana` for te-IN).
   - Custom low-latency voice session loop with barge-in support and speculative streaming.
2. **Deterministic Regulatory Compliance Engine**:
   - Strict priority-ordered pre-dispatch compliance gate (Consent attestation, internal DND list, TRAI calling window 09:00–21:00 IST, contact frequency capping, and synthetic test allowlist).
   - Immutable audit logging for every dispatch decision (`ALLOWED` vs `BLOCKED` with explicit reason codes).
3. **Multi-Tenant Architecture**:
   - Strict tenant isolation enforced at the database query level for customers, products, campaigns, communication tasks, and audit logs.
4. **Explainable ML Product-Fit Scoring**:
   - Transparent feature attribution with credit score, income, and age weighting.
5. **Campaign Orchestration & Public Tester Interface**:
   - Decoupled `CommunicationPort` architecture separating campaign management from dispatch execution.
   - Single-use, expiring, 128-bit randomized tester tokens with in-browser microphone capture and typed fallback.

