import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_ID = os.getenv('CLIENT_ID')
GUILD_ID = os.getenv('GUILD_ID')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')