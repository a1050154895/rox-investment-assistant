"""ROX投资助手 — 应用配置"""
import os


class Settings:
    PROJECT_NAME: str = "ROX投资助手"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")

    # CORS
    ALLOWED_ORIGINS: list = ["*"]

    def __init__(self):
        os.makedirs(self.DATA_DIR, exist_ok=True)


settings = Settings()
