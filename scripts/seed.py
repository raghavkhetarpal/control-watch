#!/usr/bin/env python3
"""AWM ControlWatch - Seed Script.

Seeds the database with reference data and sample users.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.database.connection import init_db, get_session


def main():
    print("Initializing database...")
    init_db()

    print("Seeding users...")
    with get_session() as session:
        session.execute(text("""
            INSERT INTO users (username, display_name, email, role)
            VALUES
                ('admin', 'Admin User', 'admin@example.com', 'ADMIN'),
                ('analyst1', 'Sarah Chen', 'sarah.chen@example.com', 'ANALYST'),
                ('analyst2', 'James Park', 'james.park@example.com', 'ANALYST'),
                ('analyst3', 'Emily Watson', 'emily.watson@example.com', 'ANALYST'),
                ('manager1', 'Maria Rodriguez', 'maria.rodriguez@example.com', 'MANAGER'),
                ('viewer1', 'David Kim', 'david.kim@example.com', 'VIEWER')
            ON CONFLICT (username) DO NOTHING
        """))

    print("✅ Seed data loaded")


if __name__ == "__main__":
    main()
