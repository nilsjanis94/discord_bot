import sqlite3
import aiosqlite
import os
from datetime import datetime

# Definiere den Pfad zur Datenbank
DB_PATH = os.path.join('data', 'moderation.db')

# Stelle sicher, dass der data Ordner existiert
os.makedirs('data', exist_ok=True)

async def init_db():
    """Initialisiert die Datenbank und erstellt die benötigten Tabellen"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Tabelle für Moderations-Aktionen
        await db.execute('''
            CREATE TABLE IF NOT EXISTS mod_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                action_type TEXT,
                reason TEXT,
                duration INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabelle für Verwarnungen
        await db.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabelle für Willkommens-Konfiguration
        await db.execute('''
            CREATE TABLE IF NOT EXISTS welcome_config (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel_id INTEGER,
                rules_channel_id INTEGER,
                verification_channel_id INTEGER,
                welcome_message TEXT,
                welcome_role_id INTEGER,
                rules_message_id INTEGER,
                temp_role_id INTEGER,
                verified_role_id INTEGER,
                enabled BOOLEAN DEFAULT 1,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabelle für Auto-Mod Konfiguration
        await db.execute('''
            CREATE TABLE IF NOT EXISTS automod_config (
                guild_id INTEGER PRIMARY KEY,
                spam_detection BOOLEAN DEFAULT 0,
                spam_threshold INTEGER DEFAULT 5,
                spam_interval INTEGER DEFAULT 5,
                link_filter BOOLEAN DEFAULT 0,
                allowed_links TEXT,
                caps_filter BOOLEAN DEFAULT 0,
                caps_threshold INTEGER DEFAULT 70,
                emoji_filter BOOLEAN DEFAULT 0,
                emoji_threshold INTEGER DEFAULT 5,
                flood_filter BOOLEAN DEFAULT 0,
                flood_threshold INTEGER DEFAULT 5,
                flood_interval INTEGER DEFAULT 3,
                enabled BOOLEAN DEFAULT 0,
                log_channel_id INTEGER,
                whitelist_roles TEXT,
                whitelist_channels TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tabelle für Wort-Filter
        await db.execute('''
            CREATE TABLE IF NOT EXISTS word_filter (
                guild_id INTEGER,
                word TEXT,
                action TEXT DEFAULT 'delete',
                added_by INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, word)
            )
        ''')

        # Tabelle für Spam-Tracking
        await db.execute('''
            CREATE TABLE IF NOT EXISTS spam_tracking (
                guild_id INTEGER,
                user_id INTEGER,
                message_count INTEGER DEFAULT 1,
                last_message TEXT,
                last_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        
        await db.commit() 