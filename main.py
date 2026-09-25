import os
import telebot
import random
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
BOT_TOKEN = "8728557922:AAEJgnb_6gJEryp1x6bcy6ihB8MyvFlxUIw"
ADMIN_ID = 7995159553
UPI_ID = "Shudhanshu539@slc"
BOT_NAME = "DAVO CASINO"

MIN_BET = 10.0
MAX_BET = 300.0

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=True, num_threads=4)

USER_BALANCES = {}
USER_UPI = {}

# Active PvP Lobby Sessions
PVP_MATCHES = {}

# Bot Start/Stop Status Flag
BOT_ACTIVE = True

def get_balance(user_id):
    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 0.0
    return USER_BALANCES[user_id]

def is_bot_active(message_or_call):
    """Check if bot is active for general users."""
    user_id = message_or_call.from_user.id
    if not BOT_ACTIVE and user_id != ADMIN_ID:
        if isinstance(message_or_call, telebot.types.CallbackQuery):
            bot.answer_callback_query(message_or_call.id, "⚠️ Bot is currently paused for Maintenance by Admin!", show_alert=True)
        else:
            bot.reply_to(message_or_call, "⚠️ <b>Bot Maintenance me hai!</b>\nAdmin ne abhi games pause kiye hain, kripya kuch samay baad try karein.")
        return False
    return True

# -------------------------------------------------------------
# START & ADMIN CONTROL PANEL
# -------------------------------------------------------------
@bot.message_handler(commands=['start'])
def send_start(message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name

    if user_id == ADMIN_ID:
        markup = InlineKeyboardMarkup()
        btn_status = InlineKeyboardButton(
            "🔴 Stop Bot" if BOT_ACTIVE else "🟢 Start Bot", 
            callback_data="admin_toggle_bot"
        )
        markup.add(btn_status)

        bot.reply_to(
            message,
            f"🎰 <b>{BOT_NAME} ADMIN PANEL</b>\n\n"
            f"<b>Current Bot Status:</b> {'🟢 ACTIVE' if BOT_ACTIVE else '🔴 STOPPED (Maintenance)'}\n\n"
            f"<b>Admin Commands:</b>\n"
            f"• <code>/addbal user_id amount</code> — Add Balance\n"
            f"• <code>/cutbal user_id amount reason</code> — Deduct Balance\n\n"
            f"<i>Niche button se aap Bot ko Start/Stop kar sakte hain:</i>",
            reply_markup=markup
        )
    else:
        if not is_bot_active(message): return
        bot.reply_to(
            message,
            f"🎰 Welcome <b>{user_name}</b> to <b>{BOT_NAME}</b>!\n\n"
            f"🎮 Type <code>/games</code> to view games list.\n"
            f"💳 Type <code>/setupi your_upi@upi</code> to set UPI.\n"
            f"📤 Type <code>/withdraw amount</code> to withdraw money.\n"
            f"💸 Reply to any message with <code>/tip amount</code> to send money!"
        )

# Callback to toggle bot Start/Stop
@bot.callback_query_handler(func=lambda call: call.data == "admin_toggle_bot")
def handle_admin_toggle(call):
    global BOT_ACTIVE
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Admin only command!", show_alert=True)
        return

    BOT_ACTIVE = not BOT_ACTIVE
    status_text = "🟢 ACTIVE" if BOT_ACTIVE else "🔴 STOPPED (Maintenance)"
    btn_text = "🔴 Stop Bot" if BOT_ACTIVE else "🟢 Start Bot"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(btn_text, callback_data="admin_toggle_bot"))

    bot.edit_message_text(
        f"🎰 <b>{BOT_NAME} ADMIN PANEL</b>\n\n"
        f"<b>Current Bot Status:</b> {status_text}\n\n"
        f"<b>Admin Commands:</b>\n"
        f"• <code>/addbal user_id amount</code> — Add Balance\n"
        f"• <code>/cutbal user_id amount reason</code> — Deduct Balance",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )
    bot.answer_callback_query(call.id, f"Bot Status Changed to: {status_text}")

