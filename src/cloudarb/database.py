"""
Database connection and session management for CloudArb platform.
"""

from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.dialects.postgresql import insert
from contextlib import contextmanager

from .config import get_settings
from .models.base import Base

settings = get_settings()

# Create database engine with connection pooling
engine = create_engine(
    settings.database.url,
    poolclass=QueuePool,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections every hour
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.

    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all database tables."""
    Base.metadata.drop_all(bind=engine)


def reset_db() -> None:
    """Reset database by dropping and recreating all tables."""
    drop_db()
    init_db()


# Database event listeners for performance monitoring
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries."""
    conn.info.setdefault('query_start_time', []).append(conn.info.get('query_start_time', []))


@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log query execution time."""
    total = conn.info.get('query_start_time', [])
    if total:
        total.pop()
        # Log queries taking longer than 1 second
        if total and total[-1] > 1.0:
            print(f"Slow query detected: {statement[:100]}...")


# Database utilities
def bulk_insert_or_update(model_class, records: list, index_elements: list = None) -> None:
    """
    Bulk insert or update records using PostgreSQL's ON CONFLICT.

    Args:
        model_class: SQLAlchemy model class
        records: List of dictionaries with record data
        index_elements: List of column names for conflict resolution
    """
    if not records:
        return

    with get_db_context() as db:
        for record in records:
            stmt = insert(model_class).values(**record)
            if index_elements:
                stmt = stmt.on_conflict_do_update(
                    index_elements=index_elements,
                    set_=record
                )
            db.execute(stmt)


def execute_raw_sql(sql: str, parameters: dict = None) -> list:
    """
    Execute raw SQL query.

    Args:
        sql: SQL query string
        parameters: Query parameters

    Returns:
        list: Query results
    """
    with get_db_context() as db:
        result = db.execute(sql, parameters or {})
        return [dict(row) for row in result]


# Database health check
def check_db_health() -> dict:
    """
    Check database health and connection status.

    Returns:
        dict: Health status information
    """
    try:
        with get_db_context() as db:
            # Test basic connectivity
            result = db.execute("SELECT 1 as test")
            test_result = result.fetchone()

            # Check connection pool status
            pool_status = {
                "pool_size": engine.pool.size(),
                "checked_in": engine.pool.checkedin(),
                "checked_out": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
            }

            return {
                "status": "healthy" if test_result and test_result[0] == 1 else "unhealthy",
                "pool_status": pool_status,
                "database_url": settings.database.url.replace(settings.database.password, "***"),
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "database_url": settings.database.url.replace(settings.database.password, "***"),
        }


# Database migration utilities
def get_table_count(table_name: str) -> int:
    """
    Get row count for a specific table.

    Args:
        table_name: Name of the table

    Returns:
        int: Number of rows in the table
    """
    with get_db_context() as db:
        result = db.execute(f"SELECT COUNT(*) FROM {table_name}")
        return result.scalar()


def get_database_size() -> dict:
    """
    Get database size information.

    Returns:
        dict: Database size information
    """
    with get_db_context() as db:
        # Get database size
        size_query = """
        SELECT
            pg_size_pretty(pg_database_size(current_database())) as size,
            pg_database_size(current_database()) as size_bytes
        """
        size_result = db.execute(size_query).fetchone()

        # Get table sizes
        table_sizes_query = """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
            pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY size_bytes DESC
        """
        table_sizes = db.execute(table_sizes_query).fetchall()

        return {
            "database_size": size_result[0] if size_result else "Unknown",
            "database_size_bytes": size_result[1] if size_result else 0,
            "table_sizes": [
                {
                    "schema": row[0],
                    "table": row[1],
                    "size": row[2],
                    "size_bytes": row[3]
                }
                for row in table_sizes
            ]
        }