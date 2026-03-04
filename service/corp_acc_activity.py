import uvicorn
import os
import sys
import asyncpg
from fastapi import FastAPI, HTTPException, Depends, APIRouter
from sqlalchemy import Column, Integer, String, Numeric, TIMESTAMP, text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import create_engine
from sqlalchemy import select,update,delete
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from .database_connection import get_db 

Base = declarative_base()

router = APIRouter(tags=['corp_acc_activity'])


class CorpAccActivity(Base):
    __tablename__ = "corp_acc_activity"

    id = Column("id", Integer, primary_key=True, index=True)
    insert_ts = Column("insert_ts", TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    update_ts = Column("update_ts", TIMESTAMP(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    label = Column("label", String(255))
    account_num = Column("account_num", String(255))
    date = Column("date", TIMESTAMP(timezone=True), nullable=False)
    post_date = Column("post_date", TIMESTAMP(timezone=True))
    party = Column("party", String(255))
    party_id = Column("party_id", Integer)
    descr = Column("descr", String(4096))
    debit = Column("debit", Numeric)
    credit = Column("credit", Numeric)
    balance = Column("balance", Numeric)
    tx_type = Column("tx_type", String(255))
    tx_status = Column("tx_status", String(255))
    tx_note = Column("tx_note", String(1024))
    update_src_id = Column("update_src_id", Integer)

class CorpAccActivityBase(BaseModel):
    label: Optional[str] = None
    account_num: Optional[str] = None
    date: datetime
    post_date: Optional[datetime] = None
    party: Optional[str] = None
    party_id: Optional[int] = None
    descr: Optional[str] = None
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None
    tx_type: Optional[str] = None
    tx_status: Optional[str] = None
    tx_note: Optional[str] = None
    update_src_id: Optional[int] = None


class CorpAccActivityRead(CorpAccActivityBase):
    id: int
    insert_ts: Optional[datetime] = None
    update_ts: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

@router.get("/accounts/activity/", response_model=List[CorpAccActivityRead])
async def list_records(limit: int = 100, offset: int = 0) -> List[CorpAccActivityRead]:
    # Note: get_db() is an async context manager (see app/database_connection.py)
    async with get_db() as db:
        result = await db.execute(select(CorpAccActivity).limit(limit).offset(offset))
        rows = result.scalars().all()
    return rows