# -------------------------------------------------------------
# GAMES MENU & WALLET
# -------------------------------------------------------------
@bot.message_handler(commands=['games', 'help'])
def send_games_list(message):
    if not is_bot_active(message): return
    chat_type = message.chat.type
    
    games_text = (
        f"🎰 <b>{BOT_NAME} — ALL GAMES</b> 🎰\n\n"
        f"🏦 <b>Host Battle:</b> <code>/hb amount</code>\n"
        f"🎲 <b>PvP Dice Duel:</b> <code>/dice amount rounds</code>\n"
        f"🎳 <b>PvP Bowling Duel:</b> <code>/bowl amount rounds</code>\n"
        f"🏀 <b>PvP Basketball Duel:</b> <code>/basketball amount rounds</code>\n"
        f"🎯 <b>PvP Dart Duel:</b> <code>/dart amount rounds</code>\n"
        f"⚡ <b>Dice Rush (vs Bot):</b> <code>/dr amount high/low/even/odd</code>\n"
        f"🚀 <b>Limbo (vs Bot):</b> <code>/limbo amount target_x</code>\n"
        f"🏰 <b>Tower (vs Bot):</b> <code>/tower amount</code>"
    )

    if chat_type == 'private':
        games_text += (
            f"\n\n"
            f"💳 <b>Deposit:</b> <code>/deposit</code>\n"
            f"⚙️ <b>Set UPI:</b> <code>/setupi upi_id</code>\n"
            f"📤 <b>Withdraw:</b> <code>/withdraw amount</code>\n"
            f"💸 <b>Tip:</b> Reply with <code>/tip amount</code>\n"
            f"📌 <b>Wallet:</b> <code>/wallet</code>"
        )

    bot.reply_to(message, games_text)

@bot.message_handler(commands=['wallet', 'balance', 'bal'])
def check_wallet(message):
    if not is_bot_active(message): return
    user_id = message.from_user.id
    upi = USER_UPI.get(user_id, "Not Set (Use /setupi)")
    bot.reply_to(
        message, 
        f"💳 <b>{BOT_NAME} WALLET</b>\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💰 Balance: ₹{get_balance(user_id):.2f}\n"
        f"📱 UPI ID: <code>{upi}</code>"
    )

# -------------------------------------------------------------
# ADMIN BALANCE MANAGEMENT
# -------------------------------------------------------------
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
        bot.reply_to(message, f"✅ Added ₹{amount:.2f} to <code>{target_id}</code>\n💳 New Bal: ₹{USER_BALANCES[target_id]:.2f}")
        try:
            bot.send_message(target_id, f"🎉 <b>ADMIN ADDED BALANCE!</b>\n💰 Added: ₹{amount:.2f}\n💳 Bal: ₹{USER_BALANCES[target_id]:.2f}")
        except Exception: pass
    except ValueError:
        bot.reply_to(message, "❌ Invalid ID or Amount!")

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

# -------------------------------------------------------------
# REPLY TIP SYSTEM
# -------------------------------------------------------------
@bot.message_handler(commands=['tip'])
def cmd_tip(message):
    if not is_bot_active(message): return
    sender_id = message.from_user.id
    args = message.text.split()

    receiver_id = None
    amount = 0.0

    if message.reply_to_message:
        receiver_id = message.reply_to_message.from_user.id
        if len(args) < 2:
            bot.reply_to(message, "⚠️ Format: Reply to message with <code>/tip amount</code>")
            return
        try:
            amount = float(args[1])
        except ValueError:
            bot.reply_to(message, "❌ Invalid Amount!")
            return

    elif len(args) >= 3:
        try:
            receiver_id = int(args[1])
            amount = float(args[2])
        except ValueError:
            bot.reply_to(message, "❌ Invalid User ID or Amount!")
            return
    else:
        bot.reply_to(message, "⚠️ Reply to a user's message with <code>/tip amount</code> or use <code>/tip user_id amount</code>")
        return

    if receiver_id == sender_id:
        bot.reply_to(message, "❌ Aap khud ko tip nahi bhej sakte!")
        return

    if amount < 1.0:
        bot.reply_to(message, "❌ Minimum tip amount ₹1.00 hai.")
        return

    if get_balance(sender_id) < amount:
        bot.reply_to(message, "❌ Insufficient balance!")
        return

    USER_BALANCES[sender_id] -= amount
    USER_BALANCES[receiver_id] = get_balance(receiver_id) + amount

    bot.reply_to(
        message,
        f"💸 <b>TIP SENT SUCCESSFULLY!</b>\n\n"
        f"👤 Sent To: <code>{receiver_id}</code>\n"
        f"💰 Amount: ₹{amount:.2f}\n"
        f"💳 Remaining Bal: ₹{USER_BALANCES[sender_id]:.2f}"
    )

    try:
        bot.send_message(
            receiver_id,
            f"🎁 <b>YOU RECEIVED A TIP!</b>\n\n"
            f"👤 From: {message.from_user.full_name} (<code>{sender_id}</code>)\n"
            f"💰 Amount: ₹{amount:.2f}\n"
            f"💳 New Bal: ₹{USER_BALANCES[receiver_id]:.2f}"
        )
    except Exception: pass

