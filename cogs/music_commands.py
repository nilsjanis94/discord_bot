import discord
from discord.ext import commands

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
            await ctx.send(f'Bin dem Kanal {channel.name} beigetreten!')
        else:
            await ctx.send('Du musst in einem Voice-Kanal sein!')

    @commands.command()
    async def leave(self, ctx):
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send('Tschüss!') 

async def setup(bot):
    await bot.add_cog(MusicCommands(bot)) 