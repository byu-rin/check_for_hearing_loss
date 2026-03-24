# 터미널 기반 한국어 청력검사 프로그램

터미널 기반의 한국어 청력검사 프로그램입니다.  
순음청력검사와 어음청력검사를 포함하며, 검사 결과를 한 장짜리 결과지(PNG)와 JSON 파일로 저장합니다.

> ⚠️ 이 프로그램은 임상 청력검사를 대체하지 않습니다. 정확한 진단은 전문 의료기관을 방문하세요.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

# 빠른 시작

## 다운로드

| 플랫폼 | 다운로드 |
|--------|----------|
| macOS | [청력검사 (Mac)](https://github.com/byu-rin/check_for_hearing_loss/releases/latest) |
| Windows | [청력검사.exe (Windows)](https://github.com/byu-rin/check_for_hearing_loss/releases/latest) |

## 실행
> 파일을 다운로드 후 더블클릭하면 바로 실행됩니다.  
> **Mac 최초 실행 시**: 시스템 설정 -> 개인정보 보호 및 보안 -> mac 을 보호하기 위해 "청력검사"가 차단되었습니다. -> 허용하기 클릭

---

# 기능

- **음량 보정** — 검사 전 헤드폰 출력 레벨을 개인에 맞게 보정
- **순음청력검사 (Pure Tone Test)** — 125 Hz ~ 8000 Hz, 좌/우 귀 각각 측정
- **어음청력검사 (Speech Test)** — 한국어 단어 인지도 검사 (TTS 또는 WAV)
- **오디오그램 자동 생성** — 검사 결과를 `audiogram.png`로 저장
- **JSON 결과 저장** — `results.json`으로 데이터 보관
- **ESC 중단 지원** — 검사 도중 안전하게 종료 가능
 
---

# 결과 예시

- 오디오그램 이미지
![오디오그램_예제](/audiogram_example.png)

- 순음청력검사 결과
```json
"음량_배율": 1.0,
  "순음역치": {
    "오른쪽": {
      "1000": 40,
      "2000": 45,
      "4000": 30,
      "8000": 35,
      "500": 35,
      "250": 30,
      "125": 35
    },
    "왼쪽": {
      "1000": 35,
      "2000": 40,
      "4000": 30,
      "8000": 40,
      "500": 35,
      "250": 30,
      "125": 35
    }
  },
  "순음평균역치": {
    "오른쪽": {
      "PTA3": 40.0,
      "PTA4": 37.5
    },
    "왼쪽": {
      "PTA3": 36.7,
      "PTA4": 35.0
    }
  },
  ```

  - 어음청력검사 결과
  ```json
  "어음인지검사": {
    "인지도": 80.0,
    "총단어수": 10,
    "정답수": 8,
    "상세": [
      {
        "word": "달",
        "response": "달",
        "correct": true
      },
      {
        "word": "구름",
        "response": "구름",
        "correct": true
      },
      {
        "word": "거북이",
        "response": "거북이",
        "correct": true
      },
      {
        "word": "가방",
        "response": "다방",
        "correct": false
      },
      {
        "word": "바다",
        "response": "바다",
        "correct": true
      },
      {
        "word": "나무",
        "response": "나무",
        "correct": true
      },
      {
        "word": "새",
        "response": "새",
        "correct": true
      },
      {
        "word": "꽃",
        "response": "복",
        "correct": false
      },
      {
        "word": "수박",
        "response": "수박",
        "correct": true
      },
      {
        "word": "학교",
        "response": "학교",
        "correct": true
      }
    ]
  },
  "초성오류분석": {
    "혼동쌍": {
      "ㄱ->ㄷ": 1,
      "ㄲ->ㅂ": 1
    },
    "오류수": {
      "ㄱ": 1,
      "ㄲ": 1
    },
    "총초성수": 18,
    "오류초성수": 2
  }
  ```

---

# 검사 순서

```
음량 보정 → 순음청력검사 (우) → 순음청력검사 (좌) → 어음청력검사 → 결과 저장
```

---

# 실행 방법 (소스 코드)

## 요구사항
 
- Python 3.9 이상
- 헤드폰 (정확한 검사를 위해 권장)

## 설치

```bash
git clone https://github.com/byu-rin/check_for_hearing_loss.git
cd YOUR_REPO (ex.Downloads)
pip install numpy sounddevice matplotlib
```

## 실행

```bash
# 기본 실행
python main.py
```

### 옵션

```bash 
# 데모 모드 (오디오 장치 없이 동작 확인)
--demo
 
# 순음검사만
--pure-tone-only
 
# 어음검사만 (단어 수 5개)
--speech-only --words 5
 
# 음량 보정 생략
--skip-calibration
```

---

# 핵심 알고리즘

## 순음청력검사
- 역치 탐색:
  - 들림: -10 dB
  - 안 들림: +5 dB
- 동일 레벨 2회 반응 시 역치 확정

## PTA 계산
```
PTA3 = (500 + 1000 + 2000 Hz) / 3
```

---

# 출력 파일
`audiogram.png`
- 좌/우 청력 시각화
- 난청 등급 색상 표시
`results.json`
- 주파수별 역치
- PTA3 / PTA4
- 어음 인지도
- 초성 오류 분석

---

# 청력 분류 (WHO 기준)
| PTA3 (dB HL) | 상태 |
| ------------ | -- |
| ≤ 25         | 정상 |
| 26–40        | 경도 |
| 41–60        | 중도 |
| 61–80        | 고도 |
| ≥ 81         | 심도 |

---

#  정확도 및 한계
- 소비자용 오디오 장비 기반 → 절대 dB HL 정확도 보장 불가
- 임상용 사용 시:
  - 음압계 + 커플러 필요
  - 기준값 재보정 필요

---

# 프로젝트 구조

```
.
├── main.py                 # 진입점 및 검사 흐름 제어
├── audio.py                # 오디오 출력 및 음량 제어
├── volume_calibration.py   # 음량 보정 모듈
├── pure_tone_test.py       # 순음청력검사 로직
├── speech_test.py          # 어음청력검사 로직
└── analysis.py             # PTA 계산, 오디오그램, 결과 저장
```

---

# 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.9+ |
| 신호 생성 | NumPy (순음 사인파 합성) |
| 오디오 출력 | sounddevice (PortAudio 바인딩) |
| 시각화 | Matplotlib (오디오그램) |
| 빌드/배포 | PyInstaller, GitHub Actions |
 
---

# 음량 보정 안내

`audio.py`의 `REFERENCE_AMPLITUDE = 0.001`은 상대적 기준값입니다.  
임상 환경에서 사용하려면 음압계와 음향 커플러를 이용해 실제 dB HL 기준으로 캘리브레이션이 필요합니다.

---

# 한국어 초성 분석 원리

유니코드 한글 공식으로 음절을 분해합니다.

```
음절 코드 − 0xAC00 → 초성 인덱스 × 21 × 28 + 중성 × 28 + 종성
```

검사 단어와 환자 답변의 초성을 비교해 혼동 쌍을 기록합니다.  
예: `ㅂ → ㅍ` (바나나를 파나나로 들음)

---

# 필요 환경

- **Python** 3.9 이상
- **패키지:** `numpy`, `sounddevice`, `matplotlib`
- **선택:** `pyttsx3` (WAV 파일 없을 때 TTS 사용)
- **하드웨어:** 헤드폰, 조용한 환경

---

# 라이선스
 
MIT License

---

# Hearing Test Program

A terminal-based Korean hearing test written in Python.  
Includes Pure Tone Audiometry and Speech Audiometry, with results saved as a single-page report (PNG) and a JSON file.

> ⚠️ This program is not a substitute for a clinical hearing test. Please visit a qualified medical professional for an accurate diagnosis.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

# Quick Start

## Downloads
| Platform | Downloads |
|--------|----------|
| macOS | [Hearing Test (Mac)](https://github.com/byu-rin/check_for_hearing_loss/releases/latest) |
| Windows | [Hearing Test.exe (Windows)](https://github.com/byu-rin/check_for_hearing_loss/releases/latest) |

## Run

> Double-click executable
> Mac first run:
System Settings -> Privacy and Security -> "Listen Confirmation" is blocked to protect your Mac. -> Click Allow

---

# Features

> Volume calibration
> Pure tone test (125–8000 Hz, both ears)
> Korean speech recognition test
> Automatic audiogram generation
> JSON result export
> ESC Interruption Support

---

# Output

- Audiogram visualization
![audiogram_example]](/audiogram_example.png)

- PTA (Pure Tone Average)
```json
"음량_배율": 1.0,
  "순음역치": {
    "오른쪽": {
      "1000": 40,
      "2000": 45,
      "4000": 30,
      "8000": 35,
      "500": 35,
      "250": 30,
      "125": 35
    },
    "왼쪽": {
      "1000": 35,
      "2000": 40,
      "4000": 30,
      "8000": 40,
      "500": 35,
      "250": 30,
      "125": 35
    }
  },
  "순음평균역치": {
    "오른쪽": {
      "PTA3": 40.0,
      "PTA4": 37.5
    },
    "왼쪽": {
      "PTA3": 36.7,
      "PTA4": 35.0
    }
  },
  ```

- Speech Audiometry
```json
  "어음인지검사": {
    "인지도": 80.0,
    "총단어수": 10,
    "정답수": 8,
    "상세": [
      {
        "word": "달",
        "response": "달",
        "correct": true
      },
      {
        "word": "구름",
        "response": "구름",
        "correct": true
      },
      {
        "word": "거북이",
        "response": "거북이",
        "correct": true
      },
      {
        "word": "가방",
        "response": "다방",
        "correct": false
      },
      {
        "word": "바다",
        "response": "바다",
        "correct": true
      },
      {
        "word": "나무",
        "response": "나무",
        "correct": true
      },
      {
        "word": "새",
        "response": "새",
        "correct": true
      },
      {
        "word": "꽃",
        "response": "복",
        "correct": false
      },
      {
        "word": "수박",
        "response": "수박",
        "correct": true
      },
      {
        "word": "학교",
        "response": "학교",
        "correct": true
      }
    ]
  },
  "초성오류분석": {
    "혼동쌍": {
      "ㄱ->ㄷ": 1,
      "ㄲ->ㅂ": 1
    },
    "오류수": {
      "ㄱ": 1,
      "ㄲ": 1
    },
    "총초성수": 18,
    "오류초성수": 2
  }
  ```

---

# Test Flow
```
Calibration → Right Ear → Left Ear → Speech Test → Save Results
```

---

# Developer Usage (Source code)

## Install
```bash
git clone https://github.com/byu-rin/check_for_hearing_loss.git
cd check_for_hearing_loss
pip install numpy sounddevice matplotlib
```

## Run
```bash
python main.py
```

### Options
```bash
# Demo mode (check Run without audio device)
--demo

# only pure-tone threshold average(PTA)
--pure-tone-only

# only Speech Audiometry
--speech-only

# skip calibration
--skip-calibration
```

---

# Core Algorithm

## Hughson-Westlake method
- Threshold logic:
  - Heard → -10 dB
  - Not heard → +5 dB
- Threshold = lowest level with 2 responses

## PTA Calculation
```
PTA3 = (500 + 1000 + 2000 Hz) / 3
```

---

# Outputs
`audiogram.png`
- Hearing thresholds visualization
- Severity color coding
`results.json`
- Frequency thresholds
- PTA values
- Speech score
- Phoneme confusion pairs

---

# Hearing Classification (WHO)
| PTA3 (dB HL) | Level    |
| ------------ | -------- |
| ≤ 25         | Normal   |
| 26–40        | Mild     |
| 41–60        | Moderate |
| 61–80        | Severe   |
| ≥ 81         | Profound |

---

# Limitations
- Consumer hardware dependent
- Not calibrated to clinical dB HL standards
- Requires SPL calibration for medical use

---

# File Structure

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

# Tech Stack

| Classification | Tech |
|------|------|
| Language | Python 3.9+ |
| signal generation | NumPy (순음 사인파 합성) |
| Audio output | sounddevice (Binding PortAudio) |
| Visualization | Matplotlib (Audiogram) |
| CI/CD | PyInstaller, GitHub Actions |
 
---

## Requirements

- **Python** 3.10+
- **Packages:** `numpy`, `sounddevice`, `matplotlib`
- **Optional:** `pyttsx3` (TTS fallback when no WAV files provided)
- **Hardware:** Stereo headphones, quiet environment

## License
 
MIT License