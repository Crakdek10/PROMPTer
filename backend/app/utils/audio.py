from __future__ import annotations
import base64

def pcm16_duration_seconds(num_bytes: int, sample_rate: int, channels: int = 1) -> float:
    if sample_rate <= 0 or channels <= 0:
        return 0.0
    return num_bytes / (sample_rate * channels * 2)

def estimate_pcm16_bytes(seconds: float, sample_rate: int, channels: int = 1) -> int:
    if seconds <= 0 or sample_rate <= 0 or channels <= 0:
        return 0
    return int(seconds * sample_rate * channels * 2)

def chunk_bytes(data: bytes, chunk_size: int) -> list[bytes]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

def bytes_to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")