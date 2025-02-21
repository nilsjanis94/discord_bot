import discord
from discord.ext import commands

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hallo(self, ctx):
        await ctx.send(f'Hallo {ctx.author.name}, ich bin der Bot vom Server X und deren persönlicher Assistent!')

    @commands.command()
    async def server(self, ctx):
        server = ctx.guild
        await ctx.send(f'Server Name: {server.name}\n'
                      f'Mitglieder: {server.member_count}')

    # Event-Beispiel
    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = member.guild.system_channel
        if channel:
            await channel.send(f'Willkommen {member.mention}!')

    @commands.command()
    async def ping(self, ctx):
        await ctx.send('Pong!')

    @commands.command()
    async def info(self, ctx):
        embed = discord.Embed(
            title="Bot Info",
            description="Ein einfacher Discord Bot",
            color=discord.Color.blue()
        )
        embed.add_field(name="Server", value=len(self.bot.guilds))
        embed.add_field(name="Erstellt von", value="Ihr Name")
        await ctx.send(embed=embed)

    @commands.command()
    async def f(self, ctx):
        await ctx.send('F')
    

async def setup(bot):
    await bot.add_cog(BasicCommands(bot))