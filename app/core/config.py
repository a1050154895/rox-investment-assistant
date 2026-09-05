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

    # 邮件（找回密码 / 邮箱验证）：未配置 SMTP 时诚实降级为 outbox 模式（dev/test）
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER: str = os.getenv("SMTP_USER", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "").strip() or os.getenv("SMTP_USER", "").strip()
    # 邮件里的链接指向的应用地址；默认取 CORS 白名单第一项
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "").strip() or (ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "http://localhost:8008")

    def __init__(self):
        os.makedirs(self.DATA_DIR, exist_ok=True)


settings = Settings()
