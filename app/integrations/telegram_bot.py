import os
import httpx
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import tempfile
from dotenv import load_dotenv
import logging

load_dotenv()

# Configuración del bot
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # Token principal del bot
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")

# Validación de configuración
if not TELEGRAM_TOKEN:
    logging.error("ERROR: TELEGRAM_TOKEN no está definido en el entorno.")
    exit(1)

logging.info(f"Bot configurado para conectar con backend: {BACKEND_URL}")

async def consultar_backend_texto(mensaje: str, user_id: int, chat_id: str = None) -> str:
    """
    Consulta el backend con manejo robusto de errores.
    """
    url = f"{BACKEND_URL}/chat/texto"
    payload = {
        "mensaje": mensaje,
        "chat_id": chat_id or str(user_id),
        "llm": "gemini"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("respuesta", "No se pudo obtener respuesta.")
            else:
                logging.error(f"Error del backend: {response.status_code} - {response.text}")
                return "Lo siento, hay un problema temporal con el servicio. Intenta de nuevo en unos momentos."
                
    except httpx.TimeoutException:
        logging.error("Timeout al consultar el backend")
        return "La consulta está tomando más tiempo del esperado. Por favor, intenta de nuevo."
    except Exception as e:
        logging.error(f"Error al consultar backend: {str(e)}")
        return "Lo siento, no puedo procesar tu consulta en este momento. Intenta de nuevo más tarde."

async def consultar_backend_imagen(image_path: str, user_id: int, caption: str = "") -> str:
    """
    Procesa imágenes con manejo robusto de errores.
    Incluye el caption (texto adjunto) si está presente.
    """
    url = f"{BACKEND_URL}/chat/imagen"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(image_path, "rb") as f:
                files = {"imagen": (os.path.basename(image_path), f, "image/jpeg")}
                data = {"mensaje": caption} if caption else {}
                response = await client.post(url, files=files, data=data)
                
            if response.status_code == 200:
                data = response.json()
                # Solo retornar la respuesta del agente, sin mostrar la descripción técnica
                return data.get('respuesta', 'No se pudo obtener respuesta.')
            else:
                return "Error al procesar la imagen. Intenta de nuevo."
                
    except Exception as e:
        logging.error(f"Error al procesar imagen: {str(e)}")
        return "No pude procesar la imagen. Intenta enviarla de nuevo."

async def consultar_backend_audio(audio_path: str, user_id: int) -> str:
    """
    Procesa audio con manejo robusto de errores.
    """
    url = f"{BACKEND_URL}/chat/audio"
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as f:
                files = {"audio": (os.path.basename(audio_path), f, "audio/mpeg")}
                response = await client.post(url, files=files)
                
            if response.status_code == 200:
                data = response.json()
                # Solo retornar la respuesta del agente, sin mostrar la transcripción
                return data.get('respuesta', 'No se pudo obtener respuesta.')
            else:
                return "Error al procesar el audio. Intenta de nuevo."
                
    except Exception as e:
        logging.error(f"Error al procesar audio: {str(e)}")
        return "No pude procesar el audio. Intenta enviarlo de nuevo."

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja mensajes de texto con logging mejorado.
    """
    user_message = update.message.text
    user_id = update.message.from_user.id
    chat_id = str(update.message.chat_id)
    
    logging.info(f"Mensaje recibido de usuario {user_id} en chat {chat_id}: {user_message}")
    
    respuesta = await consultar_backend_texto(user_message, user_id, chat_id)
    
    logging.info(f"Respuesta enviada a usuario {user_id}: {respuesta[:100]}...")
    await update.message.reply_text(respuesta)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja imágenes con cleanup automático.
    Incluye el caption (texto adjunto) si está presente.
    """
    user_id = update.message.from_user.id
    chat_id = str(update.message.chat_id)
    photo = update.message.photo[-1]  # Máxima resolución
    caption = update.message.caption or ""  # Capturar el texto adjunto
    
    logging.info(f"Imagen recibida de usuario {user_id} en chat {chat_id}")
    if caption:
        logging.info(f"Caption incluido: {caption}")
    
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            temp_file = tf.name
            file = await context.bot.get_file(photo.file_id)
            await file.download_to_drive(tf.name)
            respuesta = await consultar_backend_imagen(tf.name, user_id, caption)
            
        await update.message.reply_text(respuesta)
        
    except Exception as e:
        logging.error(f"Error procesando imagen: {str(e)}")
        await update.message.reply_text("Error al procesar la imagen. Intenta de nuevo.")
    finally:
        # Cleanup del archivo temporal
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Maneja audio con cleanup automático.
    """
    user_id = update.message.from_user.id
    audio = update.message.voice or update.message.audio
    
    if not audio:
        await update.message.reply_text("No se detectó audio válido.")
        return
        
    logging.info(f"Audio recibido de usuario {user_id}")
    
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
            temp_file = tf.name
            file = await context.bot.get_file(audio.file_id)
            await file.download_to_drive(tf.name)
            respuesta = await consultar_backend_audio(tf.name, user_id)
            
        await update.message.reply_text(respuesta)
        
    except Exception as e:
        logging.error(f"Error procesando audio: {str(e)}")
        await update.message.reply_text("Error al procesar el audio. Intenta de nuevo.")
    finally:
        # Cleanup del archivo temporal
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando de inicio mejorado.
    """
    mensaje_bienvenida = (
        "¡Hola! 👋 Soy tu agente de ventas de Sextinvalle.\n\n"
        "Puedo ayudarte con:\n"
        "• Consultas sobre productos y precios\n"
        "• Información de la empresa\n"
        "• Procesar imágenes y mensajes de voz\n\n"
        "¿En qué puedo ayudarte hoy?"
    )
    await update.message.reply_text(mensaje_bienvenida)

def main():
    """
    Función principal con manejo de errores.
    """
    try:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        # Registrar handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
        
        logging.info("Bot iniciado correctamente. Esperando mensajes...")
        app.run_polling()
        
    except Exception as e:
        logging.error(f"Error al iniciar el bot: {str(e)}")
        exit(1)

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    main() 