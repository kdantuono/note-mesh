#!/usr/bin/env python3
"""
Script per verificare la configurazione di PostgreSQL per NoteMesh.
"""

import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Load environment variables
load_dotenv()


async def verify_postgres():
    """Verifica la connessione e la struttura del database PostgreSQL."""

    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL non trovato nel file .env")
        return False

    if not database_url.startswith("postgresql"):
        print(f"❌ DATABASE_URL deve essere PostgreSQL, trovato: {database_url}")
        return False

    print(f"📌 Connessione a: {database_url.split('@')[1] if '@' in database_url else database_url}")

    try:
        # Create async engine
        engine = create_async_engine(database_url, echo=False)

        async with engine.connect() as conn:
            # Test connection
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connesso a PostgreSQL")
            print(f"   Versione: {version.split(',')[0]}")

            # Check tables
            result = await conn.execute(
                text(
                    """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """
                )
            )
            tables = [row[0] for row in result]

            if tables:
                print(f"\n📋 Tabelle trovate ({len(tables)}):")
                for table in tables:
                    if table != "alembic_version":
                        print(f"   ✓ {table}")
            else:
                print("\n⚠️  Nessuna tabella trovata. Esegui: alembic upgrade head")
                return False

            # Check UUID extension
            result = await conn.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'uuid'
                )
            """
                )
            )
            has_uuid = result.scalar()
            if has_uuid:
                print("\n✅ Tipo UUID nativo disponibile")

            # Check sample table structure
            if "users" in tables:
                result = await conn.execute(
                    text(
                        """
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name IN ('id', 'username', 'created_at')
                    ORDER BY ordinal_position
                """
                    )
                )
                print("\n📊 Struttura tabella 'users' (sample):")
                for col_name, col_type in result:
                    print(f"   - {col_name:15} {col_type}")

            # Count indexes
            result = await conn.execute(
                text(
                    """
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND tablename != 'alembic_version'
            """
                )
            )
            index_count = result.scalar()
            print(f"\n📌 Indici creati: {index_count}")

            # Check foreign keys
            result = await conn.execute(
                text(
                    """
                SELECT COUNT(*) 
                FROM information_schema.table_constraints 
                WHERE constraint_schema = 'public' 
                AND constraint_type = 'FOREIGN KEY'
            """
                )
            )
            fk_count = result.scalar()
            print(f"🔗 Foreign keys: {fk_count}")

            print("\n✨ Database PostgreSQL configurato correttamente!")
            return True

    except Exception as e:
        print(f"\n❌ Errore di connessione: {e}")
        print("\n💡 Suggerimenti:")
        print("   1. Verifica che PostgreSQL sia in esecuzione: docker ps")
        print("   2. Controlla DATABASE_URL nel file .env")
        print("   3. Assicurati che il database esista")
        return False
    finally:
        await engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(verify_postgres())
    exit(0 if success else 1)
