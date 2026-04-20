"""Tests for lakecube.fn.hierarchy — SQL predicate builders."""

from __future__ import annotations

import pytest

from lakecube.fn import ancestors, children, descendants, level, member_filter, parent


def test_parent_uses_default_key_col() -> None:
    sql = parent("market", "East")
    assert "market_key IN" in sql
    assert "ancestor" in sql
    assert "descendant = 'East'" in sql
    assert "depth = 1" in sql
    assert "lakecube.closure" in sql


def test_children_default() -> None:
    sql = children("market", "East")
    assert "market_key IN" in sql
    assert "descendant" in sql
    assert "ancestor = 'East'" in sql
    assert "depth = 1" in sql


def test_descendants_excludes_self_by_default() -> None:
    sql = descendants("market", "East")
    assert "depth >= 1" in sql


def test_descendants_include_self() -> None:
    sql = descendants("market", "East", include_self=True)
    assert "depth >= 0" in sql


def test_ancestors_excludes_self_by_default() -> None:
    sql = ancestors("market", "New York")
    assert "depth >= 1" in sql


def test_ancestors_include_self() -> None:
    sql = ancestors("market", "New York", include_self=True)
    assert "depth >= 0" in sql


def test_custom_key_col() -> None:
    sql = descendants("market", "East", key_col="fact_market_id")
    assert "fact_market_id IN" in sql
    assert "market_key" not in sql


def test_quoted_member_with_apostrophe() -> None:
    sql = descendants("product", "O'Brien's Soda")
    assert "'O''Brien''s Soda'" in sql


def test_dimension_quoted_as_literal() -> None:
    sql = descendants("market", "East")
    assert "dimension = 'market'" in sql


def test_level_zero_returns_leaves() -> None:
    sql = level("market", 0)
    assert "NOT IN" in sql
    assert "depth = 1" in sql


def test_level_nonzero() -> None:
    sql = level("market", 2)
    assert "depth = 2" in sql


class TestMemberFilter:
    def test_descendants_expression(self) -> None:
        assert "depth >= 1" in member_filter("descendants(East)", "market")

    def test_descendants_self_expression(self) -> None:
        assert "depth >= 0" in member_filter("descendants_self(East)", "market")

    def test_ancestors_expression(self) -> None:
        assert "depth >= 1" in member_filter("ancestors(East)", "market")

    def test_children_expression(self) -> None:
        sql = member_filter("children(East)", "market")
        assert "ancestor = 'East'" in sql
        assert "depth = 1" in sql

    def test_parent_expression(self) -> None:
        sql = member_filter("parent(New York)", "market")
        assert "descendant = 'New York'" in sql
        assert "depth = 1" in sql

    def test_level_expression(self) -> None:
        assert "depth = 3" in member_filter("level(3)", "market")

    def test_literal_member_fallback(self) -> None:
        assert member_filter("East", "market") == "(market_key = 'East')"

    def test_whitespace_tolerance(self) -> None:
        assert "depth >= 1" in member_filter("  descendants( East )  ", "market")

    def test_custom_key_col(self) -> None:
        sql = member_filter("descendants(East)", "market", key_col="fact_mk")
        assert "fact_mk IN" in sql

    def test_literal_with_apostrophe(self) -> None:
        sql = member_filter("O'Brien's", "product")
        assert "'O''Brien''s'" in sql


@pytest.mark.parametrize(
    "fn,expected_subquery",
    [
        (parent, "SELECT ancestor"),
        (children, "SELECT descendant"),
        (descendants, "SELECT descendant"),
        (ancestors, "SELECT ancestor"),
    ],
)
def test_all_helpers_reference_closure_table(fn, expected_subquery) -> None:
    sql = fn("market", "East")
    assert "lakecube.closure" in sql
    assert expected_subquery in sql
