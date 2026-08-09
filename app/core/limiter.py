"""共享速率限制器实例，供 main.py 和 API 模块共用。"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
