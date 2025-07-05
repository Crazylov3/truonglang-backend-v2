#!/usr/bin/env python3
"""
Database Schema Display Tool for Learnify LMS

This script provides comprehensive database schema information.
Shows tables, columns, types, constraints, indexes, and relationships.

Usage:
    python scripts/show_db_schema.py --help
    # or from Docker container:
    uv run python scripts/show_db_schema.py --help

Examples:
    # Show all schema information
    python scripts/show_db_schema.py show-all

    # Show specific table
    python scripts/show_db_schema.py show-table --table users

    # Show all tables summary
    python scripts/show_db_schema.py list-tables

    # Show relationships/foreign keys
    python scripts/show_db_schema.py show-relationships
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

import click
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database import AsyncSessionLocal, async_engine
from app.config import settings


def format_column_type(column_type: str) -> str:
    """Format column type for display."""
    return str(column_type).replace('()', '').upper()


def format_constraint(constraint: Dict[str, Any]) -> str:
    """Format constraint information for display."""
    if constraint.get('type') == 'PRIMARY KEY':
        return f"PRIMARY KEY ({', '.join(constraint.get('constrained_columns', []))})"
    elif constraint.get('type') == 'UNIQUE':
        return f"UNIQUE ({', '.join(constraint.get('constrained_columns', []))})"
    elif constraint.get('type') == 'FOREIGN KEY':
        return f"FOREIGN KEY ({', '.join(constraint.get('constrained_columns', []))}) REFERENCES {constraint.get('referred_table', '')}"
    elif constraint.get('type') == 'CHECK':
        return f"CHECK ({constraint.get('sqltext', '')})"
    return str(constraint)


@click.group()
@click.version_option(version="1.0.0", prog_name="Learnify Schema Tool")
def cli():
    """
    🗄️ Learnify Database Schema Tool
    
    Comprehensive database schema information for the Learnify LMS system.
    """
    pass


@cli.command()
def list_tables():
    """List all tables in the database."""
    
    async def _list_tables():
        click.echo("📊 Database Tables")
        click.echo("=" * 50)
        
        async with AsyncSessionLocal() as session:
            try:
                # Get all tables
                result = await session.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        tableowner,
                        hasindexes,
                        hasrules,
                        hastriggers
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename;
                """))
                
                tables = result.fetchall()
                
                if not tables:
                    click.echo("📭 No tables found in the database.")
                    return
                
                for table in tables:
                    schema, name, owner, has_indexes, has_rules, has_triggers = table
                    
                    # Get row count
                    count_result = await session.execute(text(f"SELECT COUNT(*) FROM {name};"))
                    row_count = count_result.scalar()
                    
                    click.echo(f"📋 {name}")
                    click.echo(f"   Owner: {owner}")
                    click.echo(f"   Rows: {row_count:,}")
                    click.echo(f"   Indexes: {'Yes' if has_indexes else 'No'}")
                    click.echo(f"   Rules: {'Yes' if has_rules else 'No'}")
                    click.echo(f"   Triggers: {'Yes' if has_triggers else 'No'}")
                    click.echo()
                    
            except SQLAlchemyError as e:
                click.echo(f"❌ Database error: {e}")
    
    asyncio.run(_list_tables())


