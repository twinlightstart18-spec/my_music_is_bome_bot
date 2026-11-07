import os
from flask import Flask, request
from threading import Thread
import telebot
import yt_dlp
import shutil

app = Flask('')

# ၁။ TOKEN နှင့် bot ကို ထိပ်ဆုံးပိုင်းတွင် အရင်ဆုံး သတ်မှတ်ပါ
TOKEN = os.getenv('TOKEN')
if not TOKEN:
  raise ValueError('No TOKEN found in environment variables!')

bot = telebot.TeleBot(TOKEN)


# ၂။ TOKEN သတ်မှတ်ပြီးမှ Webhook Route ကို ရေးပါ
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
  if request.headers.get('content-type') == 'application/json':
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '', 200
  return 'Forbidden', 403


@app.route('/')
def home():
  return 'I am alive'


def run():
  app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))


def keep_alive():
  t = Thread(target=run)
  t.start()


# Flask ဆာဗာကို စတင်ရန်
keep_alive()

# ၃။ Secret File ကို /tmp/ သို့ ကူးယူခြင်း
ORIGINAL_COOKIE = '/etc/secrets/cookies.txt'
COOKIE_FILE = '/tmp/cookies.txt'

if os.path.exists(ORIGINAL_COOKIE):
  shutil.copy(ORIGINAL_COOKIE, COOKIE_FILE)
elif os.path.exists('cookies.txt'):
  shutil.copy('cookies.txt', COOKIE_FILE)


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
        'cookiefile': COOKIE_FILE,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '96',
        }],
        'outtmpl': '%(id)s.%(ext)s',
        'default_search': 'ytsearch1',
        'noplaylist': True,
        'quiet': True,
        # YouTube ၏ Bot Detection ကျော်လွှားရန် ထပ်တိုးရန်များ
        'extractor-args': {'youtube': {'player-client': ['android', 'web']}},
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'no_warnings': True,
        'socket_timeout': 30,
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
  render_url = os.environ.get('RENDER_EXTERNAL_URL')
  if render_url:
    bot.remove_webhook()
    bot.set_webhook(url=f'{render_url}/{TOKEN}')
    print(f'Webhook set to: {render_url}/{TOKEN}')

  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)
