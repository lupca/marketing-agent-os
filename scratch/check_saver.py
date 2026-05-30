# scratch/check_saver.py
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    print("Successfully imported PostgresSaver")
except Exception as e:
    print(f"Could not import PostgresSaver: {e}")

try:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    print("Successfully imported AsyncPostgresSaver")
except Exception as e:
    print(f"Could not import AsyncPostgresSaver: {e}")
