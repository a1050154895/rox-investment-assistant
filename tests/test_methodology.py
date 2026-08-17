"""方法论单一事实源完整性测试。"""
from app.services.methodology import (
    KNOWLEDGE_ARTICLES,
    KNOWLEDGE_CATEGORIES,
    METHODOLOGY_LAYERS,
    STRATEGIES,
)


def test_five_layers_present():
    assert [layer["level"] for layer in METHODOLOGY_LAYERS] == ["L1", "L2", "L3", "L4", "L5"]


def test_l1_matrix_is_3x3():
    l1 = METHODOLOGY_LAYERS[0]
    assert len(l1["matrix"]["rows"]) == 3
    assert len(l1["matrix"]["cols"]) == 3


def test_l2_capital_cycle_has_five_stages():
    l2 = METHODOLOGY_LAYERS[1]
    assert [s["name"] for s in l2["stages"]] == ["积累", "集中", "流转", "分配", "再生产"]


def test_l3_has_four_contradiction_types():
    l3 = METHODOLOGY_LAYERS[2]
    assert len(l3["contradiction_types"]) == 4


def test_l4_ratios_sum_to_100():
    l4 = METHODOLOGY_LAYERS[3]
    pools = sum(int(p["ratio"].rstrip("%")) for p in l4["three_pools"])
    positions = sum(int(p["ratio"].rstrip("%")) for p in l4["position_334"])
    assert pools == 100
    assert positions == 100


def test_l5_weights_sum_to_100():
    l5 = METHODOLOGY_LAYERS[4]
    assert sum(d["weight"] for d in l5["dimensions"]) == 100


def test_every_layer_has_distilled_skill_metadata():
    for layer in METHODOLOGY_LAYERS:
        skill = layer["skill"]
        assert skill["trigger"]
        assert isinstance(skill["steps"], list) and skill["steps"]
        assert skill["boundary"]


def test_strategies_and_knowledge_non_empty():
    assert len(STRATEGIES) >= 1
    assert all(s["stage"] for s in STRATEGIES)
    assert len(KNOWLEDGE_ARTICLES) >= 1
    assert len(KNOWLEDGE_CATEGORIES) >= 1
