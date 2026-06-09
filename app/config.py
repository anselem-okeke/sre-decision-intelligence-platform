import os

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "SRE Decision Intelligence Platform")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    environment: str = os.getenv("ENVIRONMENT", "local")

    prometheus_base_url: str = os.getenv("PROMETHEUS_BASE_URL", "http://localhost:9090")
    opensearch_base_url: str = os.getenv("OPENSEARCH_BASE_URL", "http://localhost:9200")

    workload_namespace: str = os.getenv("WORKLOAD_NAMESPACE", "fintech-workload")
    frontend_service_name: str = os.getenv("FRONTEND_SERVICE_NAME", "frontend")
    frontend_app_label: str = os.getenv("FRONTEND_APP_LABEL", "frontend")

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://sre:sre_password@localhost:5432/sre_decision_intelligence",
    )


settings = Settings()
