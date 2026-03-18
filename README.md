# Terminal Hearing Test 청력 검사 프로그램

A fully terminal-based, clinical-grade hearing test written in Python.

## Features

| Module | Description |
|---|---|
| `audio.py` | Sine-wave generation, dB→amplitude conversion, WAV playback |
| `pure_tone_test.py` | Hughson-Westlake pure-tone audiometry (7 frequencies) |
| `speech_test.py` | Korean word recognition, WAV/TTS/demo playback |
| `analysis.py` | PTA calculation, audiogram plot, phoneme error analysis, JSON export |
| `main.py` | Orchestration, CLI flags, dependency check |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Full test (pure tone + speech)
python main.py

# Demo mode (no audio hardware needed — uses synthetic thresholds)
python main.py --demo

# Pure tone only
python main.py --pure-tone-only

# Speech only, 5 words
python main.py --speech-only --words 5
```

## Outputs

| File | Description |
|---|---|
| `audiogram.png` | Standard clinical audiogram (inverted Y axis, log X axis) |
| `results.json` | Complete results: thresholds, PTA, speech score, phoneme errors |

## Word List (`words.txt`)

One word per line. Optionally add a TAB-separated WAV path:

```
바나나
사과	/path/to/audio/사과.wav
```

If no WAV is provided, the program uses pyttsx3 TTS (if installed) or
displays the word briefly (demo mode).

## Hughson-Westlake Method

```
Start: 40 dB HL
  ┌─ Heard → −10 dB
  └─ Not heard → +5 dB
  
Threshold = lowest level where patient responds ≥2 times on ascending runs
```

## Korean Phoneme Analysis

Syllables are decomposed using the Unicode Hangul formula:

```
syllable − 0xAC00 → onset index × 21 × 28 + vowel × 28 + coda
```

Onset consonants (초성) are extracted and compared between the target word
and the patient's typed response. Confusion pairs are tabulated (e.g., ㄱ → ㄷ).

## Calibration Note

The `REFERENCE_AMPLITUDE = 0.001` in `audio.py` is a relative value.
For clinical use, calibrate with a sound level meter against a known dB HL
reference using a circumaural headset on an acoustic coupler.

## Requirements

- Python 3.10+
- numpy, sounddevice, matplotlib, scipy, pynput
- pyttsx3 (optional, for TTS)
- A quiet room and headphones# check_for_hearing_loss
