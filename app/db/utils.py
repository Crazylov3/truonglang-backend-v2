class DatabaseManager:
    """
    Comprehensive database management utilities for the Learnify LMS.
    
    This class provides methods for:
    - Running migrations programmatically
    - Health checks and diagnostics
    - Database initialization and setup
    """
    
    def __init__(self):
        from app.database import sync_engine, AsyncSessionLocal
        self.sync_engine = sync_engine
        self.async_session = AsyncSessionLocal
    
    async def check_migration_status(self):
        """Check if database migrations are up to date."""
        try:
            # Import alembic here to avoid circular imports
            from alembic.config import Config
            from alembic import command
            from alembic.script import ScriptDirectory
            from alembic.runtime.environment import EnvironmentContext
            
            alembic_cfg = Config("alembic.ini")
            script = ScriptDirectory.from_config(alembic_cfg)
            
            def check_current_head(rev, context):
                return script.get_current_head()
            
            with self.sync_engine.connect() as connection:
                context = EnvironmentContext(
                    config=alembic_cfg,
                    script=script,
                    fn=check_current_head,
                )
                
                with context.begin_transaction():
                    current_head = context.get_current_revision()
                    latest_head = script.get_current_head()
                    
                    return {
                        "current_revision": current_head,
                        "latest_revision": latest_head,
                        "is_up_to_date": current_head == latest_head,
                        "status": "up_to_date" if current_head == latest_head else "needs_migration"
                    }
                    
        except Exception as e:
            return {
                "error": str(e),
                "status": "error",
                "message": "Could not check migration status"
            }
    
    async def get_database_info(self):
        """Get comprehensive database information."""
        try:
            async with self.async_session() as session:
                # Check database connection
                result = await session.execute(text("SELECT version()"))
                db_version = result.scalar()
                
                # Check table existence
                tables_query = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables_result = await session.execute(tables_query)
                tables = [row[0] for row in tables_result.fetchall()]
                
                return {
                    "status": "connected",
                    "database_version": db_version,
                    "tables": tables,
                    "table_count": len(tables)
                }
                
        except Exception as e:
            return {
                "status": "disconnected",
                "error": str(e),
                "message": "Could not connect to database"
            } 