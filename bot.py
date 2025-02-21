import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import aiosqlite
from utils.db import init_db, DB_PATH

# Lade Umgebungsvariablen
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot Konfiguration
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Startup Event
@bot.event
async def on_ready():
    print(f'{bot.user} ist online!')
    
    # Initialisiere Datenbank
    await init_db()
    
    # Lade alle Cogs
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                await bot.load_extension(f'cogs.{filename[:-3]}')
                print(f'Loaded {filename}')
            except Exception as e:
                print(f'Failed to load {filename}')
                print(f'Error: {str(e)}')

# Bot starten
bot.run(TOKEN)