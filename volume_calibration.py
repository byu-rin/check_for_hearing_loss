"""
volume_calibration.py — 검사 전 음량 보정

raw mode 키 입력 방식으로 교체:
  U 또는 위방향키 → 음량 증가
  D 또는 아래방향키 → 음량 감소
  ENTER / Q → 확정
  ESC → 건너뜀
"""

import time
import sys
from audio import play_tone, set_volume_scale

CALIB_FREQUENCY = 1000   # 기준음 주파수 (Hz)
CALIB_DB        = 50     # 기준 레벨 (dB HL)
CALIB_DURATION  = 1.5    # 재생 시간 (초)

SCALE_STEPS    = [0.2, 0.4, 0.6, 0.8, 1.0, 1.3, 1.6, 2.0]
DEFAULT_STEP   = 4   # 1.0x


def _volume_bar(idx: int) -> str:
    filled = idx + 1
    empty  = len(SCALE_STEPS) - filled
    return '█' * filled + '░' * empty


def run_volume_calibration() -> float:
    """
    음량 보정을 진행하고 최종 volume_scale을 반환합니다.
    raw mode로 키를 읽어 Enter 없이 즉시 반응합니다.
    """
    print("\n" + "=" * 60)
    print("  [음량 보정]")
    print("=" * 60)
    print("""
  기준음을 들으시면서 편안한 음량을 설정해 주세요.

    U  또는  위쪽 방향키  →  소리 크게
    D  또는  아래 방향키  →  소리 작게
    ENTER                →  이 음량으로 확정
    ESC                  →  건너뜀 (기본값 사용)

  ※ 헤드폰 착용 후 진행해 주세요.
""")
    input("  준비되셨으면 ENTER를 누르세요...")

    step_idx = DEFAULT_STEP
    set_volume_scale(SCALE_STEPS[step_idx])

    import tty
    import termios
    import select
    import os

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    confirmed = False
    skipped   = False

    print(f"\n  현재 음량: {_volume_bar(step_idx)}  ({SCALE_STEPS[step_idx]:.1f}x)")
    print("  기준음을 재생합니다. 키를 눌러 조절하세요.\n")

    try:
        tty.setraw(fd)

        while True:
            # 기준음 재생
            print(f"\r  ♪ 재생 중...  [{_volume_bar(step_idx)}]  {SCALE_STEPS[step_idx]:.1f}x    ",
                  end='', flush=True)
            play_tone(CALIB_FREQUENCY, CALIB_DURATION, CALIB_DB, ear='양쪽')

            # 재생 후 최대 3초 키 입력 대기
            wait_end = time.time() + 3.0
            key_received = False

            while time.time() < wait_end:
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if not r:
                    continue

                ch = os.read(fd, 3)

                # ENTER (0x0d 또는 0x0a)
                if ch in (b'\r', b'\n', b'\r\n'):
                    confirmed = True
                    key_received = True
                    break

                # ESC (0x1b)
                elif ch and ch[0:1] == b'\x1b':
                    skipped = True
                    key_received = True
                    break

                # Q / q → 확정 (편의)
                elif ch in (b'q', b'Q'):
                    confirmed = True
                    key_received = True
                    break

                # U / u 또는 위 방향키 (ESC[A) → 음량 증가
                elif ch in (b'u', b'U') or ch == b'\x1b[A':
                    step_idx = min(step_idx + 1, len(SCALE_STEPS) - 1)
                    set_volume_scale(SCALE_STEPS[step_idx])
                    print(f"\r  음량 증가 → [{_volume_bar(step_idx)}]  {SCALE_STEPS[step_idx]:.1f}x    ",
                          end='', flush=True)
                    key_received = True
                    break

                # D / d 또는 아래 방향키 (ESC[B) → 음량 감소
                elif ch in (b'd', b'D') or ch == b'\x1b[B':
                    step_idx = max(step_idx - 1, 0)
                    set_volume_scale(SCALE_STEPS[step_idx])
                    print(f"\r  음량 감소 → [{_volume_bar(step_idx)}]  {SCALE_STEPS[step_idx]:.1f}x    ",
                          end='', flush=True)
                    key_received = True
                    break

                # Ctrl+C
                elif ch == b'\x03':
                    skipped = True
                    key_received = True
                    break

            if confirmed or skipped:
                break
            # key_received=True지만 confirmed/skipped 아니면 다시 재생

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    print()  # 줄바꿈

    final_scale = SCALE_STEPS[step_idx]
    set_volume_scale(final_scale)

    if skipped:
        print(f"\n  음량 보정을 건너뜁니다. 기본값 사용 ({final_scale:.1f}x)")
    else:
        print(f"\n  음량 확정: [{_volume_bar(step_idx)}]  {final_scale:.1f}x")

    return final_scale