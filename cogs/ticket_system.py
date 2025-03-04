import discord
from discord.ext import commands
import sys
import os
import datetime
import asyncio
from typing import Optional, Union

# Pfad zum Hauptverzeichnis hinzufügen, um utils zu importieren
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.db import Database
from utils.permissions import is_admin

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.ticket_categories = {}  # Cache für Ticket-Kategorien pro Server
        self.support_roles = {}      # Cache für Support-Rollen pro Server
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.initialize_database()
        print("✅ Ticket-System bereit!")
    
    async def initialize_database(self):
        """Initialisiert die Datenbanktabellen für das Ticket-System"""
        try:
            # Tabelle für Ticket-Konfiguration
            await self.db.execute('''
            CREATE TABLE IF NOT EXISTS ticket_config (
                guild_id TEXT PRIMARY KEY,
                category_id TEXT,
                log_channel_id TEXT,
                support_role_id TEXT,
                ticket_counter INTEGER DEFAULT 0,
                archive_category_id TEXT,
                enabled BOOLEAN DEFAULT 0,
                welcome_message TEXT DEFAULT 'Willkommen beim Support! Beschreibe dein Anliegen so detailliert wie möglich.'
            )
            ''')
            
            # Tabelle für Tickets
            await self.db.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                guild_id TEXT,
                channel_id TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                closed_by TEXT,
                status TEXT DEFAULT 'open',
                title TEXT,
                archived BOOLEAN DEFAULT 0
            )
            ''')
            
            print("✅ Ticket-System-Datenbanktabellen initialisiert")
        except Exception as e:
            print(f"❌ Fehler bei der Initialisierung der Ticket-System-Datenbanktabellen: {e}")
    
    @commands.group(name="ticket", invoke_without_command=True)
    async def ticket_cmd(self, ctx):
        """Ticket-System Befehle"""
        embed = discord.Embed(
            title="🎫 Ticket-System",
            description="Folgende Befehle sind verfügbar:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Nutzer-Befehle", 
            value="`!ticket create [titel]` - Erstellt ein neues Support-Ticket\n"
                  "`!ticket close [grund]` - Schließt ein aktuelles Ticket\n"
                  "`!ticket add @User` - Fügt einen Nutzer zum Ticket hinzu\n"
                  "`!ticket remove @User` - Entfernt einen Nutzer aus dem Ticket\n"
                  "`!ticket transcript` - Erstellt eine Textdatei mit allen Nachrichten",
            inline=False
        )
        
        embed.add_field(
            name="Admin-Befehle",
            value="`!ticket setup` - Richtet das Ticket-System ein\n"
                  "`!ticket category #kategorie` - Legt die Kategorie für Tickets fest\n"
                  "`!ticket role @rolle` - Legt die Support-Rolle fest\n"
                  "`!ticket log #kanal` - Legt den Log-Kanal fest\n"
                  "`!ticket archive` - Aktiviert Archivierung von Tickets\n"
                  "`!ticket message <nachricht>` - Legt die Willkommensnachricht fest\n"
                  "`!ticket panel #kanal` - Erstellt ein Ticket-Panel in einem Kanal\n"
                  "`!ticket list [status]` - Listet alle Tickets auf\n"
                  "`!ticket stats` - Zeigt Statistiken zum Ticket-System an",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @ticket_cmd.command(name="setup")
    @is_admin()
    async def setup_ticket_system(self, ctx):
        """Richtet das Ticket-System für den Server ein"""
        try:
            # Prüfe, ob bereits eine Konfiguration existiert
            config = await self.db.fetch_one(
                "SELECT enabled FROM ticket_config WHERE guild_id = ?",
                (str(ctx.guild.id),)
            )
            
            if config:
                return await ctx.send("⚠️ Das Ticket-System ist bereits eingerichtet. Verwende die einzelnen Befehle, um die Einstellungen zu ändern.")
            
            # Erstelle eine neue Kategorie für Tickets
            category = await ctx.guild.create_category("Support-Tickets")
            
            # Setze Berechtigungen für die Kategorie
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            await category.edit(overwrites=overwrites)
            
            # Erstelle einen Log-Kanal
            log_channel = await ctx.guild.create_text_channel(
                name="ticket-logs",
                category=category,
                overwrites=overwrites,
                topic="Log-Kanal für das Ticket-System"
            )
            
            # Füge Konfiguration in die Datenbank ein
            await self.db.execute(
                """INSERT INTO ticket_config 
                (guild_id, category_id, log_channel_id, ticket_counter, enabled) 
                VALUES (?, ?, ?, ?, ?)""",
                (str(ctx.guild.id), str(category.id), str(log_channel.id), 0, 1)
            )
            
            embed = discord.Embed(
                title="✅ Ticket-System eingerichtet",
                description="Das Ticket-System wurde erfolgreich eingerichtet.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Nächste Schritte",
                value="1. Setze eine Support-Rolle mit `!ticket role @rolle`\n"
                     "2. Erstelle ein Ticket-Panel mit `!ticket panel #kanal`\n"
                     "3. Passe die Willkommensnachricht mit `!ticket message <nachricht>` an",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # Logge die Einrichtung
            await self.log_ticket_action(
                ctx.guild,
                "Ticket-System eingerichtet",
                f"Das Ticket-System wurde von {ctx.author.mention} eingerichtet.",
                ctx.author
            )
            
        except Exception as e:
            await ctx.send(f"❌ Fehler beim Einrichten des Ticket-Systems: {e}")
    
    @ticket_cmd.command(name="category")
    @is_admin()
    async def set_ticket_category(self, ctx, category: discord.CategoryChannel):
        """Legt die Kategorie für Tickets fest"""
        await self.db.execute(
            "UPDATE ticket_config SET category_id = ? WHERE guild_id = ?",
            (str(category.id), str(ctx.guild.id))
        )
        self.ticket_categories[ctx.guild.id] = category.id
        await ctx.send(f"✅ Ticket-Kategorie wurde auf **{category.name}** gesetzt!")
    
    @ticket_cmd.command(name="role")
    @is_admin()
    async def set_support_role(self, ctx, role: discord.Role = None):
        """Legt die Support-Rolle für das Ticket-System fest"""
        if not role:
            return await ctx.send("❌ Bitte gib eine Rolle an!")
        
        try:
            # Prüfe, ob Konfiguration existiert
            config = await self.db.fetch_one(
                "SELECT enabled FROM ticket_config WHERE guild_id = ?",
                (str(ctx.guild.id),)
            )
            
            if not config:
                return await ctx.send("❌ Das Ticket-System ist noch nicht eingerichtet. Verwende `!ticket setup` zuerst.")
            
            # Aktualisiere Support-Rolle
            await self.db.execute(
                "UPDATE ticket_config SET support_role_id = ? WHERE guild_id = ?",
                (str(role.id), str(ctx.guild.id))
            )
            
            # Aktualisiere Cache
            self.support_roles[ctx.guild.id] = str(role.id)
            
            await ctx.send(f"✅ Support-Rolle wurde auf {role.mention} gesetzt.")
            
            # Logge die Änderung
            await self.log_ticket_action(
                ctx.guild,
                "Support-Rolle aktualisiert",
                f"Die Support-Rolle wurde von {ctx.author.mention} auf {role.mention} gesetzt.",
                ctx.author
            )
            
        except Exception as e:
            await ctx.send(f"❌ Fehler beim Setzen der Support-Rolle: {e}")
    
    @ticket_cmd.command(name="log")
    @is_admin()
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        """Legt den Log-Kanal fest"""
        await self.db.execute(
            "UPDATE ticket_config SET log_channel_id = ? WHERE guild_id = ?",
            (str(channel.id), str(ctx.guild.id))
        )
        await ctx.send(f"✅ Log-Kanal wurde auf {channel.mention} gesetzt!")
    
    @ticket_cmd.command(name="archive")
    @is_admin()
    async def setup_archive(self, ctx, category: Optional[discord.CategoryChannel] = None):
        """Richtet die Archiv-Kategorie ein"""
        if not category:
            # Erstelle eine neue Kategorie
            category = await ctx.guild.create_category("Archivierte Tickets")
            await category.set_permissions(ctx.guild.default_role, read_messages=False)
            
            # Support-Rolle kann Archiv nur lesen
            support_role_id = await self.get_support_role_id(ctx.guild.id)
            if support_role_id:
                support_role = ctx.guild.get_role(int(support_role_id))
                if support_role:
                    await category.set_permissions(
                        support_role, read_messages=True, send_messages=False
                    )
        
        await self.db.execute(
            "UPDATE ticket_config SET archive_category_id = ? WHERE guild_id = ?",
            (str(category.id), str(ctx.guild.id))
        )
        await ctx.send(f"✅ Archiv-Kategorie wurde auf **{category.name}** gesetzt!")
    
    @ticket_cmd.command(name="message")
    @is_admin()
    async def set_welcome_message(self, ctx, *, message: str):
        """Legt die Willkommensnachricht für Tickets fest"""
        await self.db.execute(
            "UPDATE ticket_config SET welcome_message = ? WHERE guild_id = ?",
            (message, str(ctx.guild.id))
        )
        await ctx.send(f"✅ Willkommensnachricht für Tickets wurde aktualisiert!")
    
    @ticket_cmd.command(name="panel")
    @is_admin()
    async def create_ticket_panel(self, ctx, channel: discord.TextChannel = None):
        """Erstellt ein Ticket-Panel in einem Kanal"""
        if not channel:
            channel = ctx.channel
        
        try:
            # Prüfe, ob Konfiguration existiert
            config = await self.db.fetch_one(
                "SELECT enabled, support_role_id FROM ticket_config WHERE guild_id = ?",
                (str(ctx.guild.id),)
            )
            
            if not config or not config[0]:
                return await ctx.send("❌ Das Ticket-System ist noch nicht eingerichtet. Verwende `!ticket setup` zuerst.")
            
            if not config[1]:
                return await ctx.send("❌ Es wurde noch keine Support-Rolle festgelegt. Verwende `!ticket role @rolle` zuerst.")
            
            # Erstelle Embed für das Panel
            embed = discord.Embed(
                title="🎫 Support-Ticket erstellen",
                description="Klicke auf den Button unten, um ein Support-Ticket zu erstellen.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Wofür sind Tickets?",
                value="- Hilfe bei Problemen\n"
                     "- Melden von Regelverstößen\n"
                     "- Fragen an das Server-Team\n"
                     "- Sonstige Anliegen",
                inline=False
            )
            
            # Erstelle Button-View
            view = TicketPanelView(self)
            
            # Sende Panel direkt in den Kanal
            await channel.send(embed=embed, view=view)
            await ctx.send(f"✅ Ticket-Panel wurde in {channel.mention} erstellt.")
            
        except Exception as e:
            await ctx.send(f"❌ Fehler beim Erstellen des Ticket-Panels: {e}")
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        """Behandelt Interaktionen mit dem Ticket-Button"""
        # Diese Methode entfernen oder deaktivieren, da wir bereits einen Button-Handler haben
        # Wenn wir die Methode behalten wollen, müssen wir prüfen, ob die Interaktion 
        # nicht von einer View stammt
        
        # Prüfe, ob die Interaktion von einer View stammt (hat component_type)
        if hasattr(interaction, 'data') and interaction.data.get('component_type') is not None:
            # Diese Interaktionen werden bereits durch die Views verarbeitet
            return
        
        # Nur alte Custom-ID-Interaktionen ohne View verarbeiten
        if not interaction.type == discord.InteractionType.component:
            return
        
        if interaction.data.get("custom_id") == "create_ticket":
            try:
                await interaction.response.send_modal(
                    TicketModal(cog=self, title="Support-Ticket erstellen")
                )
            except discord.errors.HTTPException as e:
                if "already been acknowledged" not in str(e):
                    # Nur Fehler loggen, die nicht mit bereits bestätigten Interaktionen zu tun haben
                    print(f"Fehler bei Interaktion: {e}")
    
    @ticket_cmd.command(name="create")
    async def create_ticket(self, ctx, *, title: str = "Kein Titel angegeben"):
        """Erstellt ein neues Support-Ticket"""
        await self.create_ticket_for_user(ctx.guild, ctx.author, title, ctx)
    
    async def create_ticket_for_user(self, guild, user, title, ctx=None, interaction=None):
        """Erstellt ein neues Ticket für einen Benutzer"""
        try:
            # Überprüfe Konfiguration
            config = await self.db.fetch_one(
                "SELECT category_id, support_role_id, ticket_counter, welcome_message, enabled FROM ticket_config WHERE guild_id = ?", 
                (str(guild.id),)
            )
            
            if not config or not config[4]:  # enabled prüfen
                response = "❌ Das Ticket-System ist für diesen Server nicht aktiviert!"
                return await self.respond(ctx, interaction, response)
            
            category_id, support_role_id, counter, welcome_msg, _ = config
            category = guild.get_channel(int(category_id))
            support_role = guild.get_role(int(support_role_id))
            
            if not category or not support_role:
                response = "❌ Ticket-Kategorie oder Support-Rolle nicht gefunden!"
                return await self.respond(ctx, interaction, response)
            
            # Prüfe, ob der Benutzer bereits ein offenes Ticket hat
            existing_ticket = await self.db.fetch_one(
                "SELECT channel_id FROM tickets WHERE guild_id = ? AND user_id = ? AND status = 'open'",
                (str(guild.id), str(user.id))
            )
            
            if existing_ticket:
                channel = guild.get_channel(int(existing_ticket[0]))
                if channel:
                    response = f"❌ Du hast bereits ein offenes Ticket: {channel.mention}!"
                    return await self.respond(ctx, interaction, response)
            
            # Erhöhe Ticket-Zähler
            counter += 1
            await self.db.execute(
                "UPDATE ticket_config SET ticket_counter = ? WHERE guild_id = ?",
                (counter, str(guild.id))
            )
            
            # Erstelle Ticket-ID
            ticket_id = f"{counter:04d}"
            
            # Erstelle Ticket-Kanal
            channel_name = f"ticket-{ticket_id}"
            
            # Erstelle Übersichtsembed für den Kanal
            embed = discord.Embed(
                title=f"Ticket #{ticket_id}: {title}",
                description=welcome_msg,
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            
            embed.add_field(name="Erstellt von", value=user.mention, inline=True)
            embed.add_field(name="Ticket-ID", value=ticket_id, inline=True)
            
            embed.set_footer(text=f"Verwende !ticket close um das Ticket zu schließen")
            
            # Erstelle den Kanal mit Berechtigungen
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Support-Ticket für {user.name} | ID: {ticket_id}"
            )
            
            # Sende Willkommensnachricht
            view = TicketControlPanel(self)
            first_message = await channel.send(
                content=f"{user.mention} {support_role.mention}",
                embed=embed,
                view=view
            )
            await first_message.pin()
            
            # Speichere Ticket in Datenbank
            await self.db.execute(
                """INSERT INTO tickets 
                (ticket_id, guild_id, channel_id, user_id, title, status) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (ticket_id, str(guild.id), str(channel.id), str(user.id), title, "open")
            )
            
            # Logge Ticket-Erstellung
            await self.log_ticket_action(
                guild, 
                f"Ticket #{ticket_id} erstellt", 
                f"Nutzer: {user.mention}\nTitel: {title}",
                user
            )
            
            response = f"✅ Dein Ticket wurde erstellt: {channel.mention}"
            await self.respond(ctx, interaction, response)
            
        except Exception as e:
            response = f"❌ Fehler beim Erstellen des Tickets: {e}"
            await self.respond(ctx, interaction, response)
    
    @ticket_cmd.command(name="close")
    async def close_ticket(self, ctx, *, reason: str = "Kein Grund angegeben"):
        """Schließt ein Ticket"""
        # Prüfe, ob der Kanal ein Ticket ist
        ticket = await self.db.fetch_one(
            "SELECT ticket_id, user_id FROM tickets WHERE channel_id = ? AND status = 'open'",
            (str(ctx.channel.id),)
        )
        
        if not ticket:
            return await ctx.send("❌ Dieser Kanal ist kein offenes Ticket!")
        
        ticket_id, user_id = ticket
        
        # Prüfe Berechtigung (entweder Ersteller, Support oder Admin)
        is_creator = str(ctx.author.id) == user_id
        is_support = await self.is_support(ctx.author)
        
        if not (is_creator or is_support):
            return await ctx.send("❌ Du hast keine Berechtigung, dieses Ticket zu schließen!")
        
        # Bestätigungsnachricht
        embed = discord.Embed(
            title="Ticket schließen",
            description=f"Möchtest du das Ticket #{ticket_id} wirklich schließen?\n\n"
                       f"Grund: {reason}",
            color=discord.Color.orange()
        )
        
        # Erstelle View mit Bestätigungsbuttons
        view = TicketCloseConfirm(self, ticket_id, reason, ctx.author)
        await ctx.send(embed=embed, view=view)
    
    async def close_ticket_confirmed(self, interaction, ticket_id, reason, closer):
        """Führt die eigentliche Ticket-Schließung aus"""
        guild = interaction.guild
        channel = interaction.channel
        
        # Updatee Ticket-Status in der Datenbank
        await self.db.execute(
            """UPDATE tickets 
            SET status = 'closed', closed_at = CURRENT_TIMESTAMP, closed_by = ? 
            WHERE ticket_id = ? AND guild_id = ?""",
            (str(closer.id), ticket_id, str(guild.id))
        )
        
        # Erstelle Abschluss-Embed
        embed = discord.Embed(
            title=f"Ticket #{ticket_id} geschlossen",
            description=f"Dieses Ticket wurde geschlossen.\n\n"
                       f"**Grund:** {reason}\n"
                       f"**Geschlossen von:** {closer.mention}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        
        # Füge Archivierungs-Option hinzu
        view = TicketArchiveView(self, ticket_id)
        
        try:
            await interaction.response.edit_message(content="Ticket wird geschlossen...", view=None)
        except:
            pass
        
        await channel.send(embed=embed, view=view)
        
        # Entferne Schreibrechte vom Ticketersteller
        ticket_data = await self.db.fetch_one(
            "SELECT user_id FROM tickets WHERE ticket_id = ?", 
            (ticket_id,)
        )
        
        if ticket_data:
            user_id = int(ticket_data[0])
            user = guild.get_member(user_id)
            
            if user:
                await channel.set_permissions(user, send_messages=False)
        
        # Logge Ticket-Schließung
        await self.log_ticket_action(
            guild, 
            f"Ticket #{ticket_id} geschlossen", 
            f"Geschlossen von: {closer.mention}\nGrund: {reason}",
            closer
        )
    
    async def archive_ticket(self, interaction, ticket_id):
        """Archiviert ein geschlossenes Ticket"""
        try:
            guild = interaction.guild
            channel = interaction.channel
            
            # Hole Archiv-Kategorie
            config = await self.db.fetch_one(
                "SELECT archive_category_id FROM ticket_config WHERE guild_id = ?", 
                (str(guild.id),)
            )
            
            if not config or not config[0]:
                return await interaction.response.send_message(
                    "❌ Es wurde keine Archiv-Kategorie eingerichtet!", ephemeral=True
                )
            
            archive_category = guild.get_channel(int(config[0]))
            if not archive_category:
                return await interaction.response.send_message(
                    "❌ Die Archiv-Kategorie wurde nicht gefunden!", ephemeral=True
                )
            
            # Verschiebe Kanal in Archiv-Kategorie
            await channel.edit(
                category=archive_category,
                sync_permissions=True
            )
            
            # Updatee Ticket-Status in der Datenbank
            await self.db.execute(
                "UPDATE tickets SET archived = 1 WHERE ticket_id = ? AND guild_id = ?",
                (ticket_id, str(guild.id))
            )
            
            # Sende Bestätigung
            await interaction.response.send_message(
                "✅ Ticket wurde archiviert!", ephemeral=True
            )
            
            # Logge Archivierung
            await self.log_ticket_action(
                guild, 
                f"Ticket #{ticket_id} archiviert", 
                f"Archiviert von: {interaction.user.mention}",
                interaction.user
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Fehler beim Archivieren: {e}", ephemeral=True
            )
    
    async def delete_ticket(self, interaction, ticket_id):
        """Löscht ein Ticket komplett"""
        try:
            guild = interaction.guild
            channel = interaction.channel
            
            # Sende Bestätigung, dass der Kanal gelöscht wird
            await interaction.response.send_message(
                "✅ Ticket wird gelöscht...", ephemeral=True
            )
            
            # Logge Löschung
            await self.log_ticket_action(
                guild, 
                f"Ticket #{ticket_id} gelöscht", 
                f"Gelöscht von: {interaction.user.mention}",
                interaction.user
            )
            
            # Ticket aus Datenbank löschen
            await self.db.execute(
                "DELETE FROM tickets WHERE ticket_id = ? AND guild_id = ?",
                (ticket_id, str(guild.id))
            )
            
            # Wartezeit für die Benutzer, um die Nachricht zu lesen
            await asyncio.sleep(3)
            
            # Kanal löschen
            await channel.delete(reason=f"Ticket #{ticket_id} gelöscht von {interaction.user}")
            
        except Exception as e:
            # Falls die Löschung fehlschlägt, versuche eine Nachricht zu senden
            try:
                await interaction.followup.send(
                    f"❌ Fehler beim Löschen: {e}", ephemeral=True
                )
            except:
                pass
    
    @ticket_cmd.command(name="add")
    async def add_user_to_ticket(self, ctx, user: discord.Member):
        """Fügt einen Benutzer zu einem Ticket hinzu"""
        # Prüfe, ob der Kanal ein Ticket ist
        ticket = await self.db.fetch_one(
            "SELECT ticket_id, user_id FROM tickets WHERE channel_id = ? AND status = 'open'",
            (str(ctx.channel.id),)
        )
        
        if not ticket:
            return await ctx.send("❌ Dieser Kanal ist kein offenes Ticket!")
        
        ticket_id, creator_id = ticket
        
        # Prüfe Berechtigung (entweder Ersteller oder Support)
        is_creator = str(ctx.author.id) == creator_id
        is_support = await self.is_support(ctx.author)
        
        if not (is_creator or is_support):
            return await ctx.send("❌ Du hast keine Berechtigung, Benutzer hinzuzufügen!")
        
        # Füge Benutzer zum Ticket hinzu
        await ctx.channel.set_permissions(user, read_messages=True, send_messages=True)
        
        # Sende Nachricht im Kanal
        embed = discord.Embed(
            title="Benutzer hinzugefügt",
            description=f"{user.mention} wurde zum Ticket hinzugefügt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        
        # Logge Aktion
        await self.log_ticket_action(
            ctx.guild, 
            f"Benutzer zu Ticket #{ticket_id} hinzugefügt", 
            f"Hinzugefügt: {user.mention}\nVon: {ctx.author.mention}",
            ctx.author
        )
    
    @ticket_cmd.command(name="remove")
    async def remove_user_from_ticket(self, ctx, user: discord.Member):
        """Entfernt einen Benutzer aus einem Ticket"""
        # Prüfe, ob der Kanal ein Ticket ist
        ticket = await self.db.fetch_one(
            "SELECT ticket_id, user_id FROM tickets WHERE channel_id = ? AND status = 'open'",
            (str(ctx.channel.id),)
        )
        
        if not ticket:
            return await ctx.send("❌ Dieser Kanal ist kein offenes Ticket!")
        
        ticket_id, creator_id = ticket
        
        # Verhindere Entfernung des Ticketerstellers
        if str(user.id) == creator_id:
            return await ctx.send("❌ Der Ersteller des Tickets kann nicht entfernt werden!")
        
        # Prüfe Berechtigung (entweder Ersteller oder Support)
        is_creator = str(ctx.author.id) == creator_id
        is_support = await self.is_support(ctx.author)
        
        if not (is_creator or is_support):
            return await ctx.send("❌ Du hast keine Berechtigung, Benutzer zu entfernen!")
        
        # Verhindere Entfernung von Support-Mitarbeitern durch den Ersteller
        if is_creator and not is_support and await self.is_support(user):
            return await ctx.send("❌ Du kannst keine Support-Mitarbeiter entfernen!")
        
        # Entferne Benutzer aus dem Ticket
        await ctx.channel.set_permissions(user, overwrite=None)
        
        # Sende Nachricht im Kanal
        embed = discord.Embed(
            title="Benutzer entfernt",
            description=f"{user.mention} wurde aus dem Ticket entfernt.",
            color=discord.Color.red()
        )
        
        await ctx.send(embed=embed)
        
        # Logge Aktion
        await self.log_ticket_action(
            ctx.guild, 
            f"Benutzer aus Ticket #{ticket_id} entfernt", 
            f"Entfernt: {user.mention}\nVon: {ctx.author.mention}",
            ctx.author
        )
    
    @ticket_cmd.command(name="list")
    @commands.has_permissions(manage_messages=True)
    async def list_tickets(self, ctx, status: str = "all"):
        """Listet alle aktiven Tickets auf"""
        status_filter = ""
        if status.lower() == "open":
            status_filter = "WHERE status = 'open'"
        elif status.lower() == "closed":
            status_filter = "WHERE status = 'closed'"
        
        tickets = await self.db.fetch_all(
            f"SELECT ticket_id, channel_id, user_id, title, created_at, status FROM tickets {status_filter} AND guild_id = ? ORDER BY created_at DESC LIMIT 25",
            (str(ctx.guild.id),)
        )
        
        if not tickets:
            return await ctx.send(f"❌ Keine {status} Tickets gefunden!")
        
        embed = discord.Embed(
            title=f"📋 {status.title()} Tickets",
            color=discord.Color.blue(),
            description=f"Es wurden {len(tickets)} Tickets gefunden:"
        )
        
        for ticket in tickets:
            ticket_id, channel_id, user_id, title, created_at, status = ticket
            
            channel = ctx.guild.get_channel(int(channel_id))
            channel_txt = f"{channel.mention}" if channel else "Kanal gelöscht"
            
            user = ctx.guild.get_member(int(user_id))
            user_txt = f"{user.mention}" if user else f"Nutzer nicht mehr auf dem Server (ID: {user_id})"
            
            embed.add_field(
                name=f"#{ticket_id}: {title}",
                value=f"Status: **{status}**\n"
                     f"Ersteller: {user_txt}\n"
                     f"Kanal: {channel_txt}\n"
                     f"Erstellt: <t:{int(datetime.datetime.fromisoformat(created_at).timestamp())}:R>",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @ticket_cmd.command(name="transcript")
    @commands.has_permissions(manage_messages=True)
    async def create_transcript(self, ctx, ticket_id: str = None, return_file: bool = False, interaction = None):
        """Erstellt ein Transcript eines Tickets"""
        # Falls kein ticket_id angegeben wurde, aktuelle Kanal-ID verwenden
        if not ticket_id:
            ticket = await self.db.fetch_one(
                "SELECT ticket_id FROM tickets WHERE channel_id = ?",
                (str(ctx.channel.id if ctx else interaction.channel.id),)
            )
            
            if not ticket:
                if return_file:
                    return None
                return await ctx.send("❌ Dieser Kanal ist kein Ticket!")
            
            ticket_id = ticket[0]
        
        # Prüfe, ob Ticket existiert
        guild_id = str(ctx.guild.id if ctx else interaction.guild.id)
        ticket_data = await self.db.fetch_one(
            "SELECT channel_id FROM tickets WHERE ticket_id = ? AND guild_id = ?",
            (ticket_id, guild_id)
        )
        
        if not ticket_data:
            if return_file:
                return None
            return await ctx.send(f"❌ Ticket #{ticket_id} wurde nicht gefunden!")
        
        channel_id = ticket_data[0]
        guild = ctx.guild if ctx else interaction.guild
        channel = guild.get_channel(int(channel_id))
        
        if not channel:
            if return_file:
                return None
            return await ctx.send(f"❌ Der Kanal für Ticket #{ticket_id} existiert nicht mehr!")
        
        # Sende Bestätigung, wenn nicht im return_file Modus
        if not return_file and ctx:
            await ctx.send("📝 Erstelle Transcript... Dies kann einen Moment dauern.")
        
        # Sammle alle Nachrichten im Kanal
        transcript = f"# Transcript für Ticket #{ticket_id}\n"
        transcript += f"Erstellt am: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
        
        async for message in channel.history(limit=500, oldest_first=True):
            timestamp = message.created_at.strftime('%d.%m.%Y %H:%M:%S')
            transcript += f"[{timestamp}] {message.author.name}:\n"
            
            if message.content:
                transcript += f"{message.content}\n"
            
            for embed in message.embeds:
                if embed.title:
                    transcript += f"[Embed: {embed.title}]\n"
            
            for attachment in message.attachments:
                transcript += f"[Anhang: {attachment.url}]\n"
            
            transcript += "\n"
        
        # Speichere Transcript als Datei
        file_name = f"ticket-{ticket_id}-transcript.txt"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(transcript)
        
        # Erstelle Discord-Datei
        discord_file = discord.File(file_name)
        
        # Wenn im return_file Modus, gib die Datei zurück
        if return_file:
            import os
            os.remove(file_name)  # Lösche temporäre Datei
            return discord_file
        
        # Sende Transcript
        if ctx:
            await ctx.send(f"✅ Transcript für Ticket #{ticket_id} erstellt:", file=discord_file)
        
        # Lösche temporäre Datei
        import os
        os.remove(file_name)
        
        return None
    
    @ticket_cmd.command(name="stats")
    @is_admin()
    async def ticket_stats(self, ctx):
        """Zeigt Statistiken zum Ticket-System"""
        # Sammle Statistiken aus der Datenbank
        stats = {}
        
        # Gesamtzahl der Tickets
        total = await self.db.fetch_one(
            "SELECT COUNT(*) FROM tickets WHERE guild_id = ?",
            (str(ctx.guild.id),)
        )
        stats["total"] = total[0] if total else 0
        
        # Offene Tickets
        open_tickets = await self.db.fetch_one(
            "SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND status = 'open'",
            (str(ctx.guild.id),)
        )
        stats["open"] = open_tickets[0] if open_tickets else 0
        
        # Geschlossene Tickets
        closed_tickets = await self.db.fetch_one(
            "SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND status = 'closed'",
            (str(ctx.guild.id),)
        )
        stats["closed"] = closed_tickets[0] if closed_tickets else 0
        
        # Archivierte Tickets
        archived_tickets = await self.db.fetch_one(
            "SELECT COUNT(*) FROM tickets WHERE guild_id = ? AND archived = 1",
            (str(ctx.guild.id),)
        )
        stats["archived"] = archived_tickets[0] if archived_tickets else 0
        
        # Top Support-Mitarbeiter
        top_support = await self.db.fetch_all(
            """SELECT closed_by, COUNT(*) as count 
            FROM tickets 
            WHERE guild_id = ? AND closed_by IS NOT NULL 
            GROUP BY closed_by 
            ORDER BY count DESC LIMIT 5""",
            (str(ctx.guild.id),)
        )
        
        # Erstelle Embed
        embed = discord.Embed(
            title="📊 Ticket-System Statistiken",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Gesamt", value=str(stats["total"]), inline=True)
        embed.add_field(name="Offen", value=str(stats["open"]), inline=True)
        embed.add_field(name="Geschlossen", value=str(stats["closed"]), inline=True)
        embed.add_field(name="Archiviert", value=str(stats["archived"]), inline=True)
        
        if top_support:
            top_text = ""
            for supporter_id, count in top_support:
                supporter = ctx.guild.get_member(int(supporter_id))
                name = supporter.display_name if supporter else f"Unbekannt ({supporter_id})"
                top_text += f"{name}: {count} Tickets\n"
            
            embed.add_field(name="Top Support-Mitarbeiter", value=top_text, inline=False)
        
        await ctx.send(embed=embed)
    
    # Hilfsfunktionen
    async def is_support(self, member):
        """Überprüft, ob ein Mitglied Support-Rechte hat"""
        if member.guild_permissions.administrator:
            return True
        
        support_role_id = await self.get_support_role_id(member.guild.id)
        if not support_role_id:
            return False
        
        support_role = member.guild.get_role(int(support_role_id))
        if not support_role:
            return False
        
        return support_role in member.roles
    
    async def get_support_role_id(self, guild_id):
        """Holt die Support-Rollen-ID aus dem Cache oder der Datenbank"""
        if guild_id in self.support_roles:
            return self.support_roles[guild_id]
        
        result = await self.db.fetch_one(
            "SELECT support_role_id FROM ticket_config WHERE guild_id = ?", 
            (str(guild_id),)
        )
        
        if result and result[0]:
            self.support_roles[guild_id] = result[0]
            return result[0]
        
        return None
    
    async def log_ticket_action(self, guild, title, description, user=None):
        """Loggt eine Ticket-Aktion im Log-Kanal"""
        config = await self.db.fetch_one(
            "SELECT log_channel_id FROM ticket_config WHERE guild_id = ?", 
            (str(guild.id),)
        )
        
        if not config or not config[0]:
            return
        
        log_channel = guild.get_channel(int(config[0]))
        if not log_channel:
            return
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        if user:
            embed.set_footer(text=f"Aktion von {user.name}", icon_url=user.display_avatar.url)
        
        await log_channel.send(embed=embed)
    
    async def respond(self, ctx, interaction, content):
        """Antwortet entweder über Context oder Interaction"""
        if ctx:
            await ctx.send(content)
        elif interaction:
            try:
                await interaction.response.send_message(content, ephemeral=True)
            except:
                await interaction.followup.send(content, ephemeral=True)
    
    async def get_log_channel(self, guild_id):
        """Holt den Log-Kanal für ein Guild"""
        config = await self.db.fetch_one(
            "SELECT log_channel_id FROM ticket_config WHERE guild_id = ?", 
            (str(guild_id),)
        )
        
        if not config or not config[0]:
            return None
        
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return None
        
        log_channel = guild.get_channel(int(config[0]))
        return log_channel


# Modal für Ticket-Erstellung
class TicketModal(discord.ui.Modal):
    def __init__(self, cog, title):
        super().__init__(title=title)
        self.cog = cog
        
        self.add_item(
            discord.ui.TextInput(
                label="Titel deines Tickets",
                placeholder="Beschreibe dein Anliegen kurz",
                required=True,
                max_length=100
            )
        )
        
        self.add_item(
            discord.ui.TextInput(
                label="Beschreibung (optional)",
                placeholder="Beschreibe dein Problem ausführlicher...",
                required=False,
                max_length=1000,
                style=discord.TextStyle.paragraph
            )
        )
    
    async def on_submit(self, interaction):
        title = self.children[0].value
        description = self.children[1].value
        
        if description:
            title = f"{title} - {description[:50]}..." if len(description) > 50 else f"{title} - {description}"
        
        await self.cog.create_ticket_for_user(
            interaction.guild, interaction.user, title, interaction=interaction
        )


# Views und Komponenten für die Benutzeroberfläche
class TicketPanelView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    @discord.ui.button(
        label="Ticket erstellen", 
        style=discord.ButtonStyle.primary,
        custom_id="create_ticket",
        emoji="🎫"
    )
    async def create_ticket_button(self, interaction, button):
        """Button zum Erstellen eines Tickets"""
        try:
            # Modal für Ticket-Erstellung anzeigen
            modal = TicketCreateModal(self.cog)
            await interaction.response.send_modal(modal)
        except Exception as e:
            print(f"Fehler beim Erstellen des Modals: {e}")

class TicketCreateModal(discord.ui.Modal, title="Support-Ticket erstellen"):
    """Modal zum Erstellen eines Tickets"""
    
    ticket_title = discord.ui.TextInput(
        label="Titel des Tickets",
        placeholder="Kurze Beschreibung deines Anliegens",
        required=True,
        max_length=100
    )
    
    ticket_description = discord.ui.TextInput(
        label="Beschreibung",
        placeholder="Beschreibe dein Anliegen ausführlich...",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction):
        """Wird aufgerufen, wenn das Modal abgesendet wird"""
        await interaction.response.defer(ephemeral=True)
        
        title = self.ticket_title.value
        description = self.ticket_description.value
        
        # Ticket erstellen
        await self.cog.create_ticket_for_user(
            interaction.guild, 
            interaction.user, 
            title, 
            ctx=None, 
            interaction=interaction
        )

class TicketControlPanel(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
    
    @discord.ui.button(
        label="Ticket schließen", 
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket",
        emoji="🔒"
    )
    async def close_ticket(self, interaction, button):
        """Button zum Schließen eines Tickets"""
        # Prüfe, ob der Nutzer berechtigt ist
        is_support = await self.cog.is_support(interaction.user)
        is_ticket_creator = False
        
        # Finde Ticket-Informationen
        ticket = await self.cog.db.fetch_one(
            "SELECT ticket_id, user_id FROM tickets WHERE channel_id = ? AND status = 'open'",
            (str(interaction.channel.id),)
        )
        
        if not ticket:
            return await interaction.response.send_message(
                "❌ Dieser Kanal ist kein aktives Ticket!",
                ephemeral=True
            )
        
        ticket_id, creator_id = ticket
        is_ticket_creator = str(interaction.user.id) == creator_id
        
        if not (is_support or is_ticket_creator):
            return await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, dieses Ticket zu schließen!",
                ephemeral=True
            )
        
        # Modal für Schließgrund anzeigen
        modal = TicketCloseModal(self.cog, ticket_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(
        label="Nutzer hinzufügen", 
        style=discord.ButtonStyle.secondary,
        custom_id="add_user",
        emoji="👥"
    )
    async def add_user(self, interaction, button):
        """Button zum Hinzufügen eines Nutzers zum Ticket"""
        # Prüfe, ob der Nutzer berechtigt ist
        is_support = await self.cog.is_support(interaction.user)
        is_ticket_creator = False
        
        # Finde Ticket-Informationen
        ticket = await self.cog.db.fetch_one(
            "SELECT user_id FROM tickets WHERE channel_id = ? AND status = 'open'",
            (str(interaction.channel.id),)
        )
        
        if not ticket:
            return await interaction.response.send_message(
                "❌ Dieser Kanal ist kein aktives Ticket!",
                ephemeral=True
            )
        
        is_ticket_creator = str(interaction.user.id) == ticket[0]
        
        if not (is_support or is_ticket_creator):
            return await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, Nutzer zu diesem Ticket hinzuzufügen!",
                ephemeral=True
            )
        
        # Modal für Nutzerhinzufügung anzeigen
        modal = TicketAddUserModal(self.cog)
        await interaction.response.send_modal(modal)

class TicketCloseModal(discord.ui.Modal, title="Ticket schließen"):
    """Modal zum Schließen eines Tickets"""
    
    reason = discord.ui.TextInput(
        label="Grund für die Schließung",
        placeholder="Warum wird das Ticket geschlossen?",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=1000
    )
    
    def __init__(self, cog, ticket_id):
        super().__init__()
        self.cog = cog
        self.ticket_id = ticket_id
    
    async def on_submit(self, interaction):
        """Wird aufgerufen, wenn das Modal abgesendet wird"""
        reason = self.reason.value
        
        # Bestätigungsdialog anzeigen
        view = TicketCloseConfirm(self.cog, self.ticket_id, reason, interaction.user)
        await interaction.response.send_message(
            f"Möchtest du dieses Ticket wirklich schließen?\nGrund: {reason}",
            view=view,
            ephemeral=False
        )

class TicketAddUserModal(discord.ui.Modal, title="Nutzer hinzufügen"):
    """Modal zum Hinzufügen eines Nutzers zu einem Ticket"""
    
    user_id = discord.ui.TextInput(
        label="Nutzer-ID oder @Erwähnung",
        placeholder="ID oder @Erwähnung des Nutzers",
        required=True,
        max_length=100
    )
    
    def __init__(self, cog):
        super().__init__()
        self.cog = cog
    
    async def on_submit(self, interaction):
        """Wird aufgerufen, wenn das Modal abgesendet wird"""
        user_input = self.user_id.value
        
        # Extrahiere Nutzer-ID aus Erwähnung oder direkter ID
        user_id = user_input.strip()
        if user_id.startswith('<@') and user_id.endswith('>'):
            user_id = user_id[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
        
        # Finde Nutzer
        try:
            user = await interaction.guild.fetch_member(int(user_id))
            if not user:
                return await interaction.response.send_message(
                    "❌ Nutzer nicht gefunden!",
                    ephemeral=True
                )
            
            # Füge Nutzer zum Ticket hinzu
            await interaction.channel.set_permissions(
                user,
                read_messages=True,
                send_messages=True
            )
            
            await interaction.response.send_message(
                f"✅ {user.mention} wurde zum Ticket hinzugefügt.",
                ephemeral=False
            )
            
        except (ValueError, discord.NotFound, discord.HTTPException) as e:
            await interaction.response.send_message(
                f"❌ Fehler beim Hinzufügen des Nutzers: {e}",
                ephemeral=True
            )

# Bestätigungsdialog zum Schließen eines Tickets
class TicketCloseConfirm(discord.ui.View):
    def __init__(self, cog, ticket_id, reason, closer):
        super().__init__(timeout=60)
        self.cog = cog
        self.ticket_id = ticket_id
        self.reason = reason
        self.closer = closer
    
    @discord.ui.button(
        label="Ja, schließen", 
        style=discord.ButtonStyle.danger,
        custom_id="confirm_close_ticket",
        emoji="✅"
    )
    async def confirm_close(self, interaction, button):
        if interaction.user.id != self.closer.id:
            return await interaction.response.send_message("❌ Nur der Initiator kann diese Aktion bestätigen!", ephemeral=True)
        
        await interaction.response.edit_message(content="Ticket wird geschlossen...", view=None)
        
        try:
            # Hole Ticket-Informationen
            ticket_data = await self.cog.db.fetch_one(
                "SELECT channel_id, user_id, title FROM tickets WHERE ticket_id = ? AND guild_id = ?",
                (self.ticket_id, str(interaction.guild.id))
            )
            
            if not ticket_data:
                return await interaction.followup.send("❌ Ticket nicht gefunden!")
            
            channel_id, user_id, title = ticket_data
            
            # Aktualisiere Ticket-Status in der Datenbank
            await self.cog.db.execute(
                """UPDATE tickets 
                SET status = 'closed', closed_at = CURRENT_TIMESTAMP, closed_by = ? 
                WHERE ticket_id = ? AND guild_id = ?""",
                (str(interaction.user.id), self.ticket_id, str(interaction.guild.id))
            )
            
            # Sende Abschlussnachricht
            embed = discord.Embed(
                title=f"Ticket #{self.ticket_id} geschlossen",
                description=f"Dieses Ticket wurde von {interaction.user.mention} geschlossen.\n\n**Grund:** {self.reason}",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            
            # Füge Archivierungsoptionen hinzu
            view = TicketArchiveView(self.cog, self.ticket_id)
            await interaction.channel.send(embed=embed, view=view)
            
            # Logge Ticket-Schließung
            await self.cog.log_ticket_action(
                interaction.guild,
                f"Ticket #{self.ticket_id} geschlossen",
                f"**Titel:** {title}\n**Geschlossen von:** {interaction.user.mention}\n**Grund:** {self.reason}",
                interaction.user
            )
            
            # Benachrichtige Ticket-Ersteller
            creator = interaction.guild.get_member(int(user_id))
            if creator:
                try:
                    creator_embed = discord.Embed(
                        title=f"Dein Ticket wurde geschlossen",
                        description=f"Dein Ticket **{title}** wurde von {interaction.user.mention} geschlossen.\n\n**Grund:** {self.reason}",
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.now()
                    )
                    await creator.send(embed=creator_embed)
                except discord.Forbidden:
                    pass  # Nutzer erlaubt keine DMs
            
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Schließen des Tickets: {e}")
    
    @discord.ui.button(
        label="Abbrechen", 
        style=discord.ButtonStyle.secondary,
        custom_id="cancel_close_ticket",
        emoji="❌"
    )
    async def cancel_close(self, interaction, button):
        if interaction.user.id != self.closer.id:
            return await interaction.response.send_message("❌ Nur der Initiator kann diese Aktion abbrechen!", ephemeral=True)
        
        await interaction.response.edit_message(content="Ticket-Schließung abgebrochen.", view=None)

class TicketArchiveView(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.ticket_id = ticket_id
    
    @discord.ui.button(
        label="Archivieren", 
        style=discord.ButtonStyle.primary,
        custom_id="archive_ticket",
        emoji="📁"
    )
    async def archive_ticket(self, interaction, button):
        # Prüfe, ob der Nutzer Support-Rechte hat
        is_support = await self.cog.is_support(interaction.user)
        if not is_support:
            return await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, dieses Ticket zu archivieren!",
                ephemeral=True
            )
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Hole Ticket-Informationen
            ticket_data = await self.cog.db.fetch_one(
                "SELECT channel_id FROM tickets WHERE ticket_id = ? AND guild_id = ?",
                (self.ticket_id, str(interaction.guild.id))
            )
            
            if not ticket_data:
                return await interaction.followup.send("❌ Ticket nicht gefunden!")
            
            # Hole Archiv-Kategorie
            config = await self.cog.db.fetch_one(
                "SELECT archive_category_id FROM ticket_config WHERE guild_id = ?",
                (str(interaction.guild.id),)
            )
            
            if not config or not config[0]:
                return await interaction.followup.send("❌ Es wurde keine Archiv-Kategorie eingerichtet!")
            
            archive_category = interaction.guild.get_channel(int(config[0]))
            if not archive_category:
                return await interaction.followup.send("❌ Die Archiv-Kategorie existiert nicht mehr!")
            
            # Verschiebe Kanal in Archiv-Kategorie
            await interaction.channel.edit(
                category=archive_category,
                sync_permissions=True
            )
            
            # Aktualisiere Ticket-Status in der Datenbank
            await self.cog.db.execute(
                "UPDATE tickets SET archived = 1 WHERE ticket_id = ? AND guild_id = ?",
                (self.ticket_id, str(interaction.guild.id))
            )
            
            # Deaktiviere alle Buttons
            for child in self.children:
                child.disabled = True
            
            await interaction.message.edit(view=self)
            
            # Sende Bestätigung
            await interaction.followup.send("✅ Ticket wurde archiviert.")
            
            # Logge Ticket-Archivierung
            await self.cog.log_ticket_action(
                interaction.guild,
                f"Ticket #{self.ticket_id} archiviert",
                f"Das Ticket wurde von {interaction.user.mention} archiviert.",
                interaction.user
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Archivieren des Tickets: {e}")
    
    @discord.ui.button(
        label="Löschen", 
        style=discord.ButtonStyle.danger,
        custom_id="delete_ticket",
        emoji="🗑️"
    )
    async def delete_ticket(self, interaction, button):
        # Prüfe, ob der Nutzer Support-Rechte hat
        is_support = await self.cog.is_support(interaction.user)
        if not is_support:
            return await interaction.response.send_message(
                "❌ Du hast keine Berechtigung, dieses Ticket zu löschen!",
                ephemeral=True
            )
        
        # Bestätigungsdialog anzeigen
        view = TicketDeleteConfirm(self.cog, self.ticket_id)
        await interaction.response.send_message(
            "⚠️ Möchtest du dieses Ticket wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden!",
            view=view,
            ephemeral=True
        )

class TicketDeleteConfirm(discord.ui.View):
    def __init__(self, cog, ticket_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.ticket_id = ticket_id
    
    @discord.ui.button(
        label="Ja, löschen", 
        style=discord.ButtonStyle.danger,
        custom_id="confirm_delete_ticket",
        emoji="✅"
    )
    async def confirm_delete(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Hole Ticket-Informationen
            ticket_data = await self.cog.db.fetch_one(
                "SELECT channel_id, title FROM tickets WHERE ticket_id = ? AND guild_id = ?",
                (self.ticket_id, str(interaction.guild.id))
            )
            
            if not ticket_data:
                return await interaction.followup.send("❌ Ticket nicht gefunden!")
            
            channel_id, title = ticket_data
            
            # Erstelle Transcript vor dem Löschen
            transcript = await self.cog.create_transcript(None, self.ticket_id, return_file=True, interaction=interaction)
            
            # Logge Ticket-Löschung mit Transcript
            if transcript:
                await self.cog.log_ticket_action(
                    interaction.guild,
                    f"Ticket #{self.ticket_id} gelöscht",
                    f"**Titel:** {title}\n**Gelöscht von:** {interaction.user.mention}",
                    interaction.user
                )
                
                log_channel = await self.cog.get_log_channel(interaction.guild.id)
                if log_channel:
                    await log_channel.send(
                        f"Transcript für gelöschtes Ticket #{self.ticket_id}:",
                        file=transcript
                    )
            
            # Lösche Ticket aus der Datenbank
            await self.cog.db.execute(
                "DELETE FROM tickets WHERE ticket_id = ? AND guild_id = ?",
                (self.ticket_id, str(interaction.guild.id))
            )
            
            # Lösche den Kanal
            channel = interaction.guild.get_channel(int(channel_id))
            if channel:
                await channel.delete(reason=f"Ticket #{self.ticket_id} gelöscht von {interaction.user.name}")
            
            await interaction.followup.send("✅ Ticket wurde gelöscht.")
            
        except Exception as e:
            await interaction.followup.send(f"❌ Fehler beim Löschen des Tickets: {e}")
    
    @discord.ui.button(
        label="Abbrechen", 
        style=discord.ButtonStyle.secondary,
        custom_id="cancel_delete_ticket",
        emoji="❌"
    )
    async def cancel_delete(self, interaction, button):
        await interaction.response.edit_message(content="Ticket-Löschung abgebrochen.", view=None)


async def setup(bot):
    await bot.add_cog(TicketSystem(bot))