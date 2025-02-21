import discord
from discord.ext import commands
import aiohttp
import datetime

class WeatherCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    @commands.command()
    async def wetter(self, ctx, stadt: str):
        """Zeigt das aktuelle Wetter für eine Stadt an"""
        # Erst die Koordinaten der Stadt finden
        async with aiohttp.ClientSession() as session:
            geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={stadt}&count=1"
            async with session.get(geocoding_url) as resp:
                location_data = await resp.json()

                if not location_data.get("results"):
                    await ctx.send(f"Sorry, ich konnte {stadt} nicht finden!")
                    return

                location = location_data["results"][0]
                lat = location["latitude"]
                lon = location["longitude"]

                # Wetterdaten abrufen
                weather_url = f"{self.base_url}?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
                async with session.get(weather_url) as resp:
                    weather_data = await resp.json()
                    current = weather_data["current_weather"]

                    # Wettercode in Text umwandeln
                    wetter_codes = {
                        0: "Klar ☀️",
                        1: "Überwiegend klar 🌤️",
                        2: "Teilweise bewölkt ⛅",
                        3: "Bewölkt ☁️",
                        45: "Neblig 🌫️",
                        48: "Neblig mit Reif 🌫️",
                        51: "Leichter Nieselregen 🌧️",
                        53: "Nieselregen 🌧️",
                        55: "Starker Nieselregen 🌧️",
                        61: "Leichter Regen 🌦️",
                        63: "Regen 🌧️",
                        65: "Starker Regen 🌧️",
                        71: "Leichter Schneefall 🌨️",
                        73: "Schneefall 🌨️",
                        75: "Starker Schneefall 🌨️",
                        95: "Gewitter ⛈️"
                    }

                    wetter_text = wetter_codes.get(current["weathercode"], "Unbekannt")

                    embed = discord.Embed(
                        title=f"Wetter in {location['name']}, {location.get('country', '')}",
                        color=discord.Color.blue(),
                        timestamp=datetime.datetime.now()
                    )
                    
                    embed.add_field(
                        name="Temperatur", 
                        value=f"{current['temperature']}°C", 
                        inline=True
                    )
                    embed.add_field(
                        name="Wetterzustand", 
                        value=wetter_text, 
                        inline=True
                    )
                    embed.add_field(
                        name="Windgeschwindigkeit", 
                        value=f"{current['windspeed']} km/h", 
                        inline=True
                    )

                    await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(WeatherCommands(bot)) 