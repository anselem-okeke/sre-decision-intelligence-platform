from typing import Any

from app.collectors.kubernetes import KubernetesCollector
from app.collectors.opensearch import OpenSearchCollector
from app.collectors.prometheus import PrometheusCollector
from app.config import settings


def collect_frontend_availability_live_signals() -> dict[str, Any]:
    prometheus = PrometheusCollector(settings.prometheus_base_url)
    kubernetes = KubernetesCollector(
        namespace=settings.workload_namespace,
        service_name=settings.frontend_service_name,
        app_label=settings.frontend_app_label,
    )
    opensearch = OpenSearchCollector(settings.opensearch_base_url)

    signals: dict[str, Any] = {}

    signals.update(prometheus.collect_frontend_availability_signals())
    signals.update(kubernetes.collect_frontend_kubernetes_signals())
    signals.update(opensearch.collect_frontend_log_signals(settings.workload_namespace))

    return signals
