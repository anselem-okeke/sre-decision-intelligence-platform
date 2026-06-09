import httpx

from app.collectors.opensearch import OpenSearchCollector


class MockTransport:
    def __call__(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "hits": {
                    "total": {
                        "value": 10
                    }
                }
            },
        )


def test_opensearch_collects_frontend_log_signals(monkeypatch):
    transport = httpx.MockTransport(MockTransport())

    def mock_post(url, json, timeout):
        with httpx.Client(transport=transport) as client:
            return client.post(url, json=json)

    monkeypatch.setattr(httpx, "post", mock_post)

    collector = OpenSearchCollector("http://opensearch.example")
    signals = collector.collect_frontend_log_signals("fintech-workload")

    assert signals["frontend_error_log_count"] == 10
    assert signals["frontend_logs"] == "mostly INFO"
