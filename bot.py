import discord
from discord.ext import commands
from config import DISCORD_TOKEN

# Bot-Konfiguration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Cogs laden
async def load_extensions():

    await bot.load_extension("cogs.moderation_commands")
    await bot.load_extension("cogs.weather_commands")

@bot.event
async def on_ready():
    await load_extensions()
    print(f'Bot ist online als {bot.user.name} und Befehle sind geladen!')

bot.run(DISCORD_TOKEN)