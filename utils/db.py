import sqlite3
import aiosqlite
import os
from datetime import datetime

DB_PATH = "data/moderation.db"

# Lösche die alte Datenbank wenn sie existiert
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print("🗑️ Alte Datenbank gelöscht")

async def init_db():
    """Initialisiert die Datenbank"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Tabelle für Willkommenssystem
        await db.execute('''
            CREATE TABLE IF NOT EXISTS welcome_config (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel_id INTEGER,
                rules_channel_id INTEGER,
                temp_role_id INTEGER,
                verified_role_id INTEGER,
                welcome_message TEXT,
                enabled BOOLEAN DEFAULT 0
            )
        ''')

        # Tabelle für Warnungen
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

        # Tabelle für Kanal-Konfiguration
        await db.execute('''
            CREATE TABLE IF NOT EXISTS channel_config (
                guild_id INTEGER PRIMARY KEY,
                mod_log_channel_id INTEGER
            )
        ''')

        await db.commit()
        print("✅ Neue Datenbank-Tabellen wurden erstellt!")

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

        # Tabelle für Serverregeln
        await db.execute('''
            CREATE TABLE IF NOT EXISTS server_rules (
                guild_id INTEGER NOT NULL,
                rule_number INTEGER NOT NULL,
                rule_title TEXT,
                rule_content TEXT NOT NULL,
                last_edited_by INTEGER,
                last_edited_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, rule_number)
            )
        ''')

        # Tabelle für Moderationsaktionen
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mod_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                active BOOLEAN DEFAULT 1
            )
        ''') 