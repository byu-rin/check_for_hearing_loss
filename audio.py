"""
audio.py — 순음 생성 및 오디오 재생 유틸리티

DSP 설명:
  - 순음청력검사에는 단순 사인파를 사용합니다.
  - dB HL → 진폭 변환 공식: amplitude = 10^(dB / 20)
    기준 진폭(REFERENCE_AMPLITUDE)은 0.001 (헤드폰 출력에 안전한 수준).
  - 클릭 잡음 방지를 위해 음 시작/끝에 5ms Hanning 램프를 적용합니다.
  - 스테레오 출력: 왼쪽(L) 또는 오른쪽(R) 귀 선택 지원.
  - volume_scale: 환자에게 맞는 음량을 보정하는 전역 배율 (0.0 ~ 2.0).
"""

import numpy as np
import sounddevice as sd
import sys

# 0 dB HL에 해당하는 기준 진폭 (상대 스케일)
# 실제 임상 사용 시에는 음압계로 캘리브레이션 필요
REFERENCE_AMPLITUDE = 0.001
SAMPLE_RATE = 44100  # Hz

# 전역 음량 배율 — run_volume_calibration()에서 조정됨
volume_scale: float = 1.0


def _get_audio_device():
    """Mac/Windows에서 기본 오디오 장치를 자동으로 감지합니다 (PyInstaller 호환성)."""
    try:
        devices = sd.query_devices()
        default_out = sd.default.device[1]  # 기본 출력 장치 인덱스
        
        # 유효한 장치 확인
        if 0 <= default_out < len(devices) and devices[default_out]['max_output_channels'] > 0:
            return default_out
    except Exception:
        pass
    
    # 폴백: 첫 번째 유효한 출력 장치 찾기
    try:
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev['max_output_channels'] > 0:
                return i
    except Exception:
        pass
    
    return None


def set_volume_scale(scale: float) -> None:
    """전역 음량 배율을 설정합니다. (0.1 ~ 2.0 범위 권장)"""
    global volume_scale
    volume_scale = max(0.01, float(scale))


def db_to_amplitude(db_hl: float) -> float:
    """dB HL을 선형 진폭으로 변환합니다 (20 log 법칙 적용)."""
    return REFERENCE_AMPLITUDE * (10 ** (db_hl / 20.0)) * volume_scale


def generate_tone(frequency: float, duration: float, db_hl: float,
                  ear: str = '양쪽',
                  sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    순음 사인파를 스테레오로 생성합니다.

    Args:
        frequency:   주파수 (Hz)
        duration:    재생 시간 (초)
        db_hl:       제시 레벨 (dB HL)
        ear:         재생 귀 — '오른쪽', '왼쪽', '양쪽'
        sample_rate: 샘플레이트

    Returns:
        shape=(samples, 2)인 float32 스테레오 배열
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    amplitude = db_to_amplitude(db_hl)
    mono = amplitude * np.sin(2 * np.pi * frequency * t)

    # 5ms Hanning 램프 — 클릭 잡음 방지
    ramp_samples = int(0.005 * sample_rate)
    ramp = np.hanning(ramp_samples * 2)
    mono[:ramp_samples] *= ramp[:ramp_samples]
    mono[-ramp_samples:] *= ramp[ramp_samples:]

    # 스테레오 채널 배분
    # sounddevice/대부분의 오디오 드라이버 규약:
    #   채널 0 = 왼쪽(L), 채널 1 = 오른쪽(R)
    stereo = np.zeros((len(mono), 2), dtype=np.float32)
    if ear == '오른쪽':
        stereo[:, 1] = mono   # 채널 1 = 오른쪽(R)
    elif ear == '왼쪽':
        stereo[:, 0] = mono   # 채널 0 = 왼쪽(L)
    else:
        stereo[:, 0] = mono   # 양쪽 동일
        stereo[:, 1] = mono

    return stereo


def play_tone(frequency: float, duration: float, db_hl: float,
              ear: str = '양쪽',
              sample_rate: int = SAMPLE_RATE,
              max_retries: int = 2) -> None:
    """
    순음을 동기 방식으로 재생합니다 (재생 완료까지 블로킹).
    PyInstaller 환경에서도 안정적으로 작동하도록 개선됨.

    Args:
        frequency:   주파수 (Hz)
        duration:    재생 시간 (초)
        db_hl:       레벨 (dB HL)
        ear:         재생 귀 — '오른쪽', '왼쪽', '양쪽'
        sample_rate: 샘플레이트
        max_retries: 실패 시 재시도 횟수
    """
    import time
    
    tone = generate_tone(frequency, duration, db_hl, ear, sample_rate)
    
    for attempt in range(max_retries):
        try:
            device = _get_audio_device()
            sd.play(tone, samplerate=sample_rate, device=device)
            sd.wait()
            return  # 성공
        except sd.PortAudioError as e:
            if attempt < max_retries - 1:
                # 재시도 전 잠시 대기 (장치 초기화 시간)
                time.sleep(0.5)
            else:
                # 모든 재시도 실패 → 에러 메시지 출력하고 계속 진행
                print(f"\n[오디오 경고] 스피커에서 음성 재생 실패 (재시도 {max_retries}회 실패):", file=sys.stderr)
                print(f"  {str(e)}", file=sys.stderr)
                print("  헤드폰/스피커 연결을 확인해 주세요.\n", file=sys.stderr)
                # 여기서 raise하지 않고 조용히 넘어감 (사용자 경험 개선)
        except Exception as e:
            print(f"\n[오디오 오류] 예상치 못한 오류: {str(e)}", file=sys.stderr)
            if attempt >= max_retries - 1:
                raise


def play_wav(filepath: str) -> None:
    """
    WAV 파일을 동기 방식으로 재생합니다.

    Args:
        filepath: .wav 파일 경로
    """
    import wave
    import struct

    with wave.open(filepath, 'rb') as wf:
        n_channels  = wf.getnchannels()
        samp_width  = wf.getsampwidth()   # bytes per sample
        frame_rate  = wf.getframerate()
        n_frames    = wf.getnframes()
        raw_data    = wf.readframes(n_frames)

    # 바이트 데이터 → numpy 배열
    if samp_width == 2:       # 16-bit PCM (가장 일반적)
        data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
    elif samp_width == 4:     # 32-bit PCM
        data = np.frombuffer(raw_data, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif samp_width == 1:     # 8-bit PCM (부호 없음)
        data = (np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"지원하지 않는 샘플 폭: {samp_width} bytes")
 
    # 스테레오 reshape (채널 수에 따라)
    if n_channels > 1:
        data = data.reshape(-1, n_channels)
 
    sd.play(data, samplerate=frame_rate)
    sd.wait()