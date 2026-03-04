import os
from typing import List, Optional
import asyncpg
from sqlalchemy import text
from fastapi import FastAPI, HTTPException, Query, Request, APIRouter
from pydantic import BaseModel
from .database_connection import Database,get_db

# app = FastAPI(title="Table Structure API")
router = APIRouter(tags=['db_metadata'])

class ColumnInfo(BaseModel):
    name: str
    type: str


class TableStructure(BaseModel):
    table: str
    columns: List[ColumnInfo]


class IndexInfo(BaseModel):
    name: str
    definition: str
    method: Optional[str] = None
    is_unique: bool
    is_primary: bool
    columns: List[str] = []
    predicate: Optional[str] = None
    expressions: Optional[str] = None


class TableIndexes(BaseModel):
    table: str
    indexes: List[IndexInfo]


@router.get("/tables/{table_name}/structure", response_model=TableStructure)
async def table_structure(
    table_name: str,
    request: Request,
    schema: str = Query("public", description="Postgres schema name"),
):
    print(f"Getting metadata for table: {table_name}")
    query = """
        SELECT
            c.table_name,
            c.column_name,
            CASE
                WHEN c.data_type = 'USER-DEFINED' THEN c.udt_name
                ELSE c.data_type
            END AS data_type
        FROM information_schema.columns c
        WHERE c.table_schema = :schema AND c.table_name = :table_name
        ORDER BY c.ordinal_position
    """
    async with get_db() as session:
        rows = await session.execute(text(query),{'schema':schema,'table_name':table_name})
        rows = [ r._asdict() for r in rows]

    if not rows:
        raise HTTPException(status_code=404, detail=f"Table not found: {schema}.{table_name}")

    data = {
        "table": f"{schema}.{table_name}",
        "columns": [{"name": r["column_name"], "type": r["data_type"]} for r in rows ],
    }
    return data


@router.get("/tables/{table_name}/indexes", response_model=TableIndexes)
async def table_indexes(
    table_name: str,
    request: Request,
    schema: str = Query("public", description="Postgres schema name"),
):
    """Return information about a table's indexes."""

    print(f"Getting indexes for table: {table_name}")

    query = """
        SELECT
            idx.relname AS index_name,
            pg_get_indexdef(idx.oid) AS index_def,
            i.indisunique AS is_unique,
            i.indisprimary AS is_primary,
            am.amname AS method,
            pg_get_expr(i.indpred, t.oid) AS predicate,
            pg_get_expr(i.indexprs, t.oid) AS expressions,
            array_remove(array_agg(a.attname ORDER BY x.ord), NULL) AS columns
        FROM pg_class t
        JOIN pg_namespace ns ON ns.oid = t.relnamespace
        JOIN pg_index i ON t.oid = i.indrelid
        JOIN pg_class idx ON idx.oid = i.indexrelid
        JOIN pg_am am ON idx.relam = am.oid
        LEFT JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS x(attnum, ord) ON true
        LEFT JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = x.attnum
        WHERE ns.nspname = :schema AND t.relname = :table_name
        GROUP BY
            idx.relname,
            idx.oid,
            i.indisunique,
            i.indisprimary,
            am.amname,
            pg_get_expr(i.indpred, t.oid),
            pg_get_expr(i.indexprs, t.oid)
        ORDER BY i.indisprimary DESC, idx.relname ASC
    """

    async with get_db() as session:
        result = await session.execute(text(query), {"schema": schema, "table_name": table_name})
        rows = [r._asdict() for r in result]

        # If there are no indexes, distinguish between:
        #   - table exists but has no secondary indexes
        #   - table does not exist (return 404)
        if not rows:
            exists_query = """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = :schema AND table_name = :table_name
                LIMIT 1
            """
            exists_res = await session.execute(text(exists_query), {"schema": schema, "table_name": table_name})
            if exists_res.first() is None:
                raise HTTPException(status_code=404, detail=f"Table not found: {schema}.{table_name}")

    data = {
        "table": f"{schema}.{table_name}",
        "indexes": [
            {
                "name": r["index_name"],
                "definition": r["index_def"],
                "method": r.get("method"),
                "is_unique": bool(r["is_unique"]),
                "is_primary": bool(r["is_primary"]),
                "columns": r.get("columns") or [],
                "predicate": r.get("predicate"),
                "expressions": r.get("expressions"),
            }
            for r in rows
        ],
    }

    return data


@router.get("/database/list",response_model=List)
async def db_list(request:Request):
    print("!!! db_list")
    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        AND table_type = 'BASE TABLE';
    """
    async with get_db() as session:
        rows = await session.execute(text(query))
        rows = [ r._asdict() for r in rows]
        print(rows)

    if not rows:
        raise HTTPException(status_code=404, detail=f"Database table list not found or error")

    data = rows
    return data



