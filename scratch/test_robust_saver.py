# scratch/test_robust_saver.py
import sys
import os
import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.base import BaseCheckpointSaver

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import POSTGRES_URL

class RobustPostgresSaver(BaseCheckpointSaver):
    def __init__(self, pool):
        super().__init__()
        self.pool = pool
        self._saver = None

    @property
    def saver(self):
        if self._saver is None:
            self._saver = AsyncPostgresSaver(self.pool)
        return self._saver

    def _run_sync(self, coro):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # If loop is already running, run it in a threadsafe way
            import threading
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result()
        else:
            # Safe to run in a new loop
            new_loop = asyncio.new_event_loop()
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()

    def get_tuple(self, config):
        return self._run_sync(self.saver.aget_tuple(config))

    def put(self, config, checkpoint, metadata, new_versions):
        return self._run_sync(self.saver.aput(config, checkpoint, metadata, new_versions))

    def put_writes(self, config, writes, task_id):
        return self._run_sync(self.saver.aput_writes(config, writes, task_id))

    def list(self, config, *, before=None, limit=None):
        return self._run_sync(self.saver.alist(config, before=before, limit=limit))
        
    async def aget_tuple(self, config):
        return await self.saver.aget_tuple(config)

    async def aput(self, config, checkpoint, metadata, new_versions):
        return await self.saver.aput(config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id):
        return await self.saver.aput_writes(config, writes, task_id)

    async def alist(self, config, *, before=None, limit=None):
        return await self.saver.alist(config, before=before, limit=limit)
        
    async def setup(self):
        await self.saver.setup()

    def get_next_version(self, current, channel):
        # AsyncPostgresSaver is sync-compatible for versioning
        return self.saver.get_next_version(current, channel)

async def test():
    pool = AsyncConnectionPool(
        conninfo=POSTGRES_URL,
        max_size=10,
        open=False,
        kwargs={"autocommit": True, "row_factory": dict_row}
    )
    await pool.open()
    
    saver = RobustPostgresSaver(pool)
    await saver.setup()
    
    config = {"configurable": {"thread_id": "robust_test_thread"}}
    
    print("Calling robust_saver.get_tuple synchronously...")
    res = saver.get_tuple(config)
    print("Result:", res)
    
    await pool.close()

asyncio.run(test())
