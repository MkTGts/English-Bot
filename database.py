import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional


DB_PATH = Path(__file__).resolve().parent / "bot.db"


def _get_connection() -> sqlite3.Connection:
    # Single connection for the whole process. check_same_thread=False allows
    # usage from different asyncio tasks in aiogram.
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


conn = _get_connection()


def _safe_add_column(column_def: str) -> None:
    """
    Try to add a column to the users table.
    If the column already exists, ignore the error.
    """
    try:
        with conn:
            conn.execute(f"ALTER TABLE users ADD COLUMN {column_def}")
    except sqlite3.OperationalError:
        # Column already exists or other non‑critical error – ignore.
        pass


def _init_db() -> None:
    """Create tables if they don't exist yet and ensure required columns exist."""
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                messages_count INTEGER DEFAULT 0,
                user_messages INTEGER DEFAULT 0,
                ai_messages INTEGER DEFAULT 0,
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

    # For existing databases created with an older schema, add missing columns.
    _safe_add_column("messages_count INTEGER DEFAULT 0")
    _safe_add_column("user_messages INTEGER DEFAULT 0")
    _safe_add_column("ai_messages INTEGER DEFAULT 0")


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


def increment_user_message(telegram_id: int) -> None:
    """Increase total and user message counters for a user."""
    with conn:
        conn.execute(
            """
            UPDATE users
            SET messages_count = COALESCE(messages_count, 0) + 1,
                user_messages = COALESCE(user_messages, 0) + 1
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )


def increment_ai_message(telegram_id: int) -> None:
    """Increase total and AI message counters for a user."""
    with conn:
        conn.execute(
            """
            UPDATE users
            SET messages_count = COALESCE(messages_count, 0) + 1,
                ai_messages = COALESCE(ai_messages, 0) + 1
            WHERE telegram_id = ?
            """,
            (telegram_id,),
        )


def get_user_stats(telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Return statistics for a user:
    - user_messages
    - ai_messages
    - messages_count
    - created_at
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            COALESCE(user_messages, 0) AS user_messages,
            COALESCE(ai_messages, 0) AS ai_messages,
            COALESCE(messages_count, 0) AS messages_count,
            created_at
        FROM users
        WHERE telegram_id = ?
        """,
        (telegram_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None

    return {
        "user_messages": row["user_messages"],
        "ai_messages": row["ai_messages"],
        "messages_count": row["messages_count"],
        "created_at": row["created_at"],
    }


def get_all_users_stats() -> List[Dict[str, Any]]:
    """
    Return statistics for all users (telegram_id, user_messages, ai_messages,
    messages_count, created_at), ordered by created_at.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            telegram_id,
            COALESCE(user_messages, 0) AS user_messages,
            COALESCE(ai_messages, 0) AS ai_messages,
            COALESCE(messages_count, 0) AS messages_count,
            created_at
        FROM users
        ORDER BY created_at ASC
        """
    )
    rows = cur.fetchall()
    return [
        {
            "telegram_id": row["telegram_id"],
            "user_messages": row["user_messages"],
            "ai_messages": row["ai_messages"],
            "messages_count": row["messages_count"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


