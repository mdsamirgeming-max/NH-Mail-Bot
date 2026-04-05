import json
import urllib.request
import time
import threading
from datetime import datetime

# ====== CONFIG ======
BOT_TOKEN = "8788508823:AAELUW3TFS3_iyH5yhfJhLRrtHH5iSIISV4"  # সরাসরি বট টোকেন
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"
AUTO_REFRESH_INTERVAL = 10  # seconds

user_data = {}  # user data storage

# ====== MULTI-LANGUAGE ======
LANG = {
    "en": {
        "menu": "👋 *NH Mail Bot*\nChoose an option:",
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
    },
    "bn": {
        "menu": "👋 *NH মেইল বট*\nঅপশন বেছে নিন:",
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
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL + "sendMessage", data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            pass
    except Exception as e:
        print("Send message error:", e)

def get_updates(offset=None):
    url = API_URL + "getUpdates"
    if offset:
        url += f"?offset={offset}"
    try:
        with urllib.request.urlopen(url) as res:
            return json.loads(res.read())
    except Exception as e:
        print("Update fetch error:", e)
        return {}

# ====== EMAIL FUNCTIONS ======
def create_email():
    url = "https://api.internal.temp-mail.io/api/v3/email/new"
    data = json.dumps({"min_name_length":10,"max_name_length":10}).encode("utf-8")
    headers = {"Content-Type":"application/json", "accept":"application/json", "User-Agent":"Mozilla/5.0"}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            r = json.loads(res.read())
            return r["email"], r["token"]
    except Exception as e:
        print("Email create error:", e)
        return None, None

def get_inbox(email):
    url = f"https://api.internal.temp-mail.io/api/v3/email/{email}/messages"
    headers = {"accept":"application/json","User-Agent":"Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read())
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
