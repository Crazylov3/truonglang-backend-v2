"""System and database management commands for admin CLI."""

import click
import os
from sqlalchemy import text, inspect
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import asyncio

from app.database import AsyncSessionLocal, redis_client
from app.config import settings
from ..utils import async_command, display_stats, display_table


@click.group(name='system')
def system_group():
    """🖥️ System and database management commands."""
    pass


@system_group.command()
@async_command
async def info():
    """Show system information and configuration."""
    click.echo("🖥️ System Information")
    click.echo("=" * 60)
    
    click.echo("\n📋 Application Configuration:")
    click.echo(f"   App Name: {settings.app_name}")
    click.echo(f"   Version: {settings.version}")
    click.echo(f"   Debug Mode: {settings.debug}")
    click.echo(f"   Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    click.echo("\n🗄️ Database Configuration:")
    click.echo(f"   Host: {settings.db_host}")
    click.echo(f"   Port: {settings.db_port}")
    click.echo(f"   Database: {settings.db_name}")
    click.echo(f"   Driver: {settings.db_driver}")
    
    click.echo("\n🔴 Redis Configuration:")
    click.echo(f"   Host: {settings.redis_host}")
    click.echo(f"   Port: {settings.redis_port}")
    click.echo(f"   Database: {settings.redis_db}")
    
    click.echo("\n🔐 Security Configuration:")
    click.echo(f"   JWT Algorithm: {settings.algorithm}")
    click.echo(f"   Access Token Expiry: {settings.access_token_expire_minutes} minutes")
    click.echo(f"   CSRF Token Expiry: {settings.csrf_token_expire_minutes} minutes")
    click.echo(f"   Password Reset Expiry: {settings.password_reset_expire_minutes} minutes")
    
    click.echo("\n📧 Email Configuration:")
    click.echo(f"   From Email: {settings.from_email}")
    click.echo(f"   From Name: {settings.from_name}")
    click.echo(f"   SendGrid Configured: {'Yes' if settings.sendgrid_api_key else 'No'}")


@system_group.command()
@async_command
async def database_info():
    """Show detailed database information and statistics."""
    click.echo("🗄️ Database Information")
    click.echo("=" * 60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Database version
            result = await session.execute(text("SELECT version();"))
            version = result.scalar()
            click.echo(f"\n🐘 PostgreSQL Version:")
            click.echo(f"   {version}")
            
            # Database size
            result = await session.execute(text("""
                SELECT 
                    pg_database.datname as database_name,
                    pg_size_pretty(pg_database_size(pg_database.datname)) AS size
                FROM pg_database
                WHERE datname = current_database();
            """))
            db_info = result.fetchone()
            if db_info:
                click.echo(f"\n📦 Database Size:")
                click.echo(f"   {db_info.database_name}: {db_info.size}")
            
            # Connection info
            result = await session.execute(text("""
                SELECT 
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections
                FROM pg_stat_activity
                WHERE datname = current_database();
            """))
            conn_info = result.fetchone()
            if conn_info:
                click.echo(f"\n🔌 Connections:")
                click.echo(f"   Total: {conn_info.total_connections}")
                click.echo(f"   Active: {conn_info.active_connections}")
                click.echo(f"   Idle: {conn_info.idle_connections}")
            
            # Table statistics
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                    n_live_tup AS row_count
                FROM pg_stat_user_tables
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10;
            """))
            tables = result.fetchall()
            
            if tables:
                click.echo(f"\n📊 Largest Tables:")
                rows = []
                for table in tables:
                    rows.append([
                        f"{table.schemaname}.{table.tablename}",
                        table.size,
                        f"{table.row_count:,}"
                    ])
                display_table(['Table', 'Size', 'Rows'], rows)
            
        except SQLAlchemyError as e:
            click.echo(f"❌ Database error: {e}")


@system_group.command()
@async_command
async def redis_info():
    """Show Redis server information and statistics."""
    click.echo("🔴 Redis Information")
    click.echo("=" * 60)
    
    try:
        # Get Redis info
        info = await redis_client.info()
        
        # Server info
        server_info = info.get('server', {})
        click.echo(f"\n📋 Server Information:")
        click.echo(f"   Version: {server_info.get('redis_version', 'Unknown')}")
        click.echo(f"   Mode: {server_info.get('redis_mode', 'Unknown')}")
        click.echo(f"   Uptime: {server_info.get('uptime_in_days', 0)} days")
        
        # Memory info
        memory_info = info.get('memory', {})
        click.echo(f"\n💾 Memory Usage:")
        click.echo(f"   Used: {memory_info.get('used_memory_human', 'Unknown')}")
        click.echo(f"   Peak: {memory_info.get('used_memory_peak_human', 'Unknown')}")
        click.echo(f"   RSS: {memory_info.get('used_memory_rss_human', 'Unknown')}")
        
        # Stats
        stats_info = info.get('stats', {})
        click.echo(f"\n📊 Statistics:")
        click.echo(f"   Total Commands: {stats_info.get('total_commands_processed', 0):,}")
        click.echo(f"   Connected Clients: {info.get('clients', {}).get('connected_clients', 0)}")
        click.echo(f"   Keys: {info.get('keyspace', {}).get('db0', {}).get('keys', 0)}")
        
        # Get some key samples
        keys = await redis_client.keys('*')
        if keys:
            click.echo(f"\n🔑 Sample Keys ({min(len(keys), 10)} of {len(keys)}):")
            for key in keys[:10]:
                key_type = await redis_client.type(key)
                ttl = await redis_client.ttl(key)
                ttl_str = f"{ttl}s" if ttl > 0 else "No expiry"
                click.echo(f"   - {key} (type: {key_type}, ttl: {ttl_str})")
        
    except Exception as e:
        click.echo(f"❌ Redis error: {e}")


@system_group.command()
@async_command
async def table_counts():
    """Show row counts for all tables."""
    click.echo("📊 Table Row Counts")
    click.echo("=" * 60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Get all table names
            inspector = inspect(session.bind)
            tables = inspector.get_table_names()
            
            stats = []
            total_rows = 0
            
            for table in sorted(tables):
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table};"))
                count = result.scalar()
                stats.append({'table': table, 'count': count})
                total_rows += count
            
            # Display results
            if stats:
                rows = []
                for stat in sorted(stats, key=lambda x: x['count'], reverse=True):
                    rows.append([stat['table'], f"{stat['count']:,}"])
                
                display_table(['Table', 'Row Count'], rows)
                click.echo(f"\n📈 Total Rows: {total_rows:,}")
            else:
                click.echo("📭 No tables found.")
                
        except SQLAlchemyError as e:
            click.echo(f"❌ Database error: {e}")


@system_group.command()
@click.option('--table', help='Specific table to check (optional)')
@async_command
async def check_indexes(table: str):
    """Check database indexes."""
    click.echo("🔍 Database Indexes")
    click.echo("=" * 60)
    
    async with AsyncSessionLocal() as session:
        try:
            if table:
                # Check specific table
                query = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE tablename = :table
                    ORDER BY indexname;
                """)
                result = await session.execute(query, {'table': table})
            else:
                # Check all user tables
                query = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY tablename, indexname;
                """)
                result = await session.execute(query)
            
            indexes = result.fetchall()
            
            if not indexes:
                click.echo("📭 No indexes found.")
                return
            
            current_table = None
            for index in indexes:
                if index.tablename != current_table:
                    current_table = index.tablename
                    click.echo(f"\n📋 Table: {index.schemaname}.{index.tablename}")
                
                click.echo(f"   - {index.indexname}")
                if click.get_current_context().obj.get('verbose'):
                    click.echo(f"     {index.indexdef}")
                    
        except SQLAlchemyError as e:
            click.echo(f"❌ Database error: {e}")


@system_group.command()
@async_command
async def clear_cache():
    """Clear Redis cache."""
    if not click.confirm("⚠️  This will clear ALL Redis cache. Continue?"):
        click.echo("❌ Operation cancelled.")
        return
    
    try:
        await redis_client.flushdb()
        click.echo("✅ Redis cache cleared successfully!")
    except Exception as e:
        click.echo(f"❌ Error clearing cache: {e}")


@system_group.command()
@click.option('--vacuum', is_flag=True, help='Run VACUUM ANALYZE')
@click.option('--reindex', is_flag=True, help='Reindex all tables')
@async_command
async def optimize_database(vacuum: bool, reindex: bool):
    """Optimize database performance."""
    if not vacuum and not reindex:
        click.echo("ℹ️  Specify --vacuum or --reindex to optimize database.")
        return
    
    async with AsyncSessionLocal() as session:
        try:
            if vacuum:
                click.echo("🔧 Running VACUUM ANALYZE...")
                await session.execute(text("VACUUM ANALYZE;"))
                await session.commit()
                click.echo("✅ VACUUM ANALYZE completed!")
            
            if reindex:
                click.echo("🔧 Reindexing database...")
                # Get current database name
                result = await session.execute(text("SELECT current_database();"))
                db_name = result.scalar()
                
                await session.execute(text(f"REINDEX DATABASE {db_name};"))
                await session.commit()
                click.echo("✅ Database reindexed!")
                
        except SQLAlchemyError as e:
            click.echo(f"❌ Database error: {e}")


@system_group.command()
@async_command
async def health_check():
    """Perform system health check."""
    click.echo("🏥 System Health Check")
    click.echo("=" * 60)
    
    health_status = {
        'database': False,
        'redis': False,
        'tables': False
    }
    
    # Check database connection
    click.echo("\n🗄️ Checking database connection...")
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1;"))
            health_status['database'] = True
            click.echo("   ✅ Database connection: OK")
    except Exception as e:
        click.echo(f"   ❌ Database connection: FAILED - {e}")
    
    # Check Redis connection
    click.echo("\n🔴 Checking Redis connection...")
    try:
        await redis_client.ping()
        health_status['redis'] = True
        click.echo("   ✅ Redis connection: OK")
    except Exception as e:
        click.echo(f"   ❌ Redis connection: FAILED - {e}")
    
    # Check critical tables
    click.echo("\n📋 Checking critical tables...")
    critical_tables = ['users', 'courses', 'enrollments', 'audit_logs']
    all_tables_ok = True
    
    try:
        async with AsyncSessionLocal() as session:
            for table in critical_tables:
                try:
                    result = await session.execute(text(f"SELECT COUNT(*) FROM {table};"))
                    count = result.scalar()
                    click.echo(f"   ✅ {table}: OK ({count} rows)")
                except Exception:
                    click.echo(f"   ❌ {table}: NOT FOUND")
                    all_tables_ok = False
        
        health_status['tables'] = all_tables_ok
    except Exception as e:
        click.echo(f"   ❌ Table check failed: {e}")
    
    # Overall status
    all_ok = all(health_status.values())
    click.echo("\n" + "=" * 60)
    if all_ok:
        click.echo("✅ Overall Status: HEALTHY")
    else:
        click.echo("❌ Overall Status: UNHEALTHY")
        failed = [k for k, v in health_status.items() if not v]
        click.echo(f"   Failed components: {', '.join(failed)}")


@system_group.command()
@click.option('--output', type=click.File('w'), help='Output file (default: stdout)')
@async_command
async def export_schema(output):
    """Export database schema to SQL file."""
    click.echo("📤 Exporting database schema...")
    
    try:
        # Use pg_dump to export schema
        import subprocess
        
        cmd = [
            'pg_dump',
            '--host', settings.db_host,
            '--port', str(settings.db_port),
            '--username', settings.db_user,
            '--dbname', settings.db_name,
            '--schema-only',
            '--no-owner',
            '--no-privileges'
        ]
        
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = settings.db_password
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            if output:
                output.write(result.stdout)
                click.echo(f"✅ Schema exported to {output.name}")
            else:
                click.echo(result.stdout)
        else:
            click.echo(f"❌ Export failed: {result.stderr}")
            
    except FileNotFoundError:
        click.echo("❌ pg_dump not found. Please install PostgreSQL client tools.")
    except Exception as e:
        click.echo(f"❌ Export error: {e}")