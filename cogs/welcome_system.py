import discord
from discord.ext import commands
import aiosqlite
from utils.db import DB_PATH
import asyncio

class WelcomeSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.welcome_configs = {}
        self.pending_verifications = {}
        
    async def cog_load(self):
        """Lädt die Willkommens-Konfigurationen aus der Datenbank"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT guild_id, welcome_channel_id, rules_channel_id, 
                       verification_channel_id, welcome_message, welcome_role_id,
                       rules_message_id, temp_role_id, verified_role_id, enabled
                FROM welcome_config
            ''') as cursor:
                async for row in cursor:
                    self.welcome_configs[row[0]] = {
                        'welcome_channel_id': row[1],
                        'rules_channel_id': row[2],
                        'verification_channel_id': row[3],
                        'welcome_message': row[4],
                        'welcome_role_id': row[5],
                        'rules_message_id': row[6],
                        'temp_role_id': row[7],
                        'verified_role_id': row[8],
                        'enabled': row[9]
                    }

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        """Willkommenssystem Befehle"""
        embed = discord.Embed(
            title="👋 Willkommenssystem Befehle",
            description="Verwalte das Willkommenssystem",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Konfiguration",
            value="`!welcome channel #kanal` - Setzt den Willkommenskanal\n"
                  "`!welcome message <Nachricht>` - Setzt die Willkommensnachricht\n"
                  "`!welcome role @rolle` - Setzt die automatische Rolle\n"
                  "`!welcome rules #kanal` - Setzt den Regelkanal\n"
                  "`!welcome verify #kanal` - Setzt den Verifikationskanal\n"
                  "`!welcome test` - Testet das Willkommenssystem\n"
                  "`!welcome toggle` - Aktiviert/Deaktiviert das System",
            inline=False
        )
        embed.add_field(
            name="Platzhalter für Nachrichten",
            value="{user} - Username\n"
                  "{mention} - User Mention\n"
                  "{server} - Servername\n"
                  "{count} - Mitgliederzahl",
            inline=False
        )
        await ctx.send(embed=embed)

    @welcome.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel):
        """Setzt den Willkommenskanal"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO welcome_config 
                (guild_id, welcome_channel_id) 
                VALUES (?, ?)
            ''', (ctx.guild.id, channel.id))
            await db.commit()
            
        self.welcome_configs.setdefault(ctx.guild.id, {})['welcome_channel_id'] = channel.id
        
        embed = discord.Embed(
            title="✅ Willkommenskanal gesetzt",
            description=f"Willkommensnachrichten werden nun in {channel.mention} gesendet.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @welcome.command(name="message")
    @commands.has_permissions(administrator=True)
    async def set_welcome_message(self, ctx, *, message: str):
        """Setzt die Willkommensnachricht"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO welcome_config 
                (guild_id, welcome_message) 
                VALUES (?, ?)
            ''', (ctx.guild.id, message))
            await db.commit()
            
        self.welcome_configs.setdefault(ctx.guild.id, {})['welcome_message'] = message
        
        # Zeige Vorschau
        preview = message.replace("{user}", ctx.author.name)\
                        .replace("{mention}", ctx.author.mention)\
                        .replace("{server}", ctx.guild.name)\
                        .replace("{count}", str(ctx.guild.member_count))
        
        embed = discord.Embed(
            title="✅ Willkommensnachricht gesetzt",
            description="**Vorschau:**\n" + preview,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @welcome.command(name="role")
    @commands.has_permissions(administrator=True)
    async def set_welcome_role(self, ctx, role: discord.Role):
        """Setzt die automatische Willkommensrolle"""
        if role >= ctx.guild.me.top_role:
            await ctx.send("❌ Diese Rolle ist zu hoch für mich!")
            return
            
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                INSERT OR REPLACE INTO welcome_config 
                (guild_id, welcome_role_id) 
                VALUES (?, ?)
            ''', (ctx.guild.id, role.id))
            await db.commit()
            
        self.welcome_configs.setdefault(ctx.guild.id, {})['welcome_role_id'] = role.id
        
        embed = discord.Embed(
            title="✅ Willkommensrolle gesetzt",
            description=f"Neue Mitglieder erhalten automatisch die Rolle {role.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @welcome.command(name="verify")
    @commands.has_permissions(administrator=True)
    async def set_verification(self, ctx, channel: discord.TextChannel = None, temp_role: discord.Role = None, verified_role: discord.Role = None):
        """Richtet das Verifikationssystem ein"""
        # Wenn keine Parameter angegeben wurden, zeige Hilfe
        if not all([channel, temp_role, verified_role]):
            embed = discord.Embed(
                title="⚙️ Verifikationssystem einrichten",
                description=(
                    "**Verwendung:**\n"
                    "`!welcome verify #kanal @temp-rolle @verifiziert-rolle`\n\n"
                    "**Beispiel:**\n"
                    "`!welcome verify #verify @rookie @member`\n\n"
                    "**Wichtig:**\n"
                    "• Kanäle müssen mit # erwähnt werden\n"
                    "• Rollen müssen mit @ erwähnt werden\n"
                    "• Kopiere die Erwähnungen nicht, sondern nutze die Discord-Autovervollständigung"
                ),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return

        if temp_role >= ctx.guild.me.top_role or verified_role >= ctx.guild.me.top_role:
            await ctx.send("❌ Eine der Rollen ist zu hoch für mich!")
            return

        try:
            # Regelwerk-Nachricht erstellen
            embed = discord.Embed(
                title="📜 Serverregeln und Verifikation",
                description=(
                    "Willkommen auf unserem Server! Um Zugang zu allen Kanälen zu erhalten, "
                    "musst du unseren Regeln zustimmen.\n\n"
                    "1. Reagiere mit ✅ um den Regeln zuzustimmen\n"
                    "2. Du erhältst dann Zugang zum Server\n\n"
                    "**Hinweis:** Durch das Reagieren stimmst du zu, dass du die Regeln "
                    "gelesen hast und diese befolgst."
                ),
                color=discord.Color.blue()
            )

            rules_message = await channel.send(embed=embed)
            await rules_message.add_reaction("✅")

            # Konfiguration speichern
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO welcome_config 
                    (guild_id, verification_channel_id, rules_message_id, temp_role_id, 
                     verified_role_id, enabled) 
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (ctx.guild.id, channel.id, rules_message.id, temp_role.id, verified_role.id))
                await db.commit()

            # Cache aktualisieren
            if ctx.guild.id not in self.welcome_configs:
                self.welcome_configs[ctx.guild.id] = {}
            
            self.welcome_configs[ctx.guild.id].update({
                'verification_channel_id': channel.id,
                'rules_message_id': rules_message.id,
                'temp_role_id': temp_role.id,
                'verified_role_id': verified_role.id,
                'enabled': True
            })

            # Debug-Ausgabe
            print(f"Verifikationssystem für Guild {ctx.guild.id} konfiguriert:")
            print(f"Temp Role ID: {temp_role.id}")
            print(f"Config: {self.welcome_configs[ctx.guild.id]}")

            embed = discord.Embed(
                title="✅ Verifikationssystem eingerichtet",
                description=(
                    f"Verifikationskanal: {channel.mention}\n"
                    f"Temporäre Rolle: {temp_role.mention}\n"
                    f"Verifizierte Rolle: {verified_role.mention}\n\n"
                    "**Test das System:**\n"
                    "1. Verlasse kurz den Server\n"
                    "2. Tritt wieder bei\n"
                    "3. Prüfe, ob du die temporäre Rolle erhältst"
                ),
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Fehler beim Einrichten des Verifikationssystems: {str(e)}")
            await ctx.send(f"❌ Fehler beim Einrichten: {str(e)}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def checkconfig(self, ctx):
        """Zeigt die aktuelle Konfiguration des Willkommenssystems"""
        config = self.welcome_configs.get(ctx.guild.id, {})
        
        embed = discord.Embed(
            title="🔧 Willkommenssystem Konfiguration",
            color=discord.Color.blue()
        )
        
        # Rollen
        temp_role = ctx.guild.get_role(config.get('temp_role_id', 0))
        verified_role = ctx.guild.get_role(config.get('verified_role_id', 0))
        
        embed.add_field(
            name="Rollen",
            value=f"Temporäre Rolle: {temp_role.mention if temp_role else 'Nicht gesetzt'}\n"
                  f"Verifizierte Rolle: {verified_role.mention if verified_role else 'Nicht gesetzt'}",
            inline=False
        )
        
        # Kanäle
        welcome_channel = ctx.guild.get_channel(config.get('welcome_channel_id', 0))
        verify_channel = ctx.guild.get_channel(config.get('verification_channel_id', 0))
        
        embed.add_field(
            name="Kanäle",
            value=f"Willkommenskanal: {welcome_channel.mention if welcome_channel else 'Nicht gesetzt'}\n"
                  f"Verifikationskanal: {verify_channel.mention if verify_channel else 'Nicht gesetzt'}",
            inline=False
        )
        
        # Status
        embed.add_field(
            name="Status",
            value=f"System aktiv: {'✅' if config.get('enabled', False) else '❌'}",
            inline=False
        )
        
        await ctx.send(embed=embed)

    async def send_verification_instructions(self, member, verify_channel):
        """Sendet Verifikationsanweisungen an den User"""
        dm_embed = discord.Embed(
            title=f"👋 Willkommen auf {member.guild.name}!",
            description=f"Hey {member.name}!\n\n"
                      f"Bitte verifiziere dich im Verifikationskanal, "
                      f"um Zugang zu allen Kanälen zu erhalten.",
            color=discord.Color.blue()
        )
        dm_embed.add_field(
            name="📝 Verifikation",
            value="1. Gehe zum Verifikationskanal\n"
                 "2. Lies die Serverregeln\n"
                 "3. Reagiere mit ✅ um dich zu verifizieren",
            inline=False
        )

        try:
            await member.send(embed=dm_embed)
            return True
        except discord.Forbidden:
            # Erstelle temporären privaten Kanal für Anweisungen
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                member: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                member.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            
            try:
                temp_channel = await member.guild.create_text_channel(
                    name=f'verify-{member.name}',
                    overwrites=overwrites,
                    category=verify_channel.category if verify_channel.category else None
                )

                instructions_embed = discord.Embed(
                    title="⚠️ Wichtige Information",
                    description=(
                        f"Hey {member.mention}!\n\n"
                        "Da deine Direktnachrichten deaktiviert sind, "
                        "wurden diese Anweisungen in einem temporären Kanal erstellt.\n\n"
                        f"**Bitte aktiviere Direktnachrichten für {member.guild.name}:**\n"
                        "1. Rechtsklick auf den Server\n"
                        "2. Privatsphäre-Einstellungen\n"
                        "3. 'Direktnachrichten von Servermitgliedern' aktivieren\n\n"
                        "Dieser Kanal wird in 5 Minuten automatisch gelöscht."
                    ),
                    color=discord.Color.orange()
                )
                instructions_embed.add_field(
                    name="📝 Verifikation",
                    value=f"1. Gehe zu {verify_channel.mention}\n"
                         "2. Lies die Serverregeln\n"
                         "3. Reagiere mit ✅ um dich zu verifizieren",
                    inline=False
                )
                
                await temp_channel.send(member.mention, embed=instructions_embed)
                
                # Lösche den Kanal nach 5 Minuten
                await asyncio.sleep(300)
                try:
                    await temp_channel.delete()
                except:
                    pass
                    
            except discord.Forbidden:
                return False
                
            return True
        except Exception as e:
            print(f"Fehler beim Senden der Verifikationsanweisungen: {str(e)}")
            return False

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Wird ausgeführt, wenn ein neues Mitglied dem Server beitritt"""
        config = self.welcome_configs.get(member.guild.id, {})
        
        try:
            # Temporäre Rolle vergeben
            if 'temp_role_id' in config and config['temp_role_id']:
                temp_role = member.guild.get_role(config['temp_role_id'])
                if temp_role and temp_role < member.guild.me.top_role:
                    try:
                        await member.add_roles(temp_role)
                    except discord.Forbidden:
                        print(f"Keine Berechtigung für Rollenvergabe an {member.name}")

            # Willkommensnachricht senden
            if 'welcome_channel_id' in config and config['welcome_channel_id']:
                channel = member.guild.get_channel(config['welcome_channel_id'])
                verify_channel = None
                
                if channel:
                    verification_text = ""
                    if 'verification_channel_id' in config and config['verification_channel_id']:
                        verify_channel = member.guild.get_channel(config['verification_channel_id'])
                        if verify_channel:
                            verification_text = f"\n\n**Wichtig:** Bitte verifiziere dich in {verify_channel.mention}, um Zugang zum Server zu erhalten!"

                    base_message = config.get('welcome_message', "Willkommen auf unserem Server, {mention}!")\
                        .replace("{user}", member.name)\
                        .replace("{mention}", member.mention)\
                        .replace("{server}", member.guild.name)\
                        .replace("{count}", str(member.guild.member_count))
                    
                    message = base_message + verification_text
                        
                    embed = discord.Embed(
                        title="👋 Willkommen!",
                        description=message,
                        color=discord.Color.blue()
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    
                    if verification_text and verify_channel:
                        embed.add_field(
                            name="📝 Nächste Schritte",
                            value=f"1. Gehe zu {verify_channel.mention}\n"
                                 f"2. Lies die Serverregeln\n"
                                 f"3. Reagiere mit ✅ um Zugang zu erhalten",
                            inline=False
                        )
                    
                    await channel.send(embed=embed)

                    # Sende Verifikationsanweisungen
                    if verify_channel:
                        await self.send_verification_instructions(member, verify_channel)

        except Exception as e:
            print(f"Fehler im on_member_join Event: {str(e)}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Wird ausgeführt, wenn eine Reaktion hinzugefügt wird"""
        if payload.user_id == self.bot.user.id:
            return

        config = self.welcome_configs.get(payload.guild_id, {})
        if not config:
            return

        # Prüfe ob es die Regelwerk-Nachricht ist
        if (payload.message_id == config.get('rules_message_id') and 
            payload.emoji.name == "✅"):
            
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return

            member = guild.get_member(payload.user_id)
            if not member:
                return

            # Rollen aktualisieren
            temp_role = guild.get_role(config['temp_role_id'])
            verified_role = guild.get_role(config['verified_role_id'])

            try:
                # Temporäre Rolle entfernen
                if temp_role:
                    await member.remove_roles(temp_role)
                
                # Verifizierte Rolle hinzufügen
                if verified_role:
                    await member.add_roles(verified_role)

                # DM an User
                try:
                    embed = discord.Embed(
                        title="✅ Erfolgreich verifiziert!",
                        description=f"Du hast nun Zugang zu allen Kanälen auf **{guild.name}**!",
                        color=discord.Color.green()
                    )
                    await member.send(embed=embed)
                except discord.Forbidden:
                    pass

                # Log-Nachricht
                if 'welcome_channel_id' in config:
                    channel = guild.get_channel(config['welcome_channel_id'])
                    if channel:
                        embed = discord.Embed(
                            title="✅ Neues verifiziertes Mitglied",
                            description=f"{member.mention} hat sich erfolgreich verifiziert!",
                            color=discord.Color.green()
                        )
                        await channel.send(embed=embed)

            except discord.Forbidden:
                pass

    @welcome.command(name="rules")
    @commands.has_permissions(administrator=True)
    async def update_rules(self, ctx, *, rules: str):
        """Aktualisiert den Regeltext"""
        config = self.welcome_configs.get(ctx.guild.id, {})
        if not config.get('verification_channel_id'):
            await ctx.send("❌ Bitte richte zuerst das Verifikationssystem ein!")
            return

        channel = ctx.guild.get_channel(config['verification_channel_id'])
        if not channel:
            await ctx.send("❌ Der Verifikationskanal wurde nicht gefunden!")
            return

        embed = discord.Embed(
            title="📜 Serverregeln",
            description=rules + "\n\n" + 
                       "**Reagiere mit ✅ um den Regeln zuzustimmen**",
            color=discord.Color.blue()
        )

        # Alte Nachricht löschen falls vorhanden
        try:
            old_message = await channel.fetch_message(config.get('rules_message_id'))
            await old_message.delete()
        except:
            pass

        # Neue Nachricht senden
        rules_message = await channel.send(embed=embed)
        await rules_message.add_reaction("✅")

        # Konfiguration aktualisieren
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                UPDATE welcome_config 
                SET rules_message_id = ?
                WHERE guild_id = ?
            ''', (rules_message.id, ctx.guild.id))
            await db.commit()

        self.welcome_configs[ctx.guild.id]['rules_message_id'] = rules_message.id
        
        await ctx.send("✅ Regeltext wurde aktualisiert!")

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot)) 