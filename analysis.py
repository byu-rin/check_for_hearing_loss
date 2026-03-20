"""
analysis.py — 오디오그램, PTA 계산, 한국어 음소 분석, 결과 저장

한국어 음절 구조: 초성 + 중성 + 종성
유니코드 한글 블록: U+AC00 ~ U+D7A3
  음절 = (초성 × 21 + 중성) × 28 + 종성 + 0xAC00
"""

import json
from collections import Counter

import matplotlib
matplotlib.use('Agg')  # GUI 없는 환경에서도 동작
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm
import numpy as np

# ── 한국어 음소 테이블 ────────────────────────────────────────────────────────

ONSET_CONSONANTS = [
    'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
    'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
]

VOWELS = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ',
          'ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']

CODAS = ['', 'ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ',
         'ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ','ㅊ',
         'ㅋ','ㅌ','ㅍ','ㅎ']


def decompose_syllable(char: str):
    """한글 음절을 (초성, 중성, 종성)으로 분해합니다. 한글이 아니면 None 반환."""
    code = ord(char)
    if not (0xAC00 <= code <= 0xD7A3):
        return None
    code -= 0xAC00
    coda_idx  = code % 28
    code //= 28
    vowel_idx = code % 21
    onset_idx = code // 21
    return ONSET_CONSONANTS[onset_idx], VOWELS[vowel_idx], CODAS[coda_idx]


def extract_onsets(word: str) -> list:
    """단어의 각 음절에서 초성을 추출합니다."""
    onsets = []
    for ch in word:
        decomp = decompose_syllable(ch)
        if decomp:
            onsets.append(decomp[0])
    return onsets


# ── 순음 분석 ────────────────────────────────────────────────────────────────

def calculate_pta(thresholds: dict) -> dict:
    """
    순음평균역치(PTA)를 계산합니다.

    PTA3: 500, 1000, 2000 Hz 평균 (어음 주파수 대역)
    PTA4: 500, 1000, 2000, 4000 Hz 평균 (확장 대역)
    """
    def avg(freqs):
        vals = [thresholds[f] for f in freqs if f in thresholds]
        return round(sum(vals) / len(vals), 1) if vals else float('nan')

    return {
        'PTA3': avg([500, 1000, 2000]),
        'PTA4': avg([500, 1000, 2000, 4000]),
    }


def classify_hearing(pta3: float) -> str:
    """PTA3 기준 WHO 청력 분류."""
    if pta3 <= 25:   return "정상 청력"
    elif pta3 <= 40: return "경도 난청 (Mild)"
    elif pta3 <= 60: return "중도 난청 (Moderate)"
    elif pta3 <= 80: return "고도 난청 (Severe)"
    else:            return "심도 난청 (Profound)"


# ── 음소 오류 분석 ────────────────────────────────────────────────────────────

def analyse_phoneme_errors(speech_results: list) -> dict:
    """
    어음검사 결과에서 초성(초성) 오류를 분석합니다.

    Returns:
        {
          'confusion_pairs': {('정답초성', '환자반응초성'): 횟수},
          'error_counts':    {'ㄱ': 2, ...},
          'total_onsets':    int,
          'error_onsets':    int,
        }
    """
    confusion_pairs: Counter = Counter()
    error_counts: Counter = Counter()
    total_onsets = 0
    error_onsets = 0

    for entry in speech_results:
        correct_onsets  = extract_onsets(entry['word'])
        response_onsets = extract_onsets(entry['response'])

        if entry['correct']:
            total_onsets += len(correct_onsets)
            continue

        length = max(len(correct_onsets), len(response_onsets))
        for i in range(length):
            c = correct_onsets[i]  if i < len(correct_onsets)  else None
            r = response_onsets[i] if i < len(response_onsets) else None

            if c:
                total_onsets += 1
            if c and r and c != r:
                confusion_pairs[(c, r)] += 1
                error_counts[c] += 1
                error_onsets += 1
            elif c and not r:
                confusion_pairs[(c, '∅')] += 1
                error_counts[c] += 1
                error_onsets += 1

    return {
        'confusion_pairs': dict(confusion_pairs),
        'error_counts': dict(error_counts),
        'total_onsets': total_onsets,
        'error_onsets': error_onsets,
    }


