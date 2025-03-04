import discord
from discord.ext import commands
from config import DISCORD_TOKEN
from utils.db import init_db

# Bot-Konfiguration mit allen notwendigen Intents
intents = discord.Intents.default()
intents.message_content = True  # Für Nachrichteninhalte
intents.members = True         # Für Mitglieder-bezogene Aktionen
intents.guilds = True         # Für Server-bezogene Aktionen
intents.bans = True           # Für Ban-bezogene Aktionen
intents.reactions = True      # Für Regelakzeptanz
intents.guild_scheduled_events = True  # Korrekter Name für den Intent

bot = commands.Bot(command_prefix='!', intents=intents)

# Cogs laden
async def load_extensions():
    try:
        await bot.load_extension("cogs.moderation_commands")
        await bot.load_extension("cogs.weather_commands")
        await bot.load_extension("cogs.welcome_system")
        await bot.load_extension("cogs.rules")  
        await bot.load_extension("cogs.reaction_roles")  
        await bot.load_extension("cogs.automod_commands")
        await bot.load_extension("cogs.temp_channels")
        await bot.load_extension("cogs.event_planner")
        await bot.load_extension("cogs.ticket_system")
        await bot.load_extension("cogs.twitch_integration")
        print("✅ Alle Extensions wurden geladen!")
    except Exception as e:
        print(f"❌ Fehler beim Laden der Extensions: {e}")

# Globaler Error Handler für fehlende Berechtigungen
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        # Dieser Fehler wird bereits in der is_admin Funktion behandelt
        pass
    elif isinstance(error, commands.CommandNotFound):
        # Ignoriere nicht existierende Befehle
        pass
    else:
        # Andere Fehler normal ausgeben
        print(f"Fehler bei Ausführung eines Befehls: {error}")
    
@bot.event
async def on_ready():
    # Datenbank initialisieren
    await init_db()
    # Extensions laden
    await load_extensions()
    print(f'Bot ist online als {bot.user.name} und Befehle sind geladen!')

bot.run(DISCORD_TOKEN)