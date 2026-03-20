# 청력 검사 프로그램

터미널 기반의 한국어 청력검사 프로그램입니다.  
순음청력검사와 어음청력검사를 포함하며, 검사 결과를 한 장짜리 결과지(PNG)와 JSON 파일로 저장합니다.

> ⚠️ 이 프로그램은 임상 청력검사를 대체하지 않습니다. 정확한 진단은 전문 의료기관을 방문하세요.

---

## 파일 구조

```
프로젝트 폴더/
├── main.py                  # 진입점 — 검사 전체 흐름 제어
├── audio.py                 # 순음 생성, dB→진폭 변환, WAV 재생
├── key_input.py             # 터미널 raw mode 키 입력 (Q / ESC)
├── volume_calibration.py    # 검사 전 음량 보정 단계
├── pure_tone_test.py        # 순음청력검사 (Hughson-Westlake 법)
├── speech_test.py           # 어음청력검사 (한국어 단어 인지도)
├── analysis.py              # PTA 계산, 오디오그램, 초성 오류 분석, JSON 저장
├── words.txt                # 어음검사 단어 목록
├── requirements.txt         # 필요 패키지 목록
└── audio/                   # WAV 파일 폴더 (선택)
    ├── 01_바나나.wav
    └── ...
```

---

## 설치

### 1. Python 버전 확인

Python 3.10 이상이 필요합니다.

```bash
python3 --version
```

### 2. 패키지 설치

```bash
pip3 install -r requirements.txt
```

macOS에서 `sounddevice` 설치 시 PortAudio가 필요합니다.

```bash
brew install portaudio
pip3 install -r requirements.txt
```

---

## 실행 방법

```bash
# 전체 검사 (음량 보정 → 순음청력검사 → 어음청력검사)
python3 main.py
```

---

## 검사 순서

### 1단계 — 음량 보정
검사 시작 전 환자에게 적합한 음량을 설정합니다.

| 키 | 동작 |
|---|---|
| `U` 또는 `↑` | 음량 증가 |
| `D` 또는 `↓` | 음량 감소 |
| `ENTER` | 현재 음량 확정 |
| `ESC` | 보정 건너뜀 (기본값 사용) |

### 2단계 — 순음청력검사
오른쪽 귀 → 왼쪽 귀 순서로 7개 주파수를 검사합니다.

| 키 | 동작 |
|---|---|
| `Q` | 소리가 들림 |
| `ESC` | 검사 즉시 중단 |

**검사 주파수:** 125 / 250 / 500 / 1000 / 2000 / 4000 / 8000 Hz

**Hughson-Westlake 하강법:**
```
시작: 60 dB HL
  1단계(초기 하강): 들릴 때마다 −10 dB → 처음 못 들으면 2단계 전환
  2단계(역치 탐색): 못 들으면 +5 dB / 들리면 −10 dB 반복
  역치 확정: 같은 레벨에서 2회 반응한 최저 레벨
```

### 3단계 — 어음청력검사
한국어 단어를 재생하고 환자가 들은 단어를 입력합니다.

| 키 | 동작 |
|---|---|
| `ENTER` | 답변 제출 |
| `W` | 단어 한 번 더 재생 (입력 전 빈 칸에서) |
| `ESC` | 검사 즉시 중단 |

---

## 단어 목록 설정 (words.txt)

```
[1/10] 잘 들어보세요...
  들은 단어 입력 (W=다시듣기): 코끼리
                                       ✓ 정답!
```

---

## 출력 결과

### `audiogram.png` — 한 장짜리 결과지

```
┌─────────────────────────┬──────────────────┐
│   순음청력검사 오디오그램  │  주파수별 역치표  │
│   오른쪽(O) / 왼쪽(X)    │  색상 코딩 포함   │
├──────────────┬───────────┴──────────────────┤
│  PTA 결과    │  어음인지도   │  초성 오류 분석  │
└──────────────┴─────────────┴─────────────────┘
```

- 오른쪽 귀: 빨간 실선 (O)
- 왼쪽 귀: 파란 점선 (X)
- 난청 등급별 배경색 (정상 / 경도 / 중도 / 고도 / 심도)

### `results.json` — 수치 데이터

