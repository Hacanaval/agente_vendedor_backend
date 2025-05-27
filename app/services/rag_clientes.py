from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.services.cliente_manager import ClienteManager
from app.services.llm_client import generar_respuesta

class RAGClientes:
    """
    RAG especializado para consultas de historial de clientes.
    
    Permite al chatbot consultar información de clientes y su historial
    de compras para brindar respuestas personalizadas y contextualizadas.
    """
    
    @staticmethod
    async def consultar_historial_cliente(
        cedula: str,
        pregunta: str,
        db: AsyncSession,
        llm: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Consulta el historial de un cliente y genera una respuesta contextualizada.
        
        Args:
            cedula: Cédula del cliente
            pregunta: Pregunta específica sobre el historial
            db: Sesión de base de datos
            llm: Modelo de LLM a usar
        """
        try:
            # Obtener historial completo del cliente
            resultado_historial = await ClienteManager.obtener_historial_compras(cedula, db)
            
            if not resultado_historial["exito"]:
                return {
                    "respuesta": f"No encontré información para el cliente con cédula {cedula}.",
                    "encontrado": False,
                    "error": resultado_historial.get("error")
                }
            
            cliente = resultado_historial["cliente"]
            historial = resultado_historial["historial"]
            
            # Construir contexto para el LLM
            contexto = RAGClientes._construir_contexto_cliente(cliente, historial)
            
            # Generar prompt especializado
            system_prompt = RAGClientes._generar_prompt_historial(cliente, contexto)
            user_prompt = f"Pregunta del usuario: {pregunta}"
            
            # Generar respuesta con LLM
            respuesta = await generar_respuesta(
                prompt=user_prompt,
                system_prompt=system_prompt,
                llm=llm
            )
            
            return {
                "respuesta": respuesta,
                "encontrado": True,
                "cliente": cliente,
                "total_compras": len(historial),
                "valor_total": cliente["valor_total_compras"]
            }
            
        except Exception as e:
            logging.error(f"Error en consulta RAG de cliente {cedula}: {e}")
            return {
                "respuesta": "Lo siento, hubo un error al consultar el historial del cliente.",
                "encontrado": False,
                "error": str(e)
            }
    
    @staticmethod
    async def buscar_cliente_por_nombre(
        nombre: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Busca clientes por nombre y retorna información básica.
        
        Args:
            nombre: Nombre o parte del nombre a buscar
            db: Sesión de base de datos
        """
        try:
            clientes = await ClienteManager.buscar_clientes(nombre, db, limite=5)
            
            if not clientes:
                return {
                    "respuesta": f"No encontré clientes con el nombre '{nombre}'.",
                    "encontrados": [],
                    "total": 0
                }
            
            # Formatear respuesta
            if len(clientes) == 1:
                cliente = clientes[0]
                respuesta = f"Encontré al cliente {cliente['nombre_completo']} (Cédula: {cliente['cedula']}) con {cliente['total_compras']} compras por un valor total de ${cliente['valor_total_compras']:,}."
            else:
                respuesta = f"Encontré {len(clientes)} clientes con ese nombre:\n\n"
                for cliente in clientes:
                    respuesta += f"• {cliente['nombre_completo']} (Cédula: {cliente['cedula']}) - {cliente['total_compras']} compras\n"
            
            return {
                "respuesta": respuesta,
                "encontrados": clientes,
                "total": len(clientes)
            }
            
        except Exception as e:
            logging.error(f"Error buscando cliente por nombre '{nombre}': {e}")
            return {
                "respuesta": "Lo siento, hubo un error al buscar el cliente.",
                "encontrados": [],
                "total": 0,
                "error": str(e)
            }
    
    @staticmethod
    async def obtener_estadisticas_cliente(
        cedula: str,
        db: AsyncSession,
        llm: str = "gemini"
    ) -> Dict[str, Any]:
        """
        Obtiene y presenta estadísticas detalladas de un cliente.
        
        Args:
            cedula: Cédula del cliente
            db: Sesión de base de datos
            llm: Modelo de LLM a usar
        """
        try:
            resultado = await ClienteManager.obtener_estadisticas_cliente(cedula, db)
            
            if not resultado["exito"]:
                return {
                    "respuesta": f"No encontré estadísticas para el cliente con cédula {cedula}.",
                    "encontrado": False,
                    "error": resultado.get("error")
                }
            
            cliente = resultado["cliente"]
            estadisticas = resultado["estadisticas"]
            
            # Construir contexto de estadísticas
            contexto_stats = RAGClientes._construir_contexto_estadisticas(cliente, estadisticas)
            
            # Generar respuesta con LLM
            system_prompt = f"""
            Eres un asistente especializado en análisis de clientes para Sextinvalle.
            Presenta las estadísticas del cliente de manera clara y profesional.
            
            Información del cliente y estadísticas:
            {contexto_stats}
            
            Instrucciones:
            - Presenta la información de manera organizada y fácil de entender
            - Destaca los puntos más importantes
            - Usa un tono profesional pero amigable
            - Incluye insights útiles sobre el comportamiento de compra
            """
            
            user_prompt = "Presenta un resumen completo de las estadísticas de este cliente."
            
            respuesta = await generar_respuesta(
                prompt=user_prompt,
                system_prompt=system_prompt,
                llm=llm
            )
            
            return {
                "respuesta": respuesta,
                "encontrado": True,
                "cliente": cliente,
                "estadisticas": estadisticas
            }
            
        except Exception as e:
            logging.error(f"Error obteniendo estadísticas de cliente {cedula}: {e}")
            return {
                "respuesta": "Lo siento, hubo un error al obtener las estadísticas del cliente.",
                "encontrado": False,
                "error": str(e)
            }
    
    @staticmethod
    def _construir_contexto_cliente(cliente: Dict, historial: List[Dict]) -> str:
        """Construye el contexto del cliente para el LLM"""
        contexto = f"""
INFORMACIÓN DEL CLIENTE:
- Nombre: {cliente['nombre_completo']}
- Cédula: {cliente['cedula']}
- Teléfono: {cliente['telefono']}
- Correo: {cliente.get('correo', 'No registrado')}
- Dirección: {cliente['direccion']}, {cliente['barrio']}
- Cliente desde: {cliente['fecha_registro'][:10] if cliente['fecha_registro'] else 'N/A'}
- Última compra: {cliente['fecha_ultima_compra'][:10] if cliente['fecha_ultima_compra'] else 'N/A'}
- Total de compras: {cliente['total_compras']}
- Valor total comprado: ${cliente['valor_total_compras']:,}

HISTORIAL DE COMPRAS (últimas {len(historial)} compras):
"""
        
        for i, compra in enumerate(historial[:10], 1):  # Mostrar máximo 10 compras recientes
            fecha = compra['fecha'][:10] if compra['fecha'] else 'N/A'
            contexto += f"""
{i}. Fecha: {fecha}
   Producto: {compra['producto']['nombre']}
   Cantidad: {compra['cantidad']}
   Total: ${compra['total']:,}
   Estado: {compra['estado']}
"""
        
        if len(historial) > 10:
            contexto += f"\n... y {len(historial) - 10} compras más anteriores."
        
        return contexto
    
    @staticmethod
    def _construir_contexto_estadisticas(cliente: Dict, estadisticas: Dict) -> str:
        """Construye el contexto de estadísticas para el LLM"""
        contexto = f"""
CLIENTE: {cliente['nombre_completo']} (Cédula: {cliente['cedula']})

RESUMEN GENERAL:
- Total de compras: {cliente['total_compras']}
- Valor total: ${cliente['valor_total_compras']:,}
- Promedio por compra: ${estadisticas['promedio_compra']:,.0f}
- Días desde última compra: {estadisticas['dias_desde_ultima_compra'] or 'N/A'}

PRODUCTOS FAVORITOS:
"""
        
        for i, producto in enumerate(estadisticas['productos_favoritos'][:5], 1):
            contexto += f"{i}. {producto['producto']} - {producto['cantidad_total']} unidades (${producto['valor_total']:,.0f})\n"
        
        contexto += "\nCOMPRAS POR MES (últimos 12 meses):\n"
        for mes_data in estadisticas['compras_por_mes'][-6:]:  # Últimos 6 meses
            mes = mes_data['mes'][:7] if mes_data['mes'] else 'N/A'
            contexto += f"- {mes}: {mes_data['cantidad_compras']} compras (${mes_data['valor_total']:,.0f})\n"
        
        return contexto
    
    @staticmethod
    def _generar_prompt_historial(cliente: Dict, contexto: str) -> str:
        """Genera el prompt del sistema para consultas de historial"""
        return f"""
Eres un asistente especializado en atención al cliente para Sextinvalle.
Tienes acceso al historial completo de compras del cliente y puedes responder preguntas específicas sobre:

- Qué productos ha comprado
- Cuándo realizó sus compras
- Frecuencia de compras
- Productos favoritos
- Valor total de compras
- Recomendaciones basadas en historial

INFORMACIÓN DISPONIBLE:
{contexto}

INSTRUCCIONES:
- Responde de manera amigable y profesional
- Usa la información específica del historial para dar respuestas precisas
- Si no tienes la información exacta, di que necesitas más detalles
- Ofrece insights útiles basados en el patrón de compras
- Mantén la confidencialidad y profesionalismo
- Sugiere productos relacionados cuando sea apropiado
"""

    @staticmethod
    async def detectar_consulta_cliente(mensaje: str) -> Dict[str, Any]:
        """
        Detecta si un mensaje es una consulta sobre historial de cliente.
        
        Args:
            mensaje: Mensaje del usuario
            
        Returns:
            Dict con información sobre si es consulta de cliente y qué tipo
        """
        mensaje_lower = mensaje.lower()
        
        # Patrones para detectar consultas de clientes (MÁS ESPECÍFICOS)
        patrones_cliente = [
            "historial del cliente", "compras del cliente", "cliente con cédula", 
            "cliente ha comprado", "última compra del cliente", "cuántas veces ha comprado",
            "qué ha comprado el cliente", "productos comprados por el cliente", 
            "estadísticas del cliente", "buscar cliente", "información del cliente", 
            "datos del cliente", "encontrar cliente", "perfil del cliente",
            "cliente número", "cédula del cliente"
        ]
        
        # Patrones para detectar cédulas (solo si hay contexto de cliente)
        import re
        cedula_match = re.search(r'\b\d{6,12}\b', mensaje)
        
        # Solo es consulta de cliente si tiene patrón específico O cédula + contexto
        # ADEMÁS debe tener contexto explícito de cliente (no productos en general)
        tiene_patron_cliente = any(patron in mensaje_lower for patron in patrones_cliente)
        tiene_cedula_con_contexto = (cedula_match and any(palabra in mensaje_lower for palabra in ["cliente", "cédula", "historial", "compras"]))
        
        # Excluir consultas que claramente son sobre productos en general  
        # MEJORADO: Detectar mejor las consultas de inventario y excluir explícitamente
        consultas_inventario_claras = [
            "qué productos tienen", "que productos tienen", "qué tienen", "que tienen",
            "productos disponibles", "catálogo", "inventario", "mostrar productos",
            "ver productos", "qué venden", "que venden", "lista de productos",
            "qué productos tienen disponibles", "que productos tienen disponibles",
            "productos tienen disponibles", "tienen disponibles", "qué hay disponible",
            "que hay disponible", "mostrar inventario", "ver inventario", 
            "catálogo de productos", "productos en stock", "stock disponible",
            "qué manejan", "que manejan", "qué ofrecen", "que ofrecen"
        ]
        
        es_consulta_inventario_clara = any(patron in mensaje_lower for patron in consultas_inventario_claras)
        
        es_consulta_cliente = (tiene_patron_cliente or tiene_cedula_con_contexto) and not es_consulta_inventario_clara
        
        # DEBUGGING
        import logging
        logging.info(f"[RAGClientes] ANÁLISIS DETALLADO:")
        logging.info(f"[RAGClientes] Mensaje original: '{mensaje}'")
        logging.info(f"[RAGClientes] Mensaje lower: '{mensaje_lower}'")
        logging.info(f"[RAGClientes] Patrones cliente encontrados: {[p for p in patrones_cliente if p in mensaje_lower]}")
        logging.info(f"[RAGClientes] Patrones inventario encontrados: {[p for p in consultas_inventario_claras if p in mensaje_lower]}")
        logging.info(f"[RAGClientes] Tiene patrón cliente: {tiene_patron_cliente}")
        logging.info(f"[RAGClientes] Tiene cédula con contexto: {tiene_cedula_con_contexto}")
        logging.info(f"[RAGClientes] Es consulta inventario clara: {es_consulta_inventario_clara}")
        logging.info(f"[RAGClientes] RESULTADO FINAL es_consulta_cliente: {es_consulta_cliente}")
        
        return {
            "es_consulta_cliente": es_consulta_cliente,
            "cedula_detectada": cedula_match.group() if cedula_match else None,
            "tipo_consulta": "historial" if "historial" in mensaje_lower else 
                           "estadisticas" if "estadísticas" in mensaje_lower else
                           "busqueda" if any(p in mensaje_lower for p in ["buscar", "encontrar"]) else
                           "general"
        } 