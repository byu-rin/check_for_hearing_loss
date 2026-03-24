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

# 시도할 샘플레이트 우선순위 목록
# 이어폰/블루투스 장치가 44100을 지원 안 할 경우 순서대로 시도
_FALLBACK_SAMPLE_RATES = [44100, 48000, 22050, 16000]

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


def _get_supported_sample_rate(device_index) -> int:
    """
    장치가 실제로 지원하는 샘플레이트를 반환합니다.
 
    macOS에서 이어폰을 꽂으면 장치가 전환되면서 44100 Hz를
    지원하지 않는 경우가 있습니다 (특히 블루투스/USB 이어폰).
    이 함수는 우선순위 목록을 순서대로 시도해 사용 가능한
    첫 번째 샘플레이트를 반환합니다.
 
    Args:
        device_index: sd.query_devices() 장치 인덱스
 
    Returns:
        사용 가능한 샘플레이트 (int). 모두 실패하면 44100 반환.
    """
    if device_index is None:
        return SAMPLE_RATE
 
    for rate in _FALLBACK_SAMPLE_RATES:
        try:
            sd.check_output_settings(device=device_index, samplerate=rate, channels=2)
            return rate
        except Exception:
            continue
 
    # 마지막 수단: 장치 기본 샘플레이트 사용
    try:
        device_info = sd.query_devices(device_index)
        default_rate = int(device_info.get('default_samplerate', SAMPLE_RATE))
        return default_rate
    except Exception:
        return SAMPLE_RATE


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

             # 매 재생마다 장치 지원 샘플레이트를 확인
            # 이어폰 연결/해제로 장치가 바뀌면 지원 샘플레이트도 달라질 수 있음
            actual_rate = _get_supported_sample_rate(device)

            # 샘플레이트가 바뀐 경우에만 tone 재생성 (성능 최적화)
            tone = generate_tone(frequency, duration, db_hl, ear, actual_rate)

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
                # 여기서 raise하지 않고 조용히 넘어가

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
    # import struct

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

        # ★ 핵심 수정: WAV 재생 시에도 장치 지원 샘플레이트 확인
    device = _get_audio_device()
    actual_rate = _get_supported_sample_rate(device)
 
    # WAV 원본 샘플레이트와 장치 지원 샘플레이트가 다르면 리샘플링
    if frame_rate != actual_rate:
        data = _resample(data, frame_rate, actual_rate)
 
    sd.play(data, samplerate=frame_rate)
    sd.wait()


def _resample(data: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    """
    선형 보간으로 오디오 데이터를 리샘플링합니다.
 
    numpy만 사용하는 간단한 구현으로, scipy 없이 동작합니다.
    청력검사용 단순 음성에는 충분한 품질을 제공합니다.
 
    Args:
        data:        원본 오디오 배열 (1D 또는 2D)
        orig_rate:   원본 샘플레이트
        target_rate: 목표 샘플레이트
 
    Returns:
        리샘플링된 배열
    """
    if orig_rate == target_rate:
        return data
 
    ratio = target_rate / orig_rate
 
    if data.ndim == 1:
        n_out = int(len(data) * ratio)
        x_old = np.linspace(0, 1, len(data))
        x_new = np.linspace(0, 1, n_out)
        return np.interp(x_new, x_old, data).astype(np.float32)
    else:
        # 다채널: 채널별로 리샘플링 후 합치기
        n_out = int(data.shape[0] * ratio)
        x_old = np.linspace(0, 1, data.shape[0])
        x_new = np.linspace(0, 1, n_out)
        channels = [np.interp(x_new, x_old, data[:, ch]) for ch in range(data.shape[1])]
        return np.column_stack(channels).astype(np.float32)