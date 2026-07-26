import sqlite3
import hashlib
import json
import time
from typing import Optional, List, Dict, Any
from config import DATABASE_PATH

class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Table for raw news items
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                summary TEXT,
                content_hash TEXT NOT NULL UNIQUE,
                fetched_at INTEGER NOT NULL,
                processed INTEGER DEFAULT 0
            )
            """)

            # Table for generated & published Telegram posts
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                post_type TEXT DEFAULT 'news',
                category TEXT,
                quality_score REAL,
                quality_breakdown TEXT,
                source_url TEXT,
                referral_links TEXT,
                telegram_message_id INTEGER,
                published_at INTEGER NOT NULL,
                status TEXT DEFAULT 'published'
            )
            """)

            # Table for deduplication fingerprints
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dedup_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT UNIQUE NOT NULL,
                topic_keywords TEXT,
                created_at INTEGER NOT NULL
            )
            """)

            # Add image_url column if not exists
            try:
                cursor.execute("ALTER TABLE news_raw ADD COLUMN image_url TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

            conn.commit()

    def is_news_seen(self, source_url: str, title: str) -> bool:
        content_hash = hashlib.sha256(f"{source_url}:{title}".encode("utf-8")).hexdigest()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM news_raw WHERE content_hash = ? OR source_url = ?", (content_hash, source_url))
            return cursor.fetchone() is not None

    def add_raw_news(self, source_name: str, source_url: str, title: str, summary: str, image_url: Optional[str] = None) -> bool:
        content_hash = hashlib.sha256(f"{source_url}:{title}".encode("utf-8")).hexdigest()
        fetched_at = int(time.time())
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO news_raw (source_name, source_url, title, summary, content_hash, fetched_at, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (source_name, source_url, title, summary, content_hash, fetched_at, image_url))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Already exists

    def get_unprocessed_news(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM news_raw WHERE processed = 0 ORDER BY fetched_at ASC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_news_processed(self, news_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE news_raw SET processed = 1 WHERE id = ?", (news_id,))
            conn.commit()

    def record_published_post(self, title: str, content: str, post_type: str, category: str, 
                              quality_score: float, quality_breakdown: Dict, source_url: str, 
                              referral_links: List[str], telegram_message_id: Optional[int] = None) -> int:
        published_at = int(time.time())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO posts (title, content, post_type, category, quality_score, quality_breakdown, source_url, referral_links, telegram_message_id, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title,
                content,
                post_type,
                category,
                quality_score,
                json.dumps(quality_breakdown, ensure_ascii=False),
                source_url,
                json.dumps(referral_links, ensure_ascii=False),
                telegram_message_id,
                published_at
            ))
            conn.commit()
            return cursor.lastrowid

    def add_fingerprint(self, fingerprint: str, keywords: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                INSERT INTO dedup_fingerprints (fingerprint, topic_keywords, created_at)
                VALUES (?, ?, ?)
                """, (fingerprint, keywords, int(time.time())))
                conn.commit()
            except sqlite3.IntegrityError:
                pass

    def get_recent_posts(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts ORDER BY published_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