# ── 오디오그램 ────────────────────────────────────────────────────────────────

AUDIOGRAM_FREQUENCIES = [125, 250, 500, 1000, 2000, 4000, 8000]


def _find_korean_font():
    """시스템에서 한국어 폰트를 찾습니다."""
    candidates = [
        'AppleGothic',        # macOS
        'NanumGothic',
        'NanumBarunGothic',
        'Malgun Gothic',      # Windows
        'UnDotum',
        'DejaVu Sans',        # 한글 미지원이지만 폴백
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return None


def plot_audiogram(thresholds_by_ear: dict,
                   pta_by_ear: dict = None,
                   speech: dict = None,
                   phoneme: dict = None,
                   output_path: str = "audiogram.png") -> None:
    """
    오디오그램 + 수치 결과표를 한 장짜리 결과지로 저장합니다.

    레이아웃:
      ┌─────────────────────────┬──────────────────┐
      │   순음청력검사 오디오그램  │  역치 수치 표    │
      │        (왼쪽 2/3)        │   (오른쪽 1/3)   │
      ├─────────────────────────┴──────────────────┤
      │   PTA 결과   │  어음인지   │  초성 오류      │
      └────────────────────────────────────────────┘
    """
    font_name = _find_korean_font()
    if font_name:
        plt.rcParams['font.family'] = font_name
    plt.rcParams['axes.unicode_minus'] = False

    # 전체 레이아웃: 위쪽(오디오그램+표), 아래쪽(요약 패널)
    fig = plt.figure(figsize=(14, 10))
    fig.patch.set_facecolor('#F8F9FA')

    # GridSpec: 2행 / 위 행=오디오그램+표, 아래 행=요약
    from matplotlib.gridspec import GridSpec
    gs = GridSpec(2, 3, figure=fig,
                  height_ratios=[2.8, 1],
                  hspace=0.35, wspace=0.35)

    ax_audio = fig.add_subplot(gs[0, :2])   # 오디오그램 (위 좌측 2칸)
    ax_table = fig.add_subplot(gs[0, 2])    # 역치 수치 표 (위 우측)
    ax_pta   = fig.add_subplot(gs[1, 0])    # PTA 요약
    ax_speech= fig.add_subplot(gs[1, 1])    # 어음인지
    ax_phon  = fig.add_subplot(gs[1, 2])    # 초성 오류

    # ── 오디오그램 ─────────────────────────────────────────────────────────────
    ax_audio.set_facecolor('#FFFFFF')
    ax_audio.axhspan(0, 25, alpha=0.08, color='#2ECC71')
    ax_audio.text(8200, 12, '정상 범위', fontsize=8, color='#27AE60',
                  alpha=0.8, va='center')

    # 난청 등급 배경
    grade_bands = [
        (25,  40, '#FFF9C4', '경도'),
        (40,  60, '#FFE0B2', '중도'),
        (60,  80, '#FFCCBC', '고도'),
        (80, 120, '#FFCDD2', '심도'),
    ]
    for y0, y1, color, label in grade_bands:
        ax_audio.axhspan(y0, y1, alpha=0.25, color=color)
        ax_audio.text(105, (y0 + y1) / 2, label, fontsize=7,
                      color='#555', alpha=0.7, va='center', ha='left')

    ax_audio.yaxis.set_major_locator(ticker.MultipleLocator(10))
    ax_audio.grid(axis='y', linestyle='--', alpha=0.4, color='#BBBBBB')
    ax_audio.grid(axis='x', linestyle=':',  alpha=0.3, color='#BBBBBB')

    # 오른쪽 귀: 빨간 O
    right = thresholds_by_ear.get('오른쪽', {})
    if right:
        freqs  = sorted([f for f in AUDIOGRAM_FREQUENCIES if f in right])
        levels = [right[f] for f in freqs]
        ax_audio.plot(freqs, levels, 'o-', color='#E74C3C', linewidth=2.5,
                      markersize=12, markerfacecolor='white',
                      markeredgewidth=2.5, label='오른쪽 귀 (O)', zorder=5)
        for f, lvl in zip(freqs, levels):
            ax_audio.annotate(f'{lvl}', xy=(f, lvl), xytext=(7, 0),
                              textcoords='offset points', ha='left',
                              fontsize=8, color='#E74C3C', fontweight='bold')

    # 왼쪽 귀: 파란 X
    left = thresholds_by_ear.get('왼쪽', {})
    if left:
        freqs  = sorted([f for f in AUDIOGRAM_FREQUENCIES if f in left])
        levels = [left[f] for f in freqs]
        ax_audio.plot(freqs, levels, 'x--', color='#2980B9', linewidth=2.5,
                      markersize=12, markeredgewidth=2.5,
                      label='왼쪽 귀 (X)', zorder=5)
        for f, lvl in zip(freqs, levels):
            ax_audio.annotate(f'{lvl}', xy=(f, lvl), xytext=(-15, 0),
                              textcoords='offset points', ha='right',
                              fontsize=8, color='#2980B9', fontweight='bold')

    ax_audio.set_xscale('log')
    ax_audio.set_xlim(100, 10000)
    ax_audio.set_xticks(AUDIOGRAM_FREQUENCIES)
    ax_audio.set_xticklabels([str(f) for f in AUDIOGRAM_FREQUENCIES], fontsize=10)
    ax_audio.set_xlabel("주파수 (Hz)", fontsize=11)
    ax_audio.set_ylim(120, -10)
    ax_audio.set_ylabel("청력역치 (dB HL)", fontsize=11)
    ax_audio.set_title("순음청력검사 오디오그램", fontsize=13,
                        fontweight='bold', pad=8)
    ax_audio.legend(loc='lower left', fontsize=10, framealpha=0.9)

    # ── 역치 수치 표 ───────────────────────────────────────────────────────────
    ax_table.set_facecolor('#FFFFFF')
    ax_table.axis('off')
    ax_table.set_title("주파수별 역치", fontsize=11, fontweight='bold', pad=6)

    col_labels = ['주파수\n(Hz)', '오른쪽\n귀 (dB)', '왼쪽\n귀 (dB)']
    rows = []
    row_colors = []
    for freq in AUDIOGRAM_FREQUENCIES:
        r_val = right.get(freq)
        l_val = left.get(freq)
        rows.append([
            str(freq),
            str(r_val) if r_val is not None else '─',
            str(l_val) if l_val is not None else '─',
        ])
        # 역치가 높을수록 배경 빨갛게
        max_val = max(v for v in [r_val, l_val] if v is not None) if \
                  any(v is not None for v in [r_val, l_val]) else 0
        if max_val > 60:
            row_colors.append(['#FFCDD2'] * 3)
        elif max_val > 40:
            row_colors.append(['#FFE0B2'] * 3)
        elif max_val > 25:
            row_colors.append(['#FFF9C4'] * 3)
        else:
            row_colors.append(['#E8F5E9'] * 3)

    tbl = ax_table.table(
        cellText=rows,
        colLabels=col_labels,
        cellColours=row_colors,
        colColours=['#CFD8DC'] * 3,
        cellLoc='center',
        loc='center',
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1.0, 1.55)

    # ── PTA 요약 패널 ──────────────────────────────────────────────────────────
    ax_pta.set_facecolor('#FFFFFF')
    ax_pta.axis('off')
    ax_pta.set_title("순음평균역치 (PTA)", fontsize=10, fontweight='bold', pad=4)

    pta_by_ear = pta_by_ear or {}
    pta_rows  = []
    pta_color = []
    for ear in ['오른쪽', '왼쪽']:
        pta = pta_by_ear.get(ear, {})
        p3  = pta.get('PTA3', None)
        p4  = pta.get('PTA4', None)
        cls = classify_hearing(p3) if p3 is not None else '─'
        pta_rows.append([
            ear + ' 귀',
            f"{p3:.1f}" if p3 is not None else '─',
            f"{p4:.1f}" if p4 is not None else '─',
            cls,
        ])
        bg = '#FFCDD2' if (p3 or 0) > 60 else \
             '#FFE0B2' if (p3 or 0) > 40 else \
             '#FFF9C4' if (p3 or 0) > 25 else '#E8F5E9'
        pta_color.append([bg] * 4)

    pta_tbl = ax_pta.table(
        cellText=pta_rows,
        colLabels=['귀', 'PTA3\n(dB)', 'PTA4\n(dB)', '청력 분류'],
        cellColours=pta_color,
        colColours=['#CFD8DC'] * 4,
        cellLoc='center',
        loc='center',
    )
    pta_tbl.auto_set_font_size(False)
    pta_tbl.set_fontsize(8)
    pta_tbl.scale(1.0, 1.8)

    # ── 어음인지 패널 ──────────────────────────────────────────────────────────
    ax_speech.set_facecolor('#FFFFFF')
    ax_speech.axis('off')
    ax_speech.set_title("어음인지검사", fontsize=10, fontweight='bold', pad=4)

    if speech:
        score = speech.get('score', 0)
        score_color = '#FFCDD2' if score < 50 else \
                      '#FFE0B2' if score < 70 else '#E8F5E9'
        sp_rows = [
            ['제시 단어', str(speech.get('total', 0))],
            ['정답 수',   str(speech.get('correct', 0))],
            ['인지도',    f"{score:.1f}%"],
        ]
        sp_colors = [['#ECEFF1', '#ECEFF1'],
                     ['#ECEFF1', '#ECEFF1'],
                     ['#CFD8DC', score_color]]
        sp_tbl = ax_speech.table(
            cellText=sp_rows,
            colLabels=['항목', '결과'],
            cellColours=sp_colors,
            colColours=['#CFD8DC'] * 2,
            cellLoc='center',
            loc='center',
        )
        sp_tbl.auto_set_font_size(False)
        sp_tbl.set_fontsize(9)
        sp_tbl.scale(1.0, 2.0)

    # ── 초성 오류 패널 ─────────────────────────────────────────────────────────
    ax_phon.set_facecolor('#FFFFFF')
    ax_phon.axis('off')
    ax_phon.set_title("초성 오류 분석", fontsize=10, fontweight='bold', pad=4)

    if phoneme:
        pairs = phoneme.get('confusion_pairs', {})
        total = phoneme.get('total_onsets', 0)
        errors = phoneme.get('error_onsets', 0)
        accuracy = ((total - errors) / total * 100) if total > 0 else 100.0

        ph_rows = [['총 초성 수', str(total)],
                   ['오류 수',    str(errors)],
                   ['정확도',     f"{accuracy:.1f}%"]]
        if pairs:
            top = sorted(pairs.items(), key=lambda x: -x[1])[:3]
            for (c, h), cnt in top:
                ph_rows.append([f"{c} → {h}", f"{cnt}회"])

        ph_colors = [['#ECEFF1', '#ECEFF1']] * len(ph_rows)
        ph_colors[2] = ['#CFD8DC', '#E8F5E9' if accuracy >= 70 else '#FFCDD2']

        ph_tbl = ax_phon.table(
            cellText=ph_rows,
            colLabels=['항목', '값'],
            cellColours=ph_colors,
            colColours=['#CFD8DC'] * 2,
            cellLoc='center',
            loc='center',
        )
        ph_tbl.auto_set_font_size(False)
        ph_tbl.set_fontsize(9)
        ph_tbl.scale(1.0, 1.7)

    # ── 타이틀 / 범례 ──────────────────────────────────────────────────────────
    import datetime
    today = datetime.date.today().strftime('%Y년 %m월 %d일')
    fig.suptitle(f"청력검사 결과지  |  검사일: {today}",
                 fontsize=15, fontweight='bold', y=0.98,
                 color='#2C3E50')

    # 난청 등급 범례 (오디오그램 아래)
    legend_text = ("난청 등급 기준:  정상 ≤25 dB  |  경도 26~40 dB  |  "
                   "중도 41~60 dB  |  고도 61~80 dB  |  심도 >80 dB")
    fig.text(0.5, 0.01, legend_text, ha='center', fontsize=8, color='#555')

    plt.savefig(output_path, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    plt.close()
    print(f"  결과지 저장 완료: {output_path}")


# ── 결과 보고서 ───────────────────────────────────────────────────────────────

def print_report(thresholds_by_ear: dict,
                 pta_by_ear: dict,
                 speech: dict,
                 phoneme: dict) -> None:
    """터미널에 최종 결과 보고서를 출력합니다."""
    print("\n" + "=" * 60)
    print("  청력검사 최종 결과 보고서")
    print("=" * 60)

    # 1. 순음역치
    print("\n  [1] 순음역치 (dB HL)")
    header = f"  {'주파수(Hz)':<12}"
    for ear in ['오른쪽', '왼쪽']:
        header += f"  {ear + ' 귀':>10}"
    print(header)
    print("  " + "─" * 36)

    for freq in AUDIOGRAM_FREQUENCIES:
        row = f"  {freq:<12}"
        for ear in ['오른쪽', '왼쪽']:
            val = thresholds_by_ear.get(ear, {}).get(freq)
            row += f"  {(str(val) + ' dB'):>10}" if val is not None else f"  {'─':>10}"
        print(row)

    # 2. PTA
    print(f"\n  [2] 순음평균역치 (PTA)")
    for ear in ['오른쪽', '왼쪽']:
        pta = pta_by_ear.get(ear, {})
        pta3 = pta.get('PTA3', float('nan'))
        pta4 = pta.get('PTA4', float('nan'))
        cls  = classify_hearing(pta3) if not (pta3 != pta3) else '─'
        print(f"  {ear} 귀:")
        print(f"    PTA3 (500/1k/2k Hz)      : {pta3} dB HL")
        print(f"    PTA4 (500/1k/2k/4k Hz)   : {pta4} dB HL")
        print(f"    청력 분류                 : {cls}")

    # 3. 어음인지
    print(f"\n  [3] 어음인지검사")
    print(f"  제시 단어 수  : {speech['total']}")
    print(f"  정답 수       : {speech['correct']}")
    print(f"  인지도        : {speech['score']:.1f}%")

    # 4. 초성 오류
    print(f"\n  [4] 초성 오류 분석")
    print(f"  총 초성 수    : {phoneme['total_onsets']}")
    print(f"  오류 초성 수  : {phoneme['error_onsets']}")

    pairs = phoneme['confusion_pairs']
    if pairs:
        print("  혼동 쌍 (정답초성 → 환자반응):")
        for (correct, heard), count in sorted(pairs.items(), key=lambda x: -x[1]):
            print(f"    {correct} → {heard}  ({count}회)")
    else:
        print("  초성 오류 없음")

    print("\n" + "=" * 60)


def save_results(thresholds_by_ear: dict,
                 pta_by_ear: dict,
                 speech: dict,
                 phoneme: dict,
                 volume_scale: float = 1.0,
                 output_path: str = "results.json") -> None:
    """모든 검사 결과를 JSON 파일로 저장합니다."""

    def stringify_keys(d):
        return {str(k): v for k, v in d.items()}

    results = {
        '음량_배율': volume_scale,
        '순음역치': {
            ear: stringify_keys(thresh)
            for ear, thresh in thresholds_by_ear.items()
        },
        '순음평균역치': pta_by_ear,
        '어음인지검사': {
            '인지도': speech.get('score', 0),
            '총단어수': speech.get('total', 0),
            '정답수': speech.get('correct', 0),
            '상세': speech.get('details', []),
        },
        '초성오류분석': {
            '혼동쌍': {
                f"{k[0]}->{k[1]}": v
                for k, v in phoneme['confusion_pairs'].items()
            },
            '오류수': phoneme['error_counts'],
            '총초성수': phoneme['total_onsets'],
            '오류초성수': phoneme['error_onsets'],
        },
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  결과 저장 완료: {output_path}")