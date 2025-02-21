import discord
from discord.ext import commands
import datetime
import json
import asyncio

class ModerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warns = {}  # In der Praxis sollten Sie eine Datenbank verwenden
        
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason=None):
        """Verwarnt ein Mitglied"""
        if member.id not in self.warns:
            self.warns[member.id] = []
        
        self.warns[member.id].append({
            'reason': reason,
            'timestamp': datetime.datetime.now().isoformat(),
            'moderator': ctx.author.id
        })
        
        embed = discord.Embed(
            title="⚠️ Verwarnung",
            description=f"{member.mention} wurde verwarnt.",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Grund", value=reason or "Kein Grund angegeben")
        embed.add_field(name="Verwarnungen", value=str(len(self.warns[member.id])))
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def timeout(self, ctx, member: discord.Member, duration: int, *, reason=None):
        """Timeout für ein Mitglied (Dauer in Minuten)"""
        duration = datetime.timedelta(minutes=duration)
        await member.timeout(duration, reason=reason)
        
        embed = discord.Embed(
            title="🔇 Timeout",
            description=f"{member.mention} wurde für {duration} stumm geschaltet.",
            color=discord.Color.orange()
        )
        embed.add_field(name="Grund", value=reason or "Kein Grund angegeben")
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):
        """Löscht eine bestimmte Anzahl von Nachrichten"""
        if amount < 1 or amount > 100:
            await ctx.send("Bitte geben Sie eine Zahl zwischen 1 und 100 an.")
            return
            
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 für den Befehl selbst
        msg = await ctx.send(f"🗑️ {len(deleted)-1} Nachrichten gelöscht.")
        await asyncio.sleep(3)
        await msg.delete()

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        """Bannt ein Mitglied"""
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🔨 Ban",
            description=f"{member.mention} wurde gebannt.",
            color=discord.Color.red()
        )
        embed.add_field(name="Grund", value=reason or "Kein Grund angegeben")
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Auto-Moderation für Nachrichten"""
        if message.author.bot:
            return

        # Beispiel für Spam-Schutz (sehr einfach)
        content = message.content.lower()
        if content.count('@everyone') > 0 and not message.author.guild_permissions.mention_everyone:
            await message.delete()
            await message.channel.send(f"{message.author.mention} Bitte keine @everyone Erwähnungen!")

async def setup(bot):
    await bot.add_cog(ModerationCommands(bot)) 