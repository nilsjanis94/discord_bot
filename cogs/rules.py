import discord
from discord.ext import commands
import aiosqlite
from utils.db import DB_PATH
import datetime

class Rules(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def rules(self, ctx):
        """Zeigt die Serverregeln an"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT rule_number, rule_title, rule_content 
                FROM server_rules 
                WHERE guild_id = ? 
                ORDER BY rule_number
            ''', (ctx.guild.id,)) as cursor:
                rules = await cursor.fetchall()

        if not rules:
            return await ctx.send("""
❌ **Keine Regeln gefunden!**

Nutze folgende Befehle:
`!rules add <nummer> <titel | inhalt>` - Neue Regel hinzufügen
`!rules edit <nummer> <titel | inhalt>` - Regel bearbeiten
`!rules remove <nummer>` - Regel entfernen
`!rules channel #kanal` - Regeln in Kanal senden

**Beispiel:**
`!rules add 1 Respekt | Behandle alle mit Respekt.`
""")

        embed = discord.Embed(
            title="📜 Serverregeln",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        for number, title, content in rules:
            embed.add_field(
                name=f"§{number} {title or ''}",
                value=content,
                inline=False
            )

        await ctx.send(embed=embed)

    @rules.command(name="add")
    @commands.has_permissions(administrator=True)
    async def add_rule(self, ctx, number: int, *, content: str):
        """Fügt eine neue Regel hinzu"""
        title = None
        if "|" in content:
            title, content = content.split("|", 1)
            title = title.strip()
            content = content.strip()

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO server_rules 
                (guild_id, rule_number, rule_title, rule_content, last_edited_by, last_edited_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (ctx.guild.id, number, title, content, ctx.author.id, datetime.datetime.now()))
            await db.commit()

        await ctx.send(f"✅ Regel {number} wurde hinzugefügt!")

    @rules.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def remove_rule(self, ctx, number: int):
        """Entfernt eine Regel"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                DELETE FROM server_rules 
                WHERE guild_id = ? AND rule_number = ?
            ''', (ctx.guild.id, number))
            await db.commit()

        await ctx.send(f"✅ Regel {number} wurde entfernt!")

    @rules.command(name="edit")
    @commands.has_permissions(administrator=True)
    async def edit_rule(self, ctx, number: int, *, content: str):
        """Bearbeitet eine bestehende Regel"""
        title = None
        if "|" in content:
            title, content = content.split("|", 1)
            title = title.strip()
            content = content.strip()

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                UPDATE server_rules 
                SET rule_title = ?, rule_content = ?, last_edited_by = ?, last_edited_at = ?
                WHERE guild_id = ? AND rule_number = ?
            ''', (title, content, ctx.author.id, datetime.datetime.now(), ctx.guild.id, number))
            await db.commit()

        await ctx.send(f"✅ Regel {number} wurde aktualisiert!")

    @rules.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def set_rules_channel(self, ctx, channel: discord.TextChannel = None):
        """Sendet die Regeln in einen bestimmten Kanal"""
        channel = channel or ctx.channel

        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT rule_number, rule_title, rule_content 
                FROM server_rules 
                WHERE guild_id = ? 
                ORDER BY rule_number
            ''', (ctx.guild.id,)) as cursor:
                rules = await cursor.fetchall()

        if not rules:
            return await ctx.send("❌ Es wurden noch keine Regeln festgelegt!")

        embed = discord.Embed(
            title="📜 Serverregeln",
            description="Bitte lies dir die folgenden Regeln sorgfältig durch.",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        for number, title, content in rules:
            embed.add_field(
                name=f"§{number} {title or ''}",
                value=content,
                inline=False
            )

        embed.set_footer(text=f"Zuletzt aktualisiert: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}")
        
        await channel.send(embed=embed)
        if channel != ctx.channel:
            await ctx.send(f"✅ Regeln wurden in {channel.mention} gesendet!")

    # Error Handler
    @rules.error
    async def rules_error(self, ctx, error):
        """Allgemeiner Error Handler für die rules Gruppe"""
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("""
❌ **Verfügbare Regelbefehle:**

`!rules` - Zeigt alle Regeln an
`!rules add <nummer> <titel | inhalt>` - Neue Regel hinzufügen
`!rules edit <nummer> <titel | inhalt>` - Regel bearbeiten
`!rules remove <nummer>` - Regel entfernen
`!rules channel #kanal` - Regeln in Kanal senden

**Beispiele:**
`!rules add 1 Respekt | Behandle alle mit Respekt.`
`!rules edit 1 Neuer Titel | Neuer Regelinhalt`
""")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Du hast keine Berechtigung, diesen Befehl zu nutzen!")

async def setup(bot):
    await bot.add_cog(Rules(bot)) 