"""
speech_test.py — 어음청력검사 (한국어 단어 인지도 검사)

개선 사항:
  1. ESC 키로 검사 즉시 중단 (raw mode KeyListener 사용)
  2. words.txt 파싱: 탭·스페이스 혼용 모두 지원
  3. W 키: 단어 한 번 더 재생
  4. 답변 입력창에 경로가 보이지 않음
  5. --speech-only --demo 로 단독 빠른 테스트 가능
"""

import os
import sys
import random
import time
import tty
import termios
import select

# 스크립트가 있는 폴더 기준으로 경로를 해석합니다.
# 터미널에서 어느 폴더에서 실행하든 동일하게 동작합니다.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

WORD_LIST_FILE = os.path.join(_SCRIPT_DIR, "words.txt")

DEFAULT_WORDS = [
    "바나나", "사과", "수박", "포도", "딸기",
    "학교", "가방", "연필", "책상", "의자",
    "하늘", "구름", "바람", "태양", "달",
]


# ── 단어 목록 로드 ─────────────────────────────────────────────────────────────

def load_word_list(filepath: str = WORD_LIST_FILE) -> list:
    """
    words.txt 에서 (단어, wav경로) 튜플 목록을 로드합니다.

    지원 형식 (탭 또는 스페이스 구분 모두 허용):
      바나나                        → (바나나, None)
      바나나\t/audio/01_바나나.wav  → (바나나, /audio/01_바나나.wav)
      바나나 /audio/01_바나나.wav   → (바나나, /audio/01_바나나.wav)
    """
    if not os.path.exists(filepath):
        print(f"  [안내] '{filepath}' 파일이 없어 기본 단어를 사용합니다.")
        return [(w, None) for w in DEFAULT_WORDS]

    entries = []
    missing_wav = []

    with open(filepath, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 탭 우선, 없으면 첫 번째 스페이스로 분리
            if '\t' in line:
                parts = line.split('\t', 1)
            else:
                parts = line.split(' ', 1)

            word = parts[0].strip()
            if not word:
                continue

            wav = parts[1].strip() if len(parts) > 1 else None

            # 상대경로면 words.txt가 있는 폴더 기준으로 절대경로 변환
            if wav and not os.path.isabs(wav):
                wav = os.path.join(_SCRIPT_DIR, wav)

            # 경로가 있는데 파일이 없으면 경고 후 None 처리
            if wav:
                if not os.path.exists(wav):
                    missing_wav.append((lineno, word, wav))
                    wav = None

            entries.append((word, wav))

    found_wav = sum(1 for _, w in entries if w is not None)
    print(f"  [안내] 단어 {len(entries)}개 로드 (WAV 있음: {found_wav}개)")
    if missing_wav:
        print(f"  [경고] WAV 파일을 찾을 수 없는 항목 {len(missing_wav)}개:")
        for lineno, word, path in missing_wav[:5]:
            print(f"         {lineno}행 '{word}' → {path}")
        if len(missing_wav) > 5:
            print(f"         ... 외 {len(missing_wav)-5}개")

    return entries


# ── 단어 재생 ─────────────────────────────────────────────────────────────────

def play_word(word: str, wav_path) -> None:
    """WAV → pyttsx3 TTS → 데모(화면 표시) 순으로 재생합니다."""
    if wav_path and os.path.exists(wav_path):
        from audio import play_wav
        play_wav(wav_path)
        return

    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 140)
        engine.say(word)
        engine.runAndWait()
        return
    except Exception:
        pass

    # 데모 모드: 단어를 1.2초간 표시 후 지움
    print(f"  [데모] {word}", end='', flush=True)
    time.sleep(1.2)
    print('\r' + ' ' * 20 + '\r', end='', flush=True)


# ── raw mode 한 글자 읽기 ─────────────────────────────────────────────────────

