import telebot
from google import genai
from google.genai import types

# ----------------- কনফিগারেশন -----------------
TELEGRAM_BOT_TOKEN = "8887518011:AAGO0eQwllSIu6CjSQrxRhABGUTspgQhsSg"
GEMINI_API_KEY = "AIzaSyA6nRChApp8sw0jbzo3bIGOPHW0B0ZwvGI"
# ----------------------------------------------

# ক্লায়েন্ট ও বট ইনিশিয়ালাইজ করা
client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# বটের জন্য অল-রাউন্ডার সিস্টেম ইনস্ট্রাকশন
system_prompt = (
    "তুমি একজন অত্যন্ত বুদ্ধিমান, অমায়িক এবং অল-রাউন্ডার পার্সোনাল এআই অ্যাসিস্ট্যান্ট। "
    "তোমার কাজ হলো ব্যবহারকারীকে পড়াশোনা (বিজ্ঞান, গণিত, রসায়ন), কোডিং, দৈনন্দিন পরিকল্পনা, "
    "এবং যেকোনো জটিল বিষয় সহজে বুঝতে সাহায্য করা। উত্তর সবসময় স্পষ্ট, সহজবোধ্য এবং টু-দ্য-পয়েন্ট রাখবে। "
    "প্রয়োজনে ধাপে ধাপে (step-by-step) ব্যাখ্যা করবে।"
)

# প্রতিটি ইউজারের চ্যাট হিস্ট্রি বা মেমোরি ধরে রাখার জন্য একটি ডিকশনারি
user_chats = {}

def get_or_create_chat(user_id):
    """প্রতিটি ইউজারের জন্য আলাদা চ্যাট সেশন (স্মৃতিশক্তি) তৈরি বা রিট্রিভ করা"""
    if user_id not in user_chats:
        user_chats[user_id] = client.chats.create(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            )
        )
    return user_chats[user_id]

# /start বা /help কমান্ড হ্যান্ডল করা
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "👋 হ্যালো! আমি আপনার পার্সোনাল অল-রাউন্ডার এআই অ্যাসিস্ট্যান্ট।\n\n"
        "📚 পড়াশোনা, গণিত, রসায়ন, ফিজিক্সের সমস্যা\n"
        "💻 কোডিং বা যেকোনো সাধারণ প্রশ্ন আমাকে করতে পারেন।\n\n"
        "💡 শুধু তাই নয়! কোনো প্রশ্ন বা জটিল অংকের ছবি তুলেও আমাকে পাঠাতে পারেন।"
    )
    bot.reply_to(message, welcome_text)

# টেক্সট মেসেজ হ্যান্ডল করা (Normal Chat)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    user_query = message.text
    
    # চ্যাট স্ক্রিনে একটি 'Typing...' স্ট্যাটাস দেখানোর জন্য
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # ইউজারের আগের স্মৃতিসহ চ্যাট সেশন নেওয়া
        chat_session = get_or_create_chat(user_id)
        response = chat_session.send_message(user_query)
        
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"❌ দুঃখিত, একটু সমস্যা হয়েছে। আবার চেষ্টা করুন।\nError: {e}")

# ছবি বা ফটো মেসেজ হ্যান্ডল করা (Image Input)
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # টেলিগ্রাম সার্ভার থেকে ছবি ডাউনলোড করা
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # জেমিনি এপিআই-এর জন্য ছবি প্রস্তুত করা
        image_bytes = types.Part.from_bytes(
            data=downloaded_file,
            mime_type="image/jpeg",
        )
        
        # ছবির সাথে যদি কোনো ক্যাপশন বা প্রশ্ন থাকে, তা নেওয়া
        prompt = message.caption if message.caption else "এই ছবিটি বিশ্লেষণ করো এবং সমাধান বুঝিয়ে দাও।"
        
        # ছবি সরাসরি জেমিনি মডেলে পাঠানো (মাল্টিমোডাল)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image_bytes, prompt],
            config=types.GenerateContentConfig(system_instruction=system_prompt)
        )
        
        bot.reply_to(message, response.text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ ছবিটি প্রসেস করা যায়নি।\nError: {e}")

# বট চালু করা
print("🤖 আপনার টেলিগ্রাম বট ব্যাকএন্ডে সচল হয়েছে... এখন টেলিগ্রামে গিয়ে চ্যাট করুন!")
bot.infinity_polling()
