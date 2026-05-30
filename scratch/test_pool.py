# scratch/test_pool.py
import sys
import os
import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import POSTGRES_URL

print("Starting pool test...")
async def run():
    print("Initializing pool...")
    pool = AsyncConnectionPool(
        conninfo=POSTGRES_URL,
        max_size=10,
        open=False,
        kwargs={"autocommit": True, "row_factory": dict_row}
    )
    print("Opening pool...")
    await pool.open()
    print("Pool opened successfully!")
    print("Closing pool...")
    await pool.close()
    print("Pool closed successfully!")

asyncio.run(run())
