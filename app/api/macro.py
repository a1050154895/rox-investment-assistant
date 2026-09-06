"""宏观代理矩阵 API。"""
from fastapi import APIRouter

from app.services.data_contract import ensure_contract
from app.services.macro_data import DERIVED_SPECS, SPECS, get_macro_matrix

router = APIRouter()


@router.get("/matrix")
async def matrix(refresh: bool = False):
    return ensure_contract(await get_macro_matrix(force=refresh), data_source="国家统计局/央行（AKShare）")


@router.get("/source-diagnosis")
async def source_diagnosis():
    """数据源健康诊断（仅元数据，无指标数值）：每个接口的行数、列名、
    首尾行观察期与排序方向，用于维护数据源时远程排查新鲜度问题。"""
    import asyncio

    from app.services.akshare_gate import gated_call

    async def probe(spec) -> dict:
        try:
            import akshare as ak
            function = getattr(ak, spec.function_name, None)
            if function is None:
                return {"key": spec.key, "status": "missing_interface"}
            frame = await asyncio.wait_for(gated_call(function), timeout=15)
            if frame is None or frame.empty:
                return {"key": spec.key, "status": "empty"}
            date_column = None
            for candidate in spec.date_columns:
                matched = [c for c in frame.columns if candidate in str(c)]
                if matched:
                    date_column = matched[0]
                    break
            periods = [str(v) for v in frame[date_column].tolist()] if date_column else []
            return {
                "key": spec.key,
                "interface": spec.function_name,
                "rows": int(len(frame)),
                "columns": [str(c) for c in frame.columns][:8],
                "head_periods": periods[:2],
                "tail_periods": periods[-2:],
                "order": "newest_first" if periods and _looks_newer(periods[0], periods[-1]) else "oldest_first",
            }
        except Exception as exc:
            return {"key": spec.key, "status": "error", "message": str(exc)[:150]}

    def _looks_newer(a: str, b: str) -> bool:
        import re
        nums = lambda s: [int(x) for x in re.findall(r"20\d{2}", s)] + [int(x) for x in re.findall(r"(\d{1,2})月", s)]
        na, nb = nums(a), nums(b)
        return na > nb if na and nb else False

    specs = list(SPECS) + list(DERIVED_SPECS)
    results = await asyncio.gather(*(probe(spec) for spec in specs))
    return {"diagnosed_at": __import__("datetime").datetime.now().isoformat(), "sources": results}