def _read_line_with_hotkeys(prompt: str, escape_flag: list) -> str:
    """
    일반 input()처럼 한 줄을 읽되, 다음 핫키를 지원합니다.
      ESC      → escape_flag[0] = True, 빈 문자열 반환
      W / w    → 단어 재생 요청: 'REPLAY' 반환
      ENTER    → 현재까지 입력된 내용 반환
      백스페이스 → 마지막 문자 삭제

    raw mode에서 직접 구현하므로 입력 내용이 창에 정상 표시됩니다.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    buf = []

    print(prompt, end='', flush=True)

    try:
        tty.setraw(fd)
        while True:
            r, _, _ = select.select([sys.stdin], [], [], 0.05)
            if not r:
                continue
            ch = os.read(fd, 3)

            # ESC (0x1b)
            if ch and ch[0:1] == b'\x1b':
                escape_flag[0] = True
                print()
                return ''

            # Ctrl+C
            elif ch == b'\x03':
                escape_flag[0] = True
                print()
                return ''

            # ENTER (CR 또는 LF)
            elif ch in (b'\r', b'\n'):
                print()  # 줄바꿈
                return ''.join(buf)

            # 백스페이스
            elif ch in (b'\x7f', b'\x08'):
                if buf:
                    buf.pop()
                    # 커서 한 칸 뒤로, 공백, 다시 뒤로
                    print('\b \b', end='', flush=True)

            # W / w → 재생 요청
            elif ch in (b'w', b'W'):
                # 현재 버퍼가 비어 있을 때만 재생 명령으로 처리
                # (단어를 입력 중일 때 w는 일반 문자로 처리)
                if not buf:
                    print()
                    return 'REPLAY'
                else:
                    buf.append('w' if ch == b'w' else 'W')
                    print(ch.decode('utf-8', errors='replace'), end='', flush=True)

            # 일반 문자 (UTF-8 멀티바이트 포함)
            elif ch and ch[0:1] not in (b'\x00',):
                try:
                    char = ch.decode('utf-8')
                    buf.append(char)
                    print(char, end='', flush=True)
                except UnicodeDecodeError:
                    pass

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ── 검사 메인 ─────────────────────────────────────────────────────────────────

def run_speech_test(num_words: int = 10) -> dict:
    """
    어음청력검사를 실행합니다.

    Returns:
        {
          'score':   인지도 (%),
          'total':   제시 단어 수,
          'correct': 정답 수,
          'details': [{'word', 'response', 'correct'}, ...],
        }
    """
    print("\n" + "=" * 60)
    print("  어음청력검사 (Speech Audiometry)")
    print("=" * 60)
    print("""
  단어가 재생되면 들은 그대로 입력하고 ENTER를 누르세요.
  철자가 정확해야 정답으로 인정됩니다.

    ENTER          →  답변 제출
    W              →  단어 한 번 더 재생 (입력 전 빈 칸에서)
    ESC            →  검사 중단
    아무것도 못 들었다면 그냥 ENTER
""")
    input("  준비되셨으면 ENTER를 누르세요...")

    word_list = load_word_list()
    random.shuffle(word_list)
    selected = word_list[:num_words]

    results = []
    correct_count = 0
    escape_flag = [False]   # raw mode 함수와 공유하는 ESC 플래그

    for i, (word, wav_path) in enumerate(selected, 1):
        if escape_flag[0]:
            break

        print(f"\n  [{i}/{num_words}] 잘 들어보세요...")
        play_word(word, wav_path)

        # 답변 입력 — W로 재생 반복 가능
        while True:
            response = _read_line_with_hotkeys("  들은 단어 입력 (W=다시듣기): ",
                                               escape_flag)

            if escape_flag[0]:
                print("\n  ESC — 어음검사 중단")
                break

            if response == 'REPLAY':
                print("  ♪ 다시 재생합니다...")
                play_word(word, wav_path)
                continue

            # 일반 답변
            break

        if escape_flag[0]:
            break

        is_correct = response == word
        if is_correct:
            correct_count += 1
            print("  ✓ 정답!")
        else:
            print(f"  ✗ 오답  (정답: {word})")

        results.append({
            'word':     word,
            'response': response,
            'correct':  is_correct,
        })

        time.sleep(0.5)

    total = len(results)
    score = (correct_count / total * 100) if total > 0 else 0.0
    print(f"\n  어음검사 완료: {correct_count}/{total}개 정답 ({score:.1f}%)")

    return {
        'score':   score,
        'total':   total,
        'correct': correct_count,
        'details': results,
    }