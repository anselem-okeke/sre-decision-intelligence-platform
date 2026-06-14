from app.signals.frontend_availability import normalize_frontend_availability_signals
from app.signals.models import SignalDomain, SignalSeverity, SignalSource


def test_frontend_availability_normalizer_creates_workload_and_platform_signals():
    raw_signals = {
        "probe_success": 0.0,
        "frontend_availability_5m": 0.6,
        "alert_state": "pending",
        "frontend_endpoints": "none",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 13,
    }

    normalized = normalize_frontend_availability_signals(raw_signals)

    names = {signal.name for signal in normalized}
    domains = {signal.domain for signal in normalized}
    sources = {signal.source for signal in normalized}

    assert "probe_success" in names
    assert "frontend_endpoints" in names

    assert SignalDomain.WORKLOAD in domains
    assert SignalDomain.PLATFORM in domains

    assert SignalSource.PROMETHEUS in sources
    assert SignalSource.KUBERNETES in sources
    assert SignalSource.OPENSEARCH in sources


def test_frontend_availability_normalizer_marks_broken_endpoint_as_critical():
    raw_signals = {
        "probe_success": 0.0,
        "frontend_availability_5m": 0.6,
        "alert_state": "pending",
        "frontend_endpoints": "none",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 13,
    }

    normalized = normalize_frontend_availability_signals(raw_signals)

    endpoint_signal = next(
        signal for signal in normalized if signal.name == "frontend_endpoints"
    )
    probe_signal = next(
        signal for signal in normalized if signal.name == "probe_success"
    )

    assert endpoint_signal.domain == SignalDomain.PLATFORM
    assert endpoint_signal.severity == SignalSeverity.CRITICAL

    assert probe_signal.domain == SignalDomain.WORKLOAD
    assert probe_signal.severity == SignalSeverity.CRITICAL


def test_frontend_availability_normalizer_marks_healthy_endpoint_as_info():
    raw_signals = {
        "probe_success": 1.0,
        "frontend_availability_5m": 1.0,
        "alert_state": "inactive",
        "frontend_endpoints": "10.244.8.229:8080",
        "frontend_pod_ready": True,
        "frontend_pod_status": "1/1 Running",
        "frontend_logs": "mostly INFO",
        "frontend_error_log_count": 0,
    }

    normalized = normalize_frontend_availability_signals(raw_signals)

    endpoint_signal = next(
        signal for signal in normalized if signal.name == "frontend_endpoints"
    )
    probe_signal = next(
        signal for signal in normalized if signal.name == "probe_success"
    )

    assert endpoint_signal.severity == SignalSeverity.INFO
    assert probe_signal.severity == SignalSeverity.INFO
