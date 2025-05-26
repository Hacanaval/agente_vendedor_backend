import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
import logging
import time

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agregar el directorio raíz al path para poder importar los módulos
sys.path.append(str(Path(__file__).parent.parent))

# Cargar variables de entorno
load_dotenv()

# Verificación segura de API Key
def verificar_api_key():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY no está configurada en el archivo .env")
        sys.exit(1)
    if len(api_key) < 10:  # Verificación básica de formato
        logger.error("GOOGLE_API_KEY parece no tener un formato válido")
        sys.exit(1)
    logger.info("GOOGLE_API_KEY configurada correctamente")
    return True

from app.services.clasificacion_tipo_llm import clasificar_tipo_mensaje_llm
from app.core.database import SessionLocal
from sqlalchemy.ext.asyncio import AsyncSession

CASOS_PRUEBA = [
    # Casos de inventario
    "¿Tienen guantes industriales?",
    "¿Qué productos ofrecen?",
    "¿Tienen ofertas?",
    "¿Cuánto cuesta el casco de seguridad?",
    "¿Tienen stock de botas?",
    "¿Qué marcas de respiradores manejan?",
    
    # Casos de venta
    "Quiero comprar 3 martillos",
    "¿Me puedes hacer una cotización?",
    "¿Puedo pagar contra entrega?",
    "Necesito 5 overoles talla M",
    "¿Tienen descuentos para empresas?",
    "Quiero agregar al carrito 2 cascos",
    
    # Casos de contexto
    "¿Dónde están ubicados?",
    "¿Cuál es el horario de atención?",
    "¿Puedo devolver un producto?",
    "¿Cuándo llega mi pedido?",
    "¿Cómo puedo contactarlos?",
    "¿Tienen garantía en los productos?",
    
    # Casos ambiguos
    "Hola, buenos días",
    "Gracias por la información",
    "¿Me puedes ayudar?",
    "Quiero saber más",
    "¿Qué me recomiendas?",
    "¿Tienen algo más?"
]

def probar_clasificacion():
    # Verificar API Key antes de comenzar las pruebas
    verificar_api_key()
    
    print("\n=== Pruebas de Clasificación de Mensajes ===\n")
    print("N°\tCategoría\tTiempo (s)\tMensaje")
    print("-" * 100)
    
    resultados = {
        "inventario": 0,
        "venta": 0,
        "contexto": 0
    }
    
    tiempos = []
    
    for i, mensaje in enumerate(CASOS_PRUEBA, 1):
        try:
            inicio = time.time()
            categoria = clasificar_tipo_mensaje_llm(mensaje)
            tiempo = time.time() - inicio
            tiempos.append(tiempo)
            
            resultados[categoria] += 1
            print(f"{i:02d}\t{categoria:<12}\t{tiempo:.3f}\t\t{mensaje}")
        except Exception as e:
            logger.error(f"Error al clasificar mensaje '{mensaje}': {str(e)}")
            print(f"{i:02d}\tERROR\t\tN/A\t\t{mensaje} (Error: {str(e)})")
    
    tiempo_promedio = sum(tiempos) / len(tiempos) if tiempos else 0
    tiempo_max = max(tiempos) if tiempos else 0
    tiempo_min = min(tiempos) if tiempos else 0
    
    print("\n=== Resumen de Resultados ===")
    print(f"Total mensajes probados: {len(CASOS_PRUEBA)}")
    print(f"Inventario: {resultados['inventario']} ({resultados['inventario']/len(CASOS_PRUEBA)*100:.1f}%)")
    print(f"Venta: {resultados['venta']} ({resultados['venta']/len(CASOS_PRUEBA)*100:.1f}%)")
    print(f"Contexto: {resultados['contexto']} ({resultados['contexto']/len(CASOS_PRUEBA)*100:.1f}%)")
    print("\n=== Métricas de Tiempo ===")
    print(f"Tiempo promedio: {tiempo_promedio:.3f} segundos")
    print(f"Tiempo mínimo: {tiempo_min:.3f} segundos")
    print(f"Tiempo máximo: {tiempo_max:.3f} segundos")

if __name__ == "__main__":
    probar_clasificacion() 