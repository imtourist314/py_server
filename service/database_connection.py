import os
import sys
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from contextlib import asynccontextmanager
import asyncio
import importlib.util


class Database:
    def __init__(self, config: dict):
        self.config = config
        self.pool = None
        self.sessionmaker = None
        self.engine = None

    async def initialize(self):
        # asyncpg pool
        if "asyncpg_dsn" in self.config:
            if self.pool:
                print("pool alread initialized")
                return
            print("asyncpg login")
            self.pool = await asyncpg.create_pool(
                dsn=self.config["asyncpg_dsn"],
                min_size=int(self.config.get("pool_min_size", 1)),
                max_size=int(self.config.get("pool_max_size", 10))
            )

        # SQLAlchemy async engine
        if "sqlalchemy_dsn" in self.config:
            if self.engine:
                print("engine already initialized")
                return
            if self.sessionmaker:
                print("session_maker already initialized")
                return

            print("sqlalchemy login")

            dsn = self.config["sqlalchemy_dsn"]

            # Ensure async driver
            if dsn.startswith("postgresql://"):
                dsn = dsn.replace("postgresql://", "postgresql+asyncpg://")

            print(f"dsn: {dsn}")
            self.engine = create_async_engine(dsn, echo=False)

            self.sessionmaker = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

    async def close(self):
        if self.pool:
            await self.pool.close()

        if self.engine:
            await self.engine.dispose()

    @asynccontextmanager
    async def get_connection(self):
        if not self.pool:
            raise Exception("asyncpg pool not initialized")

        async with self.pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def get_session(self):
        if not self.sessionmaker:
            raise Exception("SQLAlchemy not initialized")

        async with self.sessionmaker() as session:
            yield session

def get_config(module_name,module_path='config.py',db_env_var='DB_CONFIG_FILE'):
    if os.getenv(db_env_var):
        config_file = os.getenv(db_env_var)
        print(f"Load '{module_name}' from environment variable: '{db_env_var}' path: '{config_file}'")
    else:
        config_file = module_path
        print(f"Load '{module_name}' from direct path: '{module_path}'")
    spec = importlib.util.spec_from_file_location(module_name,config_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

config = get_config('config')
db_instance = Database(config.config['lambda'])

@asynccontextmanager
async def get_db():
    async with db_instance.get_session() as session:
        yield session


async def main():
    await db_instance.initialize()

    async with get_db() as session:
        print("Running test query")
        result = await session.execute(text("select * from corp_acc_activity limit 10"))
        print(result.fetchall())

    await db_instance.close()

async def startup():
    print("------->!!! in db connection startup *<----------")
    await db_instance.initialize()

if __name__ == '__main__':
    asyncio.run(main())
else:
    asyncio.run(startup())
