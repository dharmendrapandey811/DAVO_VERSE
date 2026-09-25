import telebot
import random
import time

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

@bot.message_handler(commands=['start'])
def send_start(message):
    user_id = message.from_user.id
    if user_id == ADMIN_ID:
        bot.reply_to(message, f"🎰 <b>{BOT_NAME} ADMIN PANEL</b>\n\n• <code>/addbal user_id amount</code>\n• <code>/cutbal user_id amount reason</code>")
    else:
        bot.reply_to(message, f"🎰 Welcome to <b>{BOT_NAME}</b>!\n🎮 Type <code>/games</code> for options.")

@bot.message_handler(commands=['addbal'])
def admin_add_balance(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    try:
        target_id, amount = int(args[1]), float(args[2])
        USER_BALANCES[target_id] = get_balance(target_id) + amount
        bot.reply_to(message, f"✅ Added ₹{amount:.2f} to {target_id}")
    except Exception: pass

@bot.message_handler(commands=['cutbal'])
def admin_cut_balance(message):
    if message.from_user.id != ADMIN_ID: return
    args = message.text.split()
    if len(args) < 3: return
    try:
        target_id, amount = int(args[1]), float(args[2])
        USER_BALANCES[target_id] = max(0.0, get_balance(target_id) - amount)
        bot.reply_to(message, f"✂️ Deducted ₹{amount:.2f} from {target_id}")
    except Exception: pass

@bot.message_handler(commands=['wallet', 'balance', 'bal'])
def check_wallet(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"💳 <b>Wallet:</b> ₹{get_balance(user_id):.2f}")

@bot.message_handler(commands=['dr'])
def cmd_dr(message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) < 3: return
    try:
        bet_amount, bet_type = float(args[1]), args[2].lower()
        if get_balance(user_id) < bet_amount:
            bot.reply_to(message, "❌ Low balance!")
            return
        USER_BALANCES[user_id] -= bet_amount
        dice_msg = bot.send_dice(message.chat.id, "🎲")
        val = dice_msg.dice.value
        win = (bet_type == "high" and val >= 4) or (bet_type == "low" and val <= 3) or (bet_type == "even" and val % 2 == 0) or (bet_type == "odd" and val % 2 != 0)
        if win:
            win_amt = bet_amount * 1.95
            USER_BALANCES[user_id] += win_amt
            bot.reply_to(message, f"🎲 Result: <b>{val}</b> | 🎉 WON ₹{win_amt:.2f}!")
        else:
            bot.reply_to(message, f"🎲 Result: <b>{val}</b> | 🔻 LOST ₹{bet_amount:.2f}!")
    except Exception: pass

if __name__ == "__main__":
    print("⚡ Fast Engine Online!")
    bot.infinity_polling(skip_pending=True)
