import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import uuid

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "refund_system.db"


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    target_path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    """Initialize database tables with schema constraints."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # Purchases table (with duplicate refund tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                price REAL NOT NULL,
                purchase_date TEXT NOT NULL,
                is_refunded INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Refund tickets table (audit trail)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refund_tickets (
                ticket_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                item_names TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL, -- 'ISSUED', 'REQUIRES_APPROVAL', 'REJECTED'
                reason TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        conn.commit()


def seed_db(db_path: Optional[Path] = None) -> None:
    """
    Seeds database with dynamic relative dates (e.g. today - X days).
    This ensures 30-day return policy tests never become stale.
    """
    init_db(db_path)
    today = date.today()

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Clear existing data for fresh seed
        cursor.execute("DELETE FROM refund_tickets")
        cursor.execute("DELETE FROM purchases")
        cursor.execute("DELETE FROM users")

        # Users
        users = [
            ("user123", "Alice Smith", "alice@example.com", (today - timedelta(days=60)).isoformat()),
            ("user124", "Bob Johnson", "bob@example.com", (today - timedelta(days=40)).isoformat()),
            ("user125", "Charlie Lee", "charlie@example.com", (today - timedelta(days=50)).isoformat()),
            ("user126", "Dana White", "dana@example.com", (today - timedelta(days=70)).isoformat()),
            ("user127", "Evan Brown", "evan@example.com", (today - timedelta(days=20)).isoformat()),
            ("user128", "Fiona Green", "fiona@example.com", (today - timedelta(days=30)).isoformat()),
        ]
        cursor.executemany("INSERT INTO users VALUES (?, ?, ?, ?)", users)

        # Purchases with relative dates
        # Note:
        # - user123: book (10 days ago, eligible), pen (5 days ago, eligible)
        # - user124: notebook (3 days ago, eligible)
        # - user125: pencil (15 days ago, eligible), ruler (45 days ago, EXPIRED > 30 days)
        # - user126: backpack (12 days ago, eligible), water_bottle (40 days ago, EXPIRED),
        #            lunch_box (10 days ago, eligible), premium_laptop (7 days ago, high value: $450)
        # - user127: eraser (5 days ago, ALREADY REFUNDED: is_refunded=1)
        # - user128: desk_lamp (exactly 30 days ago, boundary test: eligible), stapler (31 days ago, boundary test: expired)
        purchases = [
            ("user123", "book", 23.0, (today - timedelta(days=10)).isoformat(), 0),
            ("user123", "pen", 7.0, (today - timedelta(days=5)).isoformat(), 0),
            
            ("user124", "notebook", 12.0, (today - timedelta(days=3)).isoformat(), 0),
            
            ("user125", "pencil", 3.0, (today - timedelta(days=15)).isoformat(), 0),
            ("user125", "ruler", 5.0, (today - timedelta(days=45)).isoformat(), 0),
            
            ("user126", "backpack", 45.0, (today - timedelta(days=12)).isoformat(), 0),
            ("user126", "water_bottle", 18.0, (today - timedelta(days=40)).isoformat(), 0),
            ("user126", "lunch_box", 14.0, (today - timedelta(days=10)).isoformat(), 0),
            ("user126", "premium_laptop", 450.0, (today - timedelta(days=7)).isoformat(), 0),
            
            # Already refunded item to test idempotency and double-refund prevention
            ("user127", "eraser", 2.0, (today - timedelta(days=5)).isoformat(), 1),
            
            # Boundary test items
            ("user128", "desk_lamp", 28.0, (today - timedelta(days=30)).isoformat(), 0),
            ("user128", "stapler", 11.0, (today - timedelta(days=31)).isoformat(), 0),
        ]
        cursor.executemany("""
            INSERT INTO purchases (user_id, item_name, price, purchase_date, is_refunded)
            VALUES (?, ?, ?, ?, ?)
        """, purchases)

        # Seed an existing ticket for user127's already-refunded eraser
        existing_ticket = (
            f"TICK-{uuid.uuid4().hex[:8].upper()}",
            "user127",
            "eraser",
            2.0,
            "ISSUED",
            "Prior approved refund",
            (today - timedelta(days=2)).isoformat()
        )
        cursor.execute("""
            INSERT INTO refund_tickets VALUES (?, ?, ?, ?, ?, ?, ?)
        """, existing_ticket)

        conn.commit()


def get_user_purchases(user_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve all purchase records for a user."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, item_name, price, purchase_date, is_refunded
            FROM purchases
            WHERE user_id = ?
        """, (user_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_user_purchase_dict(user_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Returns user purchases in dictionary format compatible with the agent's tools:
    { "item_name": {"price": ..., "date": ..., "is_refunded": ...} }
    """
    purchases = get_user_purchases(user_id, db_path)
    if not purchases:
        # Check if user actually exists
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not cursor.fetchone():
                return None
        return {}

    return {
        row["item_name"]: {
            "price": row["price"],
            "date": row["purchase_date"],
            "is_refunded": bool(row["is_refunded"])
        }
        for row in purchases
    }


def issue_refund(user_id: str, item_names: List[str], amount: float, status: str = "ISSUED", reason: str = "", db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Atomic refund transaction:
    1. Validates items are not already refunded.
    2. Marks the purchase items as refunded (is_refunded=1).
    3. Records a persistent refund ticket.
    """
    ticket_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
    today_str = date.today().isoformat()

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        
        # Check if any requested item is already refunded
        placeholders = ",".join("?" for _ in item_names)
        cursor.execute(f"""
            SELECT item_name, is_refunded FROM purchases
            WHERE user_id = ? AND item_name IN ({placeholders})
        """, [user_id] + item_names)
        
        found_rows = cursor.fetchall()
        already_refunded = [r["item_name"] for r in found_rows if r["is_refunded"] == 1]
        if already_refunded:
            return {
                "success": False,
                "error": f"Item(s) already refunded: {', '.join(already_refunded)}. Duplicate refund denied."
            }

        # Mark purchases as refunded
        cursor.execute(f"""
            UPDATE purchases
            SET is_refunded = 1
            WHERE user_id = ? AND item_name IN ({placeholders})
        """, [user_id] + item_names)

        # Insert audit ticket
        cursor.execute("""
            INSERT INTO refund_tickets (ticket_id, user_id, item_names, amount, status, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticket_id, user_id, ", ".join(item_names), amount, status, reason, today_str))

        conn.commit()

        return {
            "success": True,
            "ticket_id": ticket_id,
            "user_id": user_id,
            "items": item_names,
            "amount": amount,
            "status": status,
            "created_at": today_str
        }


def get_all_tickets(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve all issued refund tickets."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM refund_tickets ORDER BY created_at DESC")
        return [dict(r) for r in cursor.fetchall()]


def get_all_purchases(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve all purchase records (used for UI inspection)."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM purchases ORDER BY user_id, purchase_date DESC")
        return [dict(r) for r in cursor.fetchall()]


if __name__ == "__main__":
    print("Initializing and seeding database...")
    seed_db()
    print("Database seeded successfully with relative dates.")
    sample = get_user_purchases("user123")
    print("Sample purchases for user123:", sample)

