import discord
from discord.ext import commands

class UtilityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def userinfo(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        embed = discord.Embed(title=f"Info über {member.name}", color=member.color)
        embed.add_field(name="Beigetreten am", value=member.joined_at.strftime("%d.%m.%Y"))
        embed.add_field(name="Account erstellt am", value=member.created_at.strftime("%d.%m.%Y"))
        embed.set_thumbnail(url=member.avatar.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        await ctx.send(member.avatar.url)

    @commands.command()
    async def servericon(self, ctx):
        await ctx.send(ctx.guild.icon.url)

# Diese Zeile ist wichtig für das Laden der Cog
async def setup(bot):
    await bot.add_cog(UtilityCommands(bot)) 