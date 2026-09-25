import os
import telebot
import random
import time
import threading
import logging
import urllib.parse
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
BOT_TOKEN = "8728557922:AAHjK4W2kxTAWhFnSEBAmA1Soj_wov3C1Kk"
ADMIN_ID = 7995159553
UPI_ID = "Shudhanshu539@slc"
BOT_NAME = "DAVO CASINO"

MIN_BET = 10.0
MAX_BET = 10000.0

# Aapka diya gaya Limbo Image File ID yahan set hai
LIMBO_IMAGE_URL = "AgACAgUAAxkBAAICKmq2gzs5GMIisCxAwPCiItZM6TElAALBE2sbz32wVfrsvGptNULkAQADAgADeQADPQQ"

# Webhook clear on startup to avoid conflict issues temporarily
try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=5)
    logging.info("Cleaned pending webhooks successfully.")
except Exception as e:
    logging.warning(f"Failed to clear webhook: {e}")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)

USER_BALANCES = {}
USER_UPI_IDS = {}
USER_WAITING_STATE = {}
PVP_MATCHES = {}
PENDING_WITHDRAWALS = {}

BOT_ACTIVE = True

# -------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------
def get_balance(user_id):
    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 0.0
    return USER_BALANCES[user_id]

def parse_amount_and_number(args, user_id, min_num=1, max_num=6):
    if len(args) < 1:
        return None, None, "⚠️ Amount aur Target/Round mention karein!"

    balance = get_balance(user_id)
    val1 = args[0].lower()
    val2 = args[1].lower() if len(args) > 1 else "1"

    amount = None
    target_num = None

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
            return None, None, f"❌ Valid Range: {min_num} - {max_num}"

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