```json
{
  "음량_배율": 1.3,
  "순음역치": {
    "오른쪽": { "500": 20, "1000": 15, ... },
    "왼쪽":   { "500": 25, "1000": 20, ... }
  },
  "순음평균역치": {
    "오른쪽": { "PTA3": 18.3, "PTA4": 22.5 },
    "왼쪽":   { "PTA3": 25.0, "PTA4": 30.0 }
  },
  "어음인지검사": { "인지도": 70.0, ... },
  "초성오류분석": { "혼동쌍": { "ㅂ->ㅍ": 1, ... }, ... }
}
```

> ESC로 검사를 중단한 경우 결과 파일은 저장되지 않습니다.

---

## 청력 분류 기준 (WHO)

| PTA3 (dB HL) | 분류 |
|---|---|
| 25 이하 | 정상 청력 |
| 26 ~ 40 | 경도 난청 |
| 41 ~ 60 | 중도 난청 |
| 61 ~ 80 | 고도 난청 |
| 81 이상 | 심도 난청 |

PTA3 = (500 Hz + 1000 Hz + 2000 Hz) / 3

---

## 음량 보정 안내

`audio.py`의 `REFERENCE_AMPLITUDE = 0.001`은 상대적 기준값입니다.  
임상 환경에서 사용하려면 음압계와 음향 커플러를 이용해 실제 dB HL 기준으로 캘리브레이션이 필요합니다.

---

## 한국어 초성 분석 원리

유니코드 한글 공식으로 음절을 분해합니다.

```
음절 코드 − 0xAC00 → 초성 인덱스 × 21 × 28 + 중성 × 28 + 종성
```

검사 단어와 환자 답변의 초성을 비교해 혼동 쌍을 기록합니다.  
예: `ㅂ → ㅍ` (바나나를 파나나로 들음)

---

## 필요 환경

- **Python** 3.10 이상
- **패키지:** `numpy`, `sounddevice`, `matplotlib`
- **선택:** `pyttsx3` (WAV 파일 없을 때 TTS 사용)
- **하드웨어:** 헤드폰, 조용한 환경



# Hearing Test Program

A terminal-based Korean hearing test written in Python.  
Includes Pure Tone Audiometry and Speech Audiometry, with results saved as a single-page report (PNG) and a JSON file.

> ⚠️ This program is not a substitute for a clinical hearing test. Please visit a qualified medical professional for an accurate diagnosis.

---

## File Structure

```
project_folder/
├── main.py                  # Entry point — controls the full test flow
├── audio.py                 # Tone generation, dB→amplitude, WAV playback
├── key_input.py             # Terminal raw mode key input (Q / ESC)
├── volume_calibration.py    # Pre-test volume calibration step
├── pure_tone_test.py        # Pure Tone Audiometry (Hughson-Westlake method)
├── speech_test.py           # Speech Audiometry (Korean word recognition)
├── analysis.py              # PTA calculation, audiogram, phoneme analysis, JSON export
├── words.txt                # Word list for speech test
├── requirements.txt         # Required packages
└── audio/                   # WAV file folder (optional)
    ├── 01_바나나.wav
    └── ...
```

---

## Installation

### 1. Check Python Version

Python 3.10 or higher is required.

```bash
python3 --version
```

### 2. Install Packages

```bash
pip3 install -r requirements.txt
```

On macOS, `sounddevice` requires PortAudio.

```bash
brew install portaudio
pip3 install -r requirements.txt
```

---

## Usage

```bash
python3 main.py
```

---

## Test Flow

### Step 1 — Volume Calibration
Sets a comfortable listening level for the patient before the test begins.

| Key | Action |
|---|---|
| `U` or `↑` | Increase volume |
| `D` or `↓` | Decrease volume |
| `ENTER` | Confirm current volume |
| `ESC` | Skip calibration (use default) |

Once confirmed, the following message is displayed:

> *Please keep the volume at this level until the test is complete for accurate results.*

### Step 2 — Pure Tone Audiometry
Tests each ear across 7 frequencies: right ear first, then left.  
Audio is delivered to the correct ear via stereo headphones (right = channel R, left = channel L).

| Key | Action |
|---|---|
| `Q` | Tone heard |
| `ESC` | Abort test immediately |

**Test frequencies:** 125 / 250 / 500 / 1000 / 2000 / 4000 / 8000 Hz

