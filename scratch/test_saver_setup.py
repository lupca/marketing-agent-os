# scratch/test_saver_setup.py
import sys
import os
import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import POSTGRES_URL

print("Starting saver setup test...")
async def run():
    pool = AsyncConnectionPool(
        conninfo=POSTGRES_URL,
        max_size=10,
        open=False,
        kwargs={"autocommit": True, "row_factory": dict_row}
    )
    await pool.open()
    print("Pool opened.")
    
    saver = AsyncPostgresSaver(pool)
    print("Running saver.setup()...")
    await saver.setup()
    print("Saver setup completed successfully!")
    
    await pool.close()
    print("Pool closed.")

asyncio.run(run())
