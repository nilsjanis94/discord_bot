import discord
from datetime import datetime
import os
from config import GUILD_ID

class ModLogger:
    def __init__(self, bot):
        self.bot = bot
        self.log_channels = {}  # {guild_id: channel_id}
        self.load_log_channels()

    def load_log_channels(self):
        """Lädt die Log-Channel-Konfiguration"""
        config_path = "data/log_channels.txt"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                for line in f:
                    guild_id, channel_id = map(int, line.strip().split(':'))
                    self.log_channels[guild_id] = channel_id

    def save_log_channels(self):
        """Speichert die Log-Channel-Konfiguration"""
        os.makedirs("data", exist_ok=True)
        with open("data/log_channels.txt", 'w') as f:
            for guild_id, channel_id in self.log_channels.items():
                f.write(f"{guild_id}:{channel_id}\n")

    async def log_mod_action(self, guild, action_type, **kwargs):
        """Loggt eine Moderationsaktion"""
        if guild.id not in self.log_channels:
            return

        channel = self.bot.get_channel(self.log_channels[guild.id])
        if not channel:
            return

        embed = discord.Embed(
            title=f"📝 {action_type}",
            timestamp=datetime.now(),
            color=self.get_action_color(action_type)
        )

        # Füge dynamische Felder basierend auf kwargs hinzu
        for key, value in kwargs.items():
            if value is not None:
                embed.add_field(name=key.replace('_', ' ').title(), value=str(value))

        await channel.send(embed=embed)

    def get_action_color(self, action_type):
        """Bestimmt die Farbe basierend auf der Aktion"""
        colors = {
            'Warnung': discord.Color.yellow(),
            'Timeout': discord.Color.orange(),
            'Ban': discord.Color.red(),
            'Kick': discord.Color.dark_red(),
            'Nachricht gelöscht': discord.Color.blue(),
            'AutoMod': discord.Color.purple(),
            'Verwarnungen gelöscht': discord.Color.green()
        }
        return colors.get(action_type, discord.Color.default()) 