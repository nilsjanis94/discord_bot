import discord
import re
import json
import os
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple, Optional
from utils.db import DB_PATH, Database

class AutoMod:
    def __init__(self, bot=None):
        self.bot = bot
        self.db = Database()
        
        # Cache für Einstellungen
        self.enabled_guilds = set()
        self.log_channels = {}
        self.whitelisted_roles = defaultdict(set)
        self.whitelisted_channels = defaultdict(set)
        self.banned_words = defaultdict(set)
        self.banned_links = defaultdict(set)
        
        # Spam-Erkennung
        self.message_history = defaultdict(list)  # {user_id: [message_timestamps]}
        self.repeat_messages = defaultdict(Counter)  # {user_id: Counter(message_content)}
        self.caps_thresholds = defaultdict(lambda: 0.7)  # Standard: 70% Großbuchstaben
        self.emoji_thresholds = defaultdict(lambda: 0.3)  # Standard: 30% Emojis
        self.spam_thresholds = defaultdict(lambda: (5, 3))  # Standard: 5 Nachrichten in 3 Sekunden
        self.flood_settings = defaultdict(lambda: (5, 5))  # Standard: 5 Nachrichten in 5 Sekunden
        
        # Cooldowns für Warnungen
        self.warning_cooldowns = {}
        
        # Laden der Einstellungen
        self.load_settings_task = None
        
    async def setup(self, bot):
        """Initialisiert den AutoMod mit dem Bot-Objekt"""
        self.bot = bot
        await self.load_settings()
        print("✅ AutoMod-Einstellungen wurden geladen")
        
    async def load_settings(self):
        """Lädt alle AutoMod-Einstellungen aus der Datenbank"""
        try:
            # Aktivierte Server laden
            enabled_guilds = await self.db.fetch_all(
                "SELECT guild_id FROM automod_config WHERE enabled = 1"
            )
            self.enabled_guilds = {int(row[0]) for row in enabled_guilds}
            
            # Log-Kanäle laden
            log_channels = await self.db.fetch_all(
                "SELECT guild_id, log_channel_id FROM automod_config WHERE log_channel_id IS NOT NULL"
            )
            self.log_channels = {int(row[0]): int(row[1]) for row in log_channels}
            
            # Whitelist-Rollen laden
            whitelist_roles = await self.db.fetch_all(
                "SELECT guild_id, role_id FROM automod_whitelist WHERE type = 'role'"
            )
            for guild_id, role_id in whitelist_roles:
                self.whitelisted_roles[int(guild_id)].add(int(role_id))
            
            # Whitelist-Kanäle laden
            whitelist_channels = await self.db.fetch_all(
                "SELECT guild_id, channel_id FROM automod_whitelist WHERE type = 'channel'"
            )
            for guild_id, channel_id in whitelist_channels:
                self.whitelisted_channels[int(guild_id)].add(int(channel_id))
            
            # Gebannte Wörter laden
            banned_words = await self.db.fetch_all(
                "SELECT guild_id, word FROM automod_filter WHERE type = 'word'"
            )
            for guild_id, word in banned_words:
                self.banned_words[int(guild_id)].add(word.lower())
            
            # Gebannte Links laden
            banned_links = await self.db.fetch_all(
                "SELECT guild_id, word FROM automod_filter WHERE type = 'link'"
            )
            for guild_id, link in banned_links:
                self.banned_links[int(guild_id)].add(link.lower())
            
            # Schwellenwerte laden
            thresholds = await self.db.fetch_all(
                "SELECT guild_id, setting_type, value FROM automod_settings"
            )
            for guild_id, setting_type, value in thresholds:
                guild_id = int(guild_id)
                if setting_type == 'caps_threshold':
                    self.caps_thresholds[guild_id] = float(value)
                elif setting_type == 'emoji_threshold':
                    self.emoji_thresholds[guild_id] = float(value)
                elif setting_type == 'spam_messages':
                    messages, interval = self.spam_thresholds[guild_id]
                    self.spam_thresholds[guild_id] = (int(value), interval)
                elif setting_type == 'spam_interval':
                    messages, _ = self.spam_thresholds[guild_id]
                    self.spam_thresholds[guild_id] = (messages, int(value))
                elif setting_type == 'flood_messages':
                    messages, interval = self.flood_settings[guild_id]
                    self.flood_settings[guild_id] = (int(value), interval)
                elif setting_type == 'flood_interval':
                    messages, _ = self.flood_settings[guild_id]
                    self.flood_settings[guild_id] = (messages, int(value))
            
            print("✅ AutoMod-Einstellungen geladen")
            print(f"Aktivierte Server: {self.enabled_guilds}")
            print(f"Spam-Einstellungen: {dict(self.spam_thresholds)}")
            print(f"Flood-Einstellungen: {dict(self.flood_settings)}")
        except Exception as e:
            print(f"❌ Fehler beim Laden der AutoMod-Einstellungen: {e}")
    
    async def is_enabled(self, guild_id: int) -> bool:
        """Prüft, ob AutoMod für diesen Server aktiviert ist"""
        return guild_id in self.enabled_guilds
    
    async def is_exempt(self, message: discord.Message) -> bool:
        """Prüft, ob der Autor der Nachricht von AutoMod ausgenommen ist"""
        if message.author.bot:
            return True
            
        guild_id = message.guild.id
        
        # Prüfe Rollen-Whitelist
        if any(role.id in self.whitelisted_roles[guild_id] for role in message.author.roles):
            print(f"🛡️ User {message.author.name} ist durch Rolle von AutoMod ausgenommen")
            return True
            
        # Prüfe Kanal-Whitelist
        if message.channel.id in self.whitelisted_channels[guild_id]:
            print(f"🛡️ Kanal {message.channel.name} ist von AutoMod ausgenommen")
            return True
            
        # Prüfe Berechtigungen
        if message.author.guild_permissions.administrator:
            print(f"🛡️ Admin {message.author.name} ist von AutoMod ausgenommen")
            return True
            
        return False
    
    async def process_message(self, message: discord.Message) -> Optional[str]:
        """Verarbeitet eine Nachricht und gibt den Verstoßtyp zurück, wenn einer erkannt wird"""
        if not message.guild:
            return None  # Ignoriere DMs
            
        guild_id = message.guild.id
        
        # Prüfe, ob AutoMod aktiviert ist
        if not await self.is_enabled(guild_id):
            return None
            
        # Prüfe, ob der User ausgenommen ist
        if await self.is_exempt(message):
            return None
            
        # Prüfe auf verbotene Wörter
        if await self.check_banned_words(message):
            return "banned_word"
            
        # Prüfe auf verbotene Links
        if await self.check_banned_links(message):
            return "banned_link"
            
        # Prüfe auf zu viele Großbuchstaben
        if await self.check_excessive_caps(message):
            return "excessive_caps"
            
        # Prüfe auf zu viele Emojis
        if await self.check_excessive_emojis(message):
            return "excessive_emojis"
            
        # Prüfe auf Spam
        if await self.check_spam(message):
            return "spam"
            
        # Prüfe auf Flood
        if await self.check_flood(message):
            return "flood"
            
        return None
    
    async def check_banned_words(self, message: discord.Message) -> bool:
        """Prüft, ob die Nachricht verbotene Wörter enthält"""
        content = message.content.lower()
        guild_id = message.guild.id
        
        # Prüfe jedes verbotene Wort
        for word in self.banned_words[guild_id]:
            # Prüfe auf exakte Übereinstimmung mit Wortgrenzen
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, content):
                print(f"🔍 Verbotenes Wort gefunden: '{word}' in Nachricht von {message.author.name}")
                return True
                
        return False
    
    async def check_banned_links(self, message: discord.Message) -> bool:
        """Prüft, ob die Nachricht verbotene Links enthält"""
        content = message.content.lower()
        guild_id = message.guild.id
        
        # Extrahiere alle URLs aus der Nachricht
        urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', content)
        
        # Prüfe auch auf Links ohne http/https
        domain_pattern = r'(?:www\.)?([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}'
        domains = re.findall(domain_pattern, content)
        
        # Kombiniere URLs und Domains
        all_links = urls + [''.join(domain) for domain in domains]
        
        # Prüfe jeden Link
        for url in all_links:
            for banned_link in self.banned_links[guild_id]:
                if banned_link in url:
                    print(f"🔍 Verbotener Link gefunden: '{url}' enthält '{banned_link}' in Nachricht von {message.author.name}")
                    return True
                    
        return False
    
    async def check_excessive_caps(self, message: discord.Message) -> bool:
        """Prüft, ob die Nachricht zu viele Großbuchstaben enthält"""
        content = message.content
        guild_id = message.guild.id
        
        # Ignoriere kurze Nachrichten
        if len(content) < 8:
            return False
            
        # Zähle Großbuchstaben
        uppercase_count = sum(1 for c in content if c.isupper())
        letter_count = sum(1 for c in content if c.isalpha())
        
        # Verhindere Division durch Null
        if letter_count == 0:
            return False
            
        # Berechne Prozentsatz
        caps_percentage = uppercase_count / letter_count
        
        # Prüfe gegen Schwellenwert
        threshold = self.caps_thresholds[guild_id]
        is_excessive = caps_percentage > threshold
        
        if is_excessive:
            print(f"🔍 Zu viele Großbuchstaben: {caps_percentage:.1%} > {threshold:.1%} in Nachricht von {message.author.name}")
            
        return is_excessive
    
    async def check_excessive_emojis(self, message: discord.Message) -> bool:
        """Prüft, ob die Nachricht zu viele Emojis enthält"""
        content = message.content
        guild_id = message.guild.id
        
        # Ignoriere kurze Nachrichten
        if len(content) < 8:
            return False
            
        # Zähle Emojis (Unicode und Discord-Emojis)
        emoji_pattern = re.compile(r'<a?:[a-zA-Z0-9_]+:\d+>|[\U00010000-\U0010ffff]')
        emojis = emoji_pattern.findall(content)
        
        # Berechne Prozentsatz
        emoji_percentage = len(emojis) / len(content)
        
        # Prüfe gegen Schwellenwert
        threshold = self.emoji_thresholds[guild_id]
        is_excessive = emoji_percentage > threshold
        
        if is_excessive:
            print(f"🔍 Zu viele Emojis: {emoji_percentage:.1%} > {threshold:.1%} in Nachricht von {message.author.name}")
            
        return is_excessive
    
    async def check_spam(self, message: discord.Message) -> bool:
        """Prüft, ob der User spammt (zu viele Nachrichten in kurzer Zeit)"""
        user_id = message.author.id
        guild_id = message.guild.id
        current_time = datetime.now()
        
        # Füge aktuelle Nachricht zur Historie hinzu
        self.message_history[user_id].append(current_time)
        
        # Entferne alte Nachrichten aus der Historie
        messages, interval = self.spam_thresholds[guild_id]
        threshold_time = current_time - timedelta(seconds=interval)
        self.message_history[user_id] = [t for t in self.message_history[user_id] if t > threshold_time]
        
        # Debug-Ausgabe
        message_count = len(self.message_history[user_id])
        print(f"🔍 Spam-Check: User {message.author.name}, Nachrichten: {message_count}/{messages} in {interval}s")
        
        # Prüfe Anzahl der Nachrichten im Zeitraum (>= statt >)
        return message_count >= messages
    
    async def check_flood(self, message: discord.Message) -> bool:
        """Prüft, ob der User den Chat flutet (wiederholte Nachrichten)"""
        user_id = message.author.id
        guild_id = message.guild.id
        content = message.content
        
        # Aktualisiere Zähler für wiederholte Nachrichten
        self.repeat_messages[user_id][content] += 1
        
        # Prüfe, ob der Schwellenwert überschritten wurde
        flood_count, flood_interval = self.flood_settings[guild_id]
        current_count = self.repeat_messages[user_id][content]
        
        # Debug-Ausgabe
        print(f"🔍 Flood-Check: User {message.author.name}, Wiederholungen: {current_count}/{flood_count} (Nachricht: '{content[:20]}...')")
        
        # Setze einen Timer, um den Zähler zurückzusetzen
        if current_count == 1:
            asyncio.create_task(self._reset_flood_counter(user_id, content, flood_interval))
            
        return current_count >= flood_count
    
    async def _reset_flood_counter(self, user_id: int, content: str, interval: int):
        """Setzt den Flood-Zähler nach dem Intervall zurück"""
        await asyncio.sleep(interval)
        if user_id in self.repeat_messages and content in self.repeat_messages[user_id]:
            del self.repeat_messages[user_id][content]
    
    async def take_action(self, message: discord.Message, violation_type: str) -> None:
        """Führt eine Aktion basierend auf dem Verstoßtyp aus"""
        try:
            # Lösche die Nachricht
            await message.delete()
            print(f"🗑️ Nachricht von {message.author.name} wurde gelöscht (Grund: {violation_type})")
            
            # Prüfe Cooldown für Warnungen
            user_id = message.author.id
            guild_id = message.guild.id
            cooldown_key = f"{guild_id}:{user_id}:{violation_type}"
            
            current_time = datetime.now()
            if cooldown_key in self.warning_cooldowns:
                if (current_time - self.warning_cooldowns[cooldown_key]).total_seconds() < 60:
                    # Noch im Cooldown, keine Warnung senden
                    return
                    
            # Setze Cooldown
            self.warning_cooldowns[cooldown_key] = current_time
            
            # Sende Warnung an den User
            warning_embed = discord.Embed(
                title="⚠️ AutoMod-Warnung",
                description=f"Deine Nachricht wurde entfernt, weil sie gegen unsere Regeln verstößt.",
                color=discord.Color.orange()
            )
            
            violation_descriptions = {
                "banned_word": "Verbotenes Wort oder Ausdruck",
                "banned_link": "Nicht erlaubter Link",
                "excessive_caps": "Zu viele Großbuchstaben",
                "excessive_emojis": "Zu viele Emojis",
                "spam": "Zu viele Nachrichten in kurzer Zeit",
                "flood": "Wiederholte Nachrichten (Flooding)"
            }
            
            warning_embed.add_field(
                name="Grund",
                value=violation_descriptions.get(violation_type, "Regelverstoß"),
                inline=False
            )
            
            try:
                await message.author.send(embed=warning_embed)
                print(f"📨 Warnung an {message.author.name} gesendet")
            except discord.Forbidden:
                # User hat DMs deaktiviert
                print(f"❌ Konnte keine DM an {message.author.name} senden (DMs deaktiviert)")
                pass
            
            # Logge den Verstoß
            await self.log_violation(message, violation_type)
            
        except discord.NotFound:
            # Nachricht wurde bereits gelöscht
            print(f"⚠️ Nachricht von {message.author.name} wurde bereits gelöscht")
            pass
        except Exception as e:
            print(f"❌ Fehler bei AutoMod-Aktion: {e}")
    
    async def log_violation(self, message: discord.Message, violation_type: str) -> None:
        """Loggt einen AutoMod-Verstoß im Log-Kanal"""
        guild_id = message.guild.id
        
        # Prüfe, ob ein Log-Kanal konfiguriert ist
        if guild_id not in self.log_channels:
            print(f"⚠️ Kein Log-Kanal für Server {guild_id} konfiguriert")
            return
            
        log_channel_id = self.log_channels[guild_id]
        log_channel = self.bot.get_channel(log_channel_id)
        
        if not log_channel:
            print(f"⚠️ Log-Kanal {log_channel_id} nicht gefunden")
            return
            
        # Erstelle Embed für Log
        log_embed = discord.Embed(
            title="🤖 AutoMod: Nachricht entfernt",
            description=f"Eine Nachricht von {message.author.mention} wurde automatisch entfernt.",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        
        # Füge Informationen hinzu
        log_embed.add_field(
            name="User",
            value=f"{message.author} (ID: {message.author.id})",
            inline=True
        )
        
        log_embed.add_field(
            name="Kanal",
            value=message.channel.mention,
            inline=True
        )
        
        violation_descriptions = {
            "banned_word": "Verbotenes Wort oder Ausdruck",
            "banned_link": "Nicht erlaubter Link",
            "excessive_caps": "Zu viele Großbuchstaben",
            "excessive_emojis": "Zu viele Emojis",
            "spam": "Zu viele Nachrichten in kurzer Zeit",
            "flood": "Wiederholte Nachrichten (Flooding)"
        }
        
        log_embed.add_field(
            name="Grund",
            value=violation_descriptions.get(violation_type, "Regelverstoß"),
            inline=False
        )
        
        # Füge Nachrichteninhalt hinzu (gekürzt, falls zu lang)
        content = message.content
        if len(content) > 1024:
            content = content[:1021] + "..."
            
        log_embed.add_field(
            name="Nachrichteninhalt",
            value=f"```{content}```",
            inline=False
        )
        
        # Sende Log
        try:
            await log_channel.send(embed=log_embed)
            print(f"📝 Verstoß in Log-Kanal protokolliert")
        except Exception as e:
            print(f"❌ Fehler beim Senden des Logs: {e}")
    
    # Konfigurationsmethoden
    async def enable(self, guild_id: int) -> None:
        """Aktiviert AutoMod für einen Server"""
        await self.db.execute(
            "INSERT OR REPLACE INTO automod_config (guild_id, enabled) VALUES (?, 1)",
            (guild_id,)
        )
        self.enabled_guilds.add(guild_id)
    
    async def disable(self, guild_id: int) -> None:
        """Deaktiviert AutoMod für einen Server"""
        await self.db.execute(
            "UPDATE automod_config SET enabled = 0 WHERE guild_id = ?",
            (guild_id,)
        )
        if guild_id in self.enabled_guilds:
            self.enabled_guilds.remove(guild_id)
    
    async def set_log_channel(self, guild_id: int, channel_id: int) -> None:
        """Setzt den Log-Kanal für einen Server"""
        await self.db.execute(
            "INSERT OR REPLACE INTO automod_config (guild_id, log_channel_id) VALUES (?, ?)",
            (guild_id, channel_id)
        )
        self.log_channels[guild_id] = channel_id
    
    async def add_whitelist_role(self, guild_id: int, role_id: int) -> None:
        """Fügt eine Rolle zur Whitelist hinzu"""
        await self.db.execute(
            "INSERT OR IGNORE INTO automod_whitelist (guild_id, role_id, type) VALUES (?, ?, 'role')",
            (guild_id, role_id)
        )
        self.whitelisted_roles[guild_id].add(role_id)
    
    async def remove_whitelist_role(self, guild_id: int, role_id: int) -> None:
        """Entfernt eine Rolle von der Whitelist"""
        await self.db.execute(
            "DELETE FROM automod_whitelist WHERE guild_id = ? AND role_id = ? AND type = 'role'",
            (guild_id, role_id)
        )
        if role_id in self.whitelisted_roles[guild_id]:
            self.whitelisted_roles[guild_id].remove(role_id)
    
    async def add_whitelist_channel(self, guild_id: int, channel_id: int) -> None:
        """Fügt einen Kanal zur Whitelist hinzu"""
        await self.db.execute(
            "INSERT OR IGNORE INTO automod_whitelist (guild_id, channel_id, type) VALUES (?, ?, 'channel')",
            (guild_id, channel_id)
        )
        self.whitelisted_channels[guild_id].add(channel_id)
    
    async def remove_whitelist_channel(self, guild_id: int, channel_id: int) -> None:
        """Entfernt einen Kanal von der Whitelist"""
        await self.db.execute(
            "DELETE FROM automod_whitelist WHERE guild_id = ? AND channel_id = ? AND type = 'channel'",
            (guild_id, channel_id)
        )
        if channel_id in self.whitelisted_channels[guild_id]:
            self.whitelisted_channels[guild_id].remove(channel_id)
    
    async def add_banned_word(self, guild_id: int, word: str) -> None:
        """Fügt ein verbotenes Wort hinzu"""
        word = word.lower()
        await self.db.execute(
            "INSERT OR IGNORE INTO automod_filter (guild_id, word, type) VALUES (?, ?, 'word')",
            (guild_id, word)
        )
        self.banned_words[guild_id].add(word)
    
    async def remove_banned_word(self, guild_id: int, word: str) -> None:
        """Entfernt ein verbotenes Wort"""
        word = word.lower()
        await self.db.execute(
            "DELETE FROM automod_filter WHERE guild_id = ? AND word = ? AND type = 'word'",
            (guild_id, word)
        )
        if word in self.banned_words[guild_id]:
            self.banned_words[guild_id].remove(word)
    
    async def add_banned_link(self, guild_id: int, link: str) -> None:
        """Fügt einen verbotenen Link hinzu"""
        link = link.lower()
        await self.db.execute(
            "INSERT OR IGNORE INTO automod_filter (guild_id, word, type) VALUES (?, ?, 'link')",
            (guild_id, link)
        )
        self.banned_links[guild_id].add(link)
    
    async def remove_banned_link(self, guild_id: int, link: str) -> None:
        """Entfernt einen verbotenen Link"""
        link = link.lower()
        await self.db.execute(
            "DELETE FROM automod_filter WHERE guild_id = ? AND word = ? AND type = 'link'",
            (guild_id, link)
        )
        if link in self.banned_links[guild_id]:
            self.banned_links[guild_id].remove(link)
    
    async def set_caps_threshold(self, guild_id: int, threshold: float) -> None:
        """Setzt den Schwellenwert für Großbuchstaben"""
        await self.db.execute(
            "INSERT OR REPLACE INTO automod_settings (guild_id, setting_type, value) VALUES (?, 'caps_threshold', ?)",
            (guild_id, str(threshold))
        )
        self.caps_thresholds[guild_id] = threshold
    
    async def set_emoji_threshold(self, guild_id: int, threshold: float) -> None:
        """Setzt den Schwellenwert für Emojis"""
        await self.db.execute(
            "INSERT OR REPLACE INTO automod_settings (guild_id, setting_type, value) VALUES (?, 'emoji_threshold', ?)",
            (guild_id, str(threshold))
        )
        self.emoji_thresholds[guild_id] = threshold
    
    async def set_spam_settings(self, guild_id: int, messages: int, interval: int) -> None:
        """Setzt die Einstellungen für Spam-Erkennung"""
        await self.db.execute(
            "INSERT OR REPLACE INTO automod_settings (guild_id, setting_type, value) VALUES (?, 'spam_messages', ?)",
            (guild_id, str(messages))
        )
        await self.db.execute(
            "INSERT OR REPLACE INTO automod_settings (guild_id, setting_type, value) VALUES (?, 'spam_interval', ?)",
            (guild_id, str(interval))
        )
        self.spam_thresholds[guild_id] = (messages, interval)
    
    async def set_flood_settings(self, guild_id: int, messages: int, interval: int) -> None:
        """Setzt die Einstellungen für Flood-Erkennung"""
        await self.db.execute(
            "INSERT OR REPLACE INTO automod_settings (guild_id, setting_type, value) VALUES (?, 'flood_messages', ?)",
            (guild_id, str(messages))
        )
        await self.db.execute(
            "INSERT OR REPLACE INTO automod_settings (guild_id, setting_type, value) VALUES (?, 'flood_interval', ?)",
            (guild_id, str(interval))
        )
        self.flood_settings[guild_id] = (messages, interval)
    
    async def get_status(self, guild_id: int) -> dict:
        """Gibt den Status der AutoMod-Einstellungen für einen Server zurück"""
        return {
            "enabled": guild_id in self.enabled_guilds,
            "log_channel": self.log_channels.get(guild_id),
            "whitelisted_roles": list(self.whitelisted_roles[guild_id]),
            "whitelisted_channels": list(self.whitelisted_channels[guild_id]),
            "banned_words_count": len(self.banned_words[guild_id]),
            "banned_links_count": len(self.banned_links[guild_id]),
            "caps_threshold": self.caps_thresholds[guild_id],
            "emoji_threshold": self.emoji_thresholds[guild_id],
            "spam_settings": self.spam_thresholds[guild_id],
            "flood_settings": self.flood_settings[guild_id]
        } 