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
        # Lade Konfigurationen beim Start
        self.bot.loop.create_task(self.load_configs())

    async def load_configs(self):
        """Lädt alle Server-Konfigurationen"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute('''
                    SELECT guild_id, welcome_channel_id, rules_channel_id, 
                           temp_role_id, verified_role_id, welcome_message, enabled
                    FROM welcome_config
                ''') as cursor:
                    async for row in cursor:
                        self.welcome_configs[row[0]] = {
                            'welcome_channel_id': row[1],
                            'rules_channel_id': row[2],
                            'temp_role_id': row[3],
                            'verified_role_id': row[4],
                            'welcome_message': row[5],
                            'enabled': row[6]
                        }
            print("✅ Willkommenssystem Konfigurationen geladen")
        except Exception as e:
            print(f"❌ Fehler beim Laden der Willkommenssystem Konfigurationen: {e}")

    async def create_rules_message(self, guild_id):
        """Erstellt die Regelnachricht mit Button"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT rule_number, rule_title, rule_content 
                FROM server_rules 
                WHERE guild_id = ? 
                ORDER BY rule_number
            ''', (guild_id,)) as cursor:
                rules = await cursor.fetchall()

        embed = discord.Embed(
            title="📜 Serverregeln",
            description="Bitte lies dir die folgenden Regeln durch und akzeptiere sie mit dem Button unten.",
            color=discord.Color.blue()
        )

        for number, title, content in rules:
            embed.add_field(
                name=f"§{number} {title or ''}",
                value=content,
                inline=False)

        # Erstelle Button zum Akzeptieren
        view = RulesView()
        return embed, view

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def welcome(self, ctx):
        """Willkommenssystem Befehle"""
        if ctx.invoked_subcommand is None:
            await ctx.send("""
🔧 **Willkommenssystem Befehle:**
`!welcome setup` - Richtet das Willkommenssystem ein
`!welcome channel #kanal` - Setzt den Willkommenskanal
`!welcome message <nachricht>` - Setzt die Willkommensnachricht
`!welcome rules #kanal` - Setzt den Regelkanal
`!welcome test` - Testet das System
            """)

    @welcome.command(name="setup")
    @commands.has_permissions(administrator=True)
    async def setup_welcome(self, ctx):
        """Richtet das Willkommenssystem ein"""
        try:
            # Erstelle Unverified Rolle falls nicht vorhanden
            unverified_role = discord.utils.get(ctx.guild.roles, name="Unverified")
            if not unverified_role:
                unverified_role = await ctx.guild.create_role(
                    name="Unverified",
                    color=discord.Color.light_grey(),
                    reason="Willkommenssystem Setup"
                )

            # Erstelle Verified Rolle falls nicht vorhanden
            verified_role = discord.utils.get(ctx.guild.roles, name="Verified")
            if not verified_role:
                verified_role = await ctx.guild.create_role(
                    name="Verified",
                    color=discord.Color.green(),
                    reason="Willkommenssystem Setup"
                )

            # Speichere Konfiguration in der Datenbank
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO welcome_config 
                    (guild_id, temp_role_id, verified_role_id, enabled) 
                    VALUES (?, ?, ?, 1)
                ''', (ctx.guild.id, unverified_role.id, verified_role.id))
                await db.commit()

            # Bestätigungsnachricht
            embed = discord.Embed(
                title="✅ Willkommenssystem eingerichtet!",
                color=discord.Color.green()
            )
            embed.add_field(name="Temporäre Rolle", value=f"@{unverified_role.name}", inline=False)
            embed.add_field(name="Verifizierte Rolle", value=f"@{verified_role.name}", inline=False)
            embed.add_field(name="Regelakzeptanz", value="aktiviert", inline=False)
            embed.add_field(
                name="Nächste Schritte", 
                value="1. `!welcome channel #kanal` - Willkommenskanal festlegen\n" +
                      "2. `!welcome rules #kanal` - Regelkanal festlegen", 
                inline=False
            )

            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Fehler beim Setup des Willkommenssystems: {e}")
            await ctx.send("❌ Es ist ein Fehler aufgetreten!")

    @welcome.command(name="channel")
    @commands.has_permissions(administrator=True)
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel):
        """Setzt den Willkommenskanal"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute('''
                    UPDATE welcome_config 
                    SET welcome_channel_id = ?
                    WHERE guild_id = ?
                ''', (channel.id, ctx.guild.id))
                await db.commit()

            await ctx.send(f"✅ Willkommenskanal wurde auf {channel.mention} gesetzt!")

        except Exception as e:
            print(f"Fehler beim Setzen des Willkommenskanals: {e}")
            await ctx.send("❌ Es ist ein Fehler aufgetreten!")

    @set_welcome_channel.error
    async def set_welcome_channel_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Bitte gib einen Kanal an! Beispiel: `!welcome channel #willkommen`")
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.send("❌ Kanal nicht gefunden! Bitte erwähne einen gültigen Kanal.")

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

        await ctx.send(f"✅ Willkommensnachricht wurde gesetzt auf:\n{message}")

    @set_welcome_message.error
    async def set_welcome_message_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("""
