import uvicorn
from fastapi import FastAPI, HTTPException, Depends,APIRouter
from contextlib import asynccontextmanager
from sqlalchemy import Column, Integer, String, TIMESTAMP, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from . import corp_acc_activity
from . import db_meta
from . import db_data
from .database_connection import Database

@asynccontextmanager
async def lifespan(app:FastAPI):
    # app.state.db etc...
    print("startup in main using lifespan")
    yield

# FastAPI App
app = FastAPI(lifespan=lifespan)
#app.include_router(corp_acc_activity.router)
app.include_router(db_meta.router)
app.include_router(db_data.router)

if __name__ == "__main__":
    uvicorn.run("service.main:app", host="0.0.0.0", port=8000, reload=True)
