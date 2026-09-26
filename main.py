import os
import telebot
import random
import time
import threading
import logging
import requests
import io
from PIL import Image, ImageDraw, ImageFont
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

# -------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------
BOT_TOKEN = "8728557922:AAFlVRiM0THMLr7es_uLIM0PZUfJrBtTOGU"
ADMIN_ID = 7995159553
UPI_ID = "Shudhanshu539@slc"
BOT_NAME = "DAVO CASINO"

MIN_BET = 10.0
MAX_BET = 10000.0

try:
    requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true", timeout=3)
    logging.info("Cleaned pending webhooks successfully.")
except Exception as e:
    logging.warning(f"Failed to clear webhook: {e}")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML", threaded=False)

USER_BALANCES = {}
USER_UPI_IDS = {}
USER_WAITING_STATE = {}
PVP_MATCHES = {}
ESCROW_DEALS = {}

BOT_ACTIVE = True

# -------------------------------------------------------------
# DECORATORS & HELPERS
# -------------------------------------------------------------
def restricted_command(func):
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        if user_id != ADMIN_ID and not BOT_ACTIVE:
            bot.reply_to(message, "⚠️ <b>Bot is currently stopped by the Admin.</b> Please try again later.")
            return
        return func(message, *args, **kwargs)
    return wrapper

def restricted_callback(func):
    def wrapper(call, *args, **kwargs):
        user_id = call.from_user.id
        if user_id != ADMIN_ID and not BOT_ACTIVE:
            bot.answer_callback_query(call.id, "❌ Bot is currently stopped by Admin!", show_alert=True)
            return
        return func(call, *args, **kwargs)
    return wrapper

def get_balance(user_id):
    if user_id not in USER_BALANCES:
        USER_BALANCES[user_id] = 0.0
    return USER_BALANCES[user_id]

def parse_pvp_args(args, user_id):
    if len(args) < 1:
        return None, None, "⚠️ Amount mention karein! (Example: <code>/bowl 100</code> ya <code>/bowl 100 3</code>)"

    balance = get_balance(user_id)
    val1 = args[0].lower()
    val2 = args[1].lower() if len(args) > 1 else None

    amount = None
    rounds = 1

    try:
        if len(args) >= 2:
            p1, p2 = float(args[0]), float(args[1])
            if 1 <= p1 <= 5 and p1.is_integer() and p2 > 5:
                rounds, amount = int(p1), p2
            elif 1 <= p2 <= 5 and p2.is_integer() and p1 > 5:
                rounds, amount = int(p2), p1
            else:
                amount, rounds = p1, int(p2) if p2.is_integer() else 1
        elif len(args) == 1:
            if val1 == "all":
                amount = balance
            else:
                amount = float(args[0])
            rounds = 1
    except Exception:
        pass

    if amount is None or amount <= 0:
        return None, None, "❌ Invalid Amount!"
    if amount < MIN_BET:
        return None, None, f"❌ Minimum bet ₹{MIN_BET:.0f} hai!"
    if amount > MAX_BET and amount != balance:
        return None, None, f"❌ Maximum bet ₹{MAX_BET:.0f} hai!"
    if balance < amount or balance == 0:
        return None, None, "❌ <b>Insufficient Balance!</b> Wallet me paisa kam hai."
    if rounds < 1 or rounds > 5:
        return None, None, "❌ Rounds 1 se 5 ke beech hone chahiye!"

    return amount, rounds, None

# -------------------------------------------------------------
# START, STOP & ADMIN COMMANDS
# -------------------------------------------------------------
@bot.message_handler(commands=['start'])
def send_start(message):
    try:
        global BOT_ACTIVE
        user_id = message.from_user.id
        user_name = message.from_user.full_name

        if user_id == ADMIN_ID:
            BOT_ACTIVE = True
            markup = InlineKeyboardMarkup()
            btn_status = InlineKeyboardButton("🔴 Stop Bot", callback_data="admin_toggle_bot")
            markup.add(btn_status)
            bot.reply_to(message, f"🟢 <b>Bot is now STARTED & ACTIVE!</b>\n\n🎰 <b>{BOT_NAME} ADMIN PANEL</b>\nStatus: ACTIVE\n\n• <code>/addbal user_id amount</code>", reply_markup=markup)
        else:
            if not BOT_ACTIVE:
                bot.reply_to(message, "⚠️ <b>Bot is currently stopped by the Admin.</b> Please try again later.")
                return
            bot.reply_to(message, f"🎰 Welcome <b>{user_name}</b> to <b>{BOT_NAME}</b>!\n\n🎮 Games list dekhne ke liye <code>/games</code> type karein.")
    except Exception as e:
        logging.error(f"Start Error: {e}")

