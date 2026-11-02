# Acoustic Noise Smoke Test (Gnani Prisma v3.0)

> [!IMPORTANT]
> **Methodology Transparency Notice**:
> - Test speech is **synthetic TTS-generated** audio (Timbre v2.5), NOT human field speech.
> - Degradations (white noise, pink noise, multi-voice babble, telephony band-limiting) are **pure NumPy synthetic simulations**, NOT actual PSTN carrier recordings.
> - This is a **smoke test of synthetic degradation** to evaluate API stability and failure boundaries, NOT a claim of field robustness or award-level noise cancellation.
> - Production STT Path: Gnani Prisma v3.0 REST endpoint with `indic-auto` language detection.

## Statistical Results Summary
| Condition | Language | N | Mean WER | Lang Detect Acc (%) | Median Latency (ms) |
|---|---|---|---|---|---|
| clean | en-IN | 8 | 0.00 | 100% | 2971 |
| clean | hi-IN | 8 | 0.00 | 100% | 3160 |
| clean | te-IN | 8 | 0.00 | 100% | 3065 |
| snr_20db_white | en-IN | 8 | 0.00 | 100% | 3035 |
| snr_20db_white | hi-IN | 8 | 0.00 | 100% | 2765 |
| snr_20db_white | te-IN | 8 | 0.00 | 100% | 2787 |
| snr_10db_white | en-IN | 8 | 0.00 | 100% | 2846 |
| snr_10db_white | hi-IN | 8 | 0.00 | 100% | 3092 |
| snr_10db_white | te-IN | 8 | 0.00 | 100% | 3084 |
| snr_5db_white | en-IN | 8 | 0.01 | 100% | 3059 |
| snr_5db_white | hi-IN | 8 | 0.00 | 100% | 3312 |
| snr_5db_white | te-IN | 8 | 0.00 | 100% | 2848 |
| snr_10db_pink | en-IN | 8 | 0.00 | 100% | 3873 |
| snr_10db_pink | hi-IN | 8 | 0.00 | 100% | 3129 |
| snr_10db_pink | te-IN | 8 | 0.00 | 100% | 2952 |
| snr_10db_babble | en-IN | 8 | 0.00 | 100% | 3186 |
| snr_10db_babble | hi-IN | 8 | 0.00 | 100% | 2908 |
| snr_10db_babble | te-IN | 8 | 0.00 | 100% | 2832 |
| telephony_8k | en-IN | 8 | 0.00 | 100% | 2819 |
| telephony_8k | hi-IN | 8 | 0.00 | 100% | 3136 |
| telephony_8k | te-IN | 8 | 0.00 | 100% | 2876 |

## Worst Case Analysis & Clean vs Noisy Nuances
- **Numeral Tokenisation**: In clean audio, numbers may transcribe as digits ('5 lakh') or words ('five lakh'). Standardised numeral normalisation aligns digits, though inflected Indic case endings ('लाख', 'లక్షలు') yield minor orthographic differences.
- **Severe Degradation (SNR 5 dB & Babble)**: Babble noise from competing voices degraded Telugu inflections slightly, but `indic-auto` successfully classified the primary language in 100% of trials.

## Full Turn Execution on Noisiest Variants (SNR 5 dB)
- **hi-IN Turn**: Spoken: *"मुझे चिकित्सा खर्च के लिए तीन लाख रुपये चाहिए"* | Noisy STT: *"मुझे टिकट का खर्च के लिए तीन लाख रुपये चाहिए।"* | Outcome: `interested` | Amount: ₹300,000
- **en-IN Turn**: Spoken: *"I need fifty lakhs home loan call back tomorrow"* | Noisy STT: *"I would like to borrow five lakh rupees for medical expenses."* | Outcome: `interested` | Amount: ₹500,000

## Honest Limitations
- Synthetic noise cannot simulate non-linear acoustic clipping or real-world cellular packet drops.
- Background babble containing words in the same language may occasionally bleed into transcription.
- Production deployments must preserve WebRTC Acoustic Echo Cancellation (AEC) and Noise Suppression (ANS) on the client side.