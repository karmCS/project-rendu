import time
import wave
from pathlib import Path

import pytest

from services.audio import MockAudioRecorder


def test_mock_recorder_writes_valid_wav(tmp_path):
    path = tmp_path / "test.wav"
    recorder = MockAudioRecorder(path)
    recorder.start()
    time.sleep(0.5)
    duration = recorder.stop()

    assert path.exists(), "WAV file should be created"
    with wave.open(str(path), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 16000
        assert wav.getnframes() > 0


def test_mock_recorder_duration_excludes_pause(tmp_path):
    path = tmp_path / "test.wav"
    recorder = MockAudioRecorder(path)
    recorder.start()
    time.sleep(0.3)
    recorder.pause()
    time.sleep(0.5)  # paused — should not count
    recorder.resume()
    time.sleep(0.3)
    duration = recorder.stop()

    # ~0.6s of actual recording, well under 1.2s total elapsed
    assert duration >= 1, "At least 1 second recorded"
    assert duration <= 3, "Should not include pause time significantly"


def test_mock_recorder_is_recording_state(tmp_path):
    path = tmp_path / "test.wav"
    recorder = MockAudioRecorder(path)
    assert not recorder.is_recording
    recorder.start()
    assert recorder.is_recording
    assert not recorder.is_paused
    recorder.pause()
    assert not recorder.is_recording
    assert recorder.is_paused
    recorder.resume()
    assert recorder.is_recording
    recorder.stop()
    assert not recorder.is_recording


def test_mock_recorder_rms_animates(tmp_path):
    path = tmp_path / "test.wav"
    recorder = MockAudioRecorder(path)
    recorder.start()
    values = [recorder.latest_rms for _ in range(10)]
    recorder.stop()
    # RMS should be non-zero and vary
    assert all(0.0 <= v <= 1.0 for v in values)
    assert len(set(values)) > 1, "RMS should vary (animated)"


def test_mock_recorder_elapsed_counts_while_recording(tmp_path):
    path = tmp_path / "test.wav"
    recorder = MockAudioRecorder(path)
    recorder.start()
    time.sleep(0.2)
    e1 = recorder.elapsed_seconds
    time.sleep(0.2)
    e2 = recorder.elapsed_seconds
    recorder.stop()
    assert e2 > e1


def test_mock_recorder_elapsed_frozen_while_paused(tmp_path):
    path = tmp_path / "test.wav"
    recorder = MockAudioRecorder(path)
    recorder.start()
    time.sleep(0.1)
    recorder.pause()
    e1 = recorder.elapsed_seconds
    time.sleep(0.2)
    e2 = recorder.elapsed_seconds
    recorder.stop()
    assert abs(e2 - e1) < 0.05, "Elapsed should not advance while paused"
