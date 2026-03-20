"""
pure_tone_test.py — 순음청력검사 (Hughson-Westlake 법)

키 입력: pynput 대신 raw mode(tty/termios) 방식 사용
  - Q   : 소리 들림
  - ESC : 검사 즉시 중단
"""

import time
import random

from audio import play_tone
from key_input import KeyListener, wait_key_or_timeout

# 검사 주파수 (Hz) — 임상 표준 순서
TEST_FREQUENCIES = [1000, 2000, 4000, 8000, 500, 250, 125]

TONE_DURATION = 1.0     # 순음 재생 시간 (초)
MIN_INTERVAL  = 1.5     # 순음 간 최소 무음 간격 (초)
MAX_INTERVAL  = 3.0     # 순음 간 최대 무음 간격 (초)
START_LEVEL   = 60      # 시작 레벨 (dB HL)
MIN_LEVEL     = -10     # 최저 레벨 (dB HL)
MAX_LEVEL     = 110     # 최고 레벨 (dB HL)
THRESHOLD_RESPONSES_REQUIRED = 2  # 역치 확정에 필요한 반응 횟수

# Hughson-Westlake 하강법:
#   1단계(초기 하강): 들릴 때마다 10 dB씩 내려가다가 처음 못 들으면 상승 전환
#   2단계(역치 탐색): 못 들으면 5 dB 올리고, 들리면 10 dB 내리기 반복
#   역치 = 상승 중 같은 레벨에서 2회 이상 반응한 최저 레벨


def _wait_interruptible(duration: float, listener: KeyListener) -> bool:
    """
    duration 초 동안 대기하되, ESC가 눌리면 즉시 True(중단) 반환.
    Returns True if ESC pressed, False if normal timeout.
    """
    end_time = time.time() + duration
    while time.time() < end_time:
        if listener.esc_pressed:
            return True   # 중단 신호
        time.sleep(0.02)
    return False


def test_frequency(frequency: int, ear: str,
                   listener: KeyListener):
    """
    단일 주파수 Hughson-Westlake 하강법 실행.

    절차:
      1단계 (초기 하강): START_LEVEL에서 시작, 들릴 때마다 10 dB씩 내림
                         처음으로 못 들으면 2단계로 전환
      2단계 (역치 탐색): 못 들으면 +5 dB, 들리면 -10 dB 반복
                         같은 레벨에서 2회 반응 → 역치 확정

    Returns: 역치 (dB HL)  또는  None (ESC 중단)
    """
    level = START_LEVEL
    responses_at_level: dict[int, int] = {}
    # 1단계(초기 하강) 중에는 역치 카운트 안 함
    initial_descent = True

    ear_label = "오른쪽 귀" if ear == '오른쪽' else "왼쪽 귀"
    print(f"\n  [{ear_label}]  {frequency} Hz")
    print(f"  Q = 들림   ESC = 중단")
    print(f"  {'─' * 42}")

    while True:
        if listener.esc_pressed:
            print("\n  ESC — 검사 중단")
            return None

        level = max(MIN_LEVEL, min(MAX_LEVEL, level))

        # 무작위 무음 간격 (타이밍 예측 방지)
        interval = random.uniform(MIN_INTERVAL, MAX_INTERVAL)
        if _wait_interruptible(interval, listener):
            print("\n  ESC — 검사 중단")
            return None

        # 레벨 표시 — 고정폭으로 한 줄 출력 (정렬 유지)
        phase = "하강" if initial_descent else "탐색"
        bar_len = max(0, min(24, (level + 10) // 5))
        bar = 'X' * bar_len + ' ' * (24 - bar_len)
        line = f"  [{phase}] {level:+4d} dB HL  [{bar}]"
        print(f"{line}", end='  ', flush=True)

        # 순음 재생
        listener.reset_q()
        play_tone(frequency, TONE_DURATION, level, ear=ear)

        # 재생 후 500 ms 추가 대기
        heard = wait_key_or_timeout(listener, 0.5)

        if listener.esc_pressed:
            print()
            return None

        if heard:
            print("<- Q (들림)")

            if initial_descent:
                # 1단계: 들리면 계속 10 dB 내려감 (역치 카운트 안 함)
                level -= 10
            else:
                # 2단계: 역치 탐색 중 들림 → 카운트 후 10 dB 내림
                responses_at_level[level] = responses_at_level.get(level, 0) + 1
                if responses_at_level[level] >= THRESHOLD_RESPONSES_REQUIRED:
                    print(f"\n  역치 확정: {frequency} Hz [{ear_label}] = {level} dB HL")
                    return level
                level -= 10

        else:
            print("<- 반응 없음")

            if initial_descent:
                # 1단계 종료 → 2단계(역치 탐색)로 전환
                initial_descent = False

            level += 5  # 못 들음 → 5 dB 증가

            if level > MAX_LEVEL:
                print(f"  역치 확정 불가 ({frequency} Hz, 최대 레벨 도달)")
                return MAX_LEVEL


def run_pure_tone_test() -> dict:
    """
    전체 순음청력검사 실행 (오른쪽 → 왼쪽).

    Returns:
        {'오른쪽': {주파수: 역치}, '왼쪽': {주파수: 역치}}
    """
    print("\n" + "=" * 60)
    print("  순음청력검사 (Pure Tone Audiometry)")
    print("=" * 60)
    print("""
  =============================================
    소리가 들리면   ->   Q 키를 누르세요
    검사 중단       ->   ESC 키를 누르세요
  =============================================

  - 아주 작은 소리도 들리면 바로 Q를 눌러 주세요.
  - 소리가 날 것 같아도 확실하지 않으면 누르지 마세요.
  - 헤드폰을 착용하고 조용한 곳에서 검사해 주세요.
  - 오른쪽 귀 -> 왼쪽 귀 순서로 진행됩니다.
""")
    input("  준비되셨으면 ENTER를 누르세요...")

    listener = KeyListener()
    listener.start()

    results = {'오른쪽': {}, '왼쪽': {}}

    try:
        for ear in ['오른쪽', '왼쪽']:
            ear_label = "오른쪽 귀" if ear == '오른쪽' else "왼쪽 귀"
            print(f"\n\n  {'=' * 50}")
            print(f"  [{ear_label}] 검사를 시작합니다.")
            print(f"  {'=' * 50}")

            # stop()이 스레드 종료를 join으로 기다리므로
            # 이후 input()이 안전하게 동작함
            listener.stop()
            input(f"\n  [{ear_label}] 헤드폰 확인 후 ENTER를 누르세요...")
            listener = KeyListener()
            listener.start()

            for freq in TEST_FREQUENCIES:
                if listener.esc_pressed:
                    break

                threshold = test_frequency(freq, ear, listener)

                if threshold is None:
                    print("\n  검사가 중단되었습니다.")
                    results['_aborted'] = True
                    return results

                results[ear][freq] = threshold

            if listener.esc_pressed:
                print("\n  검사가 중단되었습니다.")
                results['_aborted'] = True
                return results

    finally:
        listener.stop()

    print("\n\n  순음청력검사 완료.\n")
    return results