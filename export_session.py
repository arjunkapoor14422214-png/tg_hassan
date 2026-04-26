from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os
from dotenv import load_dotenv

load_dotenv()

api_id = int(os.getenv("TG_API_ID"))
api_hash = os.getenv("TG_API_HASH")

with TelegramClient("render_session_new", api_id, api_hash) as client:

    print(StringSession.save(client.session))