# -------------------------------------------------------------
# UPI & WITHDRAW SYSTEM
# -------------------------------------------------------------
@bot.message_handler(commands=['setupi'])
def cmd_setupi(message):
    if not is_bot_active(message): return
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Format: <code>/setupi your_upi_id@upi</code>")
        return

    upi_id = args[1]
    USER_UPI[user_id] = upi_id
    bot.reply_to(message, f"✅ UPI ID Saved: <code>{upi_id}</code>")

@bot.message_handler(commands=['deposit'])
def cmd_deposit(message):
    if not is_bot_active(message): return
    user_id = message.from_user.id
    args = message.text.split()
    
    if len(args) < 2:
        bot.reply_to(
            message, 
            f"💳 <b>DEPOSIT MONEY</b>\n\n"
            f"1️⃣ Send amount to UPI: <code>{UPI_ID}</code>\n"
            f"2️⃣ Request balance add: <code>/deposit amount transaction_id</code>\n\n"
            f"<i>Example: /deposit 100 123456789012</i>"
        )
        return

    try:
        amount = float(args[1])
        txn_id = args[2] if len(args) > 2 else "N/A"
        
        if amount < MIN_BET:
            bot.reply_to(message, f"❌ Minimum deposit amount is ₹{MIN_BET:.2f}")
            return

        bot.reply_to(message, "⏳ Deposit request sent to Admin for verification!")
        
        bot.send_message(
            ADMIN_ID,
            f"📥 <b>NEW DEPOSIT REQUEST!</b>\n\n"
            f"👤 User: {message.from_user.full_name} (<code>{user_id}</code>)\n"
            f"💰 Amount: ₹{amount:.2f}\n"
            f"🔢 Txn ID: <code>{txn_id}</code>\n\n"
            f"<b>To Approve:</b>\n<code>/addbal {user_id} {amount}</code>"
        )
    except ValueError:
        bot.reply_to(message, "❌ Invalid Amount!")

@bot.message_handler(commands=['withdraw'])
def cmd_withdraw(message):
    if not is_bot_active(message): return
    user_id = message.from_user.id
    args = message.text.split()

    upi_id = USER_UPI.get(user_id)
    if not upi_id:
        bot.reply_to(message, "⚠️ Pehle apni UPI set karein using: <code>/setupi your_upi@upi</code>")
        return

    if len(args) < 2:
        bot.reply_to(message, "⚠️ Format: <code>/withdraw amount</code>")
        return

    try:
        amount = float(args[1])

        if amount < MIN_BET:
            bot.reply_to(message, f"❌ Minimum withdrawal amount is ₹{MIN_BET:.2f}")
            return

        if get_balance(user_id) < amount:
            bot.reply_to(message, "❌ Insufficient balance for withdrawal!")
            return

        USER_BALANCES[user_id] -= amount
        bot.reply_to(message, f"⏳ Withdrawal request of ₹{amount:.2f} submitted!\nAdmin approval ke baad transfer hoga.")

        markup = InlineKeyboardMarkup()
        btn_approve = InlineKeyboardButton("✅ Approve", callback_data=f"wd_app_{user_id}_{amount}")
        btn_reject = InlineKeyboardButton("❌ Reject & Refund", callback_data=f"wd_rej_{user_id}_{amount}")
        markup.add(btn_approve, btn_reject)

        bot.send_message(
            ADMIN_ID,
            f"📤 <b>NEW WITHDRAWAL REQUEST!</b>\n\n"
            f"👤 User: {message.from_user.full_name} (<code>{user_id}</code>)\n"
            f"💰 Amount: ₹{amount:.2f}\n"
            f"💳 UPI ID: <code>{upi_id}</code>",
            reply_markup=markup
        )
    except ValueError:
        bot.reply_to(message, "❌ Invalid Amount!")