❌ Bitte gib eine Nachricht an!

**Beispiel:**
`!welcome message Willkommen {user} auf {server}!`

**Verfügbare Platzhalter:**
• {user} - Username
• {mention} - User-Mention
• {server} - Servername
• {count} - Mitgliederzahl
""")

    @commands.command(name="role")
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

    @commands.command(name="verify")
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
        """Wird ausgeführt wenn ein neuer User dem Server beitritt"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute('''
                    SELECT welcome_channel_id, temp_role_id, verified_role_id, welcome_message, enabled, rules_channel_id 
                    FROM welcome_config 
                    WHERE guild_id = ?
                ''', (member.guild.id,)) as cursor:
                    config = await cursor.fetchone()

                if not config or not config[4]:  # enabled check
                    return

                welcome_channel_id, temp_role_id, verified_role_id, welcome_message, _, rules_channel_id = config

                # Füge Unverified-Rolle hinzu
                if temp_role_id:
                    try:
                        unverified_role = member.guild.get_role(temp_role_id)
                        if unverified_role:
                            await member.add_roles(unverified_role)
                            print(f"✅ Unverified-Rolle zu {member.name} hinzugefügt")
                        else:
                            print(f"❌ Unverified-Rolle (ID: {temp_role_id}) nicht gefunden!")
                    except discord.Forbidden:
                        print(f"❌ Keine Berechtigung, die Unverified-Rolle zu {member.name} hinzuzufügen")
                    except Exception as e:
                        print(f"❌ Fehler beim Hinzufügen der Unverified-Rolle: {e}")
                else:
                    print(f"❌ Keine Unverified-Rolle konfiguriert für Server {member.guild.id}")

                # Sende Willkommensnachricht
                if welcome_channel_id:
                    channel = member.guild.get_channel(welcome_channel_id)
                    if channel:
                        rules_channel = member.guild.get_channel(rules_channel_id) if rules_channel_id else None
                        
                        embed = discord.Embed(
                            title=f"👋 Willkommen auf {member.guild.name}!",
                            description=welcome_message or f"Willkommen {member.mention} auf unserem Server!",
                            color=discord.Color.blue()
                        )
                        
                        instructions = []
                        if rules_channel:
                            instructions.append(f"1️⃣ Lies dir bitte die Regeln in {rules_channel.mention} durch")
                            instructions.append("2️⃣ Akzeptiere die Regeln mit ✅ um Zugriff auf alle Kanäle zu erhalten")
                        
                        if instructions:
                            embed.add_field(
                                name="📝 Nächste Schritte:",
                                value="\n".join(instructions),
                                inline=False
                            )
                        
                        embed.set_thumbnail(url=member.display_avatar.url)
                        embed.set_footer(text=f"Du bist unser {len(member.guild.members)}. Mitglied!")
                        
                        await channel.send(embed=embed)

        except Exception as e:
            print(f"Fehler im on_member_join Event: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Wird ausgeführt, wenn eine Reaktion hinzugefügt wird"""
        if payload.user_id == self.bot.user.id:
            return

        try:
            async with aiosqlite.connect(DB_PATH) as db:
                # Hole Konfiguration
                async with db.execute('''
                    SELECT rules_channel_id, temp_role_id, verified_role_id 
                    FROM welcome_config 
                    WHERE guild_id = ?
                ''', (payload.guild_id,)) as cursor:
                    config = await cursor.fetchone()

                if not config:
                    return

                rules_channel_id, temp_role_id, verified_role_id = config

                # Prüfe ob es die richtige Nachricht im richtigen Kanal ist
                if (payload.channel_id == rules_channel_id and 
                    str(payload.emoji) == "✅"):
                    
                    guild = self.bot.get_guild(payload.guild_id)
                    if not guild:
                        return

                    member = guild.get_member(payload.user_id)
                    if not member:
                        return

                    # Hole die Rollen
                    temp_role = guild.get_role(temp_role_id) if temp_role_id else None
                    verified_role = guild.get_role(verified_role_id) if verified_role_id else None

                    try:
                        # Entferne temporäre Rolle
                        if temp_role and temp_role in member.roles:
                            await member.remove_roles(temp_role)
                            print(f"Temporäre Rolle von {member.name} entfernt")

                        # Füge verifizierte Rolle hinzu
                        if verified_role and verified_role not in member.roles:
                            await member.add_roles(verified_role)
                            print(f"Verifizierte Rolle zu {member.name} hinzugefügt")

                        # Sende Bestätigung an User
                        try:
                            embed = discord.Embed(
                                title="✅ Erfolgreich verifiziert!",
                                description=f"Du hast nun Zugang zu allen Kanälen auf **{guild.name}**!",
                                color=discord.Color.green()
                            )
                            await member.send(embed=embed)
                        except discord.Forbidden:
                            pass  # User hat DMs deaktiviert

                    except discord.Forbidden:
                        print(f"Keine Berechtigung für Rollenverwaltung bei {member.name}")
                    except Exception as e:
                        print(f"Fehler bei der Verifikation von {member.name}: {e}")

        except Exception as e:
            print(f"Fehler im on_raw_reaction_add Event: {e}")

    @welcome.command(name="rules")
    @commands.has_permissions(administrator=True)
    async def set_rules_channel(self, ctx, channel: discord.TextChannel):
        """Setzt den Regelkanal"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute('''
                    UPDATE welcome_config 
                    SET rules_channel_id = ?
                    WHERE guild_id = ?
                ''', (channel.id, ctx.guild.id))
                await db.commit()

            await ctx.send(f"✅ Regelkanal wurde auf {channel.mention} gesetzt!")

        except Exception as e:
            print(f"Fehler beim Setzen des Regelkanals: {e}")
            await ctx.send("❌ Es ist ein Fehler aufgetreten!")

class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Regeln akzeptieren", style=discord.ButtonStyle.green, custom_id="accept_rules")
    async def accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button zum Akzeptieren der Regeln"""
        async with aiosqlite.connect(DB_PATH) as db:
            # Hole Rollen-IDs
            async with db.execute('''
                SELECT temp_role_id, verified_role_id 
                FROM welcome_config 
                WHERE guild_id = ?
            ''', (interaction.guild_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await interaction.response.send_message("❌ Willkommenssystem nicht eingerichtet!", ephemeral=True)
                
                temp_role_id, verified_role_id = row

        # Hole Rollen
        temp_role = interaction.guild.get_role(temp_role_id)
        verified_role = interaction.guild.get_role(verified_role_id)

        if not all([temp_role, verified_role]):
            return await interaction.response.send_message("❌ Rollen nicht gefunden!", ephemeral=True)

        # Entferne temporäre Rolle, füge verifizierte hinzu
        await interaction.user.remove_roles(temp_role)
        await interaction.user.add_roles(verified_role)

        await interaction.response.send_message("✅ Du hast die Regeln akzeptiert und bist nun verifiziert!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(WelcomeSystem(bot)) 