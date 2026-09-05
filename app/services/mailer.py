"""邮件发送服务 — SMTP（465/587），未配置时开发模式降级为日志投递。

未配置 SMTP_HOST/SMTP_USER/SMTP_PASSWORD 时：
- production：视为配置错误，抛出异常由调用方转为 503，绝不静默伪造"已发送"；
- development / test：把完整邮件内容（含链接）写入应用日志，供本地联调读取。
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate

from app.core.config import settings

logger = logging.getLogger("rox.mailer")

_SMTP_TIMEOUT_SECONDS = 15


def email_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_email(to: str, subject: str, html: str) -> str:
    """发送邮件。返回投递方式（"smtp" / "log"）；失败抛异常，由调用方决定降级方式。"""
    msg = EmailMessage()
    msg["From"] = settings.EMAIL_FROM or settings.SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=False)
    msg.set_content("您的邮件客户端不支持 HTML 内容，请使用支持 HTML 的客户端查看此邮件。")
    msg.add_alternative(html, subtype="html")

    if not email_configured():
        if settings.ENVIRONMENT == "production":
            raise RuntimeError("SMTP 未配置，无法发送邮件")
        return _deliver_to_log(msg, to)

    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=ssl.create_default_context(), timeout=_SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=_SMTP_TIMEOUT_SECONDS) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(msg)
    return "smtp"


def _deliver_to_log(msg: EmailMessage, to: str) -> str:
    """开发/测试环境的投递降级：不外发，把邮件内容完整写进日志。"""
    logger.warning(
        "邮件降级投递（SMTP 未配置，%s 环境）\nTo: %s\nSubject: %s\n%s",
        settings.ENVIRONMENT,
        to,
        msg["Subject"],
        msg.get_body(preferencelist=("html", "plain")).get_content() if msg.get_body(preferencelist=("html", "plain")) else "",
    )
    return "log"