@cli.command()
@click.option('--table', prompt='Table name', help='Name of the table to show')
def show_table(table: str):
    """Show detailed information about a specific table."""
    
    async def _show_table():
        click.echo(f"📋 Table: {table}")
        click.echo("=" * 60)
        
        async with AsyncSessionLocal() as session:
            try:
                # Check if table exists
                result = await session.execute(text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_name = '{table}' AND table_schema = 'public';
                """))
                
                if result.scalar() == 0:
                    click.echo(f"❌ Table '{table}' not found!")
                    return
                
                # Get table info
                result = await session.execute(text(f"""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('{table}')) as size,
                        pg_stat_get_live_tuples('{table}'::regclass) as live_tuples,
                        pg_stat_get_dead_tuples('{table}'::regclass) as dead_tuples
                """))
                
                table_info = result.fetchone()
                if table_info:
                    size, live_tuples, dead_tuples = table_info
                    click.echo(f"📦 Size: {size}")
                    click.echo(f"📈 Live Tuples: {live_tuples}")
                    click.echo(f"📉 Dead Tuples: {dead_tuples}")
                    click.echo()
                
                # Get columns
                result = await session.execute(text(f"""
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default,
                        ordinal_position
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' AND table_schema = 'public'
                    ORDER BY ordinal_position;
                """))
                
                columns = result.fetchall()
                
                if columns:
                    click.echo("📝 Columns:")
                    click.echo("-" * 40)
                    for col in columns:
                        col_name, data_type, max_length, nullable, default, position = col
                        
                        type_str = data_type.upper()
                        if max_length:
                            type_str += f"({max_length})"
                        
                        null_str = "NULL" if nullable == "YES" else "NOT NULL"
                        default_str = f" DEFAULT {default}" if default else ""
                        
                        click.echo(f"  {position:2d}. {col_name:<20} {type_str:<15} {null_str}{default_str}")
                    click.echo()
                
                # Get indexes
                result = await session.execute(text(f"""
                    SELECT 
                        indexname,
                        indexdef
                    FROM pg_indexes 
                    WHERE tablename = '{table}' AND schemaname = 'public'
                    ORDER BY indexname;
                """))
                
                indexes = result.fetchall()
                
                if indexes:
                    click.echo("🔍 Indexes:")
                    click.echo("-" * 40)
                    for idx_name, idx_def in indexes:
                        click.echo(f"  {idx_name}")
                        click.echo(f"    {idx_def}")
                    click.echo()
                
                # Get foreign keys
                result = await session.execute(text(f"""
                    SELECT 
                        tc.constraint_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_name = '{table}'
                        AND tc.table_schema = 'public';
                """))
                
                foreign_keys = result.fetchall()
                
                if foreign_keys:
                    click.echo("🔗 Foreign Keys:")
                    click.echo("-" * 40)
                    for fk in foreign_keys:
                        constraint_name, column_name, ref_table, ref_column = fk
                        click.echo(f"  {column_name} -> {ref_table}.{ref_column}")
                        click.echo(f"    Constraint: {constraint_name}")
                    click.echo()
                
                # Get referencing tables
                result = await session.execute(text(f"""
                    SELECT 
                        tc.table_name,
                        kcu.column_name,
                        ccu.column_name AS referenced_column
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND ccu.table_name = '{table}'
                        AND tc.table_schema = 'public';
                """))
                
                referencing_tables = result.fetchall()
                
                if referencing_tables:
                    click.echo("🔙 Referenced By:")
                    click.echo("-" * 40)
                    for ref in referencing_tables:
                        ref_table, ref_column, referenced_column = ref
                        click.echo(f"  {ref_table}.{ref_column} -> {referenced_column}")
                    click.echo()
                    
            except SQLAlchemyError as e:
                click.echo(f"❌ Database error: {e}")
    
    asyncio.run(_show_table())


@cli.command()
def show_relationships():
    """Show all foreign key relationships in the database."""
    
    async def _show_relationships():
        click.echo("🔗 Database Relationships")
        click.echo("=" * 60)
        
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(text("""
                    SELECT 
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name,
                        tc.constraint_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public'
                    ORDER BY tc.table_name, kcu.column_name;
                """))
                
                relationships = result.fetchall()
                
                if not relationships:
                    click.echo("📭 No foreign key relationships found.")
                    return
                
                current_table = None
                for rel in relationships:
                    table, column, ref_table, ref_column, constraint = rel
                    
                    if table != current_table:
                        if current_table is not None:
                            click.echo()
                        click.echo(f"📋 {table}:")
                        current_table = table
                    
                    click.echo(f"  {column} -> {ref_table}.{ref_column}")
                    
            except SQLAlchemyError as e:
                click.echo(f"❌ Database error: {e}")
    
    asyncio.run(_show_relationships())


@cli.command()
def show_all():
    """Show comprehensive database schema information."""
    
    async def _show_all():
        click.echo("🗄️ Complete Database Schema")
        click.echo("=" * 80)
        
        async with AsyncSessionLocal() as session:
            try:
                # Database info
                result = await session.execute(text("SELECT version();"))
                version = result.scalar()
                click.echo(f"🗄️  Database: {version}")
                
                result = await session.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()));"))
                size = result.scalar()
                click.echo(f"📦 Size: {size}")
                click.echo()
                
                # Get all tables
                result = await session.execute(text("""
                    SELECT tablename
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename;
                """))
                
                tables = result.fetchall()
                
                for table_tuple in tables:
                    table_name = table_tuple[0]
                    
                    click.echo(f"📋 Table: {table_name}")
                    click.echo("-" * 50)
                    
                    # Get row count
                    count_result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
                    row_count = count_result.scalar()
                    click.echo(f"📊 Rows: {row_count:,}")
                    
                    # Get columns
                    result = await session.execute(text(f"""
                        SELECT 
                            column_name,
                            data_type,
                            character_maximum_length,
                            is_nullable,
                            column_default
                        FROM information_schema.columns 
                        WHERE table_name = '{table_name}' AND table_schema = 'public'
                        ORDER BY ordinal_position;
                    """))
                    
                    columns = result.fetchall()
                    
                    click.echo("📝 Columns:")
                    for col in columns:
                        col_name, data_type, max_length, nullable, default = col
                        
                        type_str = data_type.upper()
                        if max_length:
                            type_str += f"({max_length})"
                        
                        null_str = "NULL" if nullable == "YES" else "NOT NULL"
                        default_str = f" DEFAULT {default}" if default else ""
                        
                        click.echo(f"  • {col_name:<20} {type_str:<15} {null_str}{default_str}")
                    
                    # Get foreign keys
                    result = await session.execute(text(f"""
                        SELECT 
                            kcu.column_name,
                            ccu.table_name AS foreign_table_name,
                            ccu.column_name AS foreign_column_name
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                            ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                            ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                            AND tc.table_name = '{table_name}'
                            AND tc.table_schema = 'public';
                    """))
                    
                    foreign_keys = result.fetchall()
                    
                    if foreign_keys:
                        click.echo("🔗 Foreign Keys:")
                        for fk in foreign_keys:
                            column_name, ref_table, ref_column = fk
                            click.echo(f"  • {column_name} -> {ref_table}.{ref_column}")
                    
                    click.echo()
                    
            except SQLAlchemyError as e:
                click.echo(f"❌ Database error: {e}")
    
    asyncio.run(_show_all())


@cli.command()
def show_constraints():
    """Show all constraints in the database."""
    
    async def _show_constraints():
        click.echo("🔒 Database Constraints")
        click.echo("=" * 60)
        
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(text("""
                    SELECT 
                        tc.table_name,
                        tc.constraint_name,
                        tc.constraint_type,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    LEFT JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    LEFT JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.table_schema = 'public'
                    ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name;
                """))
                
                constraints = result.fetchall()
                
                if not constraints:
                    click.echo("📭 No constraints found.")
                    return
                
                current_table = None
                for constraint in constraints:
                    table, name, type_, column, ref_table, ref_column = constraint
                    
                    if table != current_table:
                        if current_table is not None:
                            click.echo()
                        click.echo(f"📋 {table}:")
                        current_table = table
                    
                    if type_ == 'PRIMARY KEY':
                        click.echo(f"  🔑 PRIMARY KEY: {name} ({column})")
                    elif type_ == 'FOREIGN KEY':
                        click.echo(f"  🔗 FOREIGN KEY: {name} ({column} -> {ref_table}.{ref_column})")
                    elif type_ == 'UNIQUE':
                        click.echo(f"  🔒 UNIQUE: {name} ({column})")
                    elif type_ == 'CHECK':
                        click.echo(f"  ✅ CHECK: {name}")
                    else:
                        click.echo(f"  📝 {type_}: {name} ({column})")
                    
            except SQLAlchemyError as e:
                click.echo(f"❌ Database error: {e}")
    
    asyncio.run(_show_constraints())


if __name__ == '__main__':
    cli() 