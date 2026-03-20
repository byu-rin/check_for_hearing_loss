"""
key_input.py — 터미널 raw mode 키 입력 모듈

pynput 대신 표준 라이브러리(tty, termios, select)를 사용합니다.
macOS / Linux에서 권한 없이도 즉시 동작합니다.

핵심 원리:
  - termios로 터미널을 raw mode로 전환 → Enter 없이 한 글자씩 즉시 읽음
  - select로 논블로킹 확인 → 소리 재생 중에도 키 감지 가능
  - 원래 터미널 설정은 반드시 복원 (finally 블록)

ESC 바이트 시퀀스:
  - ESC 단독 키: b'\\x1b'
  - 방향키 등:   b'\\x1b[A' (ESC + [ + A) → ESC로 간주
"""

import sys
import os
import time
import threading

# Windows 환경 감지 (Windows는 msvcrt 사용)
_IS_WINDOWS = sys.platform == 'win32'

class KeyListener:
    """
    raw mode 터미널에서 비동기 키 입력을 감지합니다.
    백그라운드 스레드가 계속 stdin을 읽어 플래그를 세웁니다.

    사용법:
        listener = KeyListener()
        listener.start()
        ...
        if listener.q_pressed:   # 소리 들림
            ...
        if listener.esc_pressed: # 중단
            ...
        listener.reset_q()       # 다음 음 재생 전 Q 플래그 초기화
        listener.stop()
    """

    def __init__(self):
        self.q_pressed   = False   # Q 키: 소리 들림
        self.esc_pressed = False   # ESC 키: 검사 중단
        self._stop_flag  = False
        self._thread     = None
        self._old_settings = None

    def start(self):
        """백그라운드 키 리스너 스레드를 시작합니다."""
        self._stop_flag = False
        if _IS_WINDOWS:
            self._thread = threading.Thread(target=self._read_loop_windows, daemon=True)
        else:
            self._thread = threading.Thread(target=self._read_loop_unix, daemon=True)
        self._thread.start()

    # key_input.py — stop()이 스레드 완전 종료까지 기다림
    def stop(self):
        """리스너를 중지하고 터미널 설정을 복원합니다."""
        self._stop_flag = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)  # 터미널 복원 완료까지 대기

    def reset_q(self):
        """Q 키 플래그만 초기화합니다 (ESC는 유지)."""
        self.q_pressed = False

    # ── UNIX / macOS ──────────────────────────────────────────────────────────

    def _read_loop_unix(self):
        """Unix raw mode에서 키를 읽는 루프. 입력 에코(화면 출력)를 끕니다."""
        import tty
        import termios
        import select

        fd = sys.stdin.fileno()
        try:
            old = termios.tcgetattr(fd)
            self._old_settings = old

            # raw mode + 에코 OFF: 키 입력이 화면에 찍히지 않음
            new = termios.tcgetattr(fd)
            new[3] = new[3] & ~(termios.ICANON | termios.ECHO)  # lflags
            new[6][termios.VMIN]  = 0
            new[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSANOW, new)

            while not self._stop_flag:
                r, _, _ = select.select([sys.stdin], [], [], 0.02)
                if not r:
                    continue

                ch = os.read(fd, 3)  # 최대 3바이트 (ESC 시퀀스 대비)

                # Q 또는 q → 들림
                if ch in (b'q', b'Q'):
                    self.q_pressed = True

                # ESC: 0x1b 단독 또는 방향키(ESC+[) 시퀀스
                elif ch and ch[0:1] == b'\x1b':
                    self.esc_pressed = True

                # Ctrl+C → 강제 종료
                elif ch == b'\x03':
                    self.esc_pressed = True
                    self._stop_flag = True

        except Exception:
            pass
        finally:
            # 반드시 터미널 설정 복원
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            except Exception:
                pass

    # ── Windows ───────────────────────────────────────────────────────────────

    def _read_loop_windows(self):
        """Windows에서 msvcrt로 키를 읽는 루프."""
        import msvcrt
        while not self._stop_flag:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b'q', b'Q'):
                    self.q_pressed = True
                elif ch == b'\x1b':
                    self.esc_pressed = True
                elif ch == b'\x03':
                    self.esc_pressed = True
                    self._stop_flag = True
            time.sleep(0.02)


def wait_key_or_timeout(listener: KeyListener, duration: float) -> bool:
    """
    duration 초 동안 Q 키 입력을 기다립니다.

    Args:
        listener: 이미 start()된 KeyListener
        duration: 대기 시간 (초)

    Returns:
        True  → Q 키 눌림 (소리 들림)
        False → 타임아웃 또는 ESC
    """
    end_time = time.time() + duration
    while time.time() < end_time:
        if listener.esc_pressed:
            return False
        if listener.q_pressed:
            return True
        time.sleep(0.01)
    return False