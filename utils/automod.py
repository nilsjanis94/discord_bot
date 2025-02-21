import re
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

class AutoMod:
    def __init__(self):
        self.spam_check = defaultdict(list)  # {user_id: [message_timestamps]}
        self.caps_threshold = 0.7  # Prozentsatz für Großbuchstaben
        self.message_cooldown = 5  # Nachrichten innerhalb von X Sekunden
        self.message_threshold = 5  # Maximale Anzahl von Nachrichten
        
        # Lade Wortfilter aus JSON
        self.load_word_filters()

    def load_word_filters(self):
        filter_path = "data/word_filters.json"
        if not os.path.exists(filter_path):
            self.banned_words = []
            self.banned_links = []
            # Erstelle Standardfilter
            default_filters = {
                "banned_words": ["banned_word1", "banned_word2"],
                "banned_links": ["banned-site.com", "spam-site.net"]
            }
            os.makedirs("data", exist_ok=True)
            with open(filter_path, 'w') as f:
                json.dump(default_filters, f, indent=4)
        else:
            with open(filter_path, 'r', encoding='utf-8') as f:
                filters = json.load(f)
                self.banned_words = filters.get("banned_words", [])
                self.banned_links = filters.get("banned_links", [])

    def check_spam(self, user_id):
        """Überprüft Spam-Verhalten"""
        now = datetime.now()
        user_messages = self.spam_check[user_id]
        
        # Entferne alte Nachrichten
        user_messages = [msg for msg in user_messages 
                        if now - msg < timedelta(seconds=self.message_cooldown)]
        self.spam_check[user_id] = user_messages
        
        # Füge neue Nachricht hinzu
        user_messages.append(now)
        
        return len(user_messages) > self.message_threshold

    def check_caps(self, content):
        """Überprüft übermäßige Großbuchstaben"""
        if len(content) < 8:  # Ignoriere kurze Nachrichten
            return False
            
        caps_count = sum(1 for c in content if c.isupper())
        return (caps_count / len(content)) > self.caps_threshold

    def check_banned_words(self, content):
        """Überprüft auf verbotene Wörter"""
        content_lower = content.lower()
        return any(word.lower() in content_lower for word in self.banned_words)

    def check_banned_links(self, content):
        """Überprüft auf verbotene Links"""
        content_lower = content.lower()
        return any(link.lower() in content_lower for link in self.banned_links)

    def check_invite_links(self, content):
        """Überprüft auf Discord Einladungslinks"""
        invite_pattern = r'discord\.gg/|discord\.com/invite/'
        return bool(re.search(invite_pattern, content))

    def check_mass_mentions(self, content):
        """Überprüft auf Massen-Erwähnungen"""
        mention_count = content.count('@')
        return mention_count > 5 