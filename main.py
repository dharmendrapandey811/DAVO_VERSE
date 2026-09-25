import os
import telebot
import random
import time
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
BOT_TOKEN = "8728557922:AAH3RJ01xzFW82o058-SwPLOfqdmABGDJHQ"
ADMIN_ID = 7995159553
UPI_ID = "Shudhanshu539@slc"
BOT_NAME = "DAVO CASINO"

MIN_BET = 10.0
MAX_BET = 10000.0

# Image URL used exclusively for Limbo Game Results
LIMBO_IMAGE_URL = "https://img.freepik.com/free-vector/rocket-launch-concept-illustration_114360-1011.jpg"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)

USER_BALANCES = {}
USER_UPI = {}
ESCROW_DEALS = {}

BOT_ACTIVE = True

# -------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------
def get_balance(user_id):
    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 0.0
    return USER_BALANCES[user_id]

def is_bot_active(message_or_call):
    user_id = message_or_call.from_user.id
    if not BOT_ACTIVE and user_id != ADMIN_ID:
        if isinstance(message_or_call, telebot.types.CallbackQuery):
            try:
                bot.answer_callback_query(message_or_call.id, "⚠️ Bot Maintenance me hai!", show_alert=True)
            except Exception: pass
        else:
            try:
                bot.reply_to(message_or_call, "⚠️ <b>Bot Maintenance me hai!</b>")
            except Exception: pass
        return False
    return True

def parse_amount_and_choice(args, user_id, valid_choices=None):
    """
    Handles flexible command formats:
    /dr 100 low, /dr low 100, /dr all low, /dr low all
    """
    if len(args) < 2:
        return None, None, "⚠️ Format sahi nahi hai!"

    val1, val2 = args[0].lower(), args[1].lower()
    balance = get_balance(user_id)
    amount = None
    choice = None

    for val in [val1, val2]:
        if val == "all":
            amount = balance
        else:
            try:
                amount = float(val)
            except ValueError:
                if valid_choices and val in valid_choices:
                    choice = val

    if choice is None and valid_choices:
        if val1 in valid_choices: choice = val1
        elif val2 in valid_choices: choice = val2

    if amount is None or amount <= 0:
        return None, None, "❌ Invalid Amount!"

    if amount < MIN_BET:
        return None, None, f"❌ Minimum bet ₹{MIN_BET:.0f} hai!"

    if amount > MAX_BET and amount != balance:
        return None, None, f"❌ Maximum bet ₹{MAX_BET:.0f} hai!"

    if balance < amount or balance == 0:
        return None, None, "❌ <b>Insufficient Balance!</b> Wallet me paisa kam hai."

    return amount, choice, None

# -------------------------------------------------------------
# COMMANDS: START & ADMIN
# -------------------------------------------------------------
@bot.message_handler(commands=['start'])
def send_start(message):
    try:
        user_id = message.from_user.id
        user_name = message.from_user.full_name

        if user_id == ADMIN_ID:
            markup = InlineKeyboardMarkup()
            btn_status = InlineKeyboardButton("🔴 Stop Bot" if BOT_ACTIVE else "🟢 Start Bot", callback_data="admin_toggle_bot")
            markup.add(btn_status)
            bot.reply_to(message, f"🎰 <b>{BOT_NAME} ADMIN PANEL</b>\n\nStatus: {'🟢 ACTIVE' if BOT_ACTIVE else '🔴 STOPPED'}\n\n• <code>/addbal user_id amount</code>\n• <code>/cutbal user_id amount reason</code>", reply_markup=markup)
        else:
            if not is_bot_active(message): return
            bot.reply_to(message, f"🎰 Welcome <b>{user_name}</b> to <b>{BOT_NAME}</b>!\n\n🎮 Games list ke liye <code>/games</code> dekhein.\n⚡ Fast Bet: <code>/dr all low</code> ya <code>/dr low 100</code>")
    except Exception as e:
        logging.error(f"Start Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_toggle_bot")
