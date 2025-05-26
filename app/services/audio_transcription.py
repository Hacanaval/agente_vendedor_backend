import os
import logging
import tempfile
from typing import Optional
from openai import AsyncOpenAI

# Importación condicional de pydub
try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    logging.warning("pydub no disponible - conversión de audio limitada")

class AudioTranscriptionService:
    """Servicio para transcripción de audio usando OpenAI Whisper"""
    
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializar cliente de OpenAI"""
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key)
            logging.info("Cliente OpenAI inicializado para transcripción")
        else:
            logging.warning("OPENAI_API_KEY no configurada - transcripción no disponible")
    
    async def transcribir_audio(self, archivo_path: str, formato_original: str = None) -> Optional[str]:
        """
        Transcribe un archivo de audio usando Whisper
        
        Args:
            archivo_path: Ruta al archivo de audio
            formato_original: Formato original del archivo (opcional)
            
        Returns:
            Texto transcrito o None si hay error
        """
        if not self.client:
            logging.error("Cliente OpenAI no disponible")
            return None
        
        try:
            # Convertir a formato compatible si es necesario
            archivo_procesado = await self._procesar_audio(archivo_path, formato_original)
            
            # Transcribir con Whisper
            with open(archivo_procesado, "rb") as audio_file:
                transcript = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="es"  # Español
                )
            
            # Limpiar archivo temporal si se creó uno
            if archivo_procesado != archivo_path and os.path.exists(archivo_procesado):
                os.unlink(archivo_procesado)
            
            transcripcion = transcript.text.strip()
            logging.info(f"Audio transcrito exitosamente: {transcripcion[:100]}...")
            return transcripcion
            
        except Exception as e:
            logging.error(f"Error transcribiendo audio: {str(e)}")
            return None
    
    async def _procesar_audio(self, archivo_path: str, formato_original: str = None) -> str:
        """
        Procesa el archivo de audio para asegurar compatibilidad con Whisper
        
        Args:
            archivo_path: Ruta al archivo original
            formato_original: Formato del archivo original
            
        Returns:
            Ruta al archivo procesado (puede ser el mismo si no necesita conversión)
        """
        try:
            # Formatos soportados directamente por Whisper
            formatos_soportados = [
                "audio/mpeg", "audio/mp3", "audio/wav", "audio/m4a", 
                "audio/mp4", "audio/webm", "audio/ogg"
            ]
            
            # Si el formato ya es soportado y el archivo no es muy grande, usarlo directamente
            if formato_original in formatos_soportados:
                file_size = os.path.getsize(archivo_path)
                if file_size <= 25 * 1024 * 1024:  # 25MB límite de Whisper
                    return archivo_path
            
            # Si pydub no está disponible, usar archivo original
            if not PYDUB_AVAILABLE:
                logging.warning("pydub no disponible - usando archivo original sin conversión")
                return archivo_path
            
            # Convertir usando pydub
            logging.info(f"Convirtiendo audio de formato {formato_original}")
            
            # Cargar audio con pydub
            if formato_original == "audio/ogg":
                audio = AudioSegment.from_ogg(archivo_path)
            elif formato_original == "audio/webm":
                audio = AudioSegment.from_file(archivo_path, format="webm")
            else:
                audio = AudioSegment.from_file(archivo_path)
            
            # Optimizar para Whisper: mono, 16kHz, máximo 25MB
            audio = audio.set_channels(1)  # Mono
            audio = audio.set_frame_rate(16000)  # 16kHz
            
            # Si es muy largo, truncar a 10 minutos (límite práctico)
            max_duration = 10 * 60 * 1000  # 10 minutos en ms
            if len(audio) > max_duration:
                audio = audio[:max_duration]
                logging.warning("Audio truncado a 10 minutos para transcripción")
            
            # Guardar como MP3 temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
                temp_path = temp_file.name
            
            audio.export(temp_path, format="mp3", bitrate="64k")
            logging.info(f"Audio convertido y guardado en: {temp_path}")
            
            return temp_path
            
        except Exception as e:
            logging.error(f"Error procesando audio: {str(e)}")
            # Si falla la conversión, intentar con el archivo original
            return archivo_path
    
    def is_available(self) -> bool:
        """Verifica si el servicio de transcripción está disponible"""
        return self.client is not None

# Instancia global del servicio
audio_service = AudioTranscriptionService() 