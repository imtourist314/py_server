import re
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import text

from .database_connection import get_db

# business data router
router = APIRouter(tags=["db_data"])

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(value: str, kind: str) -> str:
    if not _IDENTIFIER_RE.match(value):
        raise HTTPException(status_code=400, detail=f"Invalid {kind}: {value!r}")
    return value


@router.get("/data/{table_name}", response_model=List[Dict[str, Any]])
async def get_data(
    table_name: str,
    request: Request,
    schema: str = Query("public", description="Postgres schema name"),
    limit: int = Query(
        10,
        ge=1,
        le=10,
        description="Maximum number of rows to return (capped at 10)",
    ),
):
    """Return up to `limit` rows from the requested table.

    `limit` is optional and defaults to 10; values > 10 are rejected.
    """

    table_name = _validate_identifier(table_name, "table_name")
    schema = _validate_identifier(schema, "schema")

    query = f'SELECT * FROM "{schema}"."{table_name}" LIMIT :limit'

    try:
        async with get_db() as session:
            result = await session.execute(text(query), {"limit": limit})
            rows = result.mappings().all()
    except Exception as e:
        # e.g. table does not exist / insufficient permissions / etc.
        raise HTTPException(status_code=400, detail=str(e))

    return [dict(r) for r in rows]
