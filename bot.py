import json
import urllib.request
import time
import threading
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

# ====== CONFIG ======
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
AUTO_REFRESH_INTERVAL = 10

user_data = {}

# ====== MULTI-LANGUAGE ======
LANG = {
    "en": {
        "menu": "👋 *Temp Mail Bot*\nChoose an option:",
        "generate": "📧 Generate Email",
        "inbox": "📬 Inbox",
        "delete": "🗑 Delete Email",
        "statistics": "📊 Statistics",
        "back": "🔙 Back",
        "auto_on": "🔄 Auto Refresh ON",
        "auto_off": "❌ Auto Refresh OFF",
        "email_limit": "❌ Maximum 15 emails per day",
        "first_generate": "❌ First generate an email",
        "inbox_empty": "📭 Inbox is empty",
        "auto_enabled": "✅ Auto Refresh Enabled",
        "auto_disabled": "❌ Auto Refresh Disabled",
        "language": "🌐 Language",
        "choose_lang": "🌐 Choose your language:",
        "lang_set_en": "✅ Language set to English",
        "lang_set_bn": "✅ ভাষা বাংলা করা হয়েছে"
    },
    "bn": {
        "menu": "👋 *টেম্প মেইল বট*\nঅপশন বেছে নিন:",
        "generate": "📧 ইমেইল তৈরি করুন",
        "inbox": "📬 ইনবক্স",
        "delete": "🗑 ইমেইল মুছে দিন",
        "statistics": "📊 পরিসংখ্যান",
        "back": "🔙 ফিরে যান",
        "auto_on": "🔄 অটো রিফ্রেশ চালু",
        "auto_off": "❌ অটো রিফ্রেশ বন্ধ",
        "email_limit": "❌ দিনে সর্বাধিক ১৫ ইমেইল তৈরি করা যাবে",
        "first_generate": "❌ প্রথমে ইমেইল তৈরি করুন",
        "inbox_empty": "📭 ইনবক্স খালি",
        "auto_enabled": "✅ অটো রিফ্রেশ চালু করা হয়েছে",
        "auto_disabled": "❌ অটো রিফ্রেশ বন্ধ করা হয়েছে",
        "language": "🌐 ভাষা পরিবর্তন",
        "choose_lang": "🌐 ভাষা নির্বাচন করুন:",
        "lang_set_en": "✅ Language set to English",
        "lang_set_bn": "✅ ভাষা বাংলা করা হয়েছে"
    }
}

# ====== UTILITY ======
def get_text(chat_id, key):
    lang = user_data.get(chat_id, {}).get("lang", "en")
    return LANG[lang].get(key, key)

