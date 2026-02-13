import pytest

from app.tools.list_tables import ListTablesTool
from app.tools.show_schema import ShowSchemaTool
from app.tools.sample_data import SampleDataTool
from app.tools.query import QueryTool
from app.tools.sql_safety import validate_sql


# --- SQL safety unit tests ---

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


# --- Tool integration tests (hit real target DB) ---

@pytest.mark.asyncio
async def test_list_tables():
    tool = ListTablesTool()
    result = await tool.execute({})
    assert "companies" in result["tables"]


@pytest.mark.asyncio
async def test_show_schema():
    tool = ShowSchemaTool()
    result = await tool.execute({"table": "companies"})
    column_names = [col["column_name"] for col in result["columns"]]
    assert "company_name" in column_names
    assert "arr_thousands" in column_names
    assert "industry_vertical" in column_names


@pytest.mark.asyncio
async def test_sample_data():
    tool = SampleDataTool()
    result = await tool.execute({"table": "companies", "limit": 3})
    assert len(result["rows"]) == 3
    assert "company_name" in result["columns"]
    assert "arr_thousands" in result["columns"]


@pytest.mark.asyncio
async def test_query_select():
    tool = QueryTool()
    result = await tool.execute({"sql": "SELECT count(*) as cnt FROM companies"})
    assert result["rows"][0][0] == 500
    assert result["row_count"] == 1


@pytest.mark.asyncio
async def test_query_rejects_insert():
    tool = QueryTool()
    with pytest.raises(ValueError, match="Only SELECT"):
        await tool.execute({"sql": "INSERT INTO companies VALUES (999, 'test')"})


@pytest.mark.asyncio
async def test_query_rejects_drop():
    tool = QueryTool()
    with pytest.raises(ValueError, match="Only SELECT"):
        await tool.execute({"sql": "DROP TABLE companies"})


@pytest.mark.asyncio
async def test_query_rejects_delete():
    tool = QueryTool()
    with pytest.raises(ValueError, match="Only SELECT"):
        await tool.execute({"sql": "DELETE FROM companies"})


@pytest.mark.asyncio
async def test_query_rejects_multi_statement():
    tool = QueryTool()
    with pytest.raises(ValueError, match="Multiple statements"):
        await tool.execute({"sql": "SELECT 1; DROP TABLE companies"})
