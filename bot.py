import telebot
import random
import json
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = "8102036774:AAENq-j3emooKkEbWT-feESDwft2hI4CjzA"
DATA_FILE = "users.json"

bot = telebot.TeleBot(TOKEN)

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_money(user_id, amount):
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"balance": 0, "last_deposit": 0}
    data[str(user_id)]["balance"] += amount
    save_data(data)

def get_balance(user_id):
    data = load_data()
    return data.get(str(user_id), {}).get("balance", 0)

def can_deposit(user_id):
    data = load_data()
    last_time = data.get(str(user_id), {}).get("last_deposit", 0)
    return time.time() - last_time >= 7200

def set_deposit_time(user_id):
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"balance": 0, "last_deposit": 0}
    data[str(user_id)]["last_deposit"] = time.time()
    save_data(data)

@bot.message_handler(commands=["deposit"])
def deposit(message):
    user_id = message.from_user.id
    if not can_deposit(user_id):
        bot.reply_to(message, "ты уже получал изумруды. попробуй позже.")
        return
    amount = random.randint(16, 30)
    add_money(user_id, amount)
    set_deposit_time(user_id)
    bot.reply_to(message, f"ты получил {amount} изумрудов.")

@bot.message_handler(commands=["blackjack"])
def start_blackjack(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)

    if balance < 10:
        bot.reply_to(message, "недостаточно изумрудов для игры. пополни баланс командой /deposit.")
        return

    add_money(user_id, -10)
    player_hand = [random.randint(1, 11), random.randint(1, 11)]
    dealer_hand = [random.randint(1, 11)]

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("взять карту", callback_data=f"hit|{user_id}|{sum(player_hand)}|{dealer_hand[0]}"),
        InlineKeyboardButton("стоп", callback_data=f"stand|{user_id}|{sum(player_hand)}|{dealer_hand[0]}")
    )

    bot.send_message(
        message.chat.id,
        f"ты начал игру в блекджек\n\nтвои карты: {player_hand} (сумма {sum(player_hand)})\nкарта дилера: {dealer_hand[0]}\n\nставка: 10 изумрудов",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("hit") or call.data.startswith("stand"))
def blackjack_game(call):
    data = call.data.split("|")
    action, user_id, player_sum, dealer_card = data[0], int(data[1]), int(data[2]), int(data[3])

    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "это не твоя игра")
        return

    if action == "hit":
        new_card = random.randint(1, 11)
        player_sum += new_card

        if player_sum > 21:
            bot.edit_message_text(
                f"ты взял {new_card}. у тебя {player_sum}, перебор\n\nты проиграл",
                call.message.chat.id, call.message.message_id
            )
        else:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("взять карту", callback_data=f"hit|{user_id}|{player_sum}|{dealer_card}"),
                InlineKeyboardButton("стоп", callback_data=f"stand|{user_id}|{player_sum}|{dealer_card}")
            )
            bot.edit_message_text(
                f"ты взял {new_card}. у тебя {player_sum}.\nкарта дилера: {dealer_card}",
                call.message.chat.id, call.message.message_id,
                reply_markup=markup
            )

    elif action == "stand":
        dealer_sum = dealer_card
        while dealer_sum < 17:
            dealer_sum += random.randint(1, 11)

        if dealer_sum > 21 or player_sum > dealer_sum:
            add_money(user_id, 20)
            bot.edit_message_text(
                f"дилер набрал {dealer_sum}. ты выиграл\n\n+20 изумрудов",
                call.message.chat.id, call.message.message_id
            )
        elif player_sum == dealer_sum:
            add_money(user_id, 10)
            bot.edit_message_text(
                f"дилер набрал {dealer_sum}. ничья\n\nставка возвращена.",
                call.message.chat.id, call.message.message_id
            )
        else:
            bot.edit_message_text(
                f"дилер набрал {dealer_sum}. ты проиграл",
                call.message.chat.id, call.message.message_id
            )

bot.polling(none_stop=True, interval=0, timeout=20)
