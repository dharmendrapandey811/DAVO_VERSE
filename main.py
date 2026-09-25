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
BOT_TOKEN = "8728557922:AAHH_9UDQngNFHoa9tfjr1g47-M4n0CEzP8"
ADMIN_ID = 7995159553
UPI_ID = "Shudhanshu539@slc"
BOT_NAME = "DAVO CASINO"

MIN_BET = 10.0
MAX_BET = 300.0

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=True, num_threads=4)

USER_BALANCES = {}
USER_UPI = {}

# Active duel sessions
ACTIVE_DICE_GAMES = {}
ACTIVE_BOWL_GAMES = {}
ACTIVE_BB_GAMES = {}
ACTIVE_DART_GAMES = {}

def get_balance(user_id):
    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 0.0
    return USER_BALANCES[user_id]

# -------------------------------------------------------------
# START & GAMES MENU
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
            f"🎰 Welcome <b>{user_name}</b> to <b>{BOT_NAME}</b>!\n\n"
            f"🎮 Type <code>/games</code> to view games list.\n"
            f"💳 Type <code>/setupi your_upi@upi</code> to set UPI.\n"
            f"📤 Type <code>/withdraw amount</code> to withdraw money.\n"
            f"💸 Reply to any message with <code>/tip amount</code> to send money!"
        )

@bot.message_handler(commands=['games', 'help'])
def send_games_list(message):
    chat_type = message.chat.type  # 'private', 'group', or 'supergroup'
    
    # Base Games List (Group me itna hi dikhega)
    games_text = (
        f"🎰 <b>{BOT_NAME} — ALL GAMES</b> 🎰\n\n"
        f"🏦 <b>Host Battle:</b> <code>/hb amount</code>\n"
        f"🎲 <b>PvP Dice Duel:</b> <code>/dice amount rounds</code>\n"
        f"🎳 <b>Bowling Duel:</b> <code>/bowl amount rounds</code>\n"
        f"🏀 <b>Basketball Duel:</b> <code>/basketball amount rounds</code>\n"
        f"🎯 <b>Dart Duel:</b> <code>/dart amount rounds</code>\n"
        f"⚡ <b>Dice Rush:</b> <code>/dr amount high/low/even/odd</code>\n"
        f"🚀 <b>Limbo:</b> <code>/limbo amount target_x</code>\n"
        f"🏰 <b>Tower:</b> <code>/tower amount</code>"
    )

    # Private Bot PM me wallet / deposit / withdraw dikhega
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
# 1. BOT FUND DISPLAY (/hb)
# -------------------------------------------------------------
@bot.message_handler(commands=['hb'])
def cmd_hb(message):
    bot.reply_to(
        message, 
        "🤖 <b>BOT FUND STATUS</b>\n\n"
        "🏦 <b>Balance:</b> $1,031.74\n"
        "✅ <b>Status:</b> Active — Bets Allowed!\n"
        "💎 <b>Network:</b> Davo Verse"
    )

