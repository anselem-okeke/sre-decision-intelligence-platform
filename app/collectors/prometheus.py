from typing import Any

import httpx


class PrometheusCollector:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def query(self, promql: str) -> dict[str, Any]:
        url = f"{self.base_url}/api/v1/query"
        response = httpx.get(url, params={"query": promql}, timeout=10.0)
        response.raise_for_status()
        return response.json()

    def get_instant_value(self, promql: str) -> float | str | None:
        data = self.query(promql)

        results = data.get("data", {}).get("result", [])
        if not results:
            return None

        value = results[0].get("value", [])
        if len(value) < 2:
            return None

        raw_value = value[1]

        try:
            return float(raw_value)
        except ValueError:
            return raw_value

    def collect_frontend_availability_signals(self) -> dict[str, Any]:
        probe_success = self.get_instant_value(
            'probe_success{job="bank-of-anthos-frontend"}'
        )

        availability = self.get_instant_value(
            'avg_over_time(probe_success{job="bank-of-anthos-frontend"}[5m])'
        )

        alert_active = self.get_instant_value(
            'ALERTS{alertname="BankOfAnthosFrontendAvailabilitySLOBreach",alertstate="pending"}'
        )

        return {
            "probe_success": probe_success,
            "frontend_availability_5m": availability,
            "alert_state": "pending" if alert_active == 1 else "inactive",
        }
