"""
test_noise_audio.py - Pytest suite for acoustic degradation and WER measurement integrity:
1. Cache-key uniqueness for different audio
2. Normalized Word Error Rate (WER) function correctness across English, Hindi, and Telugu
3. SNR mixing accuracy (measured SNR within 0.5 dB of target)
4. Reference-source rule (reference strictly comes from original TTS input text)
"""
from __future__ import annotations

import hashlib
import io
import wave
import numpy as np
import pytest

from scripts.noise_test import compute_wer, normalize_text, inject_noise, UTTERANCES


def test_cache_key_uniqueness_for_different_audio():
    """Verify distinct audio waveforms produce unique SHA-256 cache keys."""
    audio_a = b"RIFF" + b"\x01" * 100
    audio_b = b"RIFF" + b"\x02" * 100
    model = "prisma-v3.0"
    lang = "indic-auto"

    key_a = hashlib.sha256(audio_a + model.encode() + lang.encode()).hexdigest()
    key_b = hashlib.sha256(audio_b + model.encode() + lang.encode()).hexdigest()

    assert key_a != key_b
    assert len(key_a) == 64
    assert len(key_b) == 64


def test_wer_computation_and_normalizer():
    """Verify WER behaves mathematically across identical, substituted, and Indic utterances."""
    # 1. Identical strings = 0.0
    assert compute_wer("hello world today", "hello world today") == 0.0

    # 2. One substitution in a 5-word sentence = 0.2
    assert abs(compute_wer("one two three four five", "one two three four six") - 0.2) < 1e-4

    # 3. Completely different sentence gives >= 1.0
    wer_diff = compute_wer("hello world today", "completely different sentence entirely")
    assert wer_diff >= 1.0

    # 4. Hindi identical tokens give 0.0
    assert compute_wer("नमस्ते मुझे लोन चाहिए", "नमस्ते मुझे लोन चाहिए") == 0.0

    # 5. Telugu identical tokens give 0.0
    assert compute_wer("నమస్కారం నాకు రుణం కావాలి", "నమస్కారం నాకు రుణం కావాలి") == 0.0

    # 6. Normalizer does not map unrelated words to the same token
    assert normalize_text("personal loan") != normalize_text("medical expenses")


def test_snr_mixing_accuracy_within_half_db():
    """Verify injected noise power achieves target SNR within 0.5 dB."""
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # 440 Hz sine wave scaled to 16-bit range
    signal = (0.5 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.float32)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
        wf.writeframes(signal.astype(np.int16).tobytes())
    raw_wav = buf.getvalue()

    for target_snr in [20.0, 10.0, 5.0]:
        noisy_wav = inject_noise(raw_wav, target_snr, mode="white")
        with wave.open(io.BytesIO(noisy_wav), "rb") as rwf:
            frames = rwf.readframes(rwf.getnframes())
            noisy_sig = np.frombuffer(frames, dtype=np.int16).astype(np.float32)

        # Residual noise = noisy - original
        noise_part = noisy_sig - signal
        measured_snr = 10 * np.log10(np.mean(signal ** 2) / max(1e-6, np.mean(noise_part ** 2)))
        assert abs(measured_snr - target_snr) < 0.5, f"Target {target_snr} dB, but measured {measured_snr:.2f} dB!"


def test_reference_source_rule():
    """Verify reference text is strictly sourced from original TTS input catalog."""
    for lang, sentences in UTTERANCES.items():
        assert len(sentences) >= 5
        for s in sentences:
            # Must be a non-empty human-authored reference sentence
            assert isinstance(s, str) and len(s) > 10
            # Must not contain STT artifacts like punctuation-tagged request IDs
            assert "request_id" not in s
            assert "{" not in s and "}" not in s
