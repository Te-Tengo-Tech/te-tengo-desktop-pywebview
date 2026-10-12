"""«Alert in progress» as the PC can know it (US-43, CA-43.9: an update never interrupts it).

The family closes an alert in the app («Atendida», «Falsa alarma», US-19) and the agent contract
does not tell the PC, so the PC only knows what it detected itself: an alert is in progress from
the moment its camera detected a fall (``caida`` or ``caida_confirmada``) until it detected the
person getting up (``recuperacion``) or ``DURACION_S`` passed since the last fall event, whichever
comes first. ``docs/BLOCKERS.md`` records this choice.
"""

import threading
import time
from collections.abc import Callable, Iterable

from te_tengo_deteccion.clasificacion.estados import TipoEvento

DURACION_S = 30 * 60.0  # implementation choice: longer than any fall confirmation (30 s)
INICIAN = frozenset({TipoEvento.CAIDA, TipoEvento.CAIDA_CONFIRMADA})


class SeguimientoAlerta:
    """One camera's alert in progress, fed with the event types its capture loop detects."""

    def __init__(self, reloj: Callable[[], float] = time.monotonic) -> None:
        self._reloj = reloj
        self._candado = threading.Lock()
        self._desde: float | None = None

    def observar(self, tipos: Iterable[TipoEvento]) -> None:
        for tipo in tipos:
            with self._candado:
                if tipo in INICIAN:
                    self._desde = self._reloj()
                elif tipo is TipoEvento.RECUPERACION:
                    self._desde = None

    @property
    def en_curso(self) -> bool:
        with self._candado:
            desde = self._desde
        return desde is not None and self._reloj() - desde < DURACION_S