@bot.message_handler(commands=['addbal'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID: return
    try:
        args = message.text.split()
        target_id, amount = int(args[1]), float(args[2])
        USER_BALANCES[target_id] = get_balance(target_id) + amount
        bot.reply_to(message, f"✅ Added ₹{amount:.2f} to <code>{target_id}</code>")
        try:
            bot.send_message(target_id, f"🎉 <b>₹{amount:.2f} credited to your wallet!</b>\n💳 Current Balance: ₹{get_balance(target_id):.2f}")
        except Exception: pass
    except Exception:
        bot.reply_to(message, "⚠️ Format: <code>/addbal user_id amount</code>")

# -------------------------------------------------------------
# MENU, WALLET & BOT FUND
# -------------------------------------------------------------
@bot.message_handler(commands=['games', 'help'])
def send_games_list(message):
    bot.reply_to(
        message, 
        f"🎰 <b>{BOT_NAME} MENU</b> 🎰\n\n"
        f"💳 <b>FINANCE COMMANDS:</b>\n"
        f"➕ <b>Deposit:</b> <code>/deposit amount</code>\n"
        f"➖ <b>Withdraw:</b> <code>/withdraw</code>\n"
        f"💳 <b>Wallet Balance:</b> <code>/wallet</code>\n"
        f"🏦 <b>Bot Fund:</b> <code>/hb</code>\n\n"
        f"⚔️ <b>PVP / BOT GAMES:</b>\n"
        f"🎲 <b>Dice:</b> <code>/dice 100 4</code>\n"
        f"🎳 <b>Bowling:</b> <code>/bowl 100 6</code>\n"
        f"🏀 <b>Basketball:</b> <code>/basketball 100 4</code>\n"
        f"🎯 <b>Dart:</b> <code>/dart 100 5</code>\n\n"
        f"🕹️ <b>SOLO GAMES:</b>\n"
        f"🎲 <b>Dice Rush:</b> <code>/dr 100 low</code>\n"
        f"🚀 <b>Limbo:</b> <code>/limbo 100 2.0</code>\n"
        f"🎰 <b>Slots:</b> <code>/slots 100 3</code>"
    )

@bot.message_handler(commands=['wallet', 'bal'])
def check_wallet(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"💳 <b>WALLET BALANCE:</b> ₹{get_balance(user_id):.2f}\n🆔 ID: <code>{user_id}</code>")

@bot.message_handler(commands=['hb', 'botfund'])
def cmd_bot_fund(message):
    try:
        bot.reply_to(
            message,
            "🤖 <b>BOT FUND</b>\n"
            "🏦 Balance: $1,451.83\n"
            "✅ Active — Bets Allowed!\n"
            "💎 Davo Verse"
        )
    except Exception as e:
        logging.error(f"HB Command Error: {e}")

# -------------------------------------------------------------
# DEPOSIT & WITHDRAWAL
# -------------------------------------------------------------
@bot.message_handler(commands=['deposit', 'dep'])
def cmd_deposit(message):
    try:
        args = message.text.split()[1:]
        if not args:
            bot.reply_to(message, "⚠️ Usage: <code>/deposit amount</code>\nExample: <code>/deposit 500</code>")
            return

        try:
            amount = float(args[0])
            if amount < 10:
                bot.reply_to(message, "❌ Minimum deposit ₹10 hai!")
                return
        except ValueError:
            bot.reply_to(message, "❌ Valid amount enter karein!")
            return

        user_id = message.from_user.id
        note = f"Dep_{user_id}_{int(time.time())}"
        upi_url = f"upi://pay?pa={UPI_ID}&pn={urllib.parse.quote(BOT_NAME)}&am={amount:.2f}&cu=INR&tn={note}"
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(upi_url)}"

        caption = (
            f"💳 <b>DEPOSIT REQUEST</b>\n\n"
            f"💰 <b>Amount:</b> ₹{amount:.2f}\n"
            f"📍 <b>UPI ID:</b> <code>{UPI_ID}</code>\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n\n"
            f"📸 <b>INSTRUCTIONS:</b>\n"
            f"1. QR Code scan karke ₹{amount:.2f} pay karein.\n"
            f"2. Payment hone ke baad <b>Payment Screenshot</b> is bot ko chat me bhej dein!\n"
            f"3. Screenshot aate hi Admin verify karke wallet me balance add kar dega."
        )

        bot.send_photo(message.chat.id, photo=qr_api_url, caption=caption, reply_to_message_id=message.message_id)
    except Exception as e:
        logging.error(f"Deposit Error: {e}")

@bot.message_handler(commands=['withdraw', 'wd'])
def cmd_withdraw_menu(message):
    try:
        user_id = message.from_user.id
        saved_upi = USER_UPI_IDS.get(user_id, "<i>Not Set</i>")
        balance = get_balance(user_id)

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📍 Set / Change UPI ID", callback_data="wd_set_upi"))
        markup.add(InlineKeyboardButton("💸 Withdraw Money", callback_data="wd_process_req"))

        text = (
            f"🏦 <b>WITHDRAWAL DASHBOARD</b>\n\n"
            f"💳 <b>Wallet Balance:</b> ₹{balance:.2f}\n"
            f"📍 <b>Saved UPI ID:</b> <code>{saved_upi}</code>\n\n"
            f"👇 Neeche diye gaye buttons par click karein:"
        )

        bot.reply_to(message, text, reply_markup=markup)
    except Exception as e:
        logging.error(f"WD Menu Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data in ["wd_set_upi", "wd_process_req"])
def handle_withdrawal_buttons(call):
    try:
        user_id = call.from_user.id

        if call.data == "wd_set_upi":
            USER_WAITING_STATE[user_id] = "WAITING_FOR_UPI"
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "✏️ <b>Apna UPI ID type karke chat me bhejein:</b>\n(Example: <code>9876543210@paytm</code> ya <code>name@upi</code>)")

        elif call.data == "wd_process_req":
            saved_upi = USER_UPI_IDS.get(user_id)
            if not saved_upi:
                bot.answer_callback_query(call.id, "❌ Pehle 'Set UPI ID' button daba kar UPI ID save karein!", show_alert=True)
                return

            balance = get_balance(user_id)
            if balance < 50:
                bot.answer_callback_query(call.id, "❌ Minimum withdrawal ₹50 hai!", show_alert=True)
                return

            USER_WAITING_STATE[user_id] = "WAITING_FOR_WD_AMOUNT"
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                f"💵 <b>Withdrawal Amount Enter Karein:</b>\n\n"
                f"💳 Balance: ₹{balance:.2f}\n"
                f"📍 UPI ID: <code>{saved_upi}</code>\n\n"
                f"<i>Jitna withdraw karna hai woh amount type karke chat me bhejein (Min: ₹50).</i>"
            )

    except Exception as e:
        logging.error(f"WD Button Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_app_") or call.data.startswith("wd_rej_"))
