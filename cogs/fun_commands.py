import random
import discord
from discord.ext import commands

class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def würfel(self, ctx, seiten: int = 6):
        ergebnis = random.randint(1, seiten)
        await ctx.send(f'🎲 Du hast eine {ergebnis} gewürfelt!')

    @commands.command()
    async def münze(self, ctx):
        ergebnis = random.choice(['Kopf', 'Zahl'])
        await ctx.send(f'Die Münze zeigt: {ergebnis}')

    @commands.command()
    async def zitat(self, ctx):
        zitate = [
            "Der frühe Vogel fängt den Wurm!",
            "Übung macht den Meister!",
            "Wer nicht wagt, der nicht gewinnt!"
        ]
        await ctx.send(random.choice(zitate)) 

async def setup(bot):
    await bot.add_cog(FunCommands(bot))