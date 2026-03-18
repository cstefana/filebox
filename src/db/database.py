import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

#def create_sql_light_engine(path: str | None = None):
    # if path is None:
    #     path = settings.sqlite_database_url

    # if not path:
    #     raise ValueError("SQLITE_DATABASE_URL environment variable is not set.")

    #return create_engine(f"sqlite:///{path}")

load_dotenv("config.env")
_db_url = os.getenv("PG_DATABASE_URL")

def _enable_pgvector_extension(engine):
    """Enable pgvector extension in PostgreSQL."""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception as e:
        print(f" Warning: Could not enable pgvector extension: {e}")
        print("   Install pgvector on PostgreSQL with: CREATE EXTENSION vector;")
        print("   Or install the package: pip install pgvector[postgres]")
        # Don't fail startup - embedding operations will fail if used, but other features work

def create_postgres_engine(connection_string: str | None = None):
    if connection_string is None:
        connection_string = _db_url

    if not connection_string:
        raise ValueError("PG_DATABASE_URL environment variable is not set.")

    engine = create_engine(connection_string)
    _enable_pgvector_extension(engine)
    return engine

Base = declarative_base()

engine = create_postgres_engine()
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    if Session is None:
        raise ValueError("Database not configured.")
    db = Session()
    try:
        yield db
    finally:
        db.close()