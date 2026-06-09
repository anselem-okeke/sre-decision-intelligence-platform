from app.collectors.kubernetes import KubernetesCollector


def test_kubernetes_collector_combines_frontend_signals(monkeypatch):
    monkeypatch.setattr(KubernetesCollector, "_load_config", lambda self: None)

    collector = KubernetesCollector(
        namespace="fintech-workload",
        service_name="frontend",
        app_label="frontend",
    )

    monkeypatch.setattr(collector, "get_service_endpoints", lambda: "none")
    monkeypatch.setattr(collector, "get_frontend_pod_status", lambda: (True, "1/1 Running"))

    signals = collector.collect_frontend_kubernetes_signals()

    assert signals["frontend_endpoints"] == "none"
    assert signals["frontend_pod_ready"] is True
    assert signals["frontend_pod_status"] == "1/1 Running"
