import os
import telebot
import threading
from flask import Flask
from google import genai
from google.genai import types

# ----------------- এনভায়রনমেন্ট ভ্যারিয়েবল -----------------
# রেন্ডার ড্যাশবোর্ডে সেট করা টোকেনগুলো নিজে থেকেই লোড হবে
TELEGRAM_BOT_TOKEN = os.environ.get("TG_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_KEY")
# -----------------------------------------------------------

# ক্লায়েন্ট ও বট ইনিশিয়ালাইজ করা
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# আপডেট করা সিস্টেম প্রম্পট (যাতে ল্যাটেক্স কোড বা হিজিবিজি চিহ্ন না আসে)
system_prompt = (
    "তুমি একজন অত্যন্ত বুদ্ধিমান, অমায়িক এবং অল-রাউন্ডার পার্সোনাল এআই অ্যাসিস্ট্যান্ট। "
    "তোমার কাজ হলো ব্যবহারকারীকে পড়াশোনা (বিজ্ঞান, গণিত, রসায়ন), কোডিং, এবং যেকোনো জটিল বিষয় সহজে বুঝতে সাহায্য করা।\n\n"
    "⚠️ অত্যন্ত গুরুত্বপূর্ণ নির্দেশ:\n"
    "১. তোমার উত্তরের কোথাও কোনো প্রকার LaTeX বা গাণিতিক কোড (যেমন: $, \\frac, \\sin, \\delta, \\approx, \\circ) ব্যবহার করবে না।\n"
    "২. সমস্ত গাণিতিক সমীকরণ ও প্রতীক সাধারণ টেক্সট এবং সাধারণ চিহ্নে লিখবে। "
    "যেমন: ভগ্নাংশ লিখবে (A+D)/2 আকারে, ডিগ্রী বোঝাতে লিখবে 'ডিগ্রী' বা শুধু সংখ্যা, এবং গুণের জন্য '*' ব্যবহার করবে।\n"
    "৩. উত্তর সবসময় স্পষ্ট, প্লেইন টেক্সট এবং বাংলায় সুন্দর করে গুছিয়ে টু-দ্য-পয়েন্ট রাখবে।"
)

user_chats = {}

def get_or_create_chat(user_id):
    # নতুন চ্যাট শুরু হলে বা রিসেট হলে আগের মেমোরি ক্লিয়ার হবে
    if user_id not in user_chats:
        user_chats[user_id] = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            )
        )
    return user_chats[user_id]

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user_id = message.from_user.id
    # যদি আগে থেকে চ্যাট সেশন থাকে, তবে তা ডিলিট করে ফ্রেশ স্টার্ট করা হবে
    if user_id in user_chats:
        del user_chats[user_id]
        
    welcome_text = (
        "👋 হ্যালো! আমি আপনার পার্সোনাল অল-রাউন্ডার এআই অ্যাসিস্ট্যান্ট।\n\n"
        "📚 পড়াশোনা, গণিত, রসায়ন, ফিজিক্সের সমস্যা\n"
        "💻 কোডিং বা যেকোনো সাধারণ প্রশ্ন আমাকে করতে পারেন।\n\n"
        "💡 যেকোনো প্রশ্ন বা জটিল অংকের ছবি তুলেও আমাকে পাঠাতে পারেন।"
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    user_query = message.text
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        chat_session = get_or_create_chat(user_id)
        response = chat_session.send_message(user_query)
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"❌ একটু সমস্যা হয়েছে।\nError: {e}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image_bytes = types.Part.from_bytes(data=downloaded_file, mime_type="image/jpeg")
        
        # ছবির উত্তরের জন্যও ল্যাটেক্স বন্ধ করার প্রম্পট জুঁড়ে দেওয়া হয়েছে
        user_caption = message.caption if message.caption else "এই ছবিটি বিশ্লেষণ করো এবং সমাধান বুঝিয়ে দাও।"
        prompt = f"{user_caption}\n\n(মনে রাখবে: উত্তরের কোথাও কোনো LaTeX বা $ চিহ্ন ব্যবহার করা যাবে না। সাধারণ টেক্সটে উত্তর দাও।)"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image_bytes, prompt],
            config=types.GenerateContentConfig(system_instruction=system_prompt)
        )
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"❌ ছবিটি প্রসেস করা যায়নি।\nError: {e}")

# ----------------- রেন্ডার ফ্রি সার্ভার পোর্ট ট্রিক -----------------
flask_app = Flask('')

@flask_app.route('/')
def home(): 
    return "Bot is Alive!"

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    flask_app.run(host='0.0.0.0', port=port)

# ব্যাকগ্রাউন্ড থ্রেডে ফ্লাস্ক সার্ভার চালু করা
threading.Thread(target=run_flask).start()
# -----------------------------------------------------------------

print("🤖 সার্ভার চালু হচ্ছে...")

# রিস্টার্ট এবং হ্যাং হওয়া থেকে বাঁচানোর জন্য টাইম-আউট সেট করা হয়েছে
bot.infinity_polling(timeout=10, long_polling_timeout=5)