def handle_admin_toggle(call):
    global BOT_ACTIVE
    try:
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ Admin Only!", show_alert=True)
            return
        BOT_ACTIVE = not BOT_ACTIVE
        status_text = "🟢 ACTIVE" if BOT_ACTIVE else "🔴 STOPPED"
        btn_text = "🔴 Stop Bot" if BOT_ACTIVE else "🟢 Start Bot"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(btn_text, callback_data="admin_toggle_bot"))
        bot.edit_message_text(f"🎰 <b>{BOT_NAME} ADMIN PANEL</b>\n\nStatus: {status_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, f"Status: {status_text}")
    except Exception as e:
        logging.error(f"Toggle Error: {e}")

# -------------------------------------------------------------
# GAME: DICE RUSH (/dr)
# -------------------------------------------------------------
@bot.message_handler(commands=['dr', 'dicerush'])
def cmd_dice_rush(message):
    try:
        if not is_bot_active(message): return
        user_id = message.from_user.id
        args = message.text.split()[1:]

        valid_choices = ["low", "high", "even", "odd"]
        amount, choice, err = parse_amount_and_choice(args, user_id, valid_choices)

        if err:
            bot.reply_to(message, f"{err}\n\n<b>Usage:</b> <code>/dr [amount/all] [high/low/even/odd]</code>")
            return

        if not choice:
            bot.reply_to(message, "⚠️ Options: <code>low</code>, <code>high</code>, <code>even</code>, <code>odd</code>")
            return

        USER_BALANCES[user_id] -= amount

        msg = bot.send_dice(message.chat.id, emoji="🎲")
        dice_val = msg.dice.value
        time.sleep(2.5)

        win = False
        if choice == "low" and dice_val in [1, 2, 3]: win = True
        elif choice == "high" and dice_val in [4, 5, 6]: win = True
        elif choice == "even" and dice_val % 2 == 0: win = True
        elif choice == "odd" and dice_val % 2 != 0: win = True

        if win:
            payout = amount * 1.95
            USER_BALANCES[user_id] += payout
            res_text = f"🎉 <b>YOU WON!</b>\n🎲 Outcome: <b>{dice_val}</b>\n💰 Won: ₹{payout:.2f}"
        else:
            res_text = f"💔 <b>YOU LOST!</b>\n🎲 Outcome: <b>{dice_val}</b>\n🔻 Lost: ₹{amount:.2f}"

        bot.reply_to(message, f"{res_text}\n💳 Balance: ₹{get_balance(user_id):.2f}")

    except Exception as e:
        logging.error(f"DR Error: {e}")

# -------------------------------------------------------------
# GAME: LIMBO (/limbo) - PHOTO RESULT INCLUDED
# -------------------------------------------------------------
@bot.message_handler(commands=['limbo'])
def cmd_limbo(message):
    try:
        if not is_bot_active(message): return
        user_id = message.from_user.id
        args = message.text.split()[1:]

        if len(args) < 2:
            bot.reply_to(message, "⚠️ Usage: <code>/limbo [amount/all] [target]</code>\nExample: <code>/limbo 100 2.0</code> ya <code>/limbo all 1.5</code>")
            return

        balance = get_balance(user_id)
        val1, val2 = args[0].lower(), args[1].lower()

        if val1 == "all":
            amount = balance
            target = float(val2)
        elif val2 == "all":
            amount = balance
            target = float(val1)
        else:
            try:
                amount = float(val1)
                target = float(val2)
            except ValueError:
                amount = float(val2)
                target = float(val1)

        if target < 1.01 or target > 100.0:
            bot.reply_to(message, "❌ Target Multiplier 1.01x - 100.0x hona chahiye!")
            return

        if amount < MIN_BET or balance < amount or amount == 0:
            bot.reply_to(message, "❌ Insufficient Balance ya Invalid Amount!")
            return

        USER_BALANCES[user_id] -= amount

        dice_val = random.randint(1, 6)
        actual_multiplier = round(random.uniform(1.00, 4.00) + (dice_val * 0.4), 2)

        win = actual_multiplier >= target

        if win:
            payout = amount * target
            USER_BALANCES[user_id] += payout
            status = f"🎉 <b>TARGET HIT! (WIN)</b>\n💰 Won: ₹{payout:.2f}"
        else:
            status = f"💥 <b>CRASHED BELOW TARGET! (LOSS)</b>\n🔻 Lost: ₹{amount:.2f}"

        caption = (
            f"🚀 <b>LIMBO GAME RESULT</b>\n\n"
            f"🎯 Target: <b>{target:.2f}x</b>\n"
            f"📈 Rolled Result: <b>{actual_multiplier:.2f}x</b>\n\n"
            f"{status}\n"
            f"💳 Balance: ₹{get_balance(user_id):.2f}"
        )

        # Sirf Limbo ke liye Photo send ho raha hai
        bot.send_photo(
            chat_id=message.chat.id,
            photo=LIMBO_IMAGE_URL,
            caption=caption,
            reply_to_message_id=message.message_id
        )

    except Exception as e:
        logging.error(f"Limbo Error: {e}")

# -------------------------------------------------------------
# ESCROW SYSTEM
# -------------------------------------------------------------
@bot.message_handler(commands=['escrow'])
def cmd_escrow(message):
    try:
        if not is_bot_active(message): return
        user_id = message.from_user.id
        args = message.text.split()

        if len(args) < 2:
            bot.reply_to(message, "⚠️ Format: <code>/escrow amount</code>")
            return

        val = args[1].lower()
        amount = get_balance(user_id) if val == "all" else float(val)

        if amount < MIN_BET or amount > MAX_BET:
            bot.reply_to(message, f"❌ Amount ₹{MIN_BET:.0f} se ₹{MAX_BET:.0f} tak hona chahiye!")
            return

        if get_balance(user_id) < amount or amount == 0:
            bot.reply_to(message, "❌ <b>Insufficient Balance!</b>")
            return

        USER_BALANCES[user_id] -= amount
        escrow_id = f"esc_{user_id}_{int(time.time())}"

        ESCROW_DEALS[escrow_id] = {
            "creator_id": user_id,
            "creator_name": message.from_user.first_name,
            "provider_id": None,
            "provider_name": None,
            "amount": amount,
            "status": "WAITING"
        }

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🤝 Accept Deal", callback_data=f"esc_accept_{escrow_id}"),
            InlineKeyboardButton("❌ Cancel & Refund", callback_data=f"esc_cancel_{escrow_id}")
        )

        bot.reply_to(
            message,
            f"🛡️ <b>SECURE ESCROW DEAL CREATED</b>\n\n"
            f"👤 <b>Creator:</b> {message.from_user.first_name}\n"
            f"💰 <b>Hold Amount:</b> ₹{amount:.2f}\n"
            f"📌 <b>Status:</b> Waiting for Provider to accept...",
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Escrow Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("esc_"))
def handle_escrow_callbacks(call):
    try:
        if not is_bot_active(call): return
        data = call.data.split("_")
        action = data[1]
        escrow_id = "_".join(data[2:])
        user_id = call.from_user.id

        if escrow_id not in ESCROW_DEALS:
            bot.answer_callback_query(call.id, "❌ Deal Expired!", show_alert=True)
            return

        deal = ESCROW_DEALS[escrow_id]

        if action == "accept":
            if user_id == deal["creator_id"]:
                bot.answer_callback_query(call.id, "❌ Apni deal khud accept nahi kar sakte!", show_alert=True)
                return

            if deal["status"] != "WAITING":
                bot.answer_callback_query(call.id, "❌ Deal pehle se accept ho chuki hai!", show_alert=True)
                return

            deal["provider_id"] = user_id
            deal["provider_name"] = call.from_user.first_name
            deal["status"] = "ACCEPTED"

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("✅ Release Funds", callback_data=f"esc_release_{escrow_id}"),
                InlineKeyboardButton("❌ Cancel & Refund", callback_data=f"esc_cancel_{escrow_id}")
            )

            bot.edit_message_text(
                f"🛡️ <b>ESCROW IN PROGRESS</b>\n\n"
                f"👤 <b>Creator:</b> {deal['creator_name']}\n"
                f"👤 <b>Provider:</b> {deal['provider_name']}\n"
                f"💰 <b>Hold Amount:</b> ₹{deal['amount']:.2f}\n\n"
                f"<i>Creator kaam hone ke baad 'Release Funds' dabaayein.</i>",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=markup
            )
            bot.answer_callback_query(call.id, "✅ Deal Accepted!")

        elif action == "release":
            if user_id != deal["creator_id"]:
                bot.answer_callback_query(call.id, "❌ Sirf Creator release kar sakta hai!", show_alert=True)
                return

            provider_id = deal["provider_id"]
            amount = deal["amount"]

            USER_BALANCES[provider_id] = get_balance(provider_id) + amount
            bot.edit_message_text(
                f"🎉 <b>ESCROW RELEASED!</b>\n\n"
                f"👤 <b>To:</b> {deal['provider_name']}\n"
                f"💰 <b>Amount:</b> ₹{amount:.2f}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            del ESCROW_DEALS[escrow_id]

        elif action == "cancel":
            if user_id != deal["creator_id"] and user_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ Access Denied!", show_alert=True)
                return

            amount = deal["amount"]
            creator_id = deal["creator_id"]

            USER_BALANCES[creator_id] = get_balance(creator_id) + amount
            bot.edit_message_text(
                f"❌ <b>ESCROW CANCELLED & REFUNDED!</b>\n\n💰 <b>Refunded:</b> ₹{amount:.2f}",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id
            )
            del ESCROW_DEALS[escrow_id]
    except Exception as e:
        logging.error(f"Escrow CB Error: {e}")

# -------------------------------------------------------------
# WALLET & UTILS
# -------------------------------------------------------------
@bot.message_handler(commands=['games', 'help'])
def send_games_list(message):
    if not is_bot_active(message): return
    bot.reply_to(message, f"🎰 <b>{BOT_NAME} SYSTEM</b> 🎰\n\n🎲 <b>Dice Rush:</b> <code>/dr all low</code>\n🚀 <b>Limbo:</b> <code>/limbo all 2.0</code> (Photo Result)\n🛡️ <b>Escrow:</b> <code>/escrow amount</code>\n💳 <b>Wallet:</b> <code>/wallet</code>")

@bot.message_handler(commands=['wallet', 'bal'])
def check_wallet(message):
    if not is_bot_active(message): return
    user_id = message.from_user.id
    bot.reply_to(message, f"💳 <b>WALLET BALANCE:</b> ₹{get_balance(user_id):.2f}\n🆔 ID: <code>{user_id}</code>")

@bot.message_handler(commands=['addbal'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        target_id, amount = int(args[1]), float(args[2])
        USER_BALANCES[target_id] = get_balance(target_id) + amount
        bot.reply_to(message, f"✅ Added ₹{amount:.2f} to <code>{target_id}</code>")
    except Exception:
        bot.reply_to(message, "⚠️ Format: <code>/addbal user_id amount</code>")

# -------------------------------------------------------------
# RENDER SERVER (Keep Alive)
# -------------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"DAVO CASINO BOT ONLINE")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# -------------------------------------------------------------
# INFINITE RUNNER LOOP
# -------------------------------------------------------------
if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("⚡ BOT STARTED!")

    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            logging.error(f"Polling Crashed: {e}")
            time.sleep(3)
