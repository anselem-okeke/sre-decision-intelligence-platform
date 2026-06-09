from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "SRE Decision Intelligence Platform"
    app_version: str = "0.1.0"
    environment: str = "local"

    prometheus_base_url: str = "http://localhost:9090"
    opensearch_base_url: str = "http://localhost:9200"

    workload_namespace: str = "fintech-workload"
    frontend_service_name: str = "frontend"
    frontend_app_label: str = "frontend"


settings = Settings()
