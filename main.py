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

LIMBO_IMAGE_URL = "https://img.freepik.com/free-vector/rocket-launch-concept-illustration_114360-1011.jpg"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)

USER_BALANCES = {}
PVP_MATCHES = {}

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

def parse_amount_and_number(args, user_id, min_num=1, max_num=6):
    """ FLEXIBLE PARSER: Swaps amount and rounds/target automatically """
    if len(args) < 1:
        return None, None, "⚠️ Amount aur Round/Target mention karein!"

    balance = get_balance(user_id)
    val1 = args[0].lower()
    val2 = args[1].lower() if len(args) > 1 else "1"

    amount = None
    target_num = None

    # Try parsing val1 as target, val2 as amount OR vice versa
    for v in [val1, val2]:
        if v == "all":
            amount = balance
        else:
            try:
                n = float(v)
                if min_num <= n <= max_num and target_num is None and n.is_integer():
                    target_num = int(n)
                elif amount is None:
                    amount = n
            except ValueError:
                pass

    # Fallback assignment if parsing logic missed target or amount
    if amount is None or target_num is None:
        try:
            if val1 == "all":
                amount = balance
                target_num = int(val2)
            elif val2 == "all":
                amount = balance
                target_num = int(val1)
            else:
                p1, p2 = float(val1), float(val2)
                if min_num <= p1 <= max_num and p1.is_integer():
                    target_num = int(p1)
                    amount = p2
                else:
                    target_num = int(p2)
                    amount = int(p1) if p1.is_integer() else p1
        except Exception:
            return None, None, f"❌ Valid Target/Rounds Range: {min_num} - {max_num}"

    if amount is None or amount <= 0:
        return None, None, "❌ Invalid Amount!"
    if amount < MIN_BET:
        return None, None, f"❌ Minimum bet ₹{MIN_BET:.0f} hai!"
    if amount > MAX_BET and amount != balance:
        return None, None, f"❌ Maximum bet ₹{MAX_BET:.0f} hai!"
    if balance < amount or balance == 0:
        return None, None, "❌ <b>Insufficient Balance!</b> Wallet me paisa kam hai."

    return amount, target_num, None

def parse_amount_and_choice(args, user_id, valid_choices=None):
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
# START & ADMIN COMMANDS
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
            bot.reply_to(message, f"🎰 <b>{BOT_NAME} ADMIN PANEL</b>\n\nStatus: {'🟢 ACTIVE' if BOT_ACTIVE else '🔴 STOPPED'}\n\n• <code>/addbal user_id amount</code>", reply_markup=markup)
        else:
            if not is_bot_active(message): return
            bot.reply_to(message, f"🎰 Welcome <b>{user_name}</b> to <b>{BOT_NAME}</b>!\n\n🎮 Games list dekhne ke liye <code>/games</code> type karein.")
    except Exception as e:
        logging.error(f"Start Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_toggle_bot")
