# TARA Demo Script & Video Shot List

## 1. 5-Step Live Evaluator Walkthrough

### Step 1: Workspace Overview & Product Eligibility
- Navigate to **Dashboard** (`http://localhost:5173`) and log in as `analyst@testbank.com` / `password123`.
- View product catalogue under **Products** (`Personal Loan`, `Platinum Credit Card`, `Home Loan`).
- Inspect eligibility rules (minimum income, age limits, credit score requirements) and default prompts.

### Step 2: Scored Synthetic Audience & Explainability
- Navigate to **Customers** or **Leads**.
- Review synthetic profiles across Hindi, Telugu, and English.
- Inspect explainable ML fit scoring breakdown showing feature contributions.

### Step 3: Campaign Configuration & Voice Mapping
- Navigate to **Campaigns** & click *"Personal Loan: High Intent"*.
- Review AI disclosure notice, per-language voice assignments (`Nalini` for hi/en, `Suhana` for te).
- Preview rendered opening message customized per recipient.

### Step 4: Test Launch & Single-Use Tester Call
- Click **Launch Campaign** in Test Mode. Type recipient count to confirm.
- Open generated single-use tester link (`/call/{token}`).
- Conduct conversational turns via microphone or typed fallback.
- Observe real-time turn latency metrics (< 2.5s) and post-call grounded entity extraction.
- *Capturing Evaluator Call Evidence*: To capture real human speech evidence from your tester call into `docs/EVIDENCE.md`, run:
  `python backend/scripts/capture_evidence.py --communication-id <id-from-tester-call>`

### Step 5: Governance Audit Trail & CSV Export
- Navigate to **Governance**.
- Inspect immutable audit log records showing `ALLOWED` and `BLOCKED` outcomes with reason codes.
- Export interaction CSV to verify complete data retention and tenant scoping.

---

## 2. 60-Second Video Shot List (Wording Placeholder)

| Time | Visual / Screen Action | Voiceover Script (Placeholder) |
|---|---|---|
| **00:00 - 00:10** | Dashboard overview showing tenant metrics and AI disclosure notice. | [OWNER TO SUPPLY: Introduction to TARA and multilingual banking challenge] |
| **00:10 - 00:25** | Campaign builder screen highlighting voice configuration for Hindi, Telugu, and English. | [OWNER TO SUPPLY: How campaigns configure Gnani Prisma and Timbre voices] |
| **00:25 - 00:45** | Live tester session in action: audio waveform, turns in Hindi/Telugu, and post-call extraction card. | [OWNER TO SUPPLY: Demonstration of live voice interaction and grounded extraction] |
| **00:45 - 00:60** | Governance view displaying enforced compliance gates (DND, calling hours) and audit log. | [OWNER TO SUPPLY: Closing statement on regulatory compliance and transparency] |

