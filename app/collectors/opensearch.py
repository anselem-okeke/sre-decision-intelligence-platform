from typing import Any

import httpx


class OpenSearchCollector:
    def __init__(self, base_url: str, index_pattern: str = "k8s-logs-*"):
        self.base_url = base_url.rstrip("/")
        self.index_pattern = index_pattern

    def search(self, query: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{self.index_pattern}/_search"
        response = httpx.post(url, json=query, timeout=10.0)
        response.raise_for_status()
        return response.json()

    def count_frontend_error_logs(self, namespace: str) -> int:
        query = {
            "size": 0,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"kubernetes.namespace_name": namespace}},
                        {"match": {"severity": "ERROR"}},
                    ]
                }
            },
        }

        data = self.search(query)
        return int(data.get("hits", {}).get("total", {}).get("value", 0))

    def collect_frontend_log_signals(self, namespace: str) -> dict[str, Any]:
        error_count = self.count_frontend_error_logs(namespace)

        return {
            "frontend_error_log_count": error_count,
            "frontend_logs": "mostly INFO" if error_count < 20 else "elevated ERROR logs",
        }
