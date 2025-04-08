import os
import subprocess
from PIL import Image
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from keep_alive import keep_alive
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()
TOKEN = os.getenv("TOKEN")  # НЕ дублируем это в main()!

# Пути
WATERMARK_PATH = "watermark.png"
TEMP_FOLDER = "./temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Обработка фото
async def handle_photo(update: Update, context: CallbackContext):
    file = await update.message.photo[-1].get_file()
    input_path = os.path.join(TEMP_FOLDER, "input.png")
    output_path = os.path.join(TEMP_FOLDER, "output.png")

    await file.download_to_drive(input_path)
    add_watermark_photo(input_path, output_path)

    with open(output_path, "rb") as f:
        await update.message.reply_photo(f)

# Обработка видео
async def handle_video(update: Update, context: CallbackContext):
    file = await update.message.video.get_file()
    input_path = os.path.join(TEMP_FOLDER, f"input_{update.message.video.file_id}.mp4")
    output_path = os.path.join(TEMP_FOLDER, f"output_{update.message.video.file_id}.mp4")

    await file.download_to_drive(input_path)
    add_watermark_video(input_path, output_path)

    with open(output_path, "rb") as f:
        await update.message.reply_video(f)

# Стартовое сообщение
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Отправьте фото или видео, чтобы добавить водяной знак.")

def add_watermark_photo(photo_path: str, output_path: str):
    # Открываем изображение и водяной знак
    image = Image.open(photo_path).convert("RGBA")
    watermark = Image.open(WATERMARK_PATH).convert("RGBA")

    img_width, img_height = image.size

    # Масштабируем водяной знак до 30% ширины изображения
    target_wm_width = int(img_width * 0.45)
    scale_factor = target_wm_width / watermark.width
    target_wm_height = int(watermark.height * scale_factor)

    # Изменяем размер водяного знака с сохранением пропорций
    resized_watermark = watermark.resize((target_wm_width, target_wm_height), resample=Image.LANCZOS)

    # Центрируем водяной знак
    x = (img_width - target_wm_width) // 2
    y = (img_height - target_wm_height) // 2

    # Накладываем водяной знак
    image.paste(resized_watermark, (x, y), mask=resized_watermark)

    # Сохраняем изображение
    image.save(output_path, format="PNG")

# Водяной знак на видео
def add_watermark_video(video_path: str, output_path: str):
    command = [
        "ffmpeg", "-i", video_path, "-i", WATERMARK_PATH,
        "-filter_complex", "overlay=(W-w)/2:(H-h)/2",
        "-codec:a", "copy", output_path, "-y"
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        print(f"Ошибка при обработке видео: {result.stderr.decode()}")
    else:
        print(f"Видео обработано успешно: {output_path}")

# Основной запуск
def main():
    if not TOKEN:
        print("❌ Токен не найден! Проверь .env файл")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))

    keep_alive()
    app.run_polling()

if __name__ == "__main__":
    main()
