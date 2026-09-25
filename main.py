import os
import telebot
import random
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
BOT_TOKEN = "8728557922:AAGja3p-Y0aTpEurad1SLwkiBNYktfWbCbc"
ADMIN_ID = 7995159553
UPI_ID = "Shudhanshu539@slc"
BOT_NAME = "DAVO CASINO"

MIN_BET = 10.0
MAX_BET = 300.0

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=True, num_threads=4)

USER_BALANCES = {}

def get_balance(user_id):
    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 0.0
    return USER_BALANCES[user_id]

# -------------------------------------------------------------
# START & ADMIN COMMANDS
# -------------------------------------------------------------
@bot.message_handler(commands=['start'])
def send_start(message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    if user_id == ADMIN_ID:
        bot.reply_to(
            message,
            f"🎰 <b>{BOT_NAME} ADMIN PANEL</b>\n\n"
            f"<b>Admin Commands:</b>\n"
            f"• <code>/addbal user_id amount</code> — Add Balance\n"
            f"• <code>/cutbal user_id amount reason</code> — Deduct Balance"
        )
    else:
        bot.reply_to(
            message,
            f"🎰 Welcome <b>{user_name}</b> to <b>{BOT_NAME}</b>!\n"
            f"🎮 Type <code>/games</code> to view all games."
        )

# ADMIN BALANCE ADD
@bot.message_handler(commands=['addbal'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/addbal user_id amount</code>")
        return

    try:
        target_id = int(args[1])
        amount = float(args[2])
        USER_BALANCES[target_id] = get_balance(target_id) + amount
        bot.reply_to(message, f"✅ Added ₹{amount:.2f} to User ID: <code>{target_id}</code>\n💳 New Bal: ₹{USER_BALANCES[target_id]:.2f}")
        try:
            bot.send_message(target_id, f"🎉 <b>ADMIN ADDED BALANCE!</b>\n💰 Added: ₹{amount:.2f}\n💳 Bal: ₹{USER_BALANCES[target_id]:.2f}")
        except Exception: pass
    except ValueError:
        bot.reply_to(message, "❌ Invalid ID or Amount!")

# ADMIN BALANCE CUT
@bot.message_handler(commands=['cutbal'])
def admin_cut_balance(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/cutbal user_id amount reason</code>")
        return

    try:
        target_id = int(args[1])
        amount = float(args[2])
        reason = " ".join(args[3:]) if len(args) > 3 else "Admin Adjustment"
        USER_BALANCES[target_id] = max(0.0, get_balance(target_id) - amount)
        bot.reply_to(message, f"✂️ Deducted ₹{amount:.2f} from <code>{target_id}</code>\n📝 Reason: {reason}")
        try:
            bot.send_message(target_id, f"⚠️ <b>BALANCE DEDUCTED!</b>\n🔻 Amount: ₹{amount:.2f}\n📝 Reason: {reason}")
        except Exception: pass
    except ValueError:
        bot.reply_to(message, "❌ Invalid ID or Amount!")

@bot.message_handler(commands=['games', 'help'])
def send_games_list(message):
    games_text = (
        f"🎰 <b>{BOT_NAME} — GAMES LIST</b> 🎰\n\n"
        f"1️⃣ <b>Dice Rush:</b> <code>/dr amount high/low/even/odd</code>\n"
        f"2️⃣ <b>Limbo:</b> <code>/limbo amount target_x</code>\n\n"
        f"📌 <b>Wallet:</b> <code>/wallet</code>"
    )
    bot.reply_to(message, games_text)

@bot.message_handler(commands=['wallet', 'balance', 'bal'])
def check_wallet(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"💳 <b>{BOT_NAME} WALLET</b>\n🆔 ID: <code>{user_id}</code>\n💰 Balance: ₹{get_balance(user_id):.2f}")

# -------------------------------------------------------------
# GAMES SECTION
# -------------------------------------------------------------
@bot.message_handler(commands=['dr'])
def cmd_dr(message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/dr amount high/low/even/odd</code>")
        return

    try:
        bet_amount, bet_type = float(args[1]), args[2].lower()
        if bet_amount < MIN_BET or get_balance(user_id) < bet_amount:
            bot.reply_to(message, "❌ Invalid Bet or Low Balance!")
            return

        USER_BALANCES[user_id] -= bet_amount
        dice_msg = bot.send_dice(message.chat.id, "🎲")
        val = dice_msg.dice.value

        win = (bet_type == "high" and val >= 4) or (bet_type == "low" and val <= 3) or (bet_type == "even" and val % 2 == 0) or (bet_type == "odd" and val % 2 != 0)

        if win:
            win_amt = bet_amount * 1.95
            USER_BALANCES[user_id] += win_amt
            bot.reply_to(message, f"🎲 Result: <b>{val}</b> | 🎉 <b>WON ₹{win_amt:.2f}!</b>")
        else:
            bot.reply_to(message, f"🎲 Result: <b>{val}</b> | 🔻 <b>LOST ₹{bet_amount:.2f}!</b>")
    except Exception: pass

@bot.message_handler(commands=['limbo'])
def cmd_limbo(message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/limbo amount target_x</code>")
        return

    try:
        bet_amount = float(args[1])
        target_x = float(args[2].lower().replace("x", ""))
        if bet_amount < MIN_BET or get_balance(user_id) < bet_amount:
            bot.reply_to(message, "❌ Low Balance!")
            return

        USER_BALANCES[user_id] -= bet_amount
        res_x = round(random.uniform(1.00, target_x + 1.20), 2)

        if res_x >= target_x:
            win_amt = bet_amount * target_x
            USER_BALANCES[user_id] += win_amt
            bot.reply_to(message, f"🚀 <b>LIMBO RESULT: {res_x:.2f}x</b>\n🎉 <b>Target Hit! Won ₹{win_amt:.2f}!</b>")
        else:
            bot.reply_to(message, f"💥 <b>CRASHED AT {res_x:.2f}x!</b>\n🔻 Lost ₹{bet_amount:.2f}")
    except Exception: pass

# -------------------------------------------------------------
# DUMMY WEB SERVER FOR RENDER PORT CHECK
# -------------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"DAVO CASINO BOT IS ALIVE!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# -------------------------------------------------------------
# START ENGINE
# -------------------------------------------------------------
if __name__ == "__main__":
    # Web server thread me start hoga taaki Render pass ho jaye
    threading.Thread(target=run_web_server, daemon=True).start()
    
    print("⚡ DAVO CASINO FAST ENGINE ONLINE!")
    bot.infinity_polling(skip_pending=True)
