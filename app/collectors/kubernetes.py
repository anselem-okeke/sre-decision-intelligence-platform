from typing import Any

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


class KubernetesCollector:
    def __init__(self, namespace: str, service_name: str, app_label: str):
        self.namespace = namespace
        self.service_name = service_name
        self.app_label = app_label
        self._load_config()

        self.core_v1 = client.CoreV1Api()

    def _load_config(self) -> None:
        try:
            config.load_incluster_config()
        except ConfigException:
            config.load_kube_config()

    def get_service_endpoints(self) -> str:
        endpoints = self.core_v1.read_namespaced_endpoints(
            name=self.service_name,
            namespace=self.namespace,
        )

        addresses: list[str] = []

        for subset in endpoints.subsets or []:
            for address in subset.addresses or []:
                for port in subset.ports or []:
                    addresses.append(f"{address.ip}:{port.port}")

        if not addresses:
            return "none"

        return ",".join(addresses)

    def get_frontend_pod_status(self) -> tuple[bool, str]:
        pods = self.core_v1.list_namespaced_pod(
            namespace=self.namespace,
            label_selector=f"app={self.app_label}",
        )

        if not pods.items:
            return False, "not found"

        pod = pods.items[0]

        ready = False
        for condition in pod.status.conditions or []:
            if condition.type == "Ready" and condition.status == "True":
                ready = True
                break

        total_containers = len(pod.status.container_statuses or [])
        ready_containers = sum(
            1
            for container in pod.status.container_statuses or []
            if container.ready
        )

        status = f"{ready_containers}/{total_containers} {pod.status.phase}"

        return ready, status

    def collect_frontend_kubernetes_signals(self) -> dict[str, Any]:
        endpoints = self.get_service_endpoints()
        pod_ready, pod_status = self.get_frontend_pod_status()

        return {
            "frontend_endpoints": endpoints,
            "frontend_pod_ready": pod_ready,
            "frontend_pod_status": pod_status,
        }
