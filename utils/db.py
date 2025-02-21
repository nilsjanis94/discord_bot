import sqlite3
import aiosqlite
import os
from datetime import datetime

DB_PATH = "data/moderation.db"

# Stelle sicher, dass der Ordner existiert
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

async def init_db():
    """Initialisiert die Datenbank und erstellt die benötigten Tabellen"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Erstelle zuerst die channel_config Tabelle
        await db.execute('''
            CREATE TABLE IF NOT EXISTS channel_config (
                guild_id INTEGER PRIMARY KEY,
                mod_log_channel_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabelle für Verwarnungen
        await db.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                guild_id INTEGER NOT NULL,
                reason TEXT,
                moderator_id INTEGER NOT NULL,
                moderator_name TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabelle für Timeouts
        await db.execute('''
            CREATE TABLE IF NOT EXISTS timeouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                guild_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                moderator_name TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL
            )
        ''')

        # Tabelle für Kicks
        await db.execute('''
            CREATE TABLE IF NOT EXISTS kicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                guild_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                moderator_name TEXT NOT NULL,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabelle für Bans
        await db.execute('''
            CREATE TABLE IF NOT EXISTS bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                guild_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                moderator_name TEXT NOT NULL,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_temporary BOOLEAN DEFAULT 0,
                expires_at DATETIME
            )
        ''')
        
        await db.commit() 