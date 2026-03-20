"""
main.py — 청력검사 프로그램 진입점

실행 방법:
    python3 main.py                   # 전체 검사
    python3 main.py --demo            # 데모 모드 (오디오 없이 흐름 확인)
    python3 main.py --pure-tone-only  # 순음청력검사만
    python3 main.py --speech-only     # 어음청력검사만
    python3 main.py --words 5         # 어음검사 단어 수 지정
"""

import sys
import argparse

# ── 패키지 설치 확인 ──────────────────────────────────────────────────────────

def check_dependencies():
    missing = []
    for pkg in ['numpy', 'sounddevice', 'matplotlib']:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[오류] 필요한 패키지가 설치되지 않았습니다: {', '.join(missing)}")
        print(f"설치 명령어: pip3 install {' '.join(missing)}")
        sys.exit(1)

check_dependencies()

# ── 모듈 임포트 ───────────────────────────────────────────────────────────────

from volume_calibration import run_volume_calibration
from pure_tone_test import run_pure_tone_test
from speech_test import run_speech_test
from analysis import (
    calculate_pta,
    analyse_phoneme_errors,
    plot_audiogram,
    print_report,
    save_results,
)
import audio

BANNER = """
╔══════════════════════════════════════════════════════════╗
║              청력 검사 프로그램  v1.0                     ║
║         Hearing Test Program (Korean Edition)            ║
╚══════════════════════════════════════════════════════════╝

  이 프로그램은 다음 검사를 진행합니다:
    1. 음량 보정 — 환자에게 맞는 청취 레벨 설정
    2. 순음청력검사 — 오른쪽/왼쪽 귀 각각 검사
    3. 어음청력검사 — 한국어 단어 인지도 검사
    4. 결과 보고서 출력 및 오디오그램 저장

  ※ 이 프로그램은 임상 청력검사를 대체하지 않습니다.
  ※ 정확한 검사를 위해 헤드폰 착용을 권장합니다.
  ※ 조용한 환경에서 검사해 주세요.
"""


def parse_args():
    parser = argparse.ArgumentParser(
        description="터미널 기반 청력검사 프로그램 (한국어)"
    )
    parser.add_argument('--demo', action='store_true',
                        help='데모 모드: 순음=가상역치, 어음=단어표시(TTS/WAV 없어도 동작)')
    parser.add_argument('--pure-tone-only', action='store_true',
                        help='순음청력검사만 실행')
    parser.add_argument('--speech-only', action='store_true',
                        help='어음청력검사만 실행  (예: --speech-only --words 3)')
    parser.add_argument('--words', type=int, default=10, metavar='N',
                        help='어음검사 단어 수 (기본값: 10, 빠른테스트: --words 3)')
    parser.add_argument('--skip-calibration', action='store_true',
                        help='음량 보정 단계 건너뜀')
    return parser.parse_args()


def demo_thresholds() -> dict:
    """데모용 가상 역치 데이터를 반환합니다."""
    return {
        '오른쪽': {125:30, 250:25, 500:20, 1000:15, 2000:20, 4000:35, 8000:55},
        '왼쪽':   {125:35, 250:30, 500:25, 1000:20, 2000:30, 4000:45, 8000:65},
    }


def main():
    args = parse_args()
    print(BANNER)

    # ── 1. 음량 보정 ──────────────────────────────────────────────────────────
    final_volume_scale = 1.0

    if not args.demo and not args.skip_calibration:
        final_volume_scale = run_volume_calibration()
    else:
        audio.set_volume_scale(1.0)
        if args.demo:
            print("  [데모 모드] 음량 보정을 건너뜁니다.\n")

    # ── 2. 순음청력검사 ───────────────────────────────────────────────────────
    thresholds_by_ear = {'오른쪽': {}, '왼쪽': {}}
    aborted = False  # ESC로 중단됐는지 추적

    run_pure = not args.speech_only

    if run_pure:
        if args.demo:
            print("  [데모 모드] 가상 역치 데이터를 사용합니다.\n")
            thresholds_by_ear = demo_thresholds()
        else:
            result = run_pure_tone_test()
            aborted = result.pop('_aborted', False)   # 플래그 추출 후 제거
            thresholds_by_ear = result

    # ── 3. 어음청력검사 ───────────────────────────────────────────────────────
    # 순음검사가 raw mode를 사용했으므로, 어음검사 input() 전에
    # 터미널이 완전히 복원됐는지 확인 후 짧게 대기

    if run_pure and not args.demo:
        import time as _time
        _time.sleep(0.05)   # 스레드 join 후 OS 버퍼 플러시 여유

    speech_results = {'score': 0.0, 'total': 0, 'correct': 0, 'details': []}

    run_speech = not args.pure_tone_only

    if run_speech and not aborted:
        speech_results = run_speech_test(num_words=args.words)
        if speech_results.pop('_aborted', False):     # 플래그 추출 후 제거
            aborted = True

    # ── 4. 분석 및 출력 ───────────────────────────────────────────────────────
    # ESC로 중단된 경우 결과 저장 없이 종료
    if aborted:
        print("\n  검사가 중단되어 결과를 저장하지 않습니다.\n")
        return

    pta_by_ear = {}
    for ear, thresh in thresholds_by_ear.items():
        if thresh:
            pta_by_ear[ear] = calculate_pta(thresh)

    phoneme = analyse_phoneme_errors(speech_results.get('details', []))

    print_report(thresholds_by_ear, pta_by_ear, speech_results, phoneme)

    # 오디오그램 + 결과표 통합 저장
    if any(thresholds_by_ear.values()):
        plot_audiogram(
            thresholds_by_ear,
            pta_by_ear=pta_by_ear,
            speech=speech_results,
            phoneme=phoneme,
            output_path="audiogram.png",
        )

    # JSON 저장
    save_results(
        thresholds_by_ear, pta_by_ear,
        speech_results, phoneme,
        volume_scale=final_volume_scale,
        output_path="results.json"
    )

    print("\n  검사가 모두 완료되었습니다. 이용해 주셔서 감사합니다.\n")


if __name__ == "__main__":
    main()