**Hughson-Westlake Descending Method:**
```
Start: 60 dB HL
  Phase 1 (initial descent): Heard → −10 dB, until first miss → switch to Phase 2
  Phase 2 (threshold search): Miss → +5 dB / Heard → −10 dB
  Threshold confirmed: lowest level with ≥2 responses on ascending runs
```

### Step 3 — Speech Audiometry
Plays a Korean word and asks the patient to type what they heard.

| Key | Action |
|---|---|
| `ENTER` | Submit answer |
| `W` | Replay the word (only when input field is empty) |
| `ESC` | Abort test immediately |

An exact Unicode match is required for a correct response.

---

## Word List Configuration (`words.txt`)

One word per line. WAV file path is optional.  
Tab or space delimiter both supported.

```
 [1/10] 잘 들어보세요...
  들은 단어 입력 (W=다시듣기): 코끼리
                                       ✓ 정답!
```

WAV paths are resolved relative to the script's directory, so the program works correctly regardless of which folder it is run from.

---

## Output Files

### `audiogram.png` — Single-Page Result Report

```
┌─────────────────────────┬──────────────────┐
│   Pure Tone Audiogram   │  Threshold Table  │
│   Right (O) / Left (X)  │  color-coded      │
├──────────────┬──────────┴──────────────────┤
│  PTA Results │  Speech Score  │ Phoneme Err │
└──────────────┴────────────────┴─────────────┘
```

- Right ear: red solid line (O)
- Left ear: blue dashed line (X)
- Background color-coded by hearing loss grade
- Test date printed automatically

### `results.json` — Numeric Data

```json
{
  "음량_배율": 1.3,
  "순음역치": {
    "오른쪽": { "500": 20, "1000": 15, "2000": 20, ... },
    "왼쪽":   { "500": 25, "1000": 20, "2000": 30, ... }
  },
  "순음평균역치": {
    "오른쪽": { "PTA3": 18.3, "PTA4": 22.5 },
    "왼쪽":   { "PTA3": 25.0, "PTA4": 30.0 }
  },
  "어음인지검사": { "인지도": 70.0, "총단어수": 10, "정답수": 7 },
  "초성오류분석": { "혼동쌍": { "ㅂ->ㅍ": 1 }, ... }
}
```

> If the test is aborted via ESC, no result files are saved.

---

## Hearing Classification (WHO)

| PTA3 (dB HL) | Classification |
|---|---|
| ≤ 25 | Normal hearing |
| 26 – 40 | Mild hearing loss |
| 41 – 60 | Moderate hearing loss |
| 61 – 80 | Severe hearing loss |
| ≥ 81 | Profound hearing loss |

PTA3 = (500 Hz + 1000 Hz + 2000 Hz) / 3  
PTA4 = (500 Hz + 1000 Hz + 2000 Hz + 4000 Hz) / 4

---

## Volume Calibration Note

`REFERENCE_AMPLITUDE = 0.001` in `audio.py` is a relative value.  
For clinical use, calibrate against a known dB HL reference using a sound level meter and an acoustic coupler with circumaural headphones.

---

## Korean Onset Consonant (초성) Analysis

Hangul syllables are decomposed using the Unicode formula:

```
(syllable code − 0xAC00) → onset_index × 21 × 28 + vowel × 28 + coda
```

The onset consonant (초성) of each syllable is extracted from both the target word and the patient's typed response. Mismatches are recorded as confusion pairs.

Example: patient hears `파나나` instead of `바나나` → confusion pair `ㅂ → ㅍ`

---

## Key Technical Decisions

| Area | Decision |
|---|---|
| Key input | `tty` + `termios` + `select` raw mode — no `pynput`, no permission issues on macOS |
| Stereo routing | `sounddevice` channel 0 = Left (L), channel 1 = Right (R) |
| Terminal safety | `KeyListener.stop()` calls `thread.join()` before returning, ensuring terminal is fully restored before any subsequent `input()` call |
| WAV parsing | Tab and space delimiters both accepted; paths resolved relative to script location |
| ESC abort | Both pure tone and speech tests return `_aborted: True`; `main.py` skips saving when set |

---

## Requirements

- **Python** 3.10+
- **Packages:** `numpy`, `sounddevice`, `matplotlib`
- **Optional:** `pyttsx3` (TTS fallback when no WAV files provided)
- **Hardware:** Stereo headphones, quiet environment
