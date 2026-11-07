import os
from flask import Flask
from threading import Thread
import telebot
import yt_dlp
import shutil  # <-- ၁။ ဤနေရာတွင် shutil ကို import လုပ်ပါ

app = Flask('')


@app.route('/')
def home():
  return 'I am alive'


def run():
  app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))


def keep_alive():
  t = Thread(target=run)
  t.start()


# Flask ဆာဗာကို စတင်ရန်
keep_alive()

# Render ၏ Environment Variable မှ TOKEN ကို အလိုအလျောက် လှမ်းယူခြင်း
TOKEN = os.getenv('TOKEN')
if not TOKEN:
  raise ValueError("No TOKEN found in environment variables!")

# ---------------------------------------------------------
# ၂။ ဤနေရာတွင် Secret File ကို /tmp/ သို့ ကူးယူမည့် ကုဒ်ကို ထည့်ပါ
ORIGINAL_COOKIE = '/etc/secrets/cookies.txt'
COOKIE_FILE = '/tmp/cookies.txt'

if os.path.exists(ORIGINAL_COOKIE):
  shutil.copy(ORIGINAL_COOKIE, COOKIE_FILE)
elif os.path.exists('cookies.txt'):
  shutil.copy('cookies.txt', COOKIE_FILE)
# ---------------------------------------------------------

bot = telebot.TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
  welcome_text = (
      'မင်္ဂလာပါ! ဒီ Bot ကနေ YouTube က သီချင်းတွေကို ရှာဖွေပြီး Audio ဖိုင်အနေနဲ့'
      ' ပို့ပေးနိုင်ပါတယ်။\n\nကျေးဇူးပြု၍ လိုချင်တဲ့ သီချင်းနာမည် (သို့) YouTube'
      ' Link ကို ပို့ပေးပါ။'
  )
  bot.reply_to(message, welcome_text)


@bot.message_handler(func=lambda message: True)
def download_and_send_music(message):
  query = message.text
  sent_msg = bot.reply_to(
      message, f"🔍 '{query}' ကို ရှာဖွေနေပါပြီ၊ ခဏစောင့်ပါ..."
  )

  ydl_opts = {
      'format': 'bestaudio/best',
      'cookiefile': COOKIE_FILE,  # <-- ၃။ ဤနေရာတွင် COOKIE_FILE ကို သုံးပါ
      'postprocessors': [{
          'key': 'FFmpegExtractAudio',
          'preferredcodec': 'mp3',
          'preferredquality': '96',
      }],
      'outtmpl': '%(id)s.%(ext)s',
      'default_search': 'ytsearch1',
      'noplaylist': True,
      'quiet': True,
  }
  try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      info = ydl.extract_info(query, download=False)
      if 'entries' in info and len(info['entries']) > 0:
        info = ydl.extract_info(query, download=True)
        if 'entries' in info:
          info = info['entries'][0]

        filename = f"{info['id']}.mp3"
        title = info.get('title', 'Audio')

        bot.edit_message_text(
            f"📥 '{title}' ကို ပို့ဆောင်နေပါပြီ...",
            chat_id=message.chat.id,
            message_id=sent_msg.message_id,
        )

        with open(filename, 'rb') as audio:
          bot.send_audio(message.chat.id, audio, title=title)

        bot.delete_message(message.chat.id, sent_msg.message_id)

        if os.path.exists(filename):
          os.remove(filename)
      else:
        bot.edit_message_text(
            (
                f"❌ '{query}' နဲ့ ပတ်သက်တဲ့ သီချင်း မတွေ့ရှိပါ။"
                ' ကျေးဇူးပြု၍ နာမည်အမှန်ကို အသစ်ပြန်ပို့ပေးပါ။'
            ),
            chat_id=message.chat.id,
            message_id=sent_msg.message_id,
        )

  except Exception as e:
    bot.edit_message_text(
        f'❌ သီချင်းရယူရာတွင် အမှားအယွင်းရှိနေပါသည်: {str(e)}',
        chat_id=message.chat.id,
        message_id=sent_msg.message_id,
    )


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)
