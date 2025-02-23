import discord
from discord.ext import commands
from config import DISCORD_TOKEN

# Bot-Konfiguration mit allen notwendigen Intents
intents = discord.Intents.default()
intents.message_content = True  # Für Nachrichteninhalte
intents.members = True         # Für Mitglieder-bezogene Aktionen
intents.guilds = True         # Für Server-bezogene Aktionen
intents.bans = True           # Für Ban-bezogene Aktionen
intents.reactions = True      # Für Regelakzeptanz

bot = commands.Bot(command_prefix='!', intents=intents)

# Cogs laden
async def load_extensions():
    try:
        await bot.load_extension("cogs.moderation_commands")
        await bot.load_extension("cogs.weather_commands")
        await bot.load_extension("cogs.welcome_system")
        await bot.load_extension("cogs.rules")  # Stelle sicher, dass rules.py geladen wird
        print("✅ Alle Extensions wurden geladen!")
    except Exception as e:
        print(f"❌ Fehler beim Laden der Extensions: {e}")

    
@bot.event
async def on_ready():
    await load_extensions()
    print(f'Bot ist online als {bot.user.name} und Befehle sind geladen!')

bot.run(DISCORD_TOKEN)