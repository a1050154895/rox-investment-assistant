"""数据源健康与数据契约 API。"""
from fastapi import APIRouter, Depends

from app.core.auth import get_current_user
from app.models import User
from app.services.data_source_registry import health_report

router = APIRouter()


@router.get("/sources")
async def data_sources(user: User = Depends(get_current_user)):
    """全部数据源的真实健康状态与统一契约说明。

    健康状态来自服务层真实请求埋点，不做主动拨测、不伪造。
    """
    return health_report()
