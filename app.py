import datetime
import os
from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont
import telebot

TOKEN = "8635048670:AAEpm23iblKoMrVr5rLTIvyGAYCGgrEBPMQ"
bot = telebot.TeleBot(TOKEN, threaded=False)

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BG_IMAGE = os.path.join(BASE_DIR, "22222.png")
FONT_NAME = os.path.join(BASE_DIR, "Volja-Black.otf")
FONT_DATE = os.path.join(BASE_DIR, "UAF-Sans-Regular.ttf")
FONT_NUM = os.path.join(BASE_DIR, "UAF-Sans-Bold.ttf")

UKR_MONTHS = {
    1: "січня",
    2: "лютого",
    3: "березня",
    4: "квітня",
    5: "травня",
    6: "червня",
    7: "липня",
    8: "серпня",
    9: "вересня",
    10: "жовтня",
    11: "листопада",
    12: "грудня",
}


def get_current_date_parts():
  now = datetime.datetime.now()
  day = now.day
  month_name = UKR_MONTHS.get(now.month, "")
  year = f"{now.year} року"
  return f"{day} {month_name}", year


def generate_certificate_image(
    name, number="0080", date_str=None, year_str=None
):
  if not date_str or not year_str:
    date_str, year_str = get_current_date_parts()

  img = Image.open(BG_IMAGE).convert("RGBA")
  draw_main = ImageDraw.Draw(img)

  max_width = 2800
  font_large = ImageFont.truetype(FONT_NAME, size=165)
  font_small = ImageFont.truetype(FONT_NAME, size=110)

  bbox = font_large.getbbox(name)
  text_width = bbox[2] - bbox[0]

  if text_width <= max_width:
    draw_main.text((1774, 1090), name, fill="white", font=font_large, anchor="mm")
  else:
    words = name.split()
    line1_words = []
    line2_words = []
    for word in words:
      test_str = " ".join(line1_words + [word])
      bbox_test = font_small.getbbox(test_str)
      if (bbox_test[2] - bbox_test[0]) <= max_width and not line2_words:
        line1_words.append(word)
      else:
        line2_words.append(word)
    if not line1_words and line2_words:
      line1_words.append(line2_words.pop(0))

    final_wrapped_text = (
        f"{' '.join(line1_words)}\n{' '.join(line2_words)}".strip()
    )
    draw_main.multiline_text(
        (1774, 1060),
        final_wrapped_text,
        fill="white",
        font=font_small,
        anchor="mm",
        align="center",
        spacing=15,
    )

  font_date = ImageFont.truetype(FONT_DATE, size=65)
  draw_main.text((478, 1880), date_str, fill="white", font=font_date)
  draw_main.text((478, 1955), year_str, fill="white", font=font_date)

  txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
  draw_txt = ImageDraw.Draw(txt_layer)
  font_num = ImageFont.truetype(FONT_NUM, size=65)
  draw_txt.text(
      (1765, 2376),
      number,
      fill=(255, 255, 255, 85),
      font=font_num,
      anchor="mm",
  )

  img = Image.alpha_composite(img, txt_layer)
  img = img.convert("RGB")

  output_path = os.path.join(BASE_DIR, "result_thanks.png")
  img.save(output_path, "PNG")
  return output_path


# Автоматичне встановлення вебхука при старті додатка (працює і з Gunicorn)
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
if RENDER_URL:
  bot.remove_webhook()
  bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
  print(f"Вебхук успішно встановлено на: {RENDER_URL}/{TOKEN}")
else:
  print("Увага: RENDER_EXTERNAL_URL не знайдено (локальний запуск)")


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_str = request.get_data().decode("UTF-8")
  update = telebot.types.Update.de_json(json_str)
  bot.process_new_updates([update])
  return "!", 200


@app.route("/")
def index():
  return "Bot is running!", 200


@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.reply_to(
      message,
      "Вітаю! Надішліть дані у такому форматі:\n"
      "<b>Ім'я Прізвище _ Номер _ Дата _ Рік</b>\n\n"
      "Приклад:\n"
      "<code>Олег Романенко _ 0081 _ 12 листопада _ 2026 року</code>",
      parse_mode="HTML",
  )


@bot.message_handler(func=lambda message: True)
def handle_text(message):
  try:
    text = message.text.strip()
    parts = [p.strip() for p in text.split("_")]

    default_date, default_year = get_current_date_parts()
    name = parts[0]
    number = parts[1] if len(parts) > 1 and parts[1] else "0080"
    date_str = parts[2] if len(parts) > 2 and parts[2] else default_date
    year_str = parts[3] if len(parts) > 3 and parts[3] else default_year

    bot.reply_to(
        message,
        f"Генерую подяку для <b>{name}</b> (№{number}, {date_str} {year_str})...",
        parse_mode="HTML",
    )

    img_path = generate_certificate_image(name, number, date_str, year_str)

    with open(img_path, "rb") as doc:
      bot.send_document(
          message.chat.id, doc, caption=f"Подяка для {name} (№{number})"
      )

  except Exception as e:
    bot.reply_to(message, f"Сталася помилка: {e}")


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
