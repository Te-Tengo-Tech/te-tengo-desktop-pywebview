"""Live view on demand (US-23): the interface the capture loop feeds.

Blocked: how the agent learns about a live-view request and where it sends the stream depend on
the transport decision recorded in ``docs/BLOCKERS.md``. Until then the agent uses
``TransmisorNulo``. A real transmitter only has to implement this protocol: the capture loop
hands it every processed frame (480p JPEG, 8 fps) while ``activo`` is true. Frames only flow
while capture is allowed, so a paused camera or one without consent never streams (CA-23.4),
and a disconnected webcam produces no frames (CA-23.3).
"""

from typing import Protocol

from te_tengo_captura.captura.fuentes import Fotograma


class TransmisorEnVivo(Protocol):
    @property
    def activo(self) -> bool:
        """A family member is watching right now."""
        ...

    def enviar(self, fotograma: Fotograma) -> None:
        """Must not block the capture loop (queue the frame, drop it if behind)."""
        ...


class TransmisorNulo:
    """No live view until the transport is decided."""

    activo = False

    def enviar(self, fotograma: Fotograma) -> None:
        pass
