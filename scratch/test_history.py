# scratch/test_history.py
import asyncio
from graphs.main_router import graph

async def main():
    config = {"configurable": {"thread_id": "test-thread-id"}}
    # Let's see if we can get history (it might be empty but we can inspect type and attributes)
    history = []
    async for state in graph.aget_state_history(config):
        history.append(state)
        print("State Snapshot:", state)
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
