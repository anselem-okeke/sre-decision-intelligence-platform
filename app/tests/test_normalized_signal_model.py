from app.signals.models import (
    NormalizedSignal,
    SignalDomain,
    SignalSeverity,
    SignalSource,
)


def test_normalized_signal_model_accepts_workload_signal():
    signal = NormalizedSignal(
        name="frontend_5xx_rate",
        domain=SignalDomain.WORKLOAD,
        source=SignalSource.PROMETHEUS,
        service="frontend",
        namespace="fintech-workload",
        value=0.12,
        unit="ratio",
        severity=SignalSeverity.WARNING,
        meaning="Frontend is returning elevated 5xx responses",
    )

    assert signal.name == "frontend_5xx_rate"
    assert signal.domain == SignalDomain.WORKLOAD
    assert signal.source == SignalSource.PROMETHEUS
    assert signal.severity == SignalSeverity.WARNING


def test_normalized_signal_model_accepts_platform_signal():
    signal = NormalizedSignal(
        name="pod_crashloop",
        domain=SignalDomain.PLATFORM,
        source=SignalSource.KUBERNETES,
        service="frontend",
        namespace="fintech-workload",
        value=True,
        unit="boolean",
        severity=SignalSeverity.CRITICAL,
        meaning="Frontend pod is repeatedly crashing",
    )

    assert signal.name == "pod_crashloop"
    assert signal.domain == SignalDomain.PLATFORM
    assert signal.source == SignalSource.KUBERNETES
    assert signal.severity == SignalSeverity.CRITICAL
