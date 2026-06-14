from app.slo.frontend_slos import (
    FRONTEND_AVAILABILITY_30D_SLO,
    FRONTEND_AVAILABILITY_5M_SLO,
    FRONTEND_LATENCY_30D_SLO,
    TRANSACTION_SUCCESS_30D_SLO,
)
from app.slo.models import SloDefinition


class SloRegistry:
    def __init__(self, slos: list[SloDefinition]) -> None:
        self._slos = {slo.id: slo for slo in slos}

    def list_slos(self) -> list[SloDefinition]:
        return list(self._slos.values())

    def get_slo(self, slo_id: str) -> SloDefinition | None:
        return self._slos.get(slo_id)

    def require_slo(self, slo_id: str) -> SloDefinition:
        slo = self.get_slo(slo_id)

        if slo is None:
            raise KeyError(f"SLO not found: {slo_id}")

        return slo


slo_registry = SloRegistry(
    slos=[
        FRONTEND_AVAILABILITY_30D_SLO,
        FRONTEND_AVAILABILITY_5M_SLO,
        FRONTEND_LATENCY_30D_SLO,
        TRANSACTION_SUCCESS_30D_SLO,
    ]
)
