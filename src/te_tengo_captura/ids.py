"""UUID version 7 (RFC 9562): time-ordered identifiers for events (``eventoId``)."""

import os
import time
import uuid
from collections.abc import Callable


def _ahora_ms() -> int:
    return time.time_ns() // 1_000_000


def uuid7(
    reloj_ms: Callable[[], int] = _ahora_ms, aleatorio: Callable[[int], bytes] = os.urandom
) -> str:
    """48 bits of Unix time in ms, version 7, 74 random bits and the RFC 4122 variant."""
    ms = reloj_ms()
    azar = int.from_bytes(aleatorio(10), "big")
    valor = (ms & 0xFFFF_FFFF_FFFF) << 80
    valor |= 0x7 << 76  # version
    valor |= ((azar >> 62) & 0xFFF) << 64  # rand_a, 12 bits
    valor |= 0b10 << 62  # variant
    valor |= azar & ((1 << 62) - 1)  # rand_b, 62 bits
    return str(uuid.UUID(int=valor))
