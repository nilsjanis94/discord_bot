import sqlite3
import aiosqlite
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

DB_PATH = "data/discord_bot.db"

# Stelle sicher, dass das Verzeichnis existiert
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

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
        
        # Tabelle für Reaction Roles
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reaction_roles (
                message_id TEXT,
                emoji TEXT,
                role_id TEXT,
                guild_id TEXT,
                channel_id TEXT,
                description TEXT,
                PRIMARY KEY (message_id, emoji)
            )
        ''')

        # Tabelle für Wetter-Einstellungen
        await db.execute('''
            CREATE TABLE IF NOT EXISTS weather_settings (
                guild_id TEXT,
                channel_id TEXT,
                city TEXT,
                update_time TEXT,
                enabled INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, city)
            )
        ''')
        
        # AutoMod-Konfigurationstabelle
        await db.execute('''
            CREATE TABLE IF NOT EXISTS automod_config (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 0,
                log_channel_id INTEGER
            )
        ''')
        
        # AutoMod-Whitelist-Tabelle
        await db.execute('''
            CREATE TABLE IF NOT EXISTS automod_whitelist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                role_id INTEGER,
                channel_id INTEGER,
                type TEXT NOT NULL,
                UNIQUE(guild_id, role_id, type),
                UNIQUE(guild_id, channel_id, type)
            )
        ''')
        
        # AutoMod-Filter-Tabelle
        await db.execute('''
            CREATE TABLE IF NOT EXISTS automod_filter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                type TEXT NOT NULL,
                UNIQUE(guild_id, word, type)
            )
        ''')
        
        # AutoMod-Einstellungen-Tabelle
        await db.execute('''
            CREATE TABLE IF NOT EXISTS automod_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                setting_type TEXT NOT NULL,
                value TEXT NOT NULL,
                UNIQUE(guild_id, setting_type)
            )
        ''')

        # Temp Voice Channels Tables
        await db.execute('''
        CREATE TABLE IF NOT EXISTS temp_voice_config (
            guild_id INTEGER PRIMARY KEY,
            creator_channel_id INTEGER,
            category_id INTEGER,
            user_limit INTEGER DEFAULT 1,
            default_privacy TEXT DEFAULT 'public'
        )
        ''')
        
        await db.execute('''
        CREATE TABLE IF NOT EXISTS temp_voice_channels (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            owner_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            privacy TEXT DEFAULT 'public'
        )
        ''')

        await db.commit()
        print("✅ Datenbank-Tabellen wurden initialisiert!")

class Database:
    """Zentrale Datenbankklasse für den Discord Bot"""
    
    def __init__(self, db_path: str = DB_PATH):
        """Initialisiert die Datenbankverbindung"""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    async def execute(self, query: str, params: tuple = ()) -> Optional[aiosqlite.Cursor]:
        """Führt eine SQL-Abfrage asynchron aus und gibt den Cursor zurück"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                await db.commit()
                return cursor
        except aiosqlite.Error as e:
            print(f"Datenbankfehler: {e}")
            return None
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Führt eine SQL-Abfrage asynchron aus und gibt alle Ergebnisse zurück"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                return await cursor.fetchall()
        except aiosqlite.Error as e:
            print(f"Datenbankfehler: {e}")
            return []
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Tuple]:
        """Führt eine SQL-Abfrage asynchron aus und gibt ein Ergebnis zurück"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                return await cursor.fetchone()
        except aiosqlite.Error as e:
            print(f"Datenbankfehler: {e}")
            return None
    
    async def insert(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """Fügt Daten in eine Tabelle ein und gibt die ID zurück"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, tuple(data.values()))
                await db.commit()
                return cursor.lastrowid
        except aiosqlite.Error as e:
            print(f"Datenbankfehler beim Einfügen in {table}: {e}")
            return None
    
    async def update(self, table: str, data: Dict[str, Any], condition: str, params: tuple) -> bool:
        """Aktualisiert Daten in einer Tabelle und gibt True zurück, wenn erfolgreich"""
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        all_params = tuple(data.values()) + params
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, all_params)
                await db.commit()
                return cursor.rowcount > 0
        except aiosqlite.Error as e:
            print(f"Datenbankfehler beim Aktualisieren von {table}: {e}")
            return False
    
    async def delete(self, table: str, condition: str, params: tuple) -> bool:
        """Löscht Daten aus einer Tabelle und gibt True zurück, wenn erfolgreich"""
        query = f"DELETE FROM {table} WHERE {condition}"
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, params)
                await db.commit()
                return cursor.rowcount > 0
        except aiosqlite.Error as e:
            print(f"Datenbankfehler beim Löschen aus {table}: {e}")
            return False
            
    # Synchrone Methoden für einfache Operationen
    def execute_sync(self, query: str, params: tuple = ()) -> Optional[sqlite3.Cursor]:
        """Führt eine SQL-Abfrage synchron aus und gibt den Cursor zurück"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor
        except sqlite3.Error as e:
            print(f"Datenbankfehler: {e}")
            return None
    
    def fetch_all_sync(self, query: str, params: tuple = ()) -> List[Tuple]:
        """Führt eine SQL-Abfrage synchron aus und gibt alle Ergebnisse zurück"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Datenbankfehler: {e}")
            return []
    
    def fetch_one_sync(self, query: str, params: tuple = ()) -> Optional[Tuple]:
        """Führt eine SQL-Abfrage synchron aus und gibt ein Ergebnis zurück"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Datenbankfehler: {e}")
            return None
    
    def insert_sync(self, table: str, data: Dict[str, Any]) -> Optional[int]:
        """Fügt Daten synchron in eine Tabelle ein und gibt die ID zurück"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(data.values()))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Datenbankfehler beim Einfügen in {table}: {e}")
            return None 