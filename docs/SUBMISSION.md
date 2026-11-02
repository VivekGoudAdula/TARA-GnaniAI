# Challenge Submission Form Draft

## 1. Project Title
**TARA – Targeted Acquisition & Reach Agent for Indic Banking**

## 2. The Problem
Retail banks and NBFCs in India struggle to engage multilingual customers effectively. Traditional telemarketing relies on manual cold calling that often violates calling hours, disregards consent, and generates generic pitches that frustrate customers. Existing automated IVRs are rigid, mono-lingual, and lack conversational intelligence.

## 3. Who Will Use It
- **Branch Managers & Product Leads**: To configure targeted, compliant outreach campaigns for personal loans, savings accounts, and credit cards.
- **Compliance & Risk Officers**: To review automated regulatory gating (DND, consent, TRAI calling hours) and audit immutable dispatch logs.
- **Multilingual Banking Customers**: Interacting seamlessly with an AI voice agent in Hindi, Telugu, or Indian English.

## 4. Gnani AI Models & APIs Used
- **Gnani Prisma v3.0**: Speech-to-Text with real-time `indic-auto` language detection across Hindi, Telugu, and English.
- **Gnani Timbre v2.5**: Text-to-Speech using Indic voices (`Nalini` for en-IN and hi-IN, `Suhana` for te-IN) over streaming SSE.
- **External LLM**: `qwen/qwen3.8-27b` via Groq API for single-turn conversational pacing and grounded post-call extraction.
- *Explicit Non-Usage Disclosure*: Gnani Agent Builder is **NOT** used. Evon is **NOT** used.

## 5. Team Contributions
- **Team Lead / Backend & ML Engineer**: [PLACEHOLDER: Team Member 1] - Gnani voice provider, compliance engine, scoring pipeline, and database schema.
- **Frontend & Fullstack Engineer**: [PLACEHOLDER: Team Member 2] - Campaign wizard, tester call interface, audio visualizer, and governance dashboard.

## 6. Project Explanation (246 Words)
TARA is a compliance-first, multilingual outbound voice outreach platform built for Indian financial institutions. Powered directly by Gnani Prisma v3.0 and Timbre v2.5, TARA enables banks to engage customers in their preferred language—Hindi, Telugu, or Indian English—with natural conversational turns and low latency.

Unlike conventional dialing systems, TARA enforces strict deterministic governance before any outreach occurs. Every communication request passes through a 5-point machine compliance gate checking explicit consent attestation, internal Do-Not-Call (DND) status, TRAI approved calling hours (09:00 to 21:00 IST), contact frequency caps, and test-mode synthetic number allowlists. Blocked attempts are recorded into an immutable audit trail with explicit reason codes.

Once verified, TARA generates secure, single-use web-based tester links for verified test profiles. In each interactive session, TARA speaks concisely, identifies itself as an automated AI representative, asks one question at a time, and never guarantees loan approval or unverified rates. Following each conversation, a factual post-call extractor parses customer outcomes strictly grounded in spoken transcript words.

All demonstrations and benchmarks operate exclusively on synthetic banking personas and rule-generated evaluation sets without accessing real telephone networks or live financial data. By bridging intelligent Indic speech AI with rigorous regulatory guardrails, TARA demonstrates how banks can conduct respectful, automated multilingual outreach.

