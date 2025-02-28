import discord
from discord.ext import commands
import os
from typing import Dict
import sys
import os

# Füge das Hauptverzeichnis zum Pfad hinzu, damit wir utils importieren können
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db import Database
from utils.permissions import is_admin  # Importiere die neue Berechtigungsprüfung

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()

    def get_reaction_roles(self, message_id: str) -> Dict[str, str]:
        """Lädt die Reaction Roles für eine bestimmte Nachricht"""
        results = self.db.fetch_all_sync(
            'SELECT emoji, role_id FROM reaction_roles WHERE message_id = ?', 
            (message_id,)
        )
        return {row[0]: row[1] for row in results}

    @commands.group(name="reactionrole", aliases=["rr"])
    @is_admin()  # Ersetze @commands.has_permissions(administrator=True)
    async def reaction_role(self, ctx):
        """Hauptbefehl für Reaction Roles"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Bitte gib einen Unterbefehl an. Nutze `!help reactionrole` für mehr Informationen.")

    @reaction_role.command(name="create")
    async def create_reaction_role(self, ctx, emoji: str, role: discord.Role, *, beschreibung: str):
        """Erstellt eine neue Reaction Role Nachricht"""
        embed = discord.Embed(
            title="Reaction Role",
            description=f"{beschreibung}\n\nReagiere mit {emoji} um die Rolle {role.mention} zu erhalten!",
            color=discord.Color.blue()
        )
        
        message = await ctx.send(embed=embed)
        await message.add_reaction(emoji)
        
        # Speichere die Reaction Role in der Datenbank
        await self.db.insert('reaction_roles', {
            'message_id': str(message.id),
            'emoji': emoji,
            'role_id': str(role.id),
            'guild_id': str(ctx.guild.id),
            'channel_id': str(ctx.channel.id),
            'description': beschreibung
        })

    @reaction_role.command(name="remove")
    async def remove_reaction_role(self, ctx, message_id: str):
        """Entfernt eine Reaction Role Nachricht"""
        success = await self.db.delete('reaction_roles', 'message_id = ?', (message_id,))
        if success:
            await ctx.send("✅ Reaction Role wurde erfolgreich entfernt!")
        else:
            await ctx.send("❌ Diese Reaction Role existiert nicht!")

    @reaction_role.command(name="list")
    async def list_reaction_roles(self, ctx):
        """Listet alle aktiven Reaction Roles auf"""
        roles = await self.db.fetch_all(
            '''
            SELECT message_id, emoji, role_id, description 
            FROM reaction_roles 
            WHERE guild_id = ?
            ''', 
            (str(ctx.guild.id),)
        )

        if not roles:
            await ctx.send("❌ Keine aktiven Reaction Roles gefunden!")
            return

        embed = discord.Embed(
            title="Aktive Reaction Roles",
            color=discord.Color.blue()
        )
        
        for message_id, emoji, role_id, description in roles:
            role = ctx.guild.get_role(int(role_id))
            role_name = role.name if role else "Gelöschte Rolle"
            embed.add_field(
                name=f"Message ID: {message_id}",
                value=f"Emoji: {emoji}\nRolle: {role_name}\nBeschreibung: {description}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Event Handler für das Hinzufügen von Reaktionen"""
        reaction_roles = self.get_reaction_roles(str(payload.message_id))
        emoji = str(payload.emoji)
        
        if emoji in reaction_roles:
            guild = self.bot.get_guild(payload.guild_id)
            role = guild.get_role(int(reaction_roles[emoji]))
            member = guild.get_member(payload.user_id)
            
            if member and not member.bot:
                try:
                    await member.add_roles(role)
                except discord.HTTPException:
                    print(f"Fehler beim Hinzufügen der Rolle {role.name} zu {member.name}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Event Handler für das Entfernen von Reaktionen"""
        reaction_roles = self.get_reaction_roles(str(payload.message_id))
        emoji = str(payload.emoji)
        
        if emoji in reaction_roles:
            guild = self.bot.get_guild(payload.guild_id)
            role = guild.get_role(int(reaction_roles[emoji]))
            member = guild.get_member(payload.user_id)
            
            if member and not member.bot:
                try:
                    await member.remove_roles(role)
                except discord.HTTPException:
                    print(f"Fehler beim Entfernen der Rolle {role.name} von {member.name}")

async def setup(bot):
    await bot.add_cog(ReactionRoles(bot)) 