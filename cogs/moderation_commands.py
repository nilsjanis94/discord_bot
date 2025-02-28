import discord
from discord.ext import commands
import datetime
import asyncio
from utils.db import init_db, DB_PATH
import aiosqlite
import json
from utils.automod import AutoMod
from utils.mod_logger import ModLogger
from discord.ext.commands import MemberNotFound, BadArgument
import re

class ModerationCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.automod = AutoMod(bot)
        self.logger = ModLogger(bot)
        
    async def cog_load(self):
        """Wird beim Laden der Cog ausgeführt"""
        try:
            # Initialisiere zuerst die Datenbank
            await init_db()
            # Dann lade die Mod-Channels
            await self.logger.load_mod_channels()
            # Initialisiere AutoMod
            await self.automod.setup(self.bot)
        except Exception as e:
            print(f"Fehler beim Initialisieren der Moderation: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setlogchannel(self, ctx, channel: discord.TextChannel = None):
        """Setzt den Logging-Kanal"""
        channel = channel or ctx.channel
        self.logger.log_channels[ctx.guild.id] = channel.id
        self.logger.save_log_channels()
        await ctx.send(f"Logging-Kanal wurde auf {channel.mention} gesetzt!")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self, ctx, member: discord.Member, *, reason: str = None):
        """Verwarnt einen User"""
        if not reason:
            return await ctx.send("❌ Bitte gib einen Grund für die Verwarnung an!")

        if member.bot:
            return await ctx.send("❌ Bots können nicht verwarnt werden!")

        if member == ctx.author:
            return await ctx.send("❌ Du kannst dich nicht selbst verwarnen!")

        if member.top_role >= ctx.author.top_role:
            return await ctx.send("❌ Du kannst keine Mitglieder verwarnen, die eine höhere oder gleiche Rolle haben!")

        try:
            # Speichere Verwarnung in der Datenbank
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute('''
                    INSERT INTO warnings 
                    (user_id, user_name, guild_id, reason, moderator_id, moderator_name)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (member.id, str(member), ctx.guild.id, reason, ctx.author.id, str(ctx.author)))
                await db.commit()

            # Benachrichtige den User
            try:
                embed = discord.Embed(
                    title="⚠️ Verwarnung erhalten",
                    description=f"Du wurdest auf **{ctx.guild.name}** verwarnt.",
                    color=discord.Color.yellow()
                )
                embed.add_field(name="Grund", value=reason)
                embed.add_field(name="Moderator", value=ctx.author.name)
                await member.send(embed=embed)
            except discord.Forbidden:
                await ctx.send("⚠️ Der User konnte nicht per DM benachrichtigt werden.")

            # Log die Aktion
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute('SELECT COUNT(*) FROM warnings WHERE user_id = ? AND guild_id = ?', 
                                    (member.id, ctx.guild.id)) as cursor:
                    warning_count = (await cursor.fetchone())[0]

            # Sende Log-Nachricht
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute('SELECT mod_log_channel_id FROM channel_config WHERE guild_id = ?', 
                                    (ctx.guild.id,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        log_channel = ctx.guild.get_channel(row[0])
                        if log_channel:
                            embed = discord.Embed(
                                title="⚠️ Verwarnung ausgesprochen",
                                color=discord.Color.yellow(),
                                timestamp=datetime.datetime.now(datetime.timezone.utc)
                            )
                            embed.add_field(name="User", value=f"{member.mention} ({member.id})")
                            embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})")
                            embed.add_field(name="Grund", value=reason, inline=False)
                            embed.add_field(name="Verwarnungen", value=f"Dies ist Verwarnung #{warning_count}")
                            await log_channel.send(embed=embed)

            # Bestätige die Verwarnung
            await ctx.send(f"✅ {member.mention} wurde verwarnt! (Verwarnung #{warning_count})")

        except Exception as e:
            print(f"Fehler beim Verwarnen: {e}")
            await ctx.send("❌ Es ist ein Fehler aufgetreten!")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warnings(self, ctx, user: discord.Member):
        """Zeigt alle Verwarnungen eines Users"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT reason, moderator_name, timestamp 
                FROM warnings 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY timestamp DESC
            ''', (user.id, ctx.guild.id)) as cursor:
                warnings = await cursor.fetchall()

            if not warnings:
                await ctx.send(f"{user.mention} hat keine Verwarnungen.")
                return

            embed = discord.Embed(
                title=f"⚠️ Verwarnungen für {user.name}",
                color=discord.Color.yellow()
            )

            for i, (reason, mod_name, timestamp) in enumerate(warnings, 1):
                embed.add_field(
                    name=f"Verwarnung {i} | {timestamp}",
                    value=f"**Grund:** {reason or 'Kein Grund angegeben'}\n"
                          f"**Moderator:** {mod_name}",
                    inline=False
                )

            embed.set_footer(text=f"Insgesamt {len(warnings)} Verwarnung(en)")
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def delwarn(self, ctx, user: discord.Member, warn_id: int):
        """Löscht eine bestimmte Verwarnung eines Users"""
        async with aiosqlite.connect(DB_PATH) as db:
            # Prüfe ob die Verwarnung existiert
            async with db.execute('''
                SELECT id FROM warnings 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY timestamp DESC
            ''', (user.id, ctx.guild.id)) as cursor:
                warnings = await cursor.fetchall()
                
                if not warnings or warn_id > len(warnings):
                    await ctx.send("❌ Diese Verwarnung existiert nicht!")
                    return

                # Lösche die Verwarnung
                warning_db_id = warnings[warn_id - 1][0]
                await db.execute('DELETE FROM warnings WHERE id = ?', (warning_db_id,))
                await db.commit()

            embed = discord.Embed(
                title="✅ Verwarnung gelöscht",
                description=f"Verwarnung {warn_id} wurde von {user.mention} entfernt.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

            # Log die Aktion
            await self.logger.log_mod_action(
                ctx.guild,
                "Verwarnung gelöscht",
                user=user,
                moderator=ctx.author,
                content=f"Verwarnung {warn_id} wurde entfernt"
            )

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def clearwarnings(self, ctx, member: discord.Member):
        """Löscht alle Verwarnungen eines Mitglieds"""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''
                DELETE FROM warnings 
                WHERE user_id = ? AND guild_id = ?
            ''', (member.id, ctx.guild.id))
            await db.commit()

        await ctx.send(f"Alle Verwarnungen von {member.mention} wurden gelöscht.")

    async def get_member(self, ctx, user_input):
        """Hilfsfunktion um Member auf verschiedene Arten zu finden"""
        member = None
        
        # Versuche direkt die Erwähnung zu nutzen
        try:
            member = await commands.MemberConverter().convert(ctx, user_input)
            return member
        except:
            pass

        # Versuche über ID
        try:
            if user_input.isdigit():
                member = ctx.guild.get_member(int(user_input))
                if member:
                    return member
        except:
            pass

        # Versuche über Namen
        try:
            member = discord.utils.get(ctx.guild.members, name=user_input)
            if member:
                return member
            
            # Versuche über Display Name
            member = discord.utils.get(ctx.guild.members, display_name=user_input)
            if member:
                return member
        except:
            pass

        return None

    async def send_mod_action_messages(self, ctx, member, action_type, embed_data, reason=None, duration=None):
        """Sendet Benachrichtigungen für Moderationsaktionen"""
        try:
            # Zuerst: Log im Mod-Log Channel
            await self.logger.log_mod_action(
                ctx.guild,
                action_type,
                user=member,
                moderator=ctx.author,
                reason=reason,
                duration=duration,
                expires_at=embed_data['expires_at'] if isinstance(embed_data, dict) and 'expires_at' in embed_data else None,
                warning_count=embed_data['warning_count'] if isinstance(embed_data, dict) and 'warning_count' in embed_data else None
            )

            # Dann: Kurze Bestätigung im Befehlskanal
            confirm_embed = discord.Embed(
                description=f"✅ Aktion ausgeführt: {action_type} für {member.mention}",
                color=discord.Color.green()
            )
            await ctx.send(embed=confirm_embed, delete_after=5)

            # Zuletzt: DM an User
            user_embed = discord.Embed(
                title=f"🛡️ Moderation: {action_type}",
                description=f"Du wurdest auf dem Server **{ctx.guild.name}** {action_type.lower()}.",
                color=self.logger.get_action_color(action_type)
            )
            if reason:
                user_embed.add_field(name="Grund", value=reason)
            if duration:
                user_embed.add_field(name="Dauer", value=duration)
            if isinstance(embed_data, dict) and 'warning_count' in embed_data:
                user_embed.add_field(name="Verwarnungen", value=f"Du hast jetzt {embed_data['warning_count']} Verwarnung(en)")
            
            try:
                await member.send(embed=user_embed)
            except discord.Forbidden:
                await self.logger.log_mod_action(
                    ctx.guild, 
                    "Info", 
                    content=f"⚠️ DM konnte nicht gesendet werden - User hat DMs von Server-Mitgliedern deaktiviert",
                    user=member
                )
            except Exception as e:
                await self.logger.log_mod_action(
                    ctx.guild,
                    "Info",
                    content=f"⚠️ DM konnte nicht gesendet werden - Unerwarteter Fehler: {str(e)}",
                    user=member
                )

        except Exception as e:
            await ctx.send(f"❌ Fehler beim Senden der Benachrichtigungen: {str(e)}")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def timeout(self, ctx, user_input: str = None, *args):
        """Timeout für ein Mitglied"""
        if not user_input:
            embed = discord.Embed(
                title="🔇 Timeout Befehl",
                description="Schaltet einen User für eine bestimmte Zeit stumm.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Verwendung",
                value="!timeout @User/ID/Name [Minuten] [Grund]\n"
                      "Beispiel: !timeout @User 10 Spam im Chat"
            )
            await ctx.send(embed=embed)
            return

        # Finde den Member
        member = await self.get_member(ctx, user_input)
        if member is None:
            await ctx.send(f"❌ Konnte keinen User finden für: {user_input}")
            return

        # Verarbeite die Argumente
        duration_str = None
        reason_parts = []
        duration_found = False

        for arg in args:
            if not duration_found and arg.isdigit():
                duration_str = arg
                duration_found = True
            else:
                reason_parts.append(arg)

        if not duration_str:
            await ctx.send("❌ Bitte geben Sie eine gültige Zahl für die Dauer in Minuten an!")
            return

        reason = ' '.join(reason_parts) if reason_parts else None

        try:
            duration_minutes = int(duration_str)
            if duration_minutes < 1:
                await ctx.send("❌ Die Dauer muss mindestens 1 Minute betragen!")
                return
            if duration_minutes > 40320:
                await ctx.send("❌ Die maximale Timeout-Dauer beträgt 40320 Minuten (28 Tage)!")
                return

            # Berechne Ablaufzeit
            duration_delta = datetime.timedelta(minutes=duration_minutes)
            expires_at = datetime.datetime.now() + duration_delta

            # Timeout durchführen
            await member.timeout(duration_delta, reason=reason)
            
            # Erstelle Embed-Daten
            embed_data = {
                'expires_at': expires_at.strftime("%d.%m.%Y %H:%M:%S"),
                'duration': f"{duration_minutes} Minuten"
            }

            # Sende Benachrichtigungen
            await self.send_mod_action_messages(
                ctx, 
                member, 
                "Timeout", 
                embed_data,
                reason=reason,
                duration=f"{duration_minutes} Minuten"
            )

            # Speichere in Datenbank
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute('''
                    INSERT INTO timeouts (
                        user_id,
                        user_name,
                        guild_id,
                        moderator_id,
                        moderator_name,
                        duration_minutes,
                        reason,
                        expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    member.id,
                    f"{member.name}#{member.discriminator}",
                    ctx.guild.id,
                    ctx.author.id,
                    f"{ctx.author.name}#{ctx.author.discriminator}",
                    duration_minutes,
                    reason,
                    expires_at.isoformat()
                ))
                await db.commit()

        except ValueError:
            await ctx.send("❌ Die Dauer muss eine gültige Zahl sein!")
        except discord.Forbidden:
            await ctx.send("❌ Ich habe keine Berechtigung, diesen User stumm zu schalten!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Es gab einen Fehler beim Ausführen des Befehls: {str(e)}")

    @timeout.error
    async def timeout_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Du hast keine Berechtigung, diesen Befehl zu nutzen!")
        else:
            await ctx.send(f"❌ Es ist ein unerwarteter Fehler aufgetreten: {str(error)}")

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
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = None):
        """Kickt einen User vom Server"""
        if not reason:
            return await ctx.send("❌ Bitte gib einen Grund für den Kick an!")

        if member.bot:
            return await ctx.send("❌ Bots können nicht gekickt werden!")

        if member == ctx.author:
            return await ctx.send("❌ Du kannst dich nicht selbst kicken!")

        if member.top_role >= ctx.author.top_role:
            return await ctx.send("❌ Du kannst keine Mitglieder kicken, die eine höhere oder gleiche Rolle haben!")

        try:
            # DM an den User
            try:
                embed = discord.Embed(
                    title="🚫 Vom Server gekickt",
                    description=f"Du wurdest von **{ctx.guild.name}** gekickt.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Grund", value=reason)
                embed.add_field(name="Moderator", value=ctx.author.name)
                await member.send(embed=embed)
            except discord.Forbidden:
                await ctx.send("⚠️ Der User konnte nicht per DM benachrichtigt werden.")

            # Kick durchführen
            await member.kick(reason=reason)

            # Log-Nachricht senden
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute('SELECT mod_log_channel_id FROM channel_config WHERE guild_id = ?', 
                                    (ctx.guild.id,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        log_channel = ctx.guild.get_channel(row[0])
                        if log_channel:
                            embed = discord.Embed(
                                title="🚫 Mitglied gekickt",
                                color=discord.Color.red(),
                                timestamp=datetime.datetime.now(datetime.timezone.utc)
                            )
                            embed.add_field(name="User", value=f"{member} ({member.id})")
                            embed.add_field(name="Moderator", value=f"{ctx.author.mention} ({ctx.author.id})")
                            embed.add_field(name="Grund", value=reason, inline=False)
                            
                            # Verwarnungshistorie hinzufügen
                            async with db.execute('''
                                SELECT COUNT(*) 
                                FROM warnings 
                                WHERE user_id = ? AND guild_id = ?
                            ''', (member.id, ctx.guild.id)) as warning_cursor:
                                warning_count = (await warning_cursor.fetchone())[0]
                                if warning_count > 0:
                                    embed.add_field(
                                        name="Verwarnungen", 
                                        value=f"Der User hatte {warning_count} Verwarnung(en)",
                                        inline=False
                                    )
                            
                            await log_channel.send(embed=embed)

            # Bestätigung senden
            await ctx.send(f"✅ {member} wurde vom Server gekickt!")

        except discord.Forbidden:
            await ctx.send("❌ Ich habe keine Berechtigung, diesen User zu kicken!")
        except Exception as e:
            print(f"Fehler beim Kicken: {e}")
            await ctx.send("❌ Es ist ein Fehler aufgetreten!")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, user_input: str = None, *, reason=None):
        """Bannt ein Mitglied vom Server"""
        if not user_input:
            embed = discord.Embed(
                title="🔨 Ban Befehl",
                description="Bannt einen User vom Server.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="Verwendung",
                value="!ban @User/ID/Name [Grund]\n"
                      "Beispiel: !ban @User Schwerer Regelverstoß"
            )
            await ctx.send(embed=embed)
            return

        member = await self.get_member(ctx, user_input)
        if member is None:
            await ctx.send(f"❌ Konnte keinen User finden für: {user_input}")
            return

        try:
            # Erstelle Embed für Log
            embed = discord.Embed(
                title="🔨 Ban",
                description=f"{member.mention} wurde vom Server gebannt.",
                color=discord.Color.dark_red()
            )
            embed.add_field(name="User", value=f"{member.name}#{member.discriminator}")
            embed.add_field(name="ID", value=member.id)
            embed.add_field(name="Grund", value=reason or "Kein Grund angegeben")

            # Sende Benachrichtigungen
            await self.send_mod_action_messages(
                ctx, 
                member, 
                "Ban", 
                embed,
                reason=reason
            )

            # Führe Ban durch
            await member.ban(reason=reason)

            # Speichere in Datenbank
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute('''
                    INSERT INTO bans (
                        user_id,
                        user_name,
                        guild_id,
                        moderator_id,
                        moderator_name,
                        reason,
                        is_temporary
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    member.id,
                    f"{member.name}#{member.discriminator}",
                    ctx.guild.id,
                    ctx.author.id,
                    f"{ctx.author.name}#{ctx.author.discriminator}",
                    reason,
                    False
                ))
                await db.commit()

            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("❌ Ich habe keine Berechtigung, diesen User zu bannen!")
        except discord.HTTPException as e:
            await ctx.send(f"❌ Es gab einen Fehler beim Bannen: {str(e)}")

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def modlogs(self, ctx, user: discord.Member):
        """Zeigt alle Moderationsaktionen für einen User"""
        async with aiosqlite.connect(DB_PATH) as db:
            embed = discord.Embed(
                title=f"📋 Moderations-Log für {user.name}",
                color=discord.Color.blue()
            )

            # Warnungen abrufen
            async with db.execute('''
                SELECT reason, moderator_name, timestamp 
                FROM warnings 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY timestamp DESC
            ''', (user.id, ctx.guild.id)) as cursor:
                warnings = await cursor.fetchall()
                if warnings:
                    warns_text = ""
                    for reason, mod, time in warnings:
                        warns_text += f"• {time} von {mod}: {reason or 'Kein Grund'}\n"
                    embed.add_field(name="⚠️ Verwarnungen", value=warns_text, inline=False)

            # Timeouts abrufen
            async with db.execute('''
                SELECT reason, moderator_name, duration_minutes, timestamp 
                FROM timeouts 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY timestamp DESC
            ''', (user.id, ctx.guild.id)) as cursor:
                timeouts = await cursor.fetchall()
                if timeouts:
                    timeouts_text = ""
                    for reason, mod, duration, time in timeouts:
                        timeouts_text += f"• {time} von {mod} für {duration}min: {reason or 'Kein Grund'}\n"
                    embed.add_field(name="🔇 Timeouts", value=timeouts_text, inline=False)

            # Kicks abrufen
            async with db.execute('''
                SELECT reason, moderator_name, timestamp 
                FROM kicks 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY timestamp DESC
            ''', (user.id, ctx.guild.id)) as cursor:
                kicks = await cursor.fetchall()
                if kicks:
                    kicks_text = ""
                    for reason, mod, time in kicks:
                        kicks_text += f"• {time} von {mod}: {reason or 'Kein Grund'}\n"
                    embed.add_field(name="👢 Kicks", value=kicks_text, inline=False)

            # Bans abrufen
            async with db.execute('''
                SELECT reason, moderator_name, timestamp 
                FROM bans 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY timestamp DESC
            ''', (user.id, ctx.guild.id)) as cursor:
                bans = await cursor.fetchall()
                if bans:
                    bans_text = ""
                    for reason, mod, time in bans:
                        bans_text += f"• {time} von {mod}: {reason or 'Kein Grund'}\n"
                    embed.add_field(name="🔨 Bans", value=bans_text, inline=False)

            if not any([warnings, timeouts, kicks, bans]):
                embed.description = "Keine Moderationsaktionen gefunden."

            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addfilter(self, ctx, filter_type: str, *, word: str):
        """Fügt ein Wort oder einen Link zum Filter hinzu"""
        if filter_type not in ['word', 'link']:
            await ctx.send("Filter-Typ muss 'word' oder 'link' sein!")
            return

        if filter_type == 'word':
            self.automod.banned_words.append(word)
        else:
            self.automod.banned_links.append(word)

        # Speichere aktualisierte Filter
        with open('data/word_filters.json', 'w') as f:
            json.dump({
                "banned_words": self.automod.banned_words,
                "banned_links": self.automod.banned_links
            }, f, indent=4)

        await ctx.send(f"{filter_type.capitalize()} wurde zum Filter hinzugefügt!")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def viewlogs(self, ctx, limit: int = 10):
        """Zeigt die letzten Moderations-Logs"""
        if ctx.guild.id not in self.logger.log_channels:
            await ctx.send("Es wurde noch kein Logging-Kanal eingerichtet!")
            return

        channel = self.bot.get_channel(self.logger.log_channels[ctx.guild.id])
        if not channel:
            await ctx.send("Der Logging-Kanal wurde nicht gefunden!")
            return

        messages = []
        async for message in channel.history(limit=limit):
            if message.embeds:
                messages.append(message.embeds[0])

        if not messages:
            await ctx.send("Keine Logs gefunden!")
            return

        for embed in messages:
            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def activetimeouts(self, ctx):
        """Zeigt alle aktiven Timeouts auf dem Server"""
        async with aiosqlite.connect(DB_PATH) as db:
            # Zeige aktive Timeouts auf dem Server
            now = datetime.datetime.now().isoformat()
            async with db.execute('''
                SELECT user_name, reason, moderator_name, expires_at 
                FROM timeouts 
                WHERE guild_id = ? AND expires_at > ?
                ORDER BY expires_at ASC
            ''', (ctx.guild.id, now)) as cursor:
                active_timeouts = await cursor.fetchall()

            if not active_timeouts:
                await ctx.send("Es gibt derzeit keine aktiven Timeouts.")
                return

            embed = discord.Embed(
                title="🔇 Aktive Timeouts",
                color=discord.Color.orange()
            )

            for timeout in active_timeouts:
                user_name, reason, mod_name, expires = timeout
                embed.add_field(
                    name=f"Timeout für {user_name}",
                    value=f"**Grund:** {reason or 'Kein Grund angegeben'}\n"
                          f"**Moderator:** {mod_name}\n"
                          f"**Läuft ab:** {expires}",
                    inline=False
                )

            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def timeouts(self, ctx, user: discord.Member):
        """Zeigt die Timeout-Historie eines Users"""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute('''
                SELECT reason, moderator_name, duration_minutes, timestamp, expires_at 
                FROM timeouts 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY timestamp DESC LIMIT 10
            ''', (user.id, ctx.guild.id)) as cursor:
                timeouts = await cursor.fetchall()

            if not timeouts:
                await ctx.send(f"{user.mention} hatte bisher keine Timeouts.")
                return

            embed = discord.Embed(
                title=f"🔇 Timeout-Historie für {user.name}",
                color=discord.Color.orange()
            )

            for timeout in timeouts:
                reason, mod_name, duration, timestamp, expires = timeout
                embed.add_field(
                    name=f"Timeout vom {timestamp}",
                    value=f"**Grund:** {reason or 'Kein Grund angegeben'}\n"
                          f"**Moderator:** {mod_name}\n"
                          f"**Dauer:** {duration} Minuten\n"
                          f"**Abgelaufen:** {expires}",
                    inline=False
                )

            await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setmodlog(self, ctx, channel: discord.TextChannel):
        """Setzt den Kanal für Moderations-Logs"""
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO channel_config 
                    (guild_id, mod_log_channel_id) 
                    VALUES (?, ?)
                ''', (ctx.guild.id, channel.id))
                await db.commit()
            
            await ctx.send(f"✅ Mod-Log Kanal wurde auf {channel.mention} gesetzt!")
        except Exception as e:
            print(f"Fehler beim Setzen des Mod-Log Kanals: {e}")
            await ctx.send("❌ Es ist ein Fehler aufgetreten!")

async def setup(bot):
    await bot.add_cog(ModerationCommands(bot)) 