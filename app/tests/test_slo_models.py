from app.slo.registry import slo_registry


def test_slo_registry_lists_defined_slos():
    slos = slo_registry.list_slos()
    slo_ids = {slo.id for slo in slos}

    assert "frontend-availability-30d" in slo_ids
    assert "frontend-availability-5m" in slo_ids
    assert "frontend-latency-30d" in slo_ids
    assert "transaction-success-30d" in slo_ids


def test_frontend_availability_slo_has_expected_target():
    slo = slo_registry.require_slo("frontend-availability-30d")

    assert slo.target == 0.995
    assert slo.sli.id == "frontend-availability"
    assert slo.sli.signal_name == "frontend_availability_5m"
    assert slo.window == "30d"