def handle_withdrawal_approval(call):
    try:
        if call.from_user.id != ADMIN_ID: return
        data = call.data.split("_")
        action = data[1]
        wd_id = "_".join(data[2:])

        if wd_id not in PENDING_WITHDRAWALS:
            bot.answer_callback_query(call.id, "❌ Request pehle hi process ho chuki hai!", show_alert=True)
            return

        wd_data = PENDING_WITHDRAWALS[wd_id]
        u_id = wd_data["user_id"]
        amt = wd_data["amount"]

        if action == "app":
            bot.edit_message_text(f"✅ <b>WITHDRAWAL APPROVED!</b>\n👤 User: {wd_data['user_name']}\n💰 Amount: ₹{amt:.2f}\n📍 UPI: {wd_data['upi']}", chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(u_id, f"🎉 <b>WITHDRAWAL SUCCESSFUL!</b>\n\n💰 ₹{amt:.2f} aapke UPI ID (<code>{wd_data['upi']}</code>) par bhej diye gaye hain.")
        
        elif action == "rej":
            USER_BALANCES[u_id] = get_balance(u_id) + amt
            bot.edit_message_text(f"❌ <b>WITHDRAWAL REJECTED!</b>\n💰 ₹{amt:.2f} refunded to user balance.", chat_id=call.message.chat.id, message_id=call.message.message_id)
            bot.send_message(u_id, f"❌ <b>WITHDRAWAL REJECTED!</b>\n\n💰 ₹{amt:.2f} aapke wallet me refund kar diye gaye hain.")

        del PENDING_WITHDRAWALS[wd_id]

    except Exception as e:
        logging.error(f"WD Approval Error: {e}")

# -------------------------------------------------------------
# SOLO GAMES (/dr, /limbo, /slots)
# -------------------------------------------------------------
@bot.message_handler(commands=['dr', 'dicerush'])
def cmd_dice_rush(message):
    try:
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
        user_id = message.from_user.id
        args = message.text.split()[1:]
        if len(args) < 2:
            bot.reply_to(message, "⚠️ Usage: <code>/limbo [amount/all] [target]</code>\nExample: <code>/limbo 100 2.0</code>")
            return

        balance = get_balance(user_id)
        val1, val2 = args[0].lower(), args[1].lower()
        
        amount = None
        target = None

        if val1 == "all":
            amount = balance
            try: target = float(val2)
            except ValueError: pass
        elif val2 == "all":
            amount = balance
            try: target = float(val1)
            except ValueError: pass
        else:
            try:
                v1, v2 = float(val1), float(val2)
                if v1 < 10 and v2 >= 10:
                    target, amount = v1, v2
                elif v2 < 10 and v1 >= 10:
                    target, amount = v2, v1
                else:
                    amount, target = v1, v2
            except ValueError:
                bot.reply_to(message, "❌ Valid numbers enter karein!")
                return

        if amount is None or target is None or target < 1.01 or target > 100.0:
            bot.reply_to(message, "❌ <b>Invalid Target Multiplier!</b> Target <b>1.01x se 100.0x</b> ke beech hona chahiye.")
            return

        if amount < MIN_BET:
            bot.reply_to(message, f"❌ Minimum bet ₹{MIN_BET:.0f} hai!")
            return

        if balance < amount or balance == 0:
            bot.reply_to(message, "❌ <b>Insufficient Balance!</b> Wallet me paisa kam hai.")
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

        result_caption = (
            f"🚀 <b>LIMBO RESULT</b>\n\n"
            f"🎯 Target: <b>{target:.2f}x</b>\n"
            f"📈 Rolled: <b>{actual_multiplier:.2f}x</b>\n\n"
            f"{status}\n"
            f"💳 Balance: ₹{get_balance(user_id):.2f}"
        )

        try:
            bot.send_photo(
                chat_id=message.chat.id,
                photo=LIMBO_IMAGE_URL,
                caption=result_caption,
                reply_to_message_id=message.message_id
            )
        except Exception:
            bot.reply_to(message, result_caption)

    except Exception as e: logging.error(f"Limbo Error: {e}")

@bot.message_handler(commands=['slots', 'slot'])
def cmd_slots(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()[1:]

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
# PVP & BOT GAMES (/dice, /bowl, /basketball, /dart)
# -------------------------------------------------------------
def create_pvp_challenge(message, game_type, emoji, min_val=1, max_val=6):
    user_id = message.from_user.id
    args = message.text.split()[1:]

    amount, target_num, err = parse_amount_and_number(args, user_id, min_val, max_val)
    if err:
        bot.reply_to(message, f"{err}\n\n<b>Usage:</b> <code>/{game_type} [amount] [target/round]</code>")
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
                bot.answer_callback_query(call.id, "❌ Apne hi challenge se khud nahi khel sakte!", show_alert=True)
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

        bot.send_message(call.message.chat.id, f"🔴 <b>{match['p1_name']}</b> rolling...")
        m1 = bot.send_dice(call.message.chat.id, emoji=match["emoji"])
        r1 = m1.dice.value
        time.sleep(2.5)

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
# COMBINED INPUT HANDLER (TEXT & PHOTO) WITH FILE ID TOOL FOR ADMIN
# -------------------------------------------------------------
@bot.message_handler(content_types=['text', 'photo'])
def handle_text_and_photos(message):
    try:
        user_id = message.from_user.id

        # Agar Admin ne photo bheji hai, toh bot uska File ID dega
        if message.content_type == 'photo' and user_id == ADMIN_ID and message.chat.type == 'private':
            file_id = message.photo[-1].file_id
            bot.reply_to(message, f"📸 <b>Aapka File ID yeh raha:</b>\n<code>{file_id}</code>")
            return

        if user_id in USER_WAITING_STATE:
            state = USER_WAITING_STATE.get(user_id)

            if message.content_type != 'text':
                bot.reply_to(message, "❌ Kripya text message me details bhejein!")
                return

            if state == "WAITING_FOR_UPI":
                upi_input = message.text.strip()
                if "@" not in upi_input or len(upi_input) < 5:
                    bot.reply_to(message, "❌ Valid UPI ID enter karein! (e.g. <code>9876543210@paytm</code>)")
                    return

                USER_UPI_IDS[user_id] = upi_input
                del USER_WAITING_STATE[user_id]

                markup = InlineKeyboardMarkup()
                markup.add(InlineKeyboardButton("💸 Withdraw Money Now", callback_data="wd_process_req"))
                bot.reply_to(message, f"✅ <b>UPI ID Saved Successfully!</b>\n\n📍 UPI ID: <code>{upi_input}</code>", reply_markup=markup)
                return

            elif state == "WAITING_FOR_WD_AMOUNT":
                try:
                    amount = float(message.text.strip())
                except ValueError:
                    bot.reply_to(message, "❌ Kripya numeric amount type karein (e.g., 500)!")
                    return

                balance = get_balance(user_id)
                if amount < 50:
                    bot.reply_to(message, "❌ Minimum withdrawal ₹50 hai!")
                    return
                if balance < amount:
                    bot.reply_to(message, f"❌ Insufficient Balance! Aapka balance ₹{balance:.2f} hai.")
                    return

                upi_details = USER_UPI_IDS.get(user_id)
                USER_BALANCES[user_id] -= amount
                del USER_WAITING_STATE[user_id]

                wd_id = f"wd_{user_id}_{int(time.time())}"
                PENDING_WITHDRAWALS[wd_id] = {
                    "user_id": user_id,
                    "user_name": message.from_user.full_name,
                    "amount": amount,
                    "upi": upi_details
                }

                bot.reply_to(message, f"✅ <b>Withdrawal Request Submitted!</b>\n\n💰 Amount: ₹{amount:.2f}\n📍 UPI: <code>{upi_details}</code>\n⏳ Status: Pending Admin Approval")

                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("✅ Approve", callback_data=f"wd_app_{wd_id}"),
                    InlineKeyboardButton("❌ Reject & Refund", callback_data=f"wd_rej_{wd_id}")
                )

                bot.send_message(
                    ADMIN_ID,
                    f"🚨 <b>NEW WITHDRAWAL REQUEST!</b>\n\n"
                    f"👤 <b>User:</b> {message.from_user.full_name} (<code>{user_id}</code>)\n"
                    f"💰 <b>Amount:</b> ₹{amount:.2f}\n"
                    f"📍 <b>UPI/Details:</b> <code>{upi_details}</code>\n"
                    f"🆔 <b>Request ID:</b> <code>{wd_id}</code>",
                    reply_markup=markup
                )
                return

        if message.content_type == 'photo' and message.chat.type == 'private':
            user_name = message.from_user.full_name
            bot.reply_to(message, "✅ <b>Payment Screenshot Received!</b>\n\nAdmin ko verify karne ke liye bhej diya gaya hai. Kuch hi minutes me balance add ho jayega.")
            
            caption = (
                f"📸 <b>NEW DEPOSIT SCREENSHOT!</b>\n\n"
                f"👤 <b>User:</b> {user_name} (@{message.from_user.username or 'NoUsername'})\n"
                f"🆔 <b>User ID:</b> <code>{user_id}</code>\n\n"
                f"<b>Quick Add Balance:</b>\n"
                f"<code>/addbal {user_id} AMOUNT</code>"
            )
            bot.send_photo(ADMIN_ID, photo=message.photo[-1].file_id, caption=caption)
            return

    except Exception as e:
        logging.error(f"Combined Handler Error: {e}")

# -------------------------------------------------------------
# KEEP ALIVE SERVER & BOT STARTUP
# -------------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"DAVO CASINO BOT ONLINE")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"🌐 Web Server Running on Port {port}")
    server.serve_forever()

def start_polling():
    print("⚡ Starting Telegram Bot Polling...")
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            logging.error(f"Polling Crashed: {e}")
            time.sleep(3)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=start_polling, daemon=True)
    bot_thread.start()
    run_web_server()
