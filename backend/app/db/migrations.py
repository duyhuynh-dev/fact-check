"""Database migration utilities."""

from sqlalchemy import inspect, text
from sqlmodel import Session

from backend.app.db.session import get_engine


def migrate_add_progress_columns() -> None:
    """Add ingest_progress and ingest_progress_message columns to documents table if they don't exist."""
    engine = get_engine()
    
    try:
        inspector = inspect(engine)
        # Check if table exists
        if "documents" not in inspector.get_table_names():
            return  # Table doesn't exist yet, will be created by create_all
        
        # Check if columns exist
        columns = [col["name"] for col in inspector.get_columns("documents")]
    except Exception:
        # If inspection fails, try to add columns anyway (will fail gracefully if they exist)
        columns = []
    
    with Session(engine) as session:
        if "ingest_progress" not in columns:
            try:
                session.exec(text("ALTER TABLE documents ADD COLUMN ingest_progress REAL"))
                session.commit()
                print("✅ Added ingest_progress column")
            except Exception as e:
                # Column might already exist or table doesn't exist
                if "duplicate column" not in str(e).lower() and "no such table" not in str(e).lower():
                    print(f"⚠️  Could not add ingest_progress: {e}")
                session.rollback()
        
        if "ingest_progress_message" not in columns:
            try:
                session.exec(text("ALTER TABLE documents ADD COLUMN ingest_progress_message TEXT"))
                session.commit()
                print("✅ Added ingest_progress_message column")
            except Exception as e:
                # Column might already exist or table doesn't exist
                if "duplicate column" not in str(e).lower() and "no such table" not in str(e).lower():
                    print(f"⚠️  Could not add ingest_progress_message: {e}")
                session.rollback()


def run_migrations() -> None:
    """Run all pending migrations."""
    migrate_add_progress_columns()

