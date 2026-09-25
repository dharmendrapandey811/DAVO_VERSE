import os
import telebot
import random
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
BOT_TOKEN = "8728557922:AAH_5paOID8O83VpF6sgoXas8qfQ97TwhnQ"
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
            f"🎮 Type <code>/games</code> to view all games.\n"
            f"💳 Type <code>/deposit</code> or <code>/withdraw</code> for payments.\n"
            f"💸 Type <code>/tip user_id amount</code> to send money to another user."
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
        f"2️⃣ <b>Multi Dice:</b> <code>/dice amount rounds</code>\n"
        f"3️⃣ <b>Bowling:</b> <code>/bowl amount rounds</code>\n"
        f"4️⃣ <b>Basketball:</b> <code>/basketball amount rounds</code>\n"
        f"5️⃣ <b>Tower:</b> <code>/tower amount</code>\n"
        f"6️⃣ <b>Limbo:</b> <code>/limbo amount target_x</code>\n\n"
        f"💳 <b>Deposit:</b> <code>/deposit</code>\n"
        f"📤 <b>Withdraw:</b> <code>/withdraw amount upi</code>\n"
        f"💸 <b>Tip:</b> <code>/tip user_id amount</code>\n"
        f"📌 <b>Wallet:</b> <code>/wallet</code>"
    )
    bot.reply_to(message, games_text)

@bot.message_handler(commands=['wallet', 'balance', 'bal'])
def check_wallet(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"💳 <b>{BOT_NAME} WALLET</b>\n🆔 ID: <code>{user_id}</code>\n💰 Balance: ₹{get_balance(user_id):.2f}")

# -------------------------------------------------------------
# TIP / TRANSFER SYSTEM
# -------------------------------------------------------------
@bot.message_handler(commands=['tip'])
def cmd_tip(message):
    sender_id = message.from_user.id
    args = message.text.split()

    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/tip user_id amount</code>\nExample: <code>/tip 123456789 50</code>")
        return

    try:
        receiver_id = int(args[1])
        amount = float(args[2])

        if receiver_id == sender_id:
            bot.reply_to(message, "❌ Aap khud ko tip nahi bhej sakte!")
            return

        if amount < 1.0:
            bot.reply_to(message, "❌ Minimum tip amount ₹1.00 hai.")
            return

        if get_balance(sender_id) < amount:
            bot.reply_to(message, "❌ Insufficient balance for tip!")
            return

        # Transfer process
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
        except Exception:
            pass

    except ValueError:
        bot.reply_to(message, "❌ Invalid User ID or Amount!")

# -------------------------------------------------------------
# DEPOSIT & WITHDRAW HANDLERS
# -------------------------------------------------------------
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

    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/withdraw amount upi_id</code>\nExample: <code>/withdraw 100 username@upi</code>")
        return

    try:
        amount = float(args[1])
        user_upi = args[2]

        if amount < MIN_BET:
            bot.reply_to(message, f"❌ Minimum withdrawal amount is ₹{MIN_BET:.2f}")
            return

        if get_balance(user_id) < amount:
            bot.reply_to(message, "❌ Insufficient balance for withdrawal!")
            return

        USER_BALANCES[user_id] -= amount
        bot.reply_to(message, f"✅ Withdrawal request of ₹{amount:.2f} submitted!\nAdmin process karega.")

        bot.send_message(
            ADMIN_ID,
            f"📤 <b>NEW WITHDRAWAL REQUEST!</b>\n\n"
            f"👤 User: {message.from_user.full_name} (<code>{user_id}</code>)\n"
            f"💰 Amount: ₹{amount:.2f}\n"
            f"💳 UPI: <code>{user_upi}</code>\n\n"
            f"<b>If Rejected (Refund):</b>\n<code>/addbal {user_id} {amount}</code>"
        )
    except ValueError:
        bot.reply_to(message, "❌ Invalid Amount!")

# -------------------------------------------------------------
# GAMES SECTION
# -------------------------------------------------------------

# 1. DICE RUSH
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

# 2. MULTI DICE
@bot.message_handler(commands=['dice'])
def cmd_dice(message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/dice amount rounds</code>")
        return

    try:
        bet_amount, rounds = float(args[1]), int(args[2])
        if bet_amount < MIN_BET or rounds < 1 or rounds > 5 or get_balance(user_id) < bet_amount * rounds:
            bot.reply_to(message, "❌ Invalid Bet, Rounds (1-5), or Low Balance!")
            return

        total_bet = bet_amount * rounds
        USER_BALANCES[user_id] -= total_bet
        wins = 0

        for _ in range(rounds):
            msg = bot.send_dice(message.chat.id, "🎲")
            if msg.dice.value >= 4:
                wins += 1
            time.sleep(2)

        win_amt = (bet_amount * 1.95) * wins
        USER_BALANCES[user_id] += win_amt
        bot.reply_to(message, f"🎲 Rounds Played: {rounds} | Wins: {wins}\n🎉 Total Returned: ₹{win_amt:.2f}")
    except Exception: pass

# 3. BOWLING
@bot.message_handler(commands=['bowl'])
def cmd_bowl(message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/bowl amount rounds</code>")
        return

    try:
        bet_amount, rounds = float(args[1]), int(args[2])
        if bet_amount < MIN_BET or rounds < 1 or rounds > 5 or get_balance(user_id) < bet_amount * rounds:
            bot.reply_to(message, "❌ Invalid Bet or Low Balance!")
            return

        USER_BALANCES[user_id] -= bet_amount * rounds
        strikes = 0

        for _ in range(rounds):
            msg = bot.send_dice(message.chat.id, "🎳")
            if msg.dice.value == 6:
                strikes += 1
            time.sleep(2)

        win_amt = (bet_amount * 3.0) * strikes
        USER_BALANCES[user_id] += win_amt
        bot.reply_to(message, f"🎳 Strikes: {strikes}/{rounds}\n🎉 Won: ₹{win_amt:.2f}")
    except Exception: pass

# 4. BASKETBALL
@bot.message_handler(commands=['basketball', 'bb'])
def cmd_basketball(message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "⚠️ Format: <code>/basketball amount rounds</code>")
        return

    try:
        bet_amount, rounds = float(args[1]), int(args[2])
        if bet_amount < MIN_BET or rounds < 1 or rounds > 5 or get_balance(user_id) < bet_amount * rounds:
            bot.reply_to(message, "❌ Invalid Bet or Low Balance!")
            return

        USER_BALANCES[user_id] -= bet_amount * rounds
        goals = 0

        for _ in range(rounds):
            msg = bot.send_dice(message.chat.id, "🏀")
            if msg.dice.value in [4, 5]:
                goals += 1
            time.sleep(2)

        win_amt = (bet_amount * 1.8) * goals
        USER_BALANCES[user_id] += win_amt
        bot.reply_to(message, f"🏀 Basket Scores: {goals}/{rounds}\n🎉 Won: ₹{win_amt:.2f}")
    except Exception: pass

# 5. TOWER
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

# 6. LIMBO
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
    threading.Thread(target=run_web_server, daemon=True).start()
    print("⚡ DAVO CASINO FAST ENGINE ONLINE!")
    bot.infinity_polling(skip_pending=True)