@bot.callback_query_handler(func=lambda call: call.data.startswith("wd_"))
def handle_withdraw_callback(call):
    if call.from_user.id != ADMIN_ID: return

    data = call.data.split("_")
    action = data[1]
    target_id = int(data[2])
    amount = float(data[3])

    if action == "app":
        bot.edit_message_text(
            f"✅ <b>WITHDRAWAL APPROVED!</b>\n\n👤 User: <code>{target_id}</code>\n💰 Amount: ₹{amount:.2f}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        try:
            bot.send_message(target_id, f"🎉 <b>WITHDRAWAL SUCCESSFUL!</b>\n💰 ₹{amount:.2f} has been sent to your UPI ID!")
        except Exception: pass

    elif action == "rej":
        USER_BALANCES[target_id] = get_balance(target_id) + amount
        bot.edit_message_text(
            f"❌ <b>WITHDRAWAL REJECTED & REFUNDED!</b>\n\n👤 User: <code>{target_id}</code>\n💰 Refunded: ₹{amount:.2f}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
        try:
            bot.send_message(target_id, f"❌ <b>WITHDRAWAL REJECTED!</b>\n💰 ₹{amount:.2f} has been refunded back to your wallet.")
        except Exception: pass

# -------------------------------------------------------------
# BOT FUND STATUS
# -------------------------------------------------------------
@bot.message_handler(commands=['hb'])
def cmd_hb(message):
    if not is_bot_active(message): return
    bot.reply_to(
        message, 
        "🤖 <b>BOT FUND STATUS</b>\n\n"
        "🏦 <b>Balance:</b> $1,031.74\n"
        "✅ <b>Status:</b> Active — Bets Allowed!\n"
        "💎 <b>Network:</b> Davo Verse"
    )

# -------------------------------------------------------------
# PVP GAME CREATOR
# -------------------------------------------------------------
def create_pvp_game(message, game_type, emoji):
    if not is_bot_active(message): return
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        bot.reply_to(message, f"⚠️ Format: <code>/{game_type} amount rounds</code>\nExample: <code>/{game_type} 50 3</code>")
        return

    try:
        bet_amount = float(args[1])
        rounds = int(args[2])

        if bet_amount < MIN_BET or rounds < 1 or rounds > 5:
            bot.reply_to(message, "❌ Minimum Bet ₹10 and Rounds must be 1 to 5!")
            return

        if get_balance(user_id) < bet_amount:
            bot.reply_to(message, "❌ Insufficient Balance!")
            return

        match_id = f"{user_id}_{int(time.time())}"

        PVP_MATCHES[match_id] = {
            "game_type": game_type.upper(),
            "emoji": emoji,
            "bet": bet_amount,
            "rounds": rounds,
            "p1": user_id,
            "p1_name": message.from_user.first_name,
            "p2": None,
            "p2_name": None,
            "p1_rolls": [],
            "p2_rolls": [],
            "turn": None,
            "status": "WAITING",
            "chat_id": message.chat.id
        }

        markup = InlineKeyboardMarkup()
        btn_join = InlineKeyboardButton(f"🎮 Join Game (₹{bet_amount:.2f})", callback_data=f"pvp_join_{match_id}")
        btn_cancel = InlineKeyboardButton("❌ Cancel", callback_data=f"pvp_cancel_{match_id}")
        markup.add(btn_join, btn_cancel)

        bot.reply_to(
            message,
            f"{emoji} <b>PVP {game_type.upper()} DUEL LOBBY</b>\n\n"
            f"👤 <b>Host:</b> {message.from_user.first_name}\n"
            f"💰 <b>Entry Fee:</b> ₹{bet_amount:.2f}\n"
            f"🔄 <b>Rounds:</b> {rounds}\n\n"
            f"<i>Waiting for Opponent to join...</i>",
            reply_markup=markup
        )

    except ValueError:
        bot.reply_to(message, "❌ Invalid Bet or Rounds!")

@bot.message_handler(commands=['dice'])
def cmd_dice(message):
    create_pvp_game(message, "dice", "🎲")

@bot.message_handler(commands=['bowl'])
def cmd_bowl(message):
    create_pvp_game(message, "bowl", "🎳")

@bot.message_handler(commands=['basketball', 'bb'])
def cmd_bb(message):
    create_pvp_game(message, "basketball", "🏀")

@bot.message_handler(commands=['dart', 'darts'])
def cmd_dart(message):
    create_pvp_game(message, "dart", "🎯")

# -------------------------------------------------------------
# PVP CALLBACK HANDLER
# -------------------------------------------------------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("pvp_"))
def handle_pvp_callbacks(call):
    if not is_bot_active(call): return
    data = call.data.split("_")
    action = data[1]
    match_id = "_".join(data[2:])
    user_id = call.from_user.id

    if match_id not in PVP_MATCHES:
        bot.answer_callback_query(call.id, "❌ Game Expired or Invalid!", show_alert=True)
        return

    match = PVP_MATCHES[match_id]

    if action == "cancel":
        if user_id != match["p1"]:
            bot.answer_callback_query(call.id, "❌ Only Host can cancel this match!", show_alert=True)
            return
        del PVP_MATCHES[match_id]
        bot.edit_message_text("❌ <b>Game Cancelled by Host!</b>", chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if action == "join":
        if user_id == match["p1"]:
            bot.answer_callback_query(call.id, "❌ Aap khud ke game join nahi kar sakte!", show_alert=True)
            return

        if match["status"] != "WAITING":
            bot.answer_callback_query(call.id, "❌ Match already full!", show_alert=True)
            return

        if get_balance(user_id) < match["bet"]:
            bot.answer_callback_query(call.id, "❌ Balance kam hai!", show_alert=True)
            return

        if get_balance(match["p1"]) < match["bet"]:
            bot.answer_callback_query(call.id, "❌ Host ke paas sufficient balance nahi hai!", show_alert=True)
            del PVP_MATCHES[match_id]
            return

        USER_BALANCES[match["p1"]] -= match["bet"]
        USER_BALANCES[user_id] -= match["bet"]

        match["p2"] = user_id
        match["p2_name"] = call.from_user.first_name
        match["status"] = "PLAYING"
        match["turn"] = match["p1"]

        bot.edit_message_text(
            f"{match['emoji']} <b>PVP {match['game_type']} MATCH STARTED!</b>\n\n"
            f"🔴 <b>{match['p1_name']}</b> vs 🔵 <b>{match['p2_name']}</b>\n"
            f"💰 Prize Pool: ₹{(match['bet'] * 2 * 0.95):.2f}\n"
            f"🔄 Rounds: {match['rounds']}\n\n"
            f"👉 <b>{match['p1_name']}</b>, send/roll 1st {match['emoji']} now!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

# -------------------------------------------------------------
# INTERACTIVE PVP ROLLING HANDLER
# -------------------------------------------------------------
@bot.message_handler(content_types=['dice'])
def handle_pvp_rolls(message):
    if not is_bot_active(message): return
    user_id = message.from_user.id
    emoji = message.dice.emoji

    active_match = None
    for m_id, match in PVP_MATCHES.items():
        if match["status"] == "PLAYING" and user_id in [match["p1"], match["p2"]]:
            if match["emoji"] == emoji:
                active_match = match
                break

    if not active_match:
        return

    if user_id != active_match["turn"]:
        bot.reply_to(message, "⏳ Wait for your turn!")
        return

    val = message.dice.value

    if user_id == active_match["p1"]:
        active_match["p1_rolls"].append(val)
        curr_round = len(active_match["p1_rolls"])
        bot.send_message(message.chat.id, f"{active_match['emoji']} Round {curr_round}: <b>{active_match['p1_name']}</b> scored <b>{val}</b>!")

        active_match["turn"] = active_match["p2"]
        time.sleep(1)
        bot.send_message(message.chat.id, f"👉 <b>{active_match['p2_name']}</b>'s turn! Send {active_match['emoji']} now!")

    elif user_id == active_match["p2"]:
        active_match["p2_rolls"].append(val)
        curr_round = len(active_match["p2_rolls"])
        bot.send_message(message.chat.id, f"{active_match['emoji']} Round {curr_round}: <b>{active_match['p2_name']}</b> scored <b>{val}</b>!")

        if len(active_match["p2_rolls"]) == active_match["rounds"]:
            evaluate_pvp_match(active_match)
            for k, v in list(PVP_MATCHES.items()):
                if v == active_match:
                    del PVP_MATCHES[k]
                    break
        else:
            active_match["turn"] = active_match["p1"]
            time.sleep(1)
            bot.send_message(message.chat.id, f"👉 <b>{active_match['p1_name']}</b>'s turn! Send {active_match['emoji']} now!")

def evaluate_pvp_match(match):
    time.sleep(1)
    p1_wins, p2_wins = 0, 0
    p1_name, p2_name = match["p1_name"], match["p2_name"]

    summary = f"📊 <b>FINAL {match['game_type']} PVP RESULT</b>\n\n"
    for i in range(match["rounds"]):
        r1 = match["p1_rolls"][i]
        r2 = match["p2_rolls"][i]

        if r1 > r2:
            p1_wins += 1
            res = f" winner {p1_name}"
        elif r2 > r1:
            p2_wins += 1
            res = f" winner {p2_name}"
        else:
            res = " Tie"
        summary += f"Round {i+1}: {p1_name} ({r1}) vs {p2_name} ({r2}) ➔ {res}\n"

    total_pool = match["bet"] * 2
    win_amt = total_pool * 0.95

    if p1_wins > p2_wins:
        USER_BALANCES[match["p1"]] += win_amt
        summary += f"\n🎉 <b>WINNER: {p1_name}!</b>\n💰 Total Prize Won: ₹{win_amt:.2f}"
    elif p2_wins > p1_wins:
        USER_BALANCES[match["p2"]] += win_amt
        summary += f"\n🎉 <b>WINNER: {p2_name}!</b>\n💰 Total Prize Won: ₹{win_amt:.2f}"
    else:
        USER_BALANCES[match["p1"]] += match["bet"]
        USER_BALANCES[match["p2"]] += match["bet"]
        summary += f"\n🤝 <b>MATCH TIED!</b>\n💰 Both players refunded ₹{match['bet']:.2f}"

    bot.send_message(match["chat_id"], summary)

# -------------------------------------------------------------
# GAMES VS BOT (DICE RUSH, LIMBO, TOWER)
# -------------------------------------------------------------
@bot.message_handler(commands=['dr'])
def cmd_dr(message):
    if not is_bot_active(message): return
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
    if not is_bot_active(message): return
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

@bot.message_handler(commands=['tower'])
def cmd_tower(message):
    if not is_bot_active(message): return
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Format: <code>/tower amount</code>")
        return

    try:
        bet_amount = float(args[1])
        if bet_amount < MIN_BET or get_balance(user_id) < bet_amount:
            bot.reply_to(message, "❌ Low Balance!")
            return

        USER_BALANCES[user_id] -= bet_amount
        levels_cleared = 0
        for _ in range(3):
            if random.choice([True, False]):
                levels_cleared += 1
            else:
                break

        if levels_cleared > 0:
            multiplier = 1.5 ** levels_cleared
            win_amt = bet_amount * multiplier
            USER_BALANCES[user_id] += win_amt
            bot.reply_to(message, f"🏰 Cleared {levels_cleared} Levels!\n🎉 Multiplier: {multiplier:.2f}x | Won: ₹{win_amt:.2f}")
        else:
            bot.reply_to(message, f"💥 Tower Crashed on Level 1!\n🔻 Lost ₹{bet_amount:.2f}")
    except Exception: pass

# -------------------------------------------------------------
# DUMMY WEB SERVER FOR HOSTING
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
# START BOT ENGINE
# -------------------------------------------------------------
if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("⚡ DAVO CASINO FAST ENGINE ONLINE!")
    bot.infinity_polling(skip_pending=True)
