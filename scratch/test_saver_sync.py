# scratch/test_saver_sync.py
import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from graphs.main_router import postgres_checkpointer

print("Saver class:", postgres_checkpointer.__class__)
print("Saver.get_tuple method:", postgres_checkpointer.get_tuple)

config = {"configurable": {"thread_id": "test_thread"}}
try:
    print("Calling get_tuple synchronously...")
    res = postgres_checkpointer.get_tuple(config)
    print("Result type:", type(res))
    print("Result content:", res)
except Exception as e:
    print("Error calling get_tuple synchronously:", e)
