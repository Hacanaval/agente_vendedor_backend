import os
import httpx
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import tempfile
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN_FIXED = os.getenv("BOT_TOKEN_FIXED")
if not BOT_TOKEN_FIXED:
    print("ERROR: BOT_TOKEN_FIXED no está definido en el entorno. Por favor, revisa tu .env.")
    exit(1)

print(f"[DEBUG] BOT_TOKEN_FIXED usado por el bot:\n{BOT_TOKEN_FIXED}\n")

TELEGRAM_TOKEN = "7369421762:AAHe3Fp2ag39RSaQH33LZ-OkemxfQKf6oC0"  # Solo para pruebas
BACKEND_URL = "http://localhost:8001"  # Cambia si tu backend está en otro host/puerto
EMPRESA_ID = 4  # Cambia este valor por el id real de la empresa para pruebas

async def consultar_backend_texto(mensaje: str, user_id: int) -> str:
    url = f"{BACKEND_URL}/chat/texto"
    payload = {"mensaje": mensaje}
    print(f"[DEBUG] Enviando a backend: {payload} a {url}")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            url,
            json=payload
        )
        if response.status_code == 200:
            return response.json().get("respuesta", "No se pudo obtener respuesta.")
        return "Error al consultar el agente."

async def consultar_backend_imagen(image_path: str, user_id: int) -> str:
    url = f"{BACKEND_URL}/chat/imagen"
    print(f"[DEBUG] Enviando imagen a backend: {image_path} a {url}")
    async with httpx.AsyncClient(timeout=20.0) as client:
        with open(image_path, "rb") as f:
            files = {"imagen": (os.path.basename(image_path), f, "image/jpeg")}
            response = await client.post(
                url,
                files=files
            )
        if response.status_code == 200:
            data = response.json()
            return f"Descripción de la imagen: {data.get('descripcion_imagen', '')}\n\nRespuesta del agente: {data.get('respuesta_agente', '')}"
        return "Error al procesar la imagen."

async def consultar_backend_audio(audio_path: str, user_id: int) -> str:
    url = f"{BACKEND_URL}/chat/audio"
    print(f"[DEBUG] Enviando audio a backend: {audio_path} a {url}")
    async with httpx.AsyncClient(timeout=20.0) as client:
        with open(audio_path, "rb") as f:
            files = {"audio": (os.path.basename(audio_path), f, "audio/mpeg")}
            response = await client.post(
                url,
                files=files
            )
        if response.status_code == 200:
            data = response.json()
            return f"Transcripción: {data.get('transcripcion', '')}\n\nRespuesta del agente: {data.get('respuesta', '')}"
        return "Error al procesar el audio."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.message.from_user.id
    print(f"[BOT] Mensaje recibido de usuario {user_id}: {user_message}")
    respuesta = await consultar_backend_texto(user_message, user_id)
    print(f"[BOT] Respuesta a enviar a usuario {user_id}: {respuesta}")
    await update.message.reply_text(respuesta)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    photo = update.message.photo[-1]  # Highest resolution
    print(f"[BOT] Imagen recibida de usuario {user_id}")
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        file = await context.bot.get_file(photo.file_id)
        await file.download_to_drive(tf.name)
        respuesta = await consultar_backend_imagen(tf.name, user_id)
    print(f"[BOT] Respuesta a enviar a usuario {user_id} (imagen): {respuesta}")
    await update.message.reply_text(respuesta)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    audio = update.message.voice or update.message.audio
    if not audio:
        print(f"[BOT] Audio inválido recibido de usuario {user_id}")
        await update.message.reply_text("No se detectó audio válido.")
        return
    print(f"[BOT] Audio recibido de usuario {user_id}")
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
        file = await context.bot.get_file(audio.file_id)
        await file.download_to_drive(tf.name)
        respuesta = await consultar_backend_audio(tf.name, user_id)
    print(f"[BOT] Respuesta a enviar a usuario {user_id} (audio): {respuesta}")
    await update.message.reply_text(respuesta)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Soy tu agente de ventas. Puedes enviarme texto, imágenes o mensajes de voz.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    app.run_polling()

if __name__ == "__main__":
    main() 