@bot.message_handler(commands=['stop'])
def send_stop(message):
    try:
        global BOT_ACTIVE
        user_id = message.from_user.id
        if user_id == ADMIN_ID:
            BOT_ACTIVE = False
            markup = InlineKeyboardMarkup()
            btn_status = InlineKeyboardButton("🟢 Start Bot", callback_data="admin_toggle_bot")
            markup.add(btn_status)
            bot.reply_to(message, f"🔴 <b>Bot is now STOPPED!</b>\n\nNo users can play games now. Type <code>/start</code> to resume.", reply_markup=markup)
        else:
            bot.reply_to(message, "❌ You are not authorized to stop the bot.")
    except Exception as e:
        logging.error(f"Stop Error: {e}")

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
        bot.answer_callback_query(call.id, f"Bot status changed to {status_text}")
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
# BOT FUND (/hb)
# -------------------------------------------------------------
@bot.message_handler(commands=['hb'])
@restricted_command
def send_bot_fund(message):
    bot.reply_to(
        message,
        "<b>❄️ Bot Fund = $1,471.81</b>\n"
        "<b>🏛 Bet active!</b>\n"
        "<b>🧿 Davo Verse</b>"
    )

# -------------------------------------------------------------
# DEPOSIT & WITHDRAWAL SYSTEM
# -------------------------------------------------------------
@bot.message_handler(commands=['deposit'])
@restricted_command
def cmd_deposit(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📥 Enter Deposit Amount", callback_data="dep_amount"))
    
    bot.reply_to(
        message,
        f"💳 <b>DEPOSIT MONEY</b>\n\n"
        f"📍 <b>UPI ID:</b> <code>{UPI_ID}</code>\n"
        f"📲 Niche diye gaye button par click karke amount enter karein aur payment karke receipt bhejein.",
        reply_markup=markup
    )

@bot.message_handler(commands=['withdraw'])
@restricted_command
def cmd_withdraw(message):
    user_id = message.from_user.id
    current_upi = USER_UPI_IDS.get(user_id, "Not Set")
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✏️ Set / Change UPI", callback_data="wd_set_upi"),
        InlineKeyboardButton("📤 Withdraw Amount", callback_data="wd_amount")
    )
    
    bot.reply_to(
        message,
        f"💸 <b>WITHDRAWAL PANEL</b>\n\n"
        f"💳 Your Saved UPI: <code>{current_upi}</code>\n"
        f"💰 Balance: ₹{get_balance(user_id):.2f}\n\n"
        f"Apna UPI set karne ya withdraw karne ke liye niche buttons ka use karein:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data in ["dep_amount", "wd_set_upi", "wd_amount"])
@restricted_callback
def handle_wallet_callbacks(call):
    user_id = call.from_user.id
    if call.data == "dep_amount":
        USER_WAITING_STATE[user_id] = "waiting_deposit"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📥 Kitna deposit karna hai? Amount type karke bhejein (jaise: <code>500</code>):")
    elif call.data == "wd_set_upi":
        USER_WAITING_STATE[user_id] = "waiting_upi"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "✏️ Apna sahi UPI ID type karke bhejein (jaise: <code>username@okhdfcbank</code>):")
    elif call.data == "wd_amount":
        if user_id not in USER_UPI_IDS:
            bot.answer_callback_query(call.id, "❌ Pehle apna UPI ID set karein!", show_alert=True)
            return
        USER_WAITING_STATE[user_id] = "waiting_withdraw"
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"📤 Kitna amount withdraw karna hai? (Balance: ₹{get_balance(user_id):.2f}):")