def handle_admin_toggle(call):
    global BOT_ACTIVE
    try:
        if call.from_user.id != ADMIN_ID: return
        BOT_ACTIVE = not BOT_ACTIVE
        status_text = "🟢 ACTIVE" if BOT_ACTIVE else "🔴 STOPPED"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔴 Stop Bot" if BOT_ACTIVE else "🟢 Start Bot", callback_data="admin_toggle_bot"))
        bot.edit_message_text(f"🎰 <b>{BOT_NAME} ADMIN PANEL</b>\n\nStatus: {status_text}", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    except Exception as e:
        logging.error(f"Toggle Error: {e}")

# -------------------------------------------------------------
# SOLO GAMES (/dr, /limbo, /slots)
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
            bot.reply_to(message, f"{err}\n\n<b>Usage:</b> <code>/dr 100 low</code>")
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
    except Exception as e: logging.error(f"DR Error: {e}")

@bot.message_handler(commands=['limbo'])
def cmd_limbo(message):
    try:
        if not is_bot_active(message): return
        user_id = message.from_user.id
        args = message.text.split()[1:]
        if len(args) < 2:
            bot.reply_to(message, "⚠️ Usage: <code>/limbo [amount/all] [target]</code>")
            return

        balance = get_balance(user_id)
        val1, val2 = args[0].lower(), args[1].lower()
        if val1 == "all": amount, target = balance, float(val2)
        elif val2 == "all": amount, target = balance, float(val1)
        else:
            try: amount, target = float(val1), float(val2)
            except ValueError: amount, target = float(val2), float(val1)

        if target < 1.01 or target > 100.0 or amount < MIN_BET or balance < amount:
            bot.reply_to(message, "❌ Invalid Amount or Target Multiplier (1.01x - 100.0x)!")
            return

        USER_BALANCES[user_id] -= amount
        actual_multiplier = round(random.uniform(1.00, 4.00) + (random.randint(1, 6) * 0.4), 2)
        win = actual_multiplier >= target

        if win:
            payout = amount * target
            USER_BALANCES[user_id] += payout
            status = f"🎉 <b>TARGET HIT! (WIN)</b>\n💰 Won: ₹{payout:.2f}"
        else:
            status = f"💥 <b>CRASHED BELOW TARGET!</b>\n🔻 Lost: ₹{amount:.2f}"

        bot.send_photo(
            chat_id=message.chat.id,
            photo=LIMBO_IMAGE_URL,
            caption=f"🚀 <b>LIMBO RESULT</b>\n\n🎯 Target: <b>{target:.2f}x</b>\n📈 Rolled: <b>{actual_multiplier:.2f}x</b>\n\n{status}\n💳 Balance: ₹{get_balance(user_id):.2f}",
            reply_to_message_id=message.message_id
        )
    except Exception as e: logging.error(f"Limbo Error: {e}")

@bot.message_handler(commands=['slots', 'slot'])
def cmd_slots(message):
    try:
        if not is_bot_active(message): return
        user_id = message.from_user.id
        args = message.text.split()[1:]

        # FLEXIBLE ARGUMENT SUPPORT: /slots amount rounds OR /slots rounds amount
        amount, rounds, err = parse_amount_and_number(args, user_id, min_num=1, max_num=10)
        if err:
            bot.reply_to(message, f"{err}\n\n<b>Usage:</b> <code>/slots 100 3</code> ya <code>/slots 3 100</code>")
            return

        total_cost = amount * rounds
        if get_balance(user_id) < total_cost:
            bot.reply_to(message, f"❌ {rounds} rounds ke liye ₹{total_cost:.2f} chahiye. Balance kam hai!")
            return

        USER_BALANCES[user_id] -= total_cost
        bot.reply_to(message, f"🎰 <b>Playing {rounds} Rounds of Slots!</b> (Total Bet: ₹{total_cost:.2f})")

        total_payout = 0.0
        for r in range(1, rounds + 1):
            msg = bot.send_dice(message.chat.id, emoji="🎰")
            val = msg.dice.value
            time.sleep(2.2)

            if val in [1, 22, 43, 64]:
                payout = amount * 5.0
                total_payout += payout
                bot.send_message(message.chat.id, f"Round {r}: 🎰 <b>JACKPOT 5X!</b> (+₹{payout:.2f})")
            elif val in [2, 3, 4, 10, 15, 20]:
                payout = amount * 1.5
                total_payout += payout
                bot.send_message(message.chat.id, f"Round {r}: 🎉 <b>WIN 1.5X!</b> (+₹{payout:.2f})")
            else:
                bot.send_message(message.chat.id, f"Round {r}: 💔 <b>LOST!</b>")

        USER_BALANCES[user_id] += total_payout
        bot.send_message(message.chat.id, f"🎰 <b>SLOTS FINISHED!</b>\n\nTotal Won: <b>₹{total_payout:.2f}</b>\n💳 Current Balance: <b>₹{get_balance(user_id):.2f}</b>")

    except Exception as e: logging.error(f"Slots Error: {e}")

# -------------------------------------------------------------
# PvP & BOT GAMES (/dice, /bowl, /basketball, /dart)
# -------------------------------------------------------------
def create_pvp_challenge(message, game_type, emoji, min_val=1, max_val=6):
    if not is_bot_active(message): return
    user_id = message.from_user.id
    args = message.text.split()[1:]

    amount, target_num, err = parse_amount_and_number(args, user_id, min_val, max_val)
    if err:
        bot.reply_to(message, f"{err}\n\n<b>Usage:</b> <code>/{game_type} [amount] [target/round]</code> or <code>/{game_type} [target/round] [amount]</code>")
        return

    USER_BALANCES[user_id] -= amount
    match_id = f"pvp_{game_type}_{user_id}_{int(time.time())}"

    PVP_MATCHES[match_id] = {
        "game": game_type,
        "emoji": emoji,
        "p1_id": user_id,
        "p1_name": message.from_user.first_name,
        "p2_id": None,
        "p2_name": None,
        "amount": amount,
        "target": target_num,
        "status": "WAITING"
    }

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("⚔️ Accept Match", callback_data=f"pvp_accept_{match_id}"),
        InlineKeyboardButton("🤖 Play with Bot", callback_data=f"pvp_bot_{match_id}")
    )
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data=f"pvp_cancel_{match_id}"))

    bot.reply_to(
        message,
        f"⚔️ <b>{game_type.upper()} MATCH CREATED!</b> {emoji}\n\n"
        f"👤 <b>Challenger:</b> {message.from_user.first_name}\n"
        f"🎯 <b>Target/Round:</b> {target_num}\n"
        f"💰 <b>Bet Amount:</b> ₹{amount:.2f}\n"
        f"🏆 <b>Total Pot:</b> ₹{(amount * 2):.2f}\n\n"
        f"<i>Group member accept karein ya 'Play with Bot' button dabein!</i>",
        reply_markup=markup
    )

