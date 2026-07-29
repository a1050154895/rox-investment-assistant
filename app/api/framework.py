"""认知框架 API — 方法论、策略库、知识库"""
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/methodology")
async def methodology():
    """五层逻辑链方法论"""
    return {
        "layers": [
            {
                "level": "L1", "name": "宏观定调",
                "title": "马克思政治经济学根基",
                "summary": "以剩余价值理论为基础，分析社会总资本的运动规律",
                "key_concepts": ["剩余价值率", "资本有机构成", "社会总资本周转", "利润率趋向下降规律"],
                "indicators": [
                    {"name": "主权信用状态", "value": "平衡", "score": 62},
                    {"name": "价值实现度", "value": "中", "score": 55},
                    {"name": "直接税占比", "value": "缓慢提升", "score": 58},
                ]
            },
            {
                "level": "L2", "name": "资本周期",
                "title": "五阶段资本流转模型",
                "summary": "资本运动经历积累→集中→流转→分配→再生产五个阶段，每个阶段有不同的投资策略",
                "key_concepts": ["积累阶段", "集中阶段", "流转阶段", "分配阶段", "再生产阶段"],
                "current_stage": "流转",
                "stages": [
                    {"name": "积累", "desc": "资本蓄积，寻找价值洼地", "strategy": "防守为主，现金为王"},
                    {"name": "集中", "desc": "资本向优势行业集中", "strategy": "布局龙头，试仓进入"},
                    {"name": "流转", "desc": "资本从金融向实体流转", "strategy": "核心仓位持有，卫星仓位机动"},
                    {"name": "分配", "desc": "利润在各部门间分配", "strategy": "逐步减仓，锁定收益"},
                    {"name": "再生产", "desc": "资本重新配置进入下一周期", "strategy": "清仓观望，等待新周期"},
                ]
            },
            {
                "level": "L3", "name": "矛盾分析",
                "title": "毛泽东矛盾分析法应用",
                "summary": "识别主要矛盾和次要矛盾，分析矛盾的主要方面和转化趋势",
                "key_concepts": ["主要矛盾", "次要矛盾", "矛盾转化", "矛盾强度"],
                "current": {
                    "primary": {"name": "扩大内需 vs 居民收入增长放缓", "intensity": 72},
                    "secondary": {"name": "产业升级 vs 传统产能出清", "intensity": 58},
                }
            },
            {
                "level": "L4", "name": "334纪律",
                "title": "三池分配 + 建仓节奏",
                "summary": "核心30% + 卫星30% + 现金40%的三池分配体系，配合30%→30%→40%的建仓节奏",
                "key_concepts": ["核心池", "卫星池", "现金池", "试仓30%", "确认30%", "主力40%"],
                "current": {
                    "core": {"target": 30, "actual": 28},
                    "satellite": {"target": 30, "actual": 22},
                    "cash": {"target": 40, "actual": 50},
                }
            },
            {
                "level": "L5", "name": "一致性评分",
                "title": "框架一致性评分体系",
                "summary": "五维度加权评分，衡量投资决策与认知框架的一致性程度",
                "dimensions": [
                    {"name": "矛盾分析", "weight": 30, "desc": "主要矛盾强度与趋势判断"},
                    {"name": "价值规律", "weight": 35, "desc": "剩余价值率、资本有机构成、周转率"},
                    {"name": "宏观周期", "weight": 25, "desc": "当前所处资本周期阶段"},
                    {"name": "技术分析", "weight": 5, "desc": "辅助参考，非核心依据"},
                    {"name": "纪律执行", "weight": 5, "desc": "334仓位纪律遵守程度"},
                ]
            }
        ]
    }


@router.get("/strategies")
async def strategies(stage: str = Query("", description="按周期阶段筛选")):
    """策略库"""
    all_strategies = [
        {"id": 1, "name": "核心仓位长期持有策略", "stage": "流转", "style": "价值投资",
         "targets": 3, "desc": "选取高ROE、低估值、行业龙头作为核心仓位，长期持有不轻易动"},
        {"id": 2, "name": "卫星仓位波段策略", "stage": "流转", "style": "趋势跟踪",
         "targets": 5, "desc": "跟踪主力资金流向，在确认阶段加仓，分配阶段减仓"},
        {"id": 3, "name": "集中阶段龙头布局", "stage": "集中", "style": "成长投资",
         "targets": 4, "desc": "识别资本集中方向，提前布局行业龙头"},
        {"id": 4, "name": "积累阶段现金管理", "stage": "积累", "style": "防守",
         "targets": 2, "desc": "以货币基金+短债为主，保持流动性等待机会"},
        {"id": 5, "name": "分配阶段止盈策略", "stage": "分配", "style": "趋势跟踪",
         "targets": 6, "desc": "分批止盈，将利润转入现金池，等待再生产阶段"},
        {"id": 6, "name": "矛盾转化捕捉策略", "stage": "流转", "style": "事件驱动",
         "targets": 4, "desc": "当主要矛盾发生转化时，调整持仓结构"},
        {"id": 7, "name": "半导体国产替代", "stage": "集中", "style": "主题投资",
         "targets": 5, "desc": "半导体设备/材料/设计全产业链布局"},
        {"id": 8, "name": "高股息防御策略", "stage": "积累", "style": "价值投资",
         "targets": 3, "desc": "银行/公用事业/高速公路等高股息标的"},
    ]
    if stage:
        return {"strategies": [s for s in all_strategies if s["stage"] == stage]}
    return {"strategies": all_strategies}


@router.get("/knowledge")
async def knowledge(category: str = Query("", description="按分类筛选")):
    """知识库文章"""
    articles = [
        {"id": 1, "title": "资本周期五阶段详解：从积累到再生产", "category": "资本周期",
         "summary": "深入解析马克思资本周转理论在现代A股投资中的应用", "read_time": "8分钟"},
        {"id": 2, "title": "矛盾分析法：如何识别投资中的主要矛盾", "category": "矛盾分析",
         "summary": "毛泽东矛盾分析法在投资决策中的实操指南", "read_time": "12分钟"},
        {"id": 3, "title": "334仓位纪律：为什么是30/30/40", "category": "334纪律",
         "summary": "仓位管理的数学逻辑与行为金融学基础", "read_time": "6分钟"},
        {"id": 4, "title": "主权信用矩阵：宏观定调的第一步", "category": "宏观定调",
         "summary": "如何通过财政纪律和直接税占比判断宏观环境", "read_time": "10分钟"},
        {"id": 5, "title": "价值规律在股票定价中的体现", "category": "价值规律",
         "summary": "剩余价值率、资本有机构成如何影响股票估值", "read_time": "15分钟"},
        {"id": 6, "title": "东方智慧与量化投资的融合", "category": "东方智慧",
         "summary": "道儒兵法思想在现代投资框架中的启示", "read_time": "9分钟"},
        {"id": 7, "title": "框架一致性评分体系使用指南", "category": "评分体系",
         "summary": "如何用五维度评分衡量决策质量", "read_time": "7分钟"},
        {"id": 8, "title": "从资本流转看行业轮动", "category": "资本周期",
         "summary": "资本在行业间的流转规律与板块轮动判断", "read_time": "11分钟"},
    ]
    if category:
        return {"articles": [a for a in articles if a["category"] == category]}
    return {
        "articles": articles,
        "categories": ["资本周期", "矛盾分析", "334纪律", "宏观定调", "价值规律", "东方智慧", "评分体系"]
    }
