import discord
from datetime import datetime
import aiosqlite
from utils.db import DB_PATH

class ModLogger:
    def __init__(self, bot):
        self.bot = bot
        self.mod_log_channels = {}  # Cache für Mod-Log Channel IDs

    async def load_mod_channels(self):
        """Lädt die Mod-Log Channel IDs aus der Datenbank"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('SELECT guild_id, mod_log_channel_id FROM channel_config') as cursor:
                async for guild_id, channel_id in cursor:
                    self.mod_log_channels[guild_id] = channel_id

    async def set_mod_channel(self, guild_id: int, channel_id: int):
        """Setzt den Mod-Log Channel für einen Server"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO channel_config (guild_id, mod_log_channel_id)
                VALUES (?, ?)
            ''', (guild_id, channel_id))
            await db.commit()
        self.mod_log_channels[guild_id] = channel_id

    async def log_mod_action(self, guild: discord.Guild, action_type: str, **kwargs):
        """Sendet eine Mod-Log Nachricht"""
        if guild.id not in self.mod_log_channels:
            return

        channel = self.bot.get_channel(self.mod_log_channels[guild.id])
        if not channel:
            return

        # Aktuelle Zeit in deutscher Zeitzone
        current_time = datetime.now().replace(microsecond=0)

        if action_type == "Info":
            # Vereinfachtes Embed für Info-Nachrichten
            embed = discord.Embed(
                title="ℹ️ Information",
                description=kwargs.get('content', 'Keine Information'),
                color=discord.Color.blue(),
                timestamp=current_time
            )
            if 'user' in kwargs:
                user = kwargs['user']
                embed.description = f"**Betroffener User:** {user.name} ({user.id})\n{embed.description}"
            
            await channel.send(embed=embed)
            return

        # Normales Mod-Log Embed
        embed = discord.Embed(
            title=f"{self.get_action_emoji(action_type)} {action_type}",
            timestamp=current_time,
            color=self.get_action_color(action_type)
        )

        # User Information
        if 'user' in kwargs:
            user = kwargs['user']
            embed.add_field(
                name="Betroffener User",
                value=f"**Name:** {user.name}\n"
                      f"**ID:** {user.id}\n"
                      f"**Mention:** {user.mention}",
                inline=False
            )

        # Moderator Information
        if 'moderator' in kwargs:
            moderator = kwargs['moderator']
            embed.add_field(
                name="Moderator",
                value=f"**Name:** {moderator.name}\n"
                      f"**ID:** {moderator.id}",
                inline=False
            )

        # Grund
        if 'reason' in kwargs:
            embed.add_field(
                name="Grund",
                value=kwargs['reason'] or "Kein Grund angegeben",
                inline=False
            )

        # Spezifische Informationen je nach Aktionstyp
        if action_type == "Timeout":
            if 'duration' in kwargs:
                embed.add_field(
                    name="Dauer",
                    value=kwargs['duration'],
                    inline=True
                )
            if 'expires_at' in kwargs:
                embed.add_field(
                    name="Läuft ab",
                    value=kwargs['expires_at'],
                    inline=True
                )
        elif action_type == "Ban":
            if 'permanent' in kwargs:
                embed.add_field(
                    name="Typ",
                    value="Permanent" if kwargs['permanent'] else "Temporär",
                    inline=True
                )

        await channel.send(embed=embed)

    def get_action_emoji(self, action_type: str) -> str:
        """Gibt das passende Emoji für die Aktion zurück"""
        emojis = {
            "Warnung": "⚠️",
            "Timeout": "🔇",
            "Kick": "👢",
            "Ban": "🔨",
            "Unban": "🔓",
            "Mute": "🎤",
            "Unmute": "🔊"
        }
        return emojis.get(action_type, "📝")

    def get_action_color(self, action_type: str) -> discord.Color:
        """Gibt die passende Farbe für die Aktion zurück"""
        colors = {
            "Warnung": discord.Color.yellow(),
            "Timeout": discord.Color.orange(),
            "Kick": discord.Color.red(),
            "Ban": discord.Color.dark_red(),
            "Unban": discord.Color.green(),
            "Mute": discord.Color.purple(),
            "Unmute": discord.Color.green()
        }
        return colors.get(action_type, discord.Color.blue()) 