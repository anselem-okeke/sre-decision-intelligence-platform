import httpx

from app.collectors.prometheus import PrometheusCollector


class MockTransport:
    def __init__(self, value: str):
        self.value = value

    def __call__(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {
                            "metric": {},
                            "value": [1710000000.0, self.value],
                        }
                    ],
                },
            },
        )


def test_prometheus_get_instant_value(monkeypatch):
    transport = httpx.MockTransport(MockTransport("0"))

    def mock_get(url, params, timeout):
        with httpx.Client(transport=transport) as client:
            return client.get(url, params=params)

    monkeypatch.setattr(httpx, "get", mock_get)

    collector = PrometheusCollector("http://prometheus.example")
    value = collector.get_instant_value("probe_success")

    assert value == 0.0
