import math
import struct
import threading
import time
import wave
from pathlib import Path
from typing import Optional

from config import (
    AUDIO_CHANNELS,
    AUDIO_FRAMES_PER_BUFFER,
    AUDIO_SAMPLE_RATE,
    AUDIO_SAMPLE_WIDTH,
    DEV_MODE,
)

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception:
    NUMPY_AVAILABLE = False

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except Exception:
    PYAUDIO_AVAILABLE = False


def _compute_rms(data: bytes) -> float:
    if NUMPY_AVAILABLE:
        import numpy as np
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        rms = float(np.sqrt(np.mean(samples ** 2))) / 32768.0
        return min(rms * 4.0, 1.0)
    # fallback without numpy
    n = len(data) // 2
    if n == 0:
        return 0.0
    total = sum(
        struct.unpack_from("<h", data, i * 2)[0] ** 2 for i in range(n)
    )
    return min(math.sqrt(total / n) / 32768.0 * 4.0, 1.0)


class AudioRecorder:
    """Real PyAudio recorder. Pause skips frames — no silence recorded."""

    def __init__(self, output_path: Path) -> None:
        self._path = output_path
        self._pa = None
        self._stream = None
        self._wav: Optional[wave.Wave_write] = None
        self._lock = threading.Lock()
        self._paused = False
        self._running = False
        self._latest_rms: float = 0.0
        self._record_start: Optional[float] = None
        self._accumulated: float = 0.0

    def start(self) -> None:
        self._pa = pyaudio.PyAudio()
        self._wav = wave.open(str(self._path), "wb")
        self._wav.setnchannels(AUDIO_CHANNELS)
        self._wav.setsampwidth(AUDIO_SAMPLE_WIDTH)
        self._wav.setframerate(AUDIO_SAMPLE_RATE)
        self._stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_SAMPLE_RATE,
            input=True,
            frames_per_buffer=AUDIO_FRAMES_PER_BUFFER,
            stream_callback=self._callback,
        )
        with self._lock:
            self._record_start = time.monotonic()
            self._running = True
        self._stream.start_stream()

    def _callback(self, in_data, frame_count, time_info, status):
        with self._lock:
            if self._running and not self._paused:
                self._wav.writeframes(in_data)
                self._latest_rms = _compute_rms(in_data)
            else:
                self._latest_rms = 0.0
        return (in_data, pyaudio.paContinue)

    def pause(self) -> None:
        with self._lock:
            if self._paused or not self._running:
                return
            self._paused = True
            if self._record_start is not None:
                self._accumulated += time.monotonic() - self._record_start
                self._record_start = None

    def resume(self) -> None:
        with self._lock:
            if not self._paused:
                return
            self._paused = False
            self._record_start = time.monotonic()

    def stop(self) -> int:
        with self._lock:
            if not self._paused and self._record_start is not None:
                self._accumulated += time.monotonic() - self._record_start
            self._running = False
            self._record_start = None
            duration = self._accumulated

        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._pa:
            self._pa.terminate()
        if self._wav:
            self._wav.close()

        return max(1, int(round(duration)))

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._running and not self._paused

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._running and self._paused

    @property
    def latest_rms(self) -> float:
        with self._lock:
            return self._latest_rms

    @property
    def elapsed_seconds(self) -> float:
        with self._lock:
            base = self._accumulated
            if not self._paused and self._record_start is not None:
                base += time.monotonic() - self._record_start
            return base


class MockAudioRecorder:
    """Fake recorder for DEV_MODE or when PyAudio is unavailable."""

    def __init__(self, output_path: Path) -> None:
        self._path = output_path
        self._paused = False
        self._running = False
        self._start_time: Optional[float] = None
        self._accumulated: float = 0.0
        self._tick = 0
        self._write_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._start_time = time.monotonic()
        self._write_thread = threading.Thread(target=self._generate_wav, daemon=True)
        self._write_thread.start()

    def _generate_wav(self) -> None:
        chunk = AUDIO_FRAMES_PER_BUFFER
        chunk_duration = chunk / AUDIO_SAMPLE_RATE
        t = 0.0
        with wave.open(str(self._path), "wb") as wav:
            wav.setnchannels(AUDIO_CHANNELS)
            wav.setsampwidth(AUDIO_SAMPLE_WIDTH)
            wav.setframerate(AUDIO_SAMPLE_RATE)
            while self._running:
                if not self._paused:
                    frames = b"".join(
                        struct.pack(
                            "<h",
                            max(-32768, min(32767,
                                int(8000 * math.sin(2 * math.pi * 440 * (t + i / AUDIO_SAMPLE_RATE)))
                            ))
                        )
                        for i in range(chunk)
                    )
                    wav.writeframes(frames)
                    t += chunk_duration
                time.sleep(chunk_duration)

    def pause(self) -> None:
        if self._paused:
            return
        self._paused = True
        if self._start_time is not None:
            self._accumulated += time.monotonic() - self._start_time
            self._start_time = None

    def resume(self) -> None:
        if not self._paused:
            return
        self._paused = False
        self._start_time = time.monotonic()

    def stop(self) -> int:
        if not self._paused and self._start_time is not None:
            self._accumulated += time.monotonic() - self._start_time
        self._running = False
        return max(1, int(round(self._accumulated)))

    @property
    def is_recording(self) -> bool:
        return self._running and not self._paused

    @property
    def is_paused(self) -> bool:
        return self._running and self._paused

    @property
    def latest_rms(self) -> float:
        self._tick += 1
        return abs(math.sin(self._tick * 0.15)) * 0.6 + 0.1

    @property
    def elapsed_seconds(self) -> float:
        base = self._accumulated
        if not self._paused and self._start_time is not None:
            base += time.monotonic() - self._start_time
        return base


def make_recorder(output_path: Path):
    if PYAUDIO_AVAILABLE and not DEV_MODE:
        return AudioRecorder(output_path)
    return MockAudioRecorder(output_path)
