# scratch_migrate.py
from db.connection import engine
from sqlalchemy import text

def run_migration():
    print("Starting database migration...")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE content_briefs ADD COLUMN IF NOT EXISTS platform_meta JSONB DEFAULT '{}'::jsonb;"))
        conn.commit()
    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
