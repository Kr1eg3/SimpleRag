#!/usr/bin/env python3
"""
Update User API Key - для обновления API ключей пользователей
"""

import sqlite3
import os
from pathlib import Path

class UserAPIKeyUpdater:
    def __init__(self, db_path: str = "multiuser.db"):
        self.db_path = db_path

    def update_user_api_key(self, username: str, anthropic_key: str = None, openai_key: str = None):
        """Update user's API keys"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if user exists
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            if not cursor.fetchone():
                print(f"❌ User '{username}' not found")
                return False

            # Update API keys
            update_fields = []
            params = []

            if anthropic_key:
                update_fields.append("anthropic_api_key = ?")
                params.append(anthropic_key)

            if openai_key:
                update_fields.append("openai_api_key = ?")
                params.append(openai_key)

            if not update_fields:
                print("❌ No API keys provided")
                return False

            params.append(username)

            cursor.execute(f"""
                UPDATE users
                SET {', '.join(update_fields)}, last_active = CURRENT_TIMESTAMP
                WHERE username = ?
            """, params)

            conn.commit()
            conn.close()

            print(f"✅ API keys updated for user '{username}'")
            if anthropic_key:
                print(f"   Anthropic API Key: {anthropic_key[:10]}...")
            if openai_key:
                print(f"   OpenAI API Key: {openai_key[:10]}...")

            return True

        except Exception as e:
            print(f"❌ Error updating API keys: {e}")
            return False

    def get_user_info(self, username: str):
        """Get user information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT username, anthropic_api_key, openai_api_key, llm_provider, model, temperature
                FROM users WHERE username = ?
            """, (username,))

            result = cursor.fetchone()
            if not result:
                print(f"❌ User '{username}' not found")
                return None

            conn.close()

            user_info = {
                "username": result[0],
                "anthropic_api_key": result[1],
                "openai_api_key": result[2],
                "llm_provider": result[3],
                "model": result[4],
                "temperature": result[5]
            }

            print(f"👤 User: {user_info['username']}")
            print(f"   Provider: {user_info['llm_provider']}")
            print(f"   Model: {user_info['model']}")
            print(f"   Temperature: {user_info['temperature']}")

            if user_info['anthropic_api_key']:
                print(f"   Anthropic Key: {user_info['anthropic_api_key'][:10]}...")
            else:
                print(f"   Anthropic Key: Not set")

            if user_info['openai_api_key']:
                print(f"   OpenAI Key: {user_info['openai_api_key'][:10]}...")
            else:
                print(f"   OpenAI Key: Not set")

            return user_info

        except Exception as e:
            print(f"❌ Error getting user info: {e}")
            return None


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Update User API Keys")
    parser.add_argument("--username", "-u", required=True, help="Username")
    parser.add_argument("--anthropic-key", help="Anthropic API key")
    parser.add_argument("--openai-key", help="OpenAI API key")
    parser.add_argument("--info", action="store_true", help="Show user info only")
    parser.add_argument("--db", default="multiuser.db", help="Database path")

    args = parser.parse_args()

    updater = UserAPIKeyUpdater(args.db)

    if args.info:
        updater.get_user_info(args.username)
    else:
        updater.update_user_api_key(args.username, args.anthropic_key, args.openai_key)


if __name__ == "__main__":
    main()