def send_message(chat_id, text, buttons=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})

    try:
        req = urllib.request.Request(
            API_URL + "sendMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req)
    except Exception as e:
        print("Send error:", e)

def get_updates(offset=None):
    url = API_URL + "getUpdates"
    if offset:
        url += f"?offset={offset}"
    try:
        with urllib.request.urlopen(url) as res:
            return json.loads(res.read())
    except:
        return {}

# ====== EMAIL ======
def create_email():
    try:
        req = urllib.request.Request(
            "https://api.internal.temp-mail.io/api/v3/email/new",
            data=json.dumps({"min_name_length":10,"max_name_length":10}).encode(),
            headers={"Content-Type":"application/json"}
        )
        res = json.loads(urllib.request.urlopen(req).read())
        return res["email"], res["token"]
    except:
        return None, None

def get_inbox(email):
    try:
        req = urllib.request.Request(
            f"https://api.internal.temp-mail.io/api/v3/email/{email}/messages"
        )
        return json.loads(urllib.request.urlopen(req).read())
    except:
        return []

# ====== AUTO REFRESH ======
def auto_refresh(chat_id):
    while user_data.get(chat_id, {}).get("auto_refresh"):
        user = user_data.get(chat_id)
        if not user or "email" not in user:
            break

        inbox = get_inbox(user["email"])

        for msg in inbox:
            if msg["id"] not in user["seen"]:
                user["seen"].append(msg["id"])
                send_message(chat_id,
                    f"📨 From: {msg.get('from','Unknown')}\n"
                    f"📌 Subject: {msg.get('subject','No Subject')}\n"
                    f"💬 {msg.get('body_text','')[:1000]}"
                )

        time.sleep(AUTO_REFRESH_INTERVAL)

# ====== MENU ======
def main_menu(chat_id):
    buttons = [
        [{"text": get_text(chat_id,"generate"), "callback_data": "generate"}],
        [{"text": get_text(chat_id,"inbox"), "callback_data": "inbox"}],
        [{"text": get_text(chat_id,"delete"), "callback_data": "delete"}],
        [{"text": get_text(chat_id,"statistics"), "callback_data": "statistics"}],
        [{"text": get_text(chat_id,"auto_on"), "callback_data": "auto_on"}],
        [{"text": get_text(chat_id,"auto_off"), "callback_data": "auto_off"}],
        [{"text": get_text(chat_id,"language"), "callback_data": "language"}],
    ]
    send_message(chat_id, get_text(chat_id,"menu"), buttons)

def language_menu(chat_id):
    buttons = [
        [{"text": "English 🇺🇸", "callback_data": "lang_en"}],
        [{"text": "বাংলা 🇧🇩", "callback_data": "lang_bn"}],
        [{"text": get_text(chat_id,"back"), "callback_data": "back"}],
    ]
    send_message(chat_id, get_text(chat_id,"choose_lang"), buttons)

# ====== COMMAND ======
def handle_command(message):
    chat_id = message["chat"]["id"]

    if chat_id not in user_data:
        user_data[chat_id] = {
            "lang":"en",
            "count":0,
            "date":str(datetime.now().date()),
            "auto_refresh":False,
            "seen":[]
        }

    if message.get("text") == "/start":
        main_menu(chat_id)

# ====== CALLBACK ======
def handle_callback(callback):
    chat_id = callback["message"]["chat"]["id"]
    data = callback["data"]
    user = user_data[chat_id]

    if data == "language":
        language_menu(chat_id)

    elif data == "lang_en":
        user["lang"] = "en"
        send_message(chat_id,get_text(chat_id,"lang_set_en"))
        main_menu(chat_id)

    elif data == "lang_bn":
        user["lang"] = "bn"
        send_message(chat_id,get_text(chat_id,"lang_set_bn"))
        main_menu(chat_id)

    elif data == "generate":
        today = str(datetime.now().date())
        if user["date"] != today:
            user["count"] = 0
            user["date"] = today

        if user["count"] >= 15:
            send_message(chat_id,get_text(chat_id,"email_limit"))
            return

        email, token = create_email()

        if email:
            user["email"] = email
            user["token"] = token
            user["count"] += 1
            user["seen"] = []
            send_message(chat_id,f"📧 Your email:\n`{email}`")
        else:
            send_message(chat_id,"❌ Failed")

    elif data == "inbox":
        if "email" not in user:
            send_message(chat_id,get_text(chat_id,"first_generate"))
            return

        inbox = get_inbox(user["email"])

        if not inbox:
            send_message(chat_id,get_text(chat_id,"inbox_empty"))
            return

        new_found = False

        for msg in inbox:
            if msg["id"] not in user["seen"]:
                new_found = True
                user["seen"].append(msg["id"])
                send_message(chat_id,
                    f"📨 From: {msg.get('from','Unknown')}\n"
                    f"📌 Subject: {msg.get('subject','No Subject')}\n"
                    f"💬 {msg.get('body_text','')[:1000]}"
                )

        if not new_found:
            send_message(chat_id,get_text(chat_id,"inbox_empty"))

    elif data == "delete":
        if "email" in user:
            del user["email"]
            del user["token"]
            user["seen"] = []
            send_message(chat_id,get_text(chat_id,"delete"))
        else:
            send_message(chat_id,get_text(chat_id,"first_generate"))

    elif data == "statistics":
        send_message(chat_id,f"📊 Total Emails Generated: {user['count']}")

    elif data == "auto_on":
        if not user.get("auto_refresh"):
            user["auto_refresh"] = True
            send_message(chat_id,get_text(chat_id,"auto_enabled"))
            threading.Thread(target=auto_refresh,args=(chat_id,),daemon=True).start()

    elif data == "auto_off":
        user["auto_refresh"] = False
        send_message(chat_id,get_text(chat_id,"auto_disabled"))

    elif data == "back":
        main_menu(chat_id)

# ====== MAIN BOT LOOP ======
def main():
    last_update_id = None
    print("Bot running...")

    while True:
        updates = get_updates(last_update_id)

        for update in updates.get("result", []):
            last_update_id = update["update_id"] + 1

            if "message" in update:
                handle_command(update["message"])
            elif "callback_query" in update:
                handle_callback(update["callback_query"])

        time.sleep(1)

# ====== WEB SERVER ======
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Web running on port {port}")
    server.serve_forever()

# ====== START ======
if __name__ == "__main__":
    threading.Thread(target=main).start()
    run_web()        return res["email"], res["token"]
    except:
        return None, None

def get_inbox(email):
    try:
        req = urllib.request.Request(
            f"https://api.internal.temp-mail.io/api/v3/email/{email}/messages"
        )
        return json.loads(urllib.request.urlopen(req).read())
    except:
        return []

# ====== AUTO REFRESH ======
def auto_refresh(chat_id):
    while user_data.get(chat_id, {}).get("auto_refresh"):
        user = user_data.get(chat_id)
        if not user or "email" not in user:
            break

        inbox = get_inbox(user["email"])

        for msg in inbox:
            if msg["id"] not in user["seen"]:
                user["seen"].append(msg["id"])
                send_message(chat_id,
                    f"📨 From: {msg.get('from','Unknown')}\n"
                    f"📌 Subject: {msg.get('subject','No Subject')}\n"
                    f"💬 {msg.get('body_text','')[:1000]}"
                )

        time.sleep(AUTO_REFRESH_INTERVAL)

# ====== MENU ======
def main_menu(chat_id):
    buttons = [
        [{"text": get_text(chat_id,"generate"), "callback_data": "generate"}],
        [{"text": get_text(chat_id,"inbox"), "callback_data": "inbox"}],
        [{"text": get_text(chat_id,"delete"), "callback_data": "delete"}],
        [{"text": get_text(chat_id,"statistics"), "callback_data": "statistics"}],
        [{"text": get_text(chat_id,"auto_on"), "callback_data": "auto_on"}],
        [{"text": get_text(chat_id,"auto_off"), "callback_data": "auto_off"}],
        [{"text": get_text(chat_id,"language"), "callback_data": "language"}],
    ]
    send_message(chat_id, get_text(chat_id,"menu"), buttons)

def language_menu(chat_id):
    buttons = [
        [{"text": "English 🇺🇸", "callback_data": "lang_en"}],
        [{"text": "বাংলা 🇧🇩", "callback_data": "lang_bn"}],
        [{"text": get_text(chat_id,"back"), "callback_data": "back"}],
    ]
    send_message(chat_id, get_text(chat_id,"choose_lang"), buttons)

# ====== COMMAND ======
def handle_command(message):
    chat_id = message["chat"]["id"]

    if chat_id not in user_data:
        user_data[chat_id] = {
            "lang":"en",
            "count":0,
            "date":str(datetime.now().date()),
            "auto_refresh":False,
            "seen":[]
        }

    if message.get("text") == "/start":
        main_menu(chat_id)

# ====== CALLBACK ======
def handle_callback(callback):
    chat_id = callback["message"]["chat"]["id"]
    data = callback["data"]
    user = user_data[chat_id]

    if data == "language":
        language_menu(chat_id)

    elif data == "lang_en":
        user["lang"] = "en"
        send_message(chat_id,get_text(chat_id,"lang_set_en"))
        main_menu(chat_id)

    elif data == "lang_bn":
        user["lang"] = "bn"
        send_message(chat_id,get_text(chat_id,"lang_set_bn"))
        main_menu(chat_id)

    elif data == "generate":
        today = str(datetime.now().date())
        if user["date"] != today:
            user["count"] = 0
            user["date"] = today

        if user["count"] >= 15:
            send_message(chat_id,get_text(chat_id,"email_limit"))
            return

        email, token = create_email()

        if email:
            user["email"] = email
            user["token"] = token
            user["count"] += 1
            user["seen"] = []
            send_message(chat_id,f"📧 Your email:\n`{email}`")
        else:
            send_message(chat_id,"❌ Failed")

    elif data == "inbox":
        if "email" not in user:
            send_message(chat_id,get_text(chat_id,"first_generate"))
            return

        inbox = get_inbox(user["email"])

        if not inbox:
            send_message(chat_id,get_text(chat_id,"inbox_empty"))
            return

        new_found = False

        for msg in inbox:
            if msg["id"] not in user["seen"]:
                new_found = True
                user["seen"].append(msg["id"])
                send_message(chat_id,
                    f"📨 From: {msg.get('from','Unknown')}\n"
                    f"📌 Subject: {msg.get('subject','No Subject')}\n"
                    f"💬 {msg.get('body_text','')[:1000]}"
                )

        if not new_found:
            send_message(chat_id,get_text(chat_id,"inbox_empty"))

    elif data == "delete":
        if "email" in user:
            del user["email"]
            del user["token"]
            user["seen"] = []
            send_message(chat_id,get_text(chat_id,"delete"))
        else:
            send_message(chat_id,get_text(chat_id,"first_generate"))

    elif data == "statistics":
        send_message(chat_id,f"📊 Total Emails Generated: {user['count']}")

    elif data == "auto_on":
        if not user.get("auto_refresh"):
            user["auto_refresh"] = True
            send_message(chat_id,get_text(chat_id,"auto_enabled"))
            threading.Thread(target=auto_refresh,args=(chat_id,),daemon=True).start()

    elif data == "auto_off":
        user["auto_refresh"] = False
        send_message(chat_id,get_text(chat_id,"auto_disabled"))

    elif data == "back":
        main_menu(chat_id)

# ====== MAIN BOT LOOP ======
def main():
    last_update_id = None
    print("Bot running...")

    while True:
        updates = get_updates(last_update_id)

        for update in updates.get("result", []):
            last_update_id = update["update_id"] + 1

            if "message" in update:
                handle_command(update["message"])
            elif "callback_query" in update:
                handle_callback(update["callback_query"])

        time.sleep(1)

# ====== RENDER WEB SERVER ======
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Web running on port {port}")
    server.serve_forever()

# ====== START ======
if __name__ == "__main__":
    threading.Thread(target=main).start()
    run_web()            return json.loads(res.read())
    except Exception as e:
        print("Inbox fetch error:", e)
        return []

# ====== AUTO REFRESH THREAD ======
def auto_refresh(chat_id):
    while user_data.get(chat_id, {}).get("auto_refresh") and "email" in user_data[chat_id]:
        inbox = get_inbox(user_data[chat_id]["email"])
        for msg in inbox:
            if msg["id"] not in user_data[chat_id].setdefault("seen", []):
                user_data[chat_id]["seen"].append(msg["id"])
                send_message(chat_id, f"📨 From: {msg.get('from','Unknown')}\n📌 Subject: {msg.get('subject','No Subject')}\n💬 {msg.get('body_text','[No Body]')[:1000]}")
                if "link" in msg:
                    user_data[chat_id].setdefault("links", []).append(msg["link"])
        time.sleep(AUTO_REFRESH_INTERVAL)

# ====== MENU & CALLBACKS ======
def main_menu(chat_id):
    buttons = [
        [{"text": get_text(chat_id,"generate"), "callback_data": "generate"}],
        [{"text": get_text(chat_id,"inbox"), "callback_data": "inbox"}],
        [{"text": get_text(chat_id,"delete"), "callback_data": "delete"}],
        [{"text": get_text(chat_id,"statistics"), "callback_data": "statistics"}],
        [{"text": get_text(chat_id,"auto_on"), "callback_data": "auto_on"}],
        [{"text": get_text(chat_id,"auto_off"), "callback_data": "auto_off"}],
    ]
    send_message(chat_id, get_text(chat_id,"menu"), buttons)

def handle_command(message):
    chat_id = message["chat"]["id"]
    if chat_id not in user_data:
        user_data[chat_id] = {"lang":"en","count":0,"date":str(datetime.now().date()),"menu_sent":False,"auto_refresh":False,"seen":[]}
    if message.get("text") == "/start":
        if not user_data[chat_id]["menu_sent"]:
            main_menu(chat_id)
            user_data[chat_id]["menu_sent"] = True

def handle_callback(callback):
    chat_id = callback["message"]["chat"]["id"]
    data = callback["data"]
    user = user_data.get(chat_id)

    if data == "generate":
        today = str(datetime.now().date())
        if user["date"] != today:
            user["count"] = 0
            user["date"] = today
        if user["count"] >= 15:
            send_message(chat_id,get_text(chat_id,"email_limit"))
            return
        email, token = create_email()
        if email:
            user_data[chat_id]["email"] = email
            user_data[chat_id]["token"] = token
            user_data[chat_id]["count"] += 1
            user_data[chat_id]["seen"] = []
            send_message(chat_id,f"📧 Your email:\n`{email}`")
        else:
            send_message(chat_id,"❌ Failed to generate email")
    elif data == "inbox":
        if "email" not in user:
            send_message(chat_id,get_text(chat_id,"first_generate"))
        else:
            inbox = get_inbox(user["email"])
            if inbox:
                for msg in inbox:
                    if msg["id"] not in user.setdefault("seen", []):
                        user["seen"].append(msg["id"])
                        send_message(chat_id,f"📨 From: {msg.get('from','Unknown')}\n📌 Subject: {msg.get('subject','No Subject')}\n💬 {msg.get('body_text','[No Body]')[:1000]}")
                        if "link" in msg:
                            user.setdefault("links",[]).append(msg["link"])
            else:
                send_message(chat_id,get_text(chat_id,"inbox_empty"))
    elif data == "delete":
        if "email" in user:
            del user_data[chat_id]["email"]
            del user_data[chat_id]["token"]
            user["seen"] = []
            send_message(chat_id,get_text(chat_id,"delete"))
        else:
            send_message(chat_id,get_text(chat_id,"first_generate"))
    elif data == "statistics":
        send_message(chat_id,f"📊 Total Emails Generated: {user_data[chat_id]['count']}")
    elif data == "auto_on":
        user["auto_refresh"] = True
        send_message(chat_id,get_text(chat_id,"auto_enabled"))
        threading.Thread(target=auto_refresh,args=(chat_id,),daemon=True).start()
    elif data == "auto_off":
        user["auto_refresh"] = False
        send_message(chat_id,get_text(chat_id,"auto_disabled"))
    elif data == "back":
        main_menu(chat_id)

# ====== MAIN LOOP ======
def main():
    last_update_id = None
    print("🤖 Bot running...")
    while True:
        updates = get_updates(last_update_id)
        for update in updates.get("result", []):
            last_update_id = update["update_id"] + 1
            if "message" in update:
                handle_command(update["message"])
            elif "callback_query" in update:
                handle_callback(update["callback_query"])
        time.sleep(1)

if __name__ == "__main__":
    main()
