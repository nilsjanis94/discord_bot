import discord
from discord.ext import commands

class ModerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, grund=None):
        await member.kick(reason=grund)
        await ctx.send(f'{member.name} wurde gekickt. Grund: {grund}')

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, grund=None):
        await member.ban(reason=grund)
        await ctx.send(f'{member.name} wurde gebannt. Grund: {grund}')

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, anzahl: int):
        await ctx.channel.purge(limit=anzahl + 1)
        await ctx.send(f'{anzahl} Nachrichten wurden gelöscht.')

async def setup(bot):
    await bot.add_cog(ModerationCommands(bot)) 