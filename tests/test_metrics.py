"""Unit tests for the YAML metric store and its matching draft."""

from __future__ import annotations

from pathlib import Path

import pytest

from queryagent.metrics.yaml_store import YamlMetricStore

METRICS_YAML = """\
metrics:
  - name: new_users
    display_name: 新增用户
    aliases: [新用户, 新增, new users]
    definition: 按 users.created_at 日期计数；不含测试账号。
    caution: 运营口径按 first_order_at 计数
    tables: [users]
  - name: gmv
    display_name: 成交额
    aliases: [GMV, 交易额]
    definition: status='paid' 订单的 amount 求和。
    tables: [orders]
  - name: repurchase_rate
    display_name: 复购率
    definition: 下过 2 单及以上的用户占下过单用户的比例。
"""


@pytest.fixture
def store(tmp_path: Path) -> YamlMetricStore:
    path = tmp_path / "metrics.yaml"
    path.write_text(METRICS_YAML, encoding="utf-8")
    return YamlMetricStore(path)


def test_alias_hit_ranks_first(store: YamlMetricStore) -> None:
    matched = store.match("上个月每天的新增用户数")
    assert matched
    assert matched[0].name == "new_users"


def test_ascii_alias_is_case_insensitive(store: YamlMetricStore) -> None:
    matched = store.match("上周 gmv 是多少")
    assert matched
    assert matched[0].name == "gmv"


def test_no_match_returns_empty(store: YamlMetricStore) -> None:
    assert store.match("今天天气怎么样") == []


def test_top_k_caps_results(store: YamlMetricStore) -> None:
    matched = store.match("新增用户的 GMV 和复购率", top_k=1)
    assert len(matched) == 1


def test_get_by_name(store: YamlMetricStore) -> None:
    metric = store.get("new_users")
    assert metric is not None
    assert metric.caution  # the v0.2.0 clarify fuel survives loading
    assert store.get("nonexistent") is None


def test_duplicate_names_rejected(tmp_path: Path) -> None:
    text = METRICS_YAML + "  - name: gmv\n    definition: dup\n"
    path = tmp_path / "metrics.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        YamlMetricStore(path)


def test_missing_definition_rejected(tmp_path: Path) -> None:
    path = tmp_path / "metrics.yaml"
    path.write_text("metrics:\n  - name: broken\n", encoding="utf-8")
    with pytest.raises(ValueError, match="definition"):
        YamlMetricStore(path)


def test_missing_metrics_list_rejected(tmp_path: Path) -> None:
    path = tmp_path / "metrics.yaml"
    path.write_text("not_metrics: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="metrics"):
        YamlMetricStore(path)
