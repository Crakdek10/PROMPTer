from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import urlparse

@dataclass(frozen=True)
class AudioConstraints:
    allowed_formats: tuple[str, ...] = ("pcm16",)
    min_sample_rate: int = 8000
    max_sample_rate: int = 48000

    max_audio_bytes_per_chunk: int = 5 * 1024 * 1024

    required_sample_rate: Optional[int] = None

DEFAULT_AUDIO_CONSTRAINTS = AudioConstraints()

def validate_sample_rate(sr: object, c: AudioConstraints = DEFAULT_AUDIO_CONSTRAINTS) -> int:
    if not isinstance(sr, int):
        raise ValueError("Invalid sample_rate")
    if sr <= 0:
        raise ValueError("Invalid sample_rate")

    if c.required_sample_rate is not None:
        if sr != c.required_sample_rate:
            raise ValueError(f"Invalid sample_rate (expected {c.required_sample_rate})")
        return sr

    if sr < c.min_sample_rate or sr > c.max_sample_rate:
        raise ValueError(f"Invalid sample_rate (allowed {c.min_sample_rate}-{c.max_sample_rate})")
    return sr

def validate_format(fmt: object, c: AudioConstraints = DEFAULT_AUDIO_CONSTRAINTS) -> str:
    if not isinstance(fmt, str) or not fmt:
        raise ValueError("Invalid format")
    if fmt not in c.allowed_formats:
        allowed = ",".join(c.allowed_formats)
        raise ValueError(f"Only format={allowed} supported")
    return fmt

def validate_b64_string(data: object) -> str:
    if not isinstance(data, str) or not data:
        raise ValueError("Missing audio data")
    return data

def validate_audio_bytes_size(audio_bytes: bytes, c: AudioConstraints = DEFAULT_AUDIO_CONSTRAINTS) -> None:
    if len(audio_bytes) > c.max_audio_bytes_per_chunk:
        raise ValueError("Audio chunk too large")

def validate_url(url: object, allowed_schemes: Iterable[str] = ("http", "https")) -> str:
    if not isinstance(url, str) or not url:
        raise ValueError("Invalid URL")
    p = urlparse(url)
    if p.scheme not in set(allowed_schemes):
        raise ValueError(f"Invalid URL scheme (allowed: {', '.join(allowed_schemes)})")
    if not p.netloc:
        raise ValueError("Invalid URL host")
    return url