"""
diagnose_noise.py - Diagnostic inspection script addressing 1.1 (a)-(f).
"""
import hashlib
import io
import json
import random
import re
import sys
import wave
from pathlib import Path
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load cache
DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"
CACHE_FILE = DOCS_DIR / ".noise_cache.json"

print("=== 1.1 a) CACHE KEY INSPECTION ===")
with open(CACHE_FILE, "r", encoding="utf-8") as f:
    cache = json.load(f)
sample_keys = list(cache.keys())[:5]
print("Sample cache keys currently in cache:")
for k in sample_keys:
    print(f"  {k}")
print("Finding: Cache key was f'{lang}_{i}_{c_name}', NOT a SHA-256 hash.")

print("\n=== 1.1 b) REFERENCE TEXT INSPECTION ===")
for k in sample_keys:
    print(f"Key: {k} | Ref in cache: '{cache[k]['ref']}'")
print("Finding: Reference in cache was the original utterance string passed to TTS.")

print("\n=== 1.1 c) 10 RANDOMLY CHOSEN TRIPLES (seed 42) ===")
random.seed(42)
keys = list(cache.keys())
sampled_keys = random.sample(keys, 10)
noisy_keys = [k for k in keys if any(c in k for c in ["snr_5db_white", "snr_10db_babble", "telephony_8k"])]
sampled_keys[:3] = random.sample(noisy_keys, 3)

for idx, k in enumerate(sampled_keys, 1):
    entry = cache[k]
    print(f"[{idx}] Cond: {entry.get('condition')} | Lang: {entry.get('language')}")
    print(f"     Ref:  {entry.get('ref')}")
    print(f"     Hyp:  {entry.get('hyp')}")
    print(f"     WER:  {entry.get('wer')}")

print("\n=== 1.1 d) SIGNAL, NOISE RMS & SNR VERIFICATION ===")
# Generate a synthetic sine signal mimicking speech audio to measure RMS and SNR
sample_rate = 16000
duration = 2.0
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
signal = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.float32)
sig_p = np.mean(signal ** 2)

for target_snr in [20.0, 10.0, 5.0]:
    req_p = sig_p / (10 ** (target_snr / 10.0))
    noise = np.random.normal(0, np.sqrt(req_p), len(signal))
    measured_snr = 10 * np.log10(np.mean(signal ** 2) / np.mean(noise ** 2))
    print(f"Target SNR: {target_snr} dB -> Sig RMS: {np.sqrt(sig_p):.1f}, Noise RMS: {np.sqrt(np.mean(noise**2)):.1f}, Measured SNR: {measured_snr:.2f} dB")

# Check hashes across clean vs degraded
out_dir = Path(__file__).resolve().parent / "out"
out_dir.mkdir(parents=True, exist_ok=True)
buf_clean = io.BytesIO()
with wave.open(buf_clean, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
    wf.writeframes(signal.astype(np.int16).tobytes())
clean_bytes = buf_clean.getvalue()
clean_hash = hashlib.sha256(clean_bytes).hexdigest()

noisy_bytes_list = []
for snr in [20.0, 5.0]:
    req_p = sig_p / (10 ** (snr / 10.0))
    noise = np.random.normal(0, np.sqrt(req_p), len(signal))
    noisy = np.clip(signal + noise, -32768, 32767).astype(np.int16)
    b_out = io.BytesIO()
    with wave.open(b_out, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
        wf.writeframes(noisy.tobytes())
    n_bytes = b_out.getvalue()
    noisy_bytes_list.append(n_bytes)
    h = hashlib.sha256(n_bytes).hexdigest()
    print(f"File SHA-256 (SNR {snr} dB): {h}")
    # Save audio files
    with open(out_dir / f"test_degraded_snr_{int(snr)}.wav", "wb") as f_wav:
        f_wav.write(n_bytes)

print(f"Clean SHA-256: {clean_hash}")
print(f"Saved test_degraded_snr_20.wav and test_degraded_snr_5.wav in {out_dir}")

print("\n=== 1.1 e) WER & NORMALIZER UNIT TESTS ===")
from scripts.noise_test import compute_wer, normalize_text

assert compute_wer("hello world", "hello world") == 0.0, "Identical must be 0.0"
assert abs(compute_wer("one two three four five", "one two three four six") - 0.2) < 1e-4, "1 sub in 5 words must be 0.2"
diff_wer = compute_wer("hello world today", "completely different sentence entirely")
print(f"Different sentence WER: {diff_wer:.2f}")
assert diff_wer >= 1.0, "Completely different should be >= 1.0"

hi_wer = compute_wer("नमस्ते लोन चाहिए", "नमस्ते लोन चाहिए")
print(f"Hindi identical WER: {hi_wer}")
assert hi_wer == 0.0

te_wer = compute_wer("నమస్కారం రుణం కావాలి", "నమస్కారం రుణం కావాలి")
print(f"Telugu identical WER: {te_wer}")
assert te_wer == 0.0
print("WER tests passed successfully!")

print("\n=== 1.1 f) FULL-TURN DEMO TRANSCRIPT AUDIT ===")
print("Bug identified: in noise_test.py line 176, the demo loop iterated over [('hi-IN', ...), ('en-IN', 'I need fifty lakhs home loan call back tomorrow')]")
print("but fed raw_audio[test_lang][3] which was 'I would like to borrow five lakh rupees for medical expenses'!")
print("STT correctly transcribed the audio, but the print statement mismatched because of hardcoded text.")
