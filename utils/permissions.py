import discord
from discord.ext import commands

def is_admin():
    """
    Überprüft, ob der Benutzer die Admin-Rolle hat.
    Diese Funktion ersetzt die eingebaute has_permissions-Überprüfung.
    """
    async def predicate(ctx):
        # Suche nach einer Rolle mit dem Namen "Admin"
        admin_role = discord.utils.get(ctx.guild.roles, name="Admin")
        if not admin_role:
            await ctx.send("❌ Es wurde keine Rolle mit dem Namen 'Admin' gefunden!")
            return False
        
        # Prüfe, ob der Benutzer die Admin-Rolle hat
        if admin_role in ctx.author.roles:
            return True
        else:
            await ctx.send("❌ Du benötigst die Admin-Rolle, um diesen Befehl zu verwenden!")
            return False
    
    return commands.check(predicate) 