@bot.message_handler(commands=['dice'])
def cmd_pvp_dice(message):
    create_pvp_challenge(message, "dice", "🎲", 1, 6)

@bot.message_handler(commands=['bowl', 'bowling'])
def cmd_pvp_bowl(message):
    create_pvp_challenge(message, "bowl", "🎳", 1, 6)

@bot.message_handler(commands=['basketball', 'bb'])
def cmd_pvp_bb(message):
    create_pvp_challenge(message, "basketball", "🏀", 1, 5)

@bot.message_handler(commands=['dart'])
def cmd_pvp_dart(message):
    create_pvp_challenge(message, "dart", "🎯", 1, 6)

@bot.callback_query_handler(func=lambda call: call.data.startswith("pvp_"))
def handle_pvp_callbacks(call):
    try:
        if not is_bot_active(call): return
        data = call.data.split("_")
        action = data[1]
        match_id = "_".join(data[2:])
        user_id = call.from_user.id

        if match_id not in PVP_MATCHES:
            bot.answer_callback_query(call.id, "❌ Match expired or completed!", show_alert=True)
            return

        match = PVP_MATCHES[match_id]

        if action == "cancel":
            if user_id != match["p1_id"] and user_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ Sirf Challenger cancel kar sakta hai!", show_alert=True)
                return

            USER_BALANCES[match["p1_id"]] += match["amount"]
            bot.edit_message_text(f"❌ <b>Match Cancelled!</b>\n💰 ₹{match['amount']:.2f} refunded.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            del PVP_MATCHES[match_id]
            return

        p2_is_bot = False
        if action == "bot":
            if user_id != match["p1_id"]:
                bot.answer_callback_query(call.id, "❌ Sirf Challenger bot option choose kar sakta hai!", show_alert=True)
                return
            p2_is_bot = True
            match["p2_id"] = "BOT"
            match["p2_name"] = "🤖 CASINO BOT"
            match["status"] = "PLAYING"

        elif action == "accept":
            if user_id == match["p1_id"]:
                bot.answer_callback_query(call.id, "❌ Apne hi challenge se khud nahi khel sakte! 'Play with Bot' choose karein.", show_alert=True)
                return

            if get_balance(user_id) < match["amount"]:
                bot.answer_callback_query(call.id, "❌ Wallet balance kam hai!", show_alert=True)
                return

            USER_BALANCES[user_id] -= match["amount"]
            match["p2_id"] = user_id
            match["p2_name"] = call.from_user.first_name
            match["status"] = "PLAYING"

        bot.edit_message_text(
            f"⚔️ <b>MATCH STARTED!</b> {match['emoji']}\n\n"
            f"🔴 <b>{match['p1_name']}</b> VS 🔵 <b>{match['p2_name']}</b>\n"
            f"🎯 Target/Rounds: <b>{match['target']}</b> | 💰 Pot: <b>₹{(match['amount']*2):.2f}</b>\n\n"
            f"🎲 <i>Action in progress...</i>",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

        # Player 1 Roll
        bot.send_message(call.message.chat.id, f"🔴 <b>{match['p1_name']}</b> rolling...")
        m1 = bot.send_dice(call.message.chat.id, emoji=match["emoji"])
        r1 = m1.dice.value
        time.sleep(2.5)

        # Player 2 / Bot Roll
        bot.send_message(call.message.chat.id, f"🔵 <b>{match['p2_name']}</b> rolling...")
        m2 = bot.send_dice(call.message.chat.id, emoji=match["emoji"])
        r2 = m2.dice.value
        time.sleep(2.5)

        diff1 = abs(r1 - match["target"])
        diff2 = abs(r2 - match["target"])
        total_pot = match["amount"] * 2.0

        if diff1 < diff2:
            USER_BALANCES[match["p1_id"]] += total_pot
            result_text = f"🏆 <b>{match['p1_name']} WON MATCH!</b>\n🔴 {match['p1_name']}: <b>{r1}</b>\n🔵 {match['p2_name']}: <b>{r2}</b>\n\n💰 Prize: <b>₹{total_pot:.2f}</b>"
        elif diff2 < diff1:
            if not p2_is_bot:
                USER_BALANCES[match["p2_id"]] += total_pot
            result_text = f"🏆 <b>{match['p2_name']} WON MATCH!</b>\n🔴 {match['p1_name']}: <b>{r1}</b>\n🔵 {match['p2_name']}: <b>{r2}</b>\n\n💰 Winner Pot Awarded!"
        else:
            USER_BALANCES[match["p1_id"]] += match["amount"]
            if not p2_is_bot:
                USER_BALANCES[match["p2_id"]] += match["amount"]
            result_text = f"🤝 <b>MATCH TIED!</b>\n🔴 {match['p1_name']}: <b>{r1}</b>\n🔵 {match['p2_name']}: <b>{r2}</b>\n\n💰 Refund issued."

        bot.send_message(call.message.chat.id, result_text)
        del PVP_MATCHES[match_id]

    except Exception as e:
        logging.error(f"PvP CB Error: {e}")

# -------------------------------------------------------------
# MENU & WALLET
# -------------------------------------------------------------
@bot.message_handler(commands=['games', 'help'])
def send_games_list(message):
    if not is_bot_active(message): return
    bot.reply_to(
        message, 
        f"🎰 <b>{BOT_NAME} GAMES MENU</b> 🎰\n\n"
        f"⚔️ <b>PVP / BOT GAMES (Group / Solo vs Bot):</b>\n"
        f"🎲 <b>Dice:</b> <code>/dice 100 4</code> or <code>/dice 4 100</code>\n"
        f"🎳 <b>Bowling:</b> <code>/bowl 100 6</code>\n"
        f"🏀 <b>Basketball:</b> <code>/basketball 100 4</code>\n"
        f"🎯 <b>Dart:</b> <code>/dart 100 5</code> or <code>/dart 5 100</code>\n\n"
        f"🕹️ <b>SOLO GAMES:</b>\n"
        f"🎲 <b>Dice Rush:</b> <code>/dr 100 low</code>\n"
        f"🚀 <b>Limbo:</b> <code>/limbo 100 2.0</code>\n"
        f"🎰 <b>Slots:</b> <code>/slots 100 3</code> or <code>/slots 3 100</code>\n\n"
        f"💳 <b>Wallet:</b> <code>/wallet</code>"
    )

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
# KEEP ALIVE SERVER & LOOP
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

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("⚡ BOT STARTED!")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            logging.error(f"Polling Crashed: {e}")
            time.sleep(3)
