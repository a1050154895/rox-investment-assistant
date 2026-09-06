"""更新公告与软件介绍 API（公开，无鉴权——公告不含任何用户数据）。"""
from fastapi import APIRouter

from app.services.changelog import get_changelog

router = APIRouter()


@router.get("")
async def changelog():
    """更新公告列表与软件介绍；latest_version 供前端判断是否弹窗。"""
    return get_changelog()
