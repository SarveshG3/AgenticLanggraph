"""
Database initialization and connection management for Procurement PR workflow.
"""

import sqlite3
from pathlib import Path

# SQLite database path
DB_PATH = Path(__file__).with_name("procurement.db")


def get_db():
    """Get a connection to the procurement database."""
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Create and seed a local SQLite database for demo purposes."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS budgets (
            cost_center TEXT PRIMARY KEY,
            allocated REAL NOT NULL,
            used REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS approval_matrix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            min_amount REAL NOT NULL,
            max_amount REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS restricted_items (
            category TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS vendors (
            vendor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            active INTEGER NOT NULL,
            contract_ref TEXT,
            framework_agreement TEXT
        );
        """
    )
    # Seed only if empty to keep idempotent
    cur.execute("SELECT COUNT(*) FROM budgets")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO budgets(cost_center, allocated, used) VALUES (?, ?, ?)",
            [
                ("CC-4200", 20000.0, 5000.0),
                ("CC-5000", 10000.0, 9000.0),
            ],
        )

    cur.execute("SELECT COUNT(*) FROM approval_matrix")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO approval_matrix(role, min_amount, max_amount) VALUES (?, ?, ?)",
            [
                ("Manager", 0, 5000),
                ("Director", 5000, 20000),
                ("CFO", 20000, 1_000_000),
            ],
        )

    cur.execute("SELECT COUNT(*) FROM restricted_items")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO restricted_items(category) VALUES (?)",
            [
                ("Firearms",),
                ("Explosives",),
                ("Personal Travel",),
            ],
        )

    cur.execute("SELECT COUNT(*) FROM vendors")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO vendors(vendor_id, name, active, contract_ref, framework_agreement) VALUES (?, ?, ?, ?, ?)",
            [
                ("V-7788", "TechSource", 1, "MSA-123", "FA-9"),
                ("V-9999", "Blacklisted Co", 0, "NONE", None),
                ("V-1234", "OfficeSupplies Ltd", 1, "MSA-555", "FA-12"),
            ],
        )

    conn.commit()
    conn.close()


# Initialize database on import so demo runs without manual setup
init_db()
