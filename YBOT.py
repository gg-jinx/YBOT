import functions_framework
import telebot
import re
import os
import tweepy
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# --- بارگیری متغیرهای محیطی ---
load_dotenv()

# --- دریافت توکن تلگرام ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# --- دریافت کلیدهای توییتر ---
API_KEY = os.getenv("API_KEY")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")

# --- احراز هویت توییتر ---
auth = tweepy.OAuthHandler(API_KEY, API_SECRET_KEY)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
twitter_api = tweepy.API(auth)

# --- لیست ادمین‌ها ---
ADMINS = {1135603573, 554542011}

# --- ذخیره اطلاعات کاربران ---
USERS_DB = "users.txt"

# --- الگوی شناسایی آیدی توییتر ---
def extract_twitter_id(user_input):
    match = re.search(r"(?:https?:\/\/twitter\.com\/)?@?([a-zA-Z0-9_]+)", user_input)
    return match.group(1) if match else None

# --- دکمه‌های کیبورد ---
def get_user_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("SEARCH🔍"))
    return keyboard

def get_admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("SEARCH🔍"), KeyboardButton("STATES📊"))
    keyboard.add(KeyboardButton("USERS📂"))
    return keyboard

def get_cancel_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("CANCEL❌"))
    return keyboard

# --- ذخیره کاربر ---
def save_user(user_id, username):
    if not os.path.exists(USERS_DB):
        with open(USERS_DB, "w"): pass
    with open(USERS_DB, "r") as f:
        users = f.read().splitlines()
    user_entry = f"{user_id} - @{username if username else user_id}"
    if user_entry not in users:
        with open(USERS_DB, "a") as f:
            f.write(user_entry + "\n")

# --- مدیریت دستورات ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username
    save_user(user_id, username)
    
    if user_id in ADMINS:
        bot.send_message(message.chat.id, "MIU", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "HI, PUSH SEARCH BUTTON TO FIND FAV POSTS.", reply_markup=get_user_keyboard())

@bot.message_handler(func=lambda message: message.text == "SEARCH🔍")
def ask_for_twitter_id(message):
    bot.send_message(message.chat.id, "PLEASE ENTER YOUR TWITTER USERNAME OR PROFILE LINK.", reply_markup=get_cancel_keyboard())
    bot.register_next_step_handler(message, process_twitter_id)

@bot.message_handler(func=lambda message: message.text == "CANCEL❌")
def cancel_search(message):
    bot.send_message(message.chat.id, "RETURNED TO MAIN MENU✅", reply_markup=get_admin_keyboard() if message.from_user.id in ADMINS else get_user_keyboard())

# --- دریافت توییت‌های محبوب ---
def get_popular_tweets(chat_id, twitter_id):
    try:
        tweets = twitter_api.user_timeline(screen_name=twitter_id, count=50, tweet_mode="extended")
        popular_tweets = sorted([{'text': t.full_text, 'likes': t.favorite_count, 'id': t.id_str} for t in tweets if t.favorite_count > 500], key=lambda x: x['likes'], reverse=True)
    
        if not popular_tweets:
            bot.send_message(chat_id, "THERE IS NO FAV POSTS❌")
            return
    
        response_text = "YOUR FAVS🔥"
        for i, tweet in enumerate(popular_tweets, 1):
            tweet_url = f"https://twitter.com/{twitter_id}/status/{tweet['id']}"
            response_text += f"\n{i}. [{tweet['text'][:50]}...]({tweet_url}) ({tweet['likes']} ♥️)"
            
            if len(response_text) > 3800:
                bot.send_message(chat_id, response_text, parse_mode="Markdown")
                response_text = ""
    
        if response_text:
            bot.send_message(chat_id, response_text, parse_mode="Markdown")
    
    except tweepy.TweepError as e:
        bot.send_message(chat_id, f"ERROR: {e.reason}")
        
# --- دریافت آیدی توییتر ---
def process_twitter_id(message):
    if message.text == "CANCEL❌":
        cancel_search(message)
        return
    
    twitter_id = extract_twitter_id(message.text)
    if not twitter_id:
        bot.send_message(message.chat.id, "INVALID❗️ TRY AGAIN.", reply_markup=get_user_keyboard())
        return
    
    bot.send_message(message.chat.id, f"VALID✅: @{twitter_id}\nFINDING TWEETS...")
    get_popular_tweets(message.chat.id, twitter_id)

@bot.message_handler(func=lambda message: message.text == "STATES📊" and message.from_user.id in ADMINS)
def get_statistics(message):
    with open(USERS_DB, "r") as f:
        users = f.read().splitlines()
    bot.send_message(message.chat.id, f"👥 Total Users: {len(users)}")

@bot.message_handler(func=lambda message: message.text == "USERS📂" and message.from_user.id in ADMINS)
def send_user_list(message):
    with open(USERS_DB, "rb") as f:
        bot.send_document(message.chat.id, f)

# --- راه‌اندازی بات ---
bot.polling(none_stop=True)