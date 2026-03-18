from contextlib import asynccontextmanager
from sqlalchemy import text

from db.database import Base, engine


@asynccontextmanager
async def lifespan(app):
    """
    Application lifespan handler for startup and shutdown events.
    """
    # Startup
    print("\n" + "=" * 60)
    print("🚀 Starting Chatbox API")
    print("=" * 60)

    # Enable pgvector extension (required for the Vector column type).
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified")

    # Check database connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("Application may not function correctly!")

    yield

    # Shutdown
    engine.dispose()
    print("👋 Chatbox API shutdown complete")