# -------------------------------------------------------------
# 2. PVP DICE DUEL (/dice)
# -------------------------------------------------------------
@bot.message_handler(commands=['dice'])
def cmd_dice(message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/dice amount rounds</code>\nExample: <code>/dice 50 3</code>")
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

        USER_BALANCES[user_id] -= bet_amount

        bot.reply_to(
            message,
            f"🎲 <b>DICE BATTLE STARTED!</b>\n"
            f"💰 Bet Amount: ₹{bet_amount:.2f}\n"
            f"🔄 Total Rounds: {rounds}\n\n"
            f"👉 <b>YOUR TURN! Send/Roll {rounds} Dice 🎲 now!</b>"
        )

        ACTIVE_DICE_GAMES[user_id] = {
            "bet": bet_amount,
            "total_rounds": rounds,
            "user_rolls": [],
            "bot_rolls": [],
            "chat_id": message.chat.id
        }

    except ValueError:
        bot.reply_to(message, "❌ Invalid Bet or Rounds!")

# -------------------------------------------------------------
# 3. BOWLING DUEL (/bowl)
# -------------------------------------------------------------
@bot.message_handler(commands=['bowl'])
def cmd_bowl(message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/bowl amount rounds</code>\nExample: <code>/bowl 50 3</code>")
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

        USER_BALANCES[user_id] -= bet_amount

        bot.reply_to(
            message,
            f"🎳 <b>BOWLING BATTLE STARTED!</b>\n"
            f"💰 Bet Amount: ₹{bet_amount:.2f}\n"
            f"🔄 Total Rounds: {rounds}\n\n"
            f"👉 <b>YOUR TURN! Send {rounds} Bowling 🎳 emoji now!</b>"
        )

        ACTIVE_BOWL_GAMES[user_id] = {
            "bet": bet_amount,
            "total_rounds": rounds,
            "user_rolls": [],
            "bot_rolls": [],
            "chat_id": message.chat.id
        }

    except ValueError:
        bot.reply_to(message, "❌ Invalid Bet or Rounds!")

# -------------------------------------------------------------
# 4. BASKETBALL DUEL (/basketball or /bb)
# -------------------------------------------------------------
@bot.message_handler(commands=['basketball', 'bb'])
def cmd_basketball(message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/basketball amount rounds</code>\nExample: <code>/bb 50 3</code>")
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

        USER_BALANCES[user_id] -= bet_amount

        bot.reply_to(
            message,
            f"🏀 <b>BASKETBALL BATTLE STARTED!</b>\n"
            f"💰 Bet Amount: ₹{bet_amount:.2f}\n"
            f"🔄 Total Rounds: {rounds}\n\n"
            f"👉 <b>YOUR TURN! Send {rounds} Basketball 🏀 emoji now!</b>"
        )

        ACTIVE_BB_GAMES[user_id] = {
            "bet": bet_amount,
            "total_rounds": rounds,
            "user_rolls": [],
            "bot_rolls": [],
            "chat_id": message.chat.id
        }

    except ValueError:
        bot.reply_to(message, "❌ Invalid Bet or Rounds!")

# -------------------------------------------------------------
# 5. DART DUEL (/dart or /darts)
# -------------------------------------------------------------
@bot.message_handler(commands=['dart', 'darts'])
def cmd_dart(message):
    user_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/dart amount rounds</code>\nExample: <code>/dart 50 3</code>")
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

        USER_BALANCES[user_id] -= bet_amount

        bot.reply_to(
            message,
            f"🎯 <b>DART BATTLE STARTED!</b>\n"
            f"💰 Bet Amount: ₹{bet_amount:.2f}\n"
            f"🔄 Total Rounds: {rounds}\n\n"
            f"👉 <b>YOUR TURN! Send {rounds} Dart 🎯 emoji now!</b>"
        )

        ACTIVE_DART_GAMES[user_id] = {
            "bet": bet_amount,
            "total_rounds": rounds,
            "user_rolls": [],
            "bot_rolls": [],
            "chat_id": message.chat.id
        }

    except ValueError:
        bot.reply_to(message, "❌ Invalid Bet or Rounds!")

# -------------------------------------------------------------
# INTERACTIVE GAME HANDLER FOR ROLL EMOJIS (DICE, BOWL, BB, DART)
# -------------------------------------------------------------
@bot.message_handler(content_types=['dice'])
def handle_all_interactive_rolls(message):
    user_id = message.from_user.id
    emoji = message.dice.emoji

    # 1. PVP DICE DUEL (🎲)
    if user_id in ACTIVE_DICE_GAMES and emoji == "🎲":
        game = ACTIVE_DICE_GAMES[user_id]
        user_val = message.dice.value
        game["user_rolls"].append(user_val)

        current_round = len(game["user_rolls"])
        bot.send_message(message.chat.id, f"🎯 Round {current_round}: You rolled <b>{user_val}</b>!")

        time.sleep(1)
        bot.send_message(message.chat.id, "🤖 Bot's turn to roll...")
        bot_msg = bot.send_dice(message.chat.id, "🎲")
        bot_val = bot_msg.dice.value
        game["bot_rolls"].append(bot_val)

        time.sleep(2)

        if len(game["user_rolls"]) == game["total_rounds"]:
            evaluate_duel_match(message.chat.id, user_id, game, "🎲 Dice")
            del ACTIVE_DICE_GAMES[user_id]
        return

    # 2. BOWLING DUEL (🎳)
    if user_id in ACTIVE_BOWL_GAMES and emoji == "🎳":
        game = ACTIVE_BOWL_GAMES[user_id]
        user_val = message.dice.value
        game["user_rolls"].append(user_val)

        current_round = len(game["user_rolls"])
        bot.send_message(message.chat.id, f"🎳 Round {current_round}: Your score <b>{user_val}</b>!")

        time.sleep(1)
        bot.send_message(message.chat.id, "🤖 Bot's turn to bowl...")
        bot_msg = bot.send_dice(message.chat.id, "🎳")
        bot_val = bot_msg.dice.value
        game["bot_rolls"].append(bot_val)

        time.sleep(2)

        if len(game["user_rolls"]) == game["total_rounds"]:
            evaluate_duel_match(message.chat.id, user_id, game, "🎳 Bowling")
            del ACTIVE_BOWL_GAMES[user_id]
        return

    # 3. BASKETBALL DUEL (🏀)
    if user_id in ACTIVE_BB_GAMES and emoji == "🏀":
        game = ACTIVE_BB_GAMES[user_id]
        user_val = message.dice.value
        game["user_rolls"].append(user_val)

        current_round = len(game["user_rolls"])
        bot.send_message(message.chat.id, f"🏀 Round {current_round}: Your basket score <b>{user_val}</b>!")

        time.sleep(1)
        bot.send_message(message.chat.id, "🤖 Bot's turn to shoot...")
        bot_msg = bot.send_dice(message.chat.id, "🏀")
        bot_val = bot_msg.dice.value
        game["bot_rolls"].append(bot_val)

        time.sleep(2)

        if len(game["user_rolls"]) == game["total_rounds"]:
            evaluate_duel_match(message.chat.id, user_id, game, "🏀 Basketball")
            del ACTIVE_BB_GAMES[user_id]
        return

    # 4. DART DUEL (🎯)
    if user_id in ACTIVE_DART_GAMES and emoji == "🎯":
        game = ACTIVE_DART_GAMES[user_id]
        user_val = message.dice.value
        game["user_rolls"].append(user_val)

        current_round = len(game["user_rolls"])
        bot.send_message(message.chat.id, f"🎯 Round {current_round}: Your dart score <b>{user_val}</b>!")

        time.sleep(1)
        bot.send_message(message.chat.id, "🤖 Bot's turn to throw dart...")
        bot_msg = bot.send_dice(message.chat.id, "🎯")
        bot_val = bot_msg.dice.value
        game["bot_rolls"].append(bot_val)

        time.sleep(2)

        if len(game["user_rolls"]) == game["total_rounds"]:
            evaluate_duel_match(message.chat.id, user_id, game, "🎯 Dart")
            del ACTIVE_DART_GAMES[user_id]
        return

# COMMON MATCH RESULT EVALUATOR
def evaluate_duel_match(chat_id, user_id, game, game_name):
    user_wins = 0
    bot_wins = 0

    summary = f"📊 <b>FINAL {game_name.upper()} RESULT</b>\n\n"
    for i in range(game["total_rounds"]):
        u_r = game["user_rolls"][i]
        b_r = game["bot_rolls"][i]
        if u_r > b_r:
            user_wins += 1
            res = " You Won"
        elif b_r > u_r:
            bot_wins += 1
            res = " Bot Won"
        else:
            res = " Tie"
        summary += f"Round {i+1}: You ({u_r}) vs Bot ({b_r}) ➔ {res}\n"

    if user_wins > bot_wins:
        win_amt = game["bet"] * 1.95
        USER_BALANCES[user_id] += win_amt
        summary += f"\n🎉 <b>YOU WON THE MATCH!</b>\n💰 Total Prize: ₹{win_amt:.2f}"
    elif bot_wins > user_wins:
        summary += f"\n💥 <b>BOT WON THE MATCH!</b>\n🔻 You Lost: ₹{game['bet']:.2f}"
    else:
        USER_BALANCES[user_id] += game["bet"]
        summary += f"\n🤝 <b>MATCH TIED!</b>\n💰 Bet Refunded: ₹{game['bet']:.2f}"

    bot.send_message(chat_id, summary)

# -------------------------------------------------------------
# NON-INTERACTIVE GAMES (DR, LIMBO, TOWER)
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

@bot.message_handler(commands=['tower'])
def cmd_tower(message):
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
# DUMMY WEB SERVER FOR HOSTING (RENDER / REPLIT / HEROKU)
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
