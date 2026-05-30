# scratch/test_async_saver_sync.py
import sys
import os
import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import POSTGRES_URL

async def run():
    pool = AsyncConnectionPool(
        conninfo=POSTGRES_URL,
        max_size=10,
        open=False,
        kwargs={"autocommit": True, "row_factory": dict_row}
    )
    await pool.open()
    
    saver = AsyncPostgresSaver(pool)
    await saver.setup()
    
    config = {"configurable": {"thread_id": "test_thread_async"}}
    
    print("Calling saver.get_tuple synchronously...")
    try:
        res = saver.get_tuple(config)
        print("Result:", res)
    except Exception as e:
        print("Error calling get_tuple synchronously:", e)
        
    await pool.close()

asyncio.run(run())
