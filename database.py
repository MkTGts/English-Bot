import sqlite3
from pathlib import Path
from typing import List, Dict, Any


DB_PATH = Path(__file__).resolve().parent / "bot.db"


def _get_connection() -> sqlite3.Connection:
    # Single connection for the whole process. check_same_thread=False allows
    # usage from different asyncio tasks in aiogram.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


conn = _get_connection()


def _init_db() -> None:
    """Create tables if they don't exist yet."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


_init_db()


def create_user_if_not_exists(telegram_id: int) -> None:
    """Create user record if it doesn't exist yet."""
    with conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (telegram_id)
            VALUES (?)
            """,
            (telegram_id,),
        )


def save_message(telegram_id: int, role: str, content: str) -> None:
    """Persist a single message for a given telegram_id."""
    with conn:
        conn.execute(
            """
            INSERT INTO messages (telegram_id, role, content)
            VALUES (?, ?, ?)
            """,
            (telegram_id, role, content),
        )


def get_last_messages(telegram_id: int, limit: int = 6) -> List[Dict[str, Any]]:
    """
    Return last `limit` messages for a user, ordered from oldest to newest.

    The result is a list of dicts: [{"role": "...", "content": "..."}, ...]
    suitable for passing directly to OpenAI (after adding system prompt).
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT role, content
        FROM messages
        WHERE telegram_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (telegram_id, limit),
    )
    rows = cur.fetchall()
    # We selected in DESC order, so reverse to get chronological order.
    ordered = list(reversed(rows))
    return [{"role": row["role"], "content": row["content"]} for row in ordered]


def clear_dialog(telegram_id: int) -> None:
    """Remove all messages for a given telegram_id."""
    with conn:
        conn.execute(
            """
            DELETE FROM messages
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )

