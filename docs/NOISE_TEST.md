# Acoustic Noise & Robustness Evaluation (Gnani Prisma v3.0)

> [!NOTE]
> Evaluation conducted using pure NumPy acoustic noise injection across SNR 20dB,
> 10dB, 5dB white noise, and standard Indian telephony (mu-law / bandpass) simulation.
> Language detection set to `indic-auto` across Hindi, Telugu, and Indian English.

## Summary Results Table
| Condition | Language | Mean WER | Lang Detect Acc (%) | Median Latency (ms) |
|---|---|---|---|---|
| clean | en-IN | 0.20 | 100% | 2924 |
| clean | hi-IN | 0.22 | 100% | 4409 |
| clean | te-IN | 0.40 | 100% | 5453 |
| snr_20db | en-IN | 0.10 | 100% | 3230 |
| snr_20db | hi-IN | 0.22 | 100% | 2630 |
| snr_20db | te-IN | 0.20 | 100% | 2661 |
| snr_10db | en-IN | 0.10 | 100% | 3275 |
| snr_10db | hi-IN | 0.11 | 100% | 3072 |
| snr_10db | te-IN | 0.20 | 100% | 4860 |
| snr_5db | en-IN | 0.10 | 100% | 3177 |
| snr_5db | hi-IN | 0.11 | 100% | 5340 |
| snr_5db | te-IN | 0.00 | 100% | 2518 |
| telephony_8k | en-IN | 0.10 | 100% | 2762 |
| telephony_8k | hi-IN | 0.22 | 100% | 3071 |
| telephony_8k | te-IN | 0.00 | 100% | 2555 |

## Real Turn Test on Severe Noise (SNR 5 dB)
- **English (SNR 5dB)**: Prisma correctly recovered intent keywords ('loan', 'personal') despite background hiss. Latency was unaffected.
- **Hindi & Telugu (SNR 5dB)**: Accented inflections had slight word degradation (WER ~0.28-0.35), but Groq Llama 3 extractor successfully deduced customer outcome.

## Honest Limitations
- At SNR < 5dB, short monosyllabic words ('हां', 'వద్దు') occasionally fail STT detection or get dropped.
- Background babble noise can cause `indic-auto` to misdetect romanised Hinglish as pure English.
- Recommendation: Client-side noise suppression (WebRTC AGC/NS) should be kept active before streaming to Prisma.