# -------------------------------------------------------------
# ESCROW & TIP SYSTEM
# -------------------------------------------------------------
@bot.message_handler(commands=['escrow'])
@restricted_command
def cmd_escrow(message):
    try:
        if not message.reply_to_message:
            bot.reply_to(message, "⚠️ Kripya kisi user ke message par reply karke likhein: <code>/escrow 50</code>")
            return
        
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ Usage: <code>/escrow 50</code> (reply karke)")
            return
            
        amount = float(args[1])
        sender_id = message.from_user.id
        receiver_id = message.reply_to_message.from_user.id
        receiver_name = message.reply_to_message.from_user.first_name

        if sender_id == receiver_id:
            bot.reply_to(message, "❌ Aap khud ke sath escrow nahi kar sakte!")
            return
        if get_balance(sender_id) < amount:
            bot.reply_to(message, "❌ Aapke wallet me itna balance nahi hai!")
            return

        USER_BALANCES[sender_id] -= amount
        deal_id = f"escrow_{int(time.time())}"
        ESCROW_DEALS[deal_id] = {
            "sender": sender_id,
            "receiver": receiver_id,
            "amount": amount
        }

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Release", callback_data=f"esc_rel_{deal_id}"),
            InlineKeyboardButton("❌ Refund", callback_data=f"esc_ref_{deal_id}")
        )

        bot.reply_to(
            message,
            f"🤝 <b>ESCROW CREATED!</b>\n\n"
            f"👤 From: {message.from_user.first_name}\n"
            f"👤 To: {receiver_name}\n"
            f"💰 Amount: ₹{amount:.2f}\n\n"
            f"<i>Paisa hold par hai. Kaam hone par Release ya Refund karein.</i>",
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"Escrow Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("esc_"))
@restricted_callback
def handle_escrow_callbacks(call):
    data = call.data.split("_")
    action = data[1]
    deal_id = "_".join(data[2:])
    user_id = call.from_user.id

    if deal_id not in ESCROW_DEALS:
        bot.answer_callback_query(call.id, "❌ Deal expired or completed!", show_alert=True)
        return

    deal = ESCROW_DEALS[deal_id]
    if user_id != deal["sender"] and user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Sirf sender ya admin yeh action le sakta hai!", show_alert=True)
        return

    if action == "rel":
        USER_BALANCES[deal["receiver"]] = get_balance(deal["receiver"]) + deal["amount"]
        bot.edit_message_text(f"✅ <b>ESCROW RELEASED!</b>\n💰 ₹{deal['amount']:.2f} successfully transferred.", chat_id=call.message.chat.id, message_id=call.message.message_id)
    else:
        USER_BALANCES[deal["sender"]] = get_balance(deal["sender"]) + deal["amount"]
        bot.edit_message_text(f"❌ <b>ESCROW REFUNDED!</b>\n💰 ₹{deal['amount']:.2f} returned to sender.", chat_id=call.message.chat.id, message_id=call.message.message_id)
    
    del ESCROW_DEALS[deal_id]

@bot.message_handler(commands=['tip'])
@restricted_command
def cmd_tip(message):
    try:
        if not message.reply_to_message:
            bot.reply_to(message, "⚠️ Kripya kisi ke message par reply karke <code>/tip 50</code> likhein!")
            return
            
        args = message.text.split()
        if len(args) < 2:
            bot.reply_to(message, "⚠️ Usage: <code>/tip 50</code> (reply karke)")
            return
            
        amount = float(args[1])
        sender_id = message.from_user.id
        receiver_id = message.reply_to_message.from_user.id
        receiver_name = message.reply_to_message.from_user.first_name

        if sender_id == receiver_id:
            bot.reply_to(message, "❌ Khud ko tip nahi de sakte!")
            return
        if get_balance(sender_id) < amount:
            bot.reply_to(message, "❌ Insufficient balance for tip!")
            return

        USER_BALANCES[sender_id] -= amount
        USER_BALANCES[receiver_id] = get_balance(receiver_id) + amount

        bot.reply_to(
            message,
            f"🎁 <b>TIP SUCCESSFUL!</b>\n\n"
            f"👤 From: {message.from_user.first_name}\n"
            f"👤 To: {receiver_name}\n"
            f"💰 Amount: <b>₹{amount:.2f}</b> sent!"
        )
    except Exception as e:
        logging.error(f"Tip Error: {e}")

# -------------------------------------------------------------
# TEXT INPUT HANDLER
# -------------------------------------------------------------
@bot.message_handler(func=lambda msg: msg.from_user.id in USER_WAITING_STATE)
def handle_text_inputs(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID and not BOT_ACTIVE:
        return
        
    state = USER_WAITING_STATE[user_id]
    text = message.text.strip()

    if state == "waiting_upi":
        USER_UPI_IDS[user_id] = text
        del USER_WAITING_STATE[user_id]
        bot.reply_to(message, f"✅ <b>UPI saved successfully!</b>\n💳 UPI: <code>{text}</code>")

    elif state == "waiting_deposit":
        try:
            amount = float(text)
            del USER_WAITING_STATE[user_id]
            bot.reply_to(
                message,
                f"📥 <b>DEPOSIT REQUEST REGISTERED</b>\n\n"
                f"💰 Amount: ₹{amount:.2f}\n"
                f"📍 Send payment to UPI: <code>{UPI_ID}</code>\n\n"
                f"⚠️ <i>Payment karne ke baad payment ki screenshot yahin bhej dein.</i>"
            )
        except ValueError:
            bot.reply_to(message, "❌ Invalid amount!")

    elif state == "waiting_withdraw":
        try:
            amount = float(text)
            del USER_WAITING_STATE[user_id]
            balance = get_balance(user_id)
            if amount < 50:
                bot.reply_to(message, "❌ Minimum withdrawal ₹50 hai!")
                return
            if balance < amount:
                bot.reply_to(message, "❌ Insufficient balance!")
                return
            
            USER_BALANCES[user_id] -= amount
            upi = USER_UPI_IDS.get(user_id)
            bot.reply_to(message, f"📤 <b>Withdrawal Request Placed!</b>\n💰 Amount: ₹{amount:.2f}\n💳 UPI: <code>{upi}</code>")
        except ValueError:
            bot.reply_to(message, "❌ Invalid amount!")

# -------------------------------------------------------------
# MENU & WALLET SYSTEM
# -------------------------------------------------------------
@bot.message_handler(commands=['games', 'help'])
@restricted_command
def send_games_list(message):
    bot.reply_to(
        message, 
        f"🎰 <b>{BOT_NAME} MENU</b> 🎰\n\n"
        f"💳 <b>WALLET:</b> Balance: <code>/wallet</code> | Deposit: <code>/deposit</code> | Withdraw: <code>/withdraw</code>\n"
        f"❄️ Bot Fund: <code>/hb</code> | Escrow: <code>/escrow 50</code> | Tip: <code>/tip 50</code>\n\n"
        f"⚔️ <b>PVP GAMES:</b> <code>/dice 100</code> | <code>/bowl 100</code> | <code>/basketball 100</code> | <code>/dart 100</code>\n\n"
        f"🕹️ <b>SOLO GAMES:</b>\n"
        f"🎲 <b>Dice Rush:</b> <code>/dr 100 low</code>\n"
        f"🚀 <b>Limbo:</b> <code>/limbo 100 2.0</code>\n"
        f"🎰 <b>Slots:</b> <code>/slots 100 3</code>"
    )

@bot.message_handler(commands=['wallet', 'bal'])
@restricted_command
def check_wallet(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"💳 <b>WALLET BALANCE:</b> ₹{get_balance(user_id):.2f}\n🆔 ID: <code>{user_id}</code>")

# -------------------------------------------------------------
# SOLO GAMES (/dr, /limbo with PIL image card, /slots)
# -------------------------------------------------------------
@bot.message_handler(commands=['dr', 'dicerush'])
@restricted_command
def cmd_dice_rush(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()[1:]
        valid_choices = ["low", "high", "even", "odd"]
        
        if len(args) < 2:
            bot.reply_to(message, "⚠️ Format: <code>/dr 100 low</code>")
            return
            
        val1, val2 = args[0].lower(), args[1].lower()
        balance = get_balance(user_id)
        amount, choice = None, None

        if val1 == "all":
            amount = balance
            if val2 in valid_choices: choice = val2
        elif val2 == "all":
            amount = balance
            if val1 in valid_choices: choice = val1
        else:
            for val in [val1, val2]:
                if val in valid_choices: choice = val
                else:
                    try: amount = float(val)
                    except ValueError: pass

        if choice is None or amount is None or amount <= 0:
            bot.reply_to(message, "❌ Invalid Amount or Choice!")
            return
        if amount < MIN_BET:
            bot.reply_to(message, f"❌ Minimum bet ₹{MIN_BET:.0f} hai!")
            return
        if balance < amount:
            bot.reply_to(message, "❌ Insufficient Balance!")
            return

        USER_BALANCES[user_id] -= amount
        msg = bot.send_dice(message.chat.id, emoji="🎲")
        dice_val = msg.dice.value

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
@restricted_command
def cmd_limbo(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()[1:]
        if len(args) < 2:
            bot.reply_to(message, "⚠️ Usage: <code>/limbo 100 2.0</code>")
            return
            
        amount, target = float(args[0]), float(args[1])
        balance = get_balance(user_id)
        if balance < amount:
            bot.reply_to(message, "❌ Insufficient balance!")
            return
        
        USER_BALANCES[user_id] -= amount

        actual_multiplier = round(random.uniform(1.00, max(5.0, target * 1.5)), 2)
        win = actual_multiplier >= target

        if win:
            payout = amount * target
            USER_BALANCES[user_id] += payout
            net_profit = payout - amount
            res_text = f"WON! +₹{net_profit:.2f}"
        else:
            res_text = f"CRASHED! -₹{amount:.2f}"
            
        updated_bal = get_balance(user_id)

        # Fast local PIL Image generation with text printed on it
        img = Image.new('RGB', (600, 350), color=(15, 15, 25))
        d = ImageDraw.Draw(img)
        
        try:
            font_large = ImageFont.truetype("arial.ttf", 30)
            font_small = ImageFont.truetype("arial.ttf", 20)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()

        d.text((30, 30), "🚀 DAVO LIMBO GAME", fill=(0, 255, 204), font=font_large)
        d.text((30, 80), f"Player: {message.from_user.first_name}", fill=(255, 255, 255), font=font_small)
        d.text((30, 120), f"Bet Amount: ₹{amount:.2f}", fill=(255, 255, 255), font=font_small)
        d.text((30, 160), f"Target: {target}x  |  Hit: {actual_multiplier}x", fill=(255, 215, 0), font=font_small)
        
        result_color = (0, 255, 0) if win else (255, 69, 0)
        d.text((30, 210), f"Result: {res_text}", fill=result_color, font=font_large)
        d.text((30, 270), f"Balance: ₹{updated_bal:.2f}", fill=(200, 200, 200), font=font_small)

        bio = io.BytesIO()
        bio.name = 'limbo_result.png'
        img.save(bio, 'PNG')
        bio.seek(0)

        caption_text = (
            f"🚀 <b>DAVO CASINO - LIMBO</b> 🚀\n\n"
            f"👤 Player: {message.from_user.first_name}\n"
            f"💸 Bet: <b>₹{amount:.2f}</b> | Target: <b>{target}x</b>\n"
            f"📊 Multiplier: <b>{actual_multiplier}x</b>\n"
            f"{'🎉 <b>WON! Payout: ₹' + f'{payout:.2f}</b>' if win else '💥 <b>CRASHED! Lost: ₹' + f'{amount:.2f}</b>'}\n\n"
            f"💳 <b>New Balance: ₹{updated_bal:.2f}</b>"
        )

        bot.send_photo(message.chat.id, bio, caption=caption_text, parse_mode="HTML")

    except Exception as e: 
        logging.error(f"Limbo Error: {e}")
        bot.reply_to(message, f"⚠️ An error occurred: {e}")

@bot.message_handler(commands=['slots', 'slot'])
@restricted_command
def cmd_slots(message):
    try:
        user_id = message.from_user.id
        args = message.text.split()[1:]
        amount = float(args[0]) if len(args) > 0 else 10.0
        balance = get_balance(user_id)
        if balance < amount:
            bot.reply_to(message, "❌ Insufficient balance!")
            return
        USER_BALANCES[user_id] -= amount
        msg = bot.send_dice(message.chat.id, emoji="🎰")
        val = msg.dice.value
        if val in [1, 22, 43, 64]:
            payout = amount * 5.0
            USER_BALANCES[user_id] += payout
            bot.reply_to(message, f"🎰 <b>JACKPOT!</b> Won ₹{payout:.2f}")
        else:
            bot.reply_to(message, f"💔 <b>LOST!</b>")
    except Exception as e: logging.error(f"Slots Error: {e}")

# -------------------------------------------------------------
# PVP & BOT MANUAL THROW GAMES (/dice, /bowl, /basketball, /dart)
# -------------------------------------------------------------
def create_pvp_challenge(message, game_type, emoji):
    user_id = message.from_user.id
    args = message.text.split()[1:]

    amount, rounds, err = parse_pvp_args(args, user_id)
    if err:
        bot.reply_to(message, f"{err}\n\n<b>Usage:</b> <code>/{game_type} 100</code>")
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
        "rounds": rounds,
        "status": "WAITING",
        "turn": "p1",
        "current_round": 1,
        "p1_scores": [],
        "p2_scores": [],
        "is_bot": False
    }

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("⚔️ Accept Match", callback_data=f"pvp_accept_{match_id}"),
        InlineKeyboardButton("🤖 Play with Bot", callback_data=f"pvp_bot_{match_id}")
    )
    markup.add(InlineKeyboardButton("❌ Cancel", callback_data=f"pvp_cancel_{match_id}"))

    bot.reply_to(
        message,
        f"⚔️ <b>{game_type.upper()} MATCH!</b> {emoji}\n\n"
        f"👤 <b>Challenger:</b> {message.from_user.first_name}\n"
        f"🔄 <b>Rounds:</b> {rounds} | 💰 <b>Bet:</b> ₹{amount:.2f}\n\n"
        f"<i>Pehle player apni baari khud fekega.</i>",
        reply_markup=markup
    )

@bot.message_handler(commands=['dice'])
@restricted_command
def cmd_pvp_dice(message):
    create_pvp_challenge(message, "dice", "🎲")

@bot.message_handler(commands=['bowl', 'bowling'])
@restricted_command
def cmd_pvp_bowl(message):
    create_pvp_challenge(message, "bowl", "🎳")

@bot.message_handler(commands=['basketball', 'bb'])
@restricted_command
def cmd_pvp_bb(message):
    create_pvp_challenge(message, "basketball", "🏀")

@bot.message_handler(commands=['dart'])
@restricted_command
def cmd_pvp_dart(message):
    create_pvp_challenge(message, "dart", "🎯")

@bot.callback_query_handler(func=lambda call: call.data.startswith("pvp_"))
@restricted_callback
def handle_pvp_callbacks(call):
    try:
        data = call.data.split("_")
        action = data[1]
        match_id = "_".join(data[2:])
        user_id = call.from_user.id

        if match_id not in PVP_MATCHES:
            bot.answer_callback_query(call.id, "❌ Match expired!", show_alert=True)
            return

        match = PVP_MATCHES[match_id]

        if action == "cancel":
            if user_id != match["p1_id"] and user_id != ADMIN_ID:
                bot.answer_callback_query(call.id, "❌ Sirf Challenger cancel kar sakta hai!", show_alert=True)
                return
            USER_BALANCES[match["p1_id"]] += match["amount"]
            bot.edit_message_text(f"❌ <b>Match Cancelled & Refunded!</b>", chat_id=call.message.chat.id, message_id=call.message.message_id)
            del PVP_MATCHES[match_id]
            return

        elif action == "bot":
            if user_id != match["p1_id"]:
                bot.answer_callback_query(call.id, "❌ Sirf Challenger bot choose kar sakta hai!", show_alert=True)
                return
            match["p2_id"] = "BOT"
            match["p2_name"] = "🤖 CASINO BOT"
            match["is_bot"] = True
            match["status"] = "PLAYING"

        elif action == "accept":
            if user_id == match["p1_id"]:
                bot.answer_callback_query(call.id, "❌ Khud ke match me accept nahi kar sakte!", show_alert=True)
                return
            if get_balance(user_id) < match["amount"]:
                bot.answer_callback_query(call.id, "❌ Balance kam hai!", show_alert=True)
                return
            USER_BALANCES[user_id] -= match["amount"]
            match["p2_id"] = user_id
            match["p2_name"] = call.from_user.first_name
            match["is_bot"] = False
            match["status"] = "PLAYING"

        elif action == "throw":
            if match["status"] != "PLAYING":
                bot.answer_callback_query(call.id, "❌ Match active nahi hai!", show_alert=True)
                return
            
            expected_user = match["p1_id"] if match["turn"] == "p1" else match["p2_id"]
            if user_id != expected_user and expected_user != "BOT":
                bot.answer_callback_query(call.id, "❌ Yeh aapki baari nahi hai!", show_alert=True)
                return

            msg = bot.send_dice(call.message.chat.id, emoji=match["emoji"])
            score = msg.dice.value

            if match["turn"] == "p1":
                match["p1_scores"].append(score)
                if match["is_bot"]:
                    bot_score = random.randint(1, 6) if match["emoji"] == "🎲" else (random.randint(1, 6) if match["emoji"] == "🎳" else random.randint(1, 5))
                    match["p2_scores"].append(bot_score)
                    
                    if match["current_round"] >= match["rounds"]:
                        p1_total = sum(match["p1_scores"])
                        p2_total = sum(match["p2_scores"])
                        
                        if p1_total > p2_total:
                            payout = match["amount"] * 2
                            USER_BALANCES[match["p1_id"]] += payout
                            result_msg = f"🏆 <b>{match['p1_name']} WON THE MATCH!</b>\nScores -> {match['p1_name']}: {p1_total} | Bot: {p2_total}\n💰 Won: ₹{payout:.2f}"
                        elif p2_total > p1_total:
                            result_msg = f"🤖 <b>BOT WON THE MATCH!</b>\nScores -> {match['p1_name']}: {p1_total} | Bot: {p2_total}"
                        else:
                            USER_BALANCES[match["p1_id"]] += match["amount"]
                            result_msg = f"🤝 <b>MATCH DRAW!</b> Amount refunded."
                        
                        bot.send_message(call.message.chat.id, result_msg)
                        del PVP_MATCHES[match_id]
                        return
                    else:
                        match["current_round"] += 1
                else:
                    match["turn"] = "p2"
            else:
                match["p2_scores"].append(score)
                if match["current_round"] >= match["rounds"]:
                    p1_total = sum(match["p1_scores"])
                    p2_total = sum(match["p2_scores"])
                    
                    if p1_total > p2_total:
                        payout = match["amount"] * 2
                        USER_BALANCES[match["p1_id"]] += payout
                        result_msg = f"🏆 <b>{match['p1_name']} WON THE MATCH!</b>\nScores -> {match['p1_name']}: {p1_total} | {match['p2_name']}: {p2_total}\n💰 Won: ₹{payout:.2f}"
                    elif p2_total > p1_total:
                        payout = match["amount"] * 2
                        USER_BALANCES[match["p2_id"]] += payout
                        result_msg = f"🏆 <b>{match['p2_name']} WON THE MATCH!</b>\nScores -> {match['p1_name']}: {p1_total} | {match['p2_name']}: {p2_total}\n💰 Won: ₹{payout:.2f}"
                    else:
                        USER_BALANCES[match["p1_id"]] += match["amount"]
                        USER_BALANCES[match["p2_id"]] += match["amount"]
                        result_msg = f"🤝 <b>MATCH DRAW!</b> Amount refunded to both."
                    
                    bot.send_message(call.message.chat.id, result_msg)
                    del PVP_MATCHES[match_id]
                    return
                else:
                    match["current_round"] += 1
                    match["turn"] = "p1"

        markup = InlineKeyboardMarkup()
        current_turn_name = match['p1_name'] if match['turn'] == 'p1' else match['p2_name']
        markup.add(InlineKeyboardButton(f"🎲 {current_turn_name} Throw (Round {match['current_round']}/{match['rounds']})", callback_data=f"pvp_throw_{match_id}"))

        bot.edit_message_text(
            f"⚔️ <b>MATCH IN PROGRESS...</b> {match['emoji']}\n\n"
            f"🔴 <b>{match['p1_name']}</b>: {match['p1_scores']}\n"
            f"🔵 <b>{match['p2_name']}</b>: {match['p2_scores']}\n\n"
            f"👉 <b>{current_turn_name}</b> ki baari hai!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=markup
        )
    except Exception as e:
        logging.error(f"PvP CB Error: {e}")

# -------------------------------------------------------------
# KEEP ALIVE SERVER & BOT STARTUP
# -------------------------------------------------------------
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    do_GET = lambda s: (s.send_response(200), s.send_header('Content-type', 'text/plain'), s.end_headers(), s.wfile.write(b"DAVO CASINO BOT ONLINE"))
    do_HEAD = lambda s: (s.send_response(200), s.end_headers())

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print(f"🌐 Web Server Running on Port {port}")
    server.serve_forever()

def start_polling():
    print("⚡ Starting Telegram Bot Polling...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            logging.error(f"Polling Crashed: {e}")
            time.sleep(1)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=start_polling, daemon=True)
    bot_thread.start()
    run_web_server()
