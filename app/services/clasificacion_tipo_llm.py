import os
import logging
from typing import Literal
import google.generativeai as genai
from app.services.prompts import SYSTEM_PROMPT_CLASIFICACION

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

DEFAULT_MODEL = os.getenv("LLM_CLASIFICACION_MODEL", "gemini-2.0-flash")
model = genai.GenerativeModel(DEFAULT_MODEL)

async def clasificar_tipo_mensaje_llm(mensaje: str) -> Literal["inventario", "venta", "cliente", "contexto"]:
    """
    Clasifica un mensaje en 'inventario', 'venta', 'cliente' o 'contexto' usando Gemini (Google).
    
    - inventario: Consultas sobre productos, catálogo, disponibilidad
    - venta: Intenciones de compra, pedidos, cotizaciones
    - cliente: Consultas sobre historial de clientes, información específica de clientes
    - contexto: Información general sobre la empresa
    
    Si el resultado no es válido, retorna 'contexto' por defecto.
    """
    
    # Detección rápida para consultas de cliente
    mensaje_lower = mensaje.lower()
    palabras_cliente = [
        "cliente", "clientes", "historial", "compras del cliente", 
        "información del cliente", "estadísticas del cliente"
    ]
    
    # Si contiene número que parece cédula + palabras de cliente
    if any(palabra in mensaje_lower for palabra in palabras_cliente):
        import re
        # Buscar números que parezcan cédulas (8-10 dígitos)
        cedula_pattern = r'\b\d{8,10}\b'
        if re.search(cedula_pattern, mensaje):
            logging.info(f"[clasificar_tipo_mensaje_llm] Detección rápida de cliente: {mensaje}")
            return "cliente"
    
    # Clasificación usando LLM con prompt mejorado
    prompt_mejorado = f"""
Clasifica el siguiente mensaje en una de estas categorías exactas:
- inventario: Para consultas sobre productos, catálogo, disponibilidad, stock, precios de productos
- venta: Para intenciones de compra, pedidos, cotizaciones, "quiero comprar"
- cliente: Para consultas sobre historial de clientes, información específica de un cliente identificado por cédula o nombre
- contexto: Para información general sobre la empresa, servicios, ubicación

MENSAJE: "{mensaje}"

Responde SOLO con una palabra: inventario, venta, cliente o contexto
"""
    
    try:
        response = await model.generate_content_async(prompt_mejorado)
        categoria = response.text.strip().lower()
        
        # Validar que la categoría sea válida
        categorias_validas = {"inventario", "venta", "cliente", "contexto"}
        if categoria not in categorias_validas:
            categoria = "contexto"
        
        logging.info(f"[clasificar_tipo_mensaje_llm] Mensaje: '{mensaje[:50]}...' -> Categoría: {categoria}")
        return categoria
        
    except Exception as e:
        logging.error(f"[clasificar_tipo_mensaje_llm] Error al clasificar: {str(e)}")
        return "contexto"
