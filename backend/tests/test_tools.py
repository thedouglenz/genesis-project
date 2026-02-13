from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.sql_safety import validate_sql


# --- SQL safety unit tests (no DB needed) ---

def test_sql_safety_allows_select():
    result = validate_sql("SELECT * FROM companies")
    assert result == "SELECT * FROM companies"


def test_sql_safety_case_insensitive():
    result = validate_sql("select * from companies")
    assert result == "select * from companies"


def test_sql_safety_strips_whitespace():
    result = validate_sql("  SELECT 1  ")
    assert result == "SELECT 1"


def test_sql_safety_rejects_insert():
    with pytest.raises(ValueError, match="Only SELECT"):
        validate_sql("INSERT INTO companies VALUES (1)")


def test_sql_safety_rejects_drop():
    with pytest.raises(ValueError, match="Forbidden keyword"):
        validate_sql("SELECT 1 FROM (DROP TABLE companies)")


def test_sql_safety_rejects_delete():
    with pytest.raises(ValueError, match="Only SELECT"):
        validate_sql("DELETE FROM companies")


def test_sql_safety_rejects_multi_statement():
    with pytest.raises(ValueError, match="Multiple statements"):
        validate_sql("SELECT 1; DROP TABLE companies")


def test_sql_safety_rejects_empty():
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_sql("")


# --- Tool integration tests (mocked DB) ---

def _mock_engine_connect(rows, columns=None):
    """Create a mock for target_engine.connect() context manager."""
    result_mock = MagicMock()
    result_mock.fetchall.return_value = rows
    result_mock.fetchone.return_value = rows[0] if rows else None
    result_mock.fetchmany.return_value = rows
    if columns:
        result_mock.keys.return_value = columns

    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=result_mock)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, conn


@pytest.mark.asyncio
async def test_list_tables():
    from app.tools.list_tables import ListTablesTool

    ctx, conn = _mock_engine_connect([("companies",), ("orders",)])

    with patch("app.tools.list_tables.target_engine") as mock_engine:
        mock_engine.connect.return_value = ctx
        tool = ListTablesTool()
        result = await tool.execute({})

    assert "companies" in result["tables"]
    assert "orders" in result["tables"]


@pytest.mark.asyncio
async def test_show_schema():
    from app.tools.show_schema import ShowSchemaTool

    rows = [
        ("company_name", "character varying", "NO"),
        ("arr_thousands", "integer", "YES"),
        ("industry_vertical", "character varying", "YES"),
    ]
    ctx, conn = _mock_engine_connect(rows)

    with patch("app.tools.show_schema.target_engine") as mock_engine:
        mock_engine.connect.return_value = ctx
        tool = ShowSchemaTool()
        result = await tool.execute({"table": "companies"})

    column_names = [col["column_name"] for col in result["columns"]]
    assert "company_name" in column_names
    assert "arr_thousands" in column_names
    assert "industry_vertical" in column_names


@pytest.mark.asyncio
async def test_sample_data():
    from app.tools.sample_data import SampleDataTool

    # First call: table existence check; second call: actual data
    check_result = MagicMock()
    check_result.fetchone.return_value = ("companies",)

    data_result = MagicMock()
    data_result.keys.return_value = ["company_name", "arr_thousands"]
    data_result.fetchall.return_value = [
        ("Acme Corp", 1000),
        ("Beta Inc", 2000),
        ("Gamma LLC", 3000),
    ]

    conn = AsyncMock()
    conn.execute = AsyncMock(side_effect=[check_result, data_result])

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("app.tools.sample_data.target_engine") as mock_engine:
        mock_engine.connect.return_value = ctx
        tool = SampleDataTool()
        result = await tool.execute({"table": "companies", "limit": 3})

    assert len(result["rows"]) == 3
    assert "company_name" in result["columns"]
    assert "arr_thousands" in result["columns"]


@pytest.mark.asyncio
async def test_query_select():
    from app.tools.query import QueryTool

    ctx, conn = _mock_engine_connect([(500,)], columns=["cnt"])

    with patch("app.tools.query.target_engine") as mock_engine:
        mock_engine.connect.return_value = ctx
        tool = QueryTool()
        result = await tool.execute({"sql": "SELECT count(*) as cnt FROM companies"})

    assert result["rows"][0][0] == 500
    assert result["row_count"] == 1


@pytest.mark.asyncio
async def test_query_rejects_insert():
    from app.tools.query import QueryTool

    tool = QueryTool()
    with pytest.raises(ValueError, match="Only SELECT"):
        await tool.execute({"sql": "INSERT INTO companies VALUES (999, 'test')"})


@pytest.mark.asyncio
async def test_query_rejects_drop():
    from app.tools.query import QueryTool

    tool = QueryTool()
    with pytest.raises(ValueError, match="Only SELECT"):
        await tool.execute({"sql": "DROP TABLE companies"})


@pytest.mark.asyncio
async def test_query_rejects_delete():
    from app.tools.query import QueryTool

    tool = QueryTool()
    with pytest.raises(ValueError, match="Only SELECT"):
        await tool.execute({"sql": "DELETE FROM companies"})


@pytest.mark.asyncio
async def test_query_rejects_multi_statement():
    from app.tools.query import QueryTool

    tool = QueryTool()
    with pytest.raises(ValueError, match="Multiple statements"):
        await tool.execute({"sql": "SELECT 1; DROP TABLE companies"})
