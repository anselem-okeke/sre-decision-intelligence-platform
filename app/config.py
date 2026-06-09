from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "SRE Decision Intelligence Platform"
    app_version: str = "0.1.0"
    environment: str = "local"


settings = Settings()
