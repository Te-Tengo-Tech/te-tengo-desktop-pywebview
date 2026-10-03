"""Búfer del clip del evento: guarda los fotogramas de 6 s antes y 6 s después del evento.

Así el familiar puede ver qué pasó justo antes y justo después de la alerta.
"""

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Clip:
    evento_id: str
    instante_evento: float
    fotogramas: list[tuple[float, bytes]]


class BufferClip:
    """Guarda los fotogramas recientes y arma el clip cuando pasan los segundos posteriores."""

    def __init__(self, segundos_antes: float = 6.0, segundos_despues: float = 6.0) -> None:
        self._antes = segundos_antes
        self._despues = segundos_despues
        self._fotogramas: deque[tuple[float, bytes]] = deque()
        self._pendientes: list[tuple[str, float]] = []

    def agregar(self, instante: float, jpeg: bytes) -> list[Clip]:
        """Agrega un fotograma y devuelve los clips que quedaron completos."""
        self._fotogramas.append((instante, jpeg))
        listos = [(eid, t) for eid, t in self._pendientes if instante >= t + self._despues]
        self._pendientes = [(eid, t) for eid, t in self._pendientes if instante < t + self._despues]
        clips = [self._armar(eid, t) for eid, t in listos]
        self._podar(instante)
        return clips

    def marcar_evento(self, evento_id: str, instante: float) -> None:
        self._pendientes.append((evento_id, instante))

    def _armar(self, evento_id: str, instante: float) -> Clip:
        desde, hasta = instante - self._antes, instante + self._despues
        return Clip(
            evento_id,
            instante,
            [(t, f) for t, f in self._fotogramas if desde <= t <= hasta],
        )

    def _podar(self, instante: float) -> None:
        # Conserva lo necesario para el clip pendiente más antiguo o, si no hay, los últimos
        # ``segundos_antes``.
        referencia = min([t for _, t in self._pendientes], default=instante)
        limite = referencia - self._antes
        while self._fotogramas and self._fotogramas[0][0] < limite:
            self._fotogramas.popleft()
