"""ROX投资助手 — 应用配置"""
import os


class Settings:
    PROJECT_NAME: str = "ROX投资助手"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")

    # CORS：生产环境只允许显式域名；可用逗号分隔覆盖。
    _default_origins = "https://rox-investment-assistant.onrender.com" if ENVIRONMENT == "production" else "http://localhost:8008,http://127.0.0.1:8008"
    ALLOWED_ORIGINS: list[str] = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",") if origin.strip()]

    def __init__(self):
        os.makedirs(self.DATA_DIR, exist_ok=True)


settings = Settings()
