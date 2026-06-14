from typing import Any

from app.signals.models import (
    NormalizedSignal,
    SignalDomain,
    SignalSeverity,
    SignalSource,
)


def severity_from_probe_success(value: float | int | None) -> SignalSeverity:
    if value == 1 or value == 1.0:
        return SignalSeverity.INFO

    if value == 0 or value == 0.0:
        return SignalSeverity.CRITICAL

    return SignalSeverity.UNKNOWN


def severity_from_availability(value: float | int | None) -> SignalSeverity:
    if value is None:
        return SignalSeverity.UNKNOWN

    if value < 0.95:
        return SignalSeverity.CRITICAL

    if value < 0.99:
        return SignalSeverity.WARNING

    return SignalSeverity.INFO


def severity_from_endpoints(value: Any) -> SignalSeverity:
    if value == "none":
        return SignalSeverity.CRITICAL

    if value:
        return SignalSeverity.INFO

    return SignalSeverity.UNKNOWN


def severity_from_boolean_health(value: bool | None) -> SignalSeverity:
    if value is True:
        return SignalSeverity.INFO

    if value is False:
        return SignalSeverity.CRITICAL

    return SignalSeverity.UNKNOWN


def make_signal(
    name: str,
    domain: SignalDomain,
    source: SignalSource,
    value: Any,
    meaning: str,
    service: str | None = None,
    namespace: str | None = None,
    unit: str | None = None,
    severity: SignalSeverity = SignalSeverity.UNKNOWN,
    labels: dict[str, Any] | None = None,
    raw: dict[str, Any] | None = None,
) -> NormalizedSignal:
    return NormalizedSignal(
        name=name,
        domain=domain,
        source=source,
        service=service,
        namespace=namespace,
        value=value,
        unit=unit,
        severity=severity,
        meaning=meaning,
        labels=labels or {},
        raw=raw,
    )