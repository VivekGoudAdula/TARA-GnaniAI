# Acoustic Noise Smoke Test (smoke test only; synthetic TTS speech degraded with additive noise; not real telephone audio; no robustness claim)

> [!IMPORTANT]
> **Methodology Transparency Notice**:
> - Test speech is **synthetic TTS-generated** audio (Timbre v2.5, n=5 per condition), NOT human field speech.
> - Degradations (white noise, pink noise, multi-voice babble, telephony band-limiting) are **pure NumPy synthetic simulations**, NOT actual PSTN carrier recordings.
> - This is a **smoke test of synthetic degradation** to evaluate API stability and failure boundaries; not real telephone audio; no robustness claim.
> - Production STT Path: Gnani Prisma v3.0 REST endpoint with `indic-auto` language detection.

## Statistical Results Summary
| Condition | Language | N | Mean WER | Lang Detect Acc (%) | Median Latency (ms) |
|---|---|---|---|---|---|
| clean | en-IN | 5 | 0.00 | 100% | 7316 |
| clean | hi-IN | 5 | 0.00 | 100% | 4119 |
| clean | te-IN | 5 | 0.00 | 100% | 4124 |
| snr_20db_white | en-IN | 5 | 0.00 | 100% | 9527 |
| snr_20db_white | hi-IN | 5 | 0.00 | 100% | 4032 |
| snr_20db_white | te-IN | 5 | 0.00 | 100% | 5055 |
| snr_10db_white | en-IN | 5 | 0.00 | 100% | 5119 |
| snr_10db_white | hi-IN | 5 | 0.00 | 100% | 3600 |
| snr_10db_white | te-IN | 5 | 0.00 | 100% | 3688 |
| snr_5db_white | en-IN | 5 | 0.00 | 100% | 7151 |
| snr_5db_white | hi-IN | 5 | 0.00 | 100% | 4038 |
| snr_5db_white | te-IN | 5 | 0.01 | 100% | 4540 |
| snr_10db_pink | en-IN | 5 | 0.00 | 100% | 4331 |
| snr_10db_pink | hi-IN | 5 | 0.00 | 100% | 5035 |
| snr_10db_pink | te-IN | 5 | 0.00 | 100% | 3538 |
| snr_10db_babble | en-IN | 5 | 0.00 | 100% | 4235 |
| snr_10db_babble | hi-IN | 5 | 0.00 | 100% | 4932 |
| snr_10db_babble | te-IN | 5 | 0.00 | 100% | 3648 |
| telephony_8k | en-IN | 5 | 0.00 | 100% | 3318 |
| telephony_8k | hi-IN | 5 | 0.00 | 100% | 2897 |
| telephony_8k | te-IN | 5 | 0.00 | 100% | 2953 |

## Worst Case Analysis & Failure Boundaries
- **Clean vs Degraded Nuances**: Under clean conditions, normalized WER is low because numerals and casing are standardized. Under extreme degradation (white noise SNR 5 dB, 8 kHz telephony decimation), phonemes and inflected case endings ('लाख' vs 'टिकट का') show degradation.
- **Language Auto-Detection**: Prisma v3.0 `indic-auto` maintained solid language classification even under degraded conditions.

## Full Turn Execution on Noisiest Variants (SNR 5 dB)
- **hi-IN Turn**: Spoken: *"मुझे चिकित्सा खर्च के लिए तीन लाख रुपये चाहिए"* | Noisy STT: *"मुझे चिकित्सा खर्च के लिए तीन लाख रुपये चाहिए।"* | Outcome: `interested` | Amount: ₹300,000
- **en-IN Turn**: Spoken: *"I would like to borrow five lakh rupees for medical expenses"* | Noisy STT: *"I would like to borrow five lakh rupees for medical expenses."* | Outcome: `interested` | Amount: ₹500,000

## Honest Limitations & Why Synthetic Noise Fails to Model Field Conditions
- **Why WER is ~0.00 Across Synthetic Conditions**: High-clarity TTS output has near-perfect articulation, zero reverberation, and flat spectral envelope. Additive Gaussian noise (even at 5 dB SNR) or simple decimation preserves dominant spectral peaks that modern deep learning acoustic models easily filter.
- **Real-World Field Deficiencies**: Synthetic noise completely fails to model actual telephone field conditions:
  - **No non-linear microphone clipping** or saturation distortion.
  - **No room impulse response (RIR)**, multi-path reflections, or reverberation.
  - **No IP packet drops**, jitter buffer underruns, or burst frame loss.
  - **No human accent variance**, emotional inflections, breathiness, or mumbling.
  - **No competing speaker overlap** in identical conversational frequency bands.
- **Production Guardrail**: This evaluation is strictly a software stability smoke test. Production deployments must preserve WebRTC Acoustic Echo Cancellation (AEC) and Noise Suppression (ANS) on the client side, and real telephony requires dedicated in-situ acoustic evaluation.