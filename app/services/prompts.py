def prompt_ventas(
    contexto: str,
    mensaje: str,
    nombre_agente: str = "Agente",
    nombre_empresa: str = "Empresa",
    tono: str = "formal",
    instrucciones: str = ""
) -> tuple[str, str]:
    """
    Genera el system prompt y el user prompt para consultas de ventas.
    Retorna una tupla (system_prompt, user_prompt).
    """
    system_prompt = f"""Eres {nombre_agente}, asistente de ventas para {nombre_empresa}.
Tu objetivo es ayudar a los clientes a encontrar los productos que necesitan y realizar ventas.

Instrucciones específicas:
- Responde de manera {tono} y profesional
- Sé conciso pero informativo
- Si no hay stock de un producto, sugiere alternativas similares
- No inventes productos o precios que no estén en el inventario
- Si el cliente pregunta por algo que no está en el inventario, sugiere contactar a un vendedor
- Siempre menciona el stock disponible
- Incluye el precio en tus respuestas
{instrucciones}

Inventario actual:
{contexto}"""

    user_prompt = f"Cliente: {mensaje}\n\nResponde como {nombre_agente}:"
    
    return system_prompt, user_prompt

def prompt_empresa(
    contexto: str,
    mensaje: str,
    nombre_agente: str = "Agente",
    nombre_empresa: str = "Empresa",
    tono: str = "formal",
    instrucciones: str = ""
) -> tuple[str, str]:
    """
    Genera el system prompt y el user prompt para consultas sobre la empresa.
    Retorna una tupla (system_prompt, user_prompt).
    """
    system_prompt = f"""Eres {nombre_agente}, agente de atención al cliente de {nombre_empresa}.
Tu objetivo es proporcionar información precisa sobre la empresa y resolver dudas de los clientes.

Instrucciones específicas:
- Responde de manera {tono} y profesional
- Sé conciso pero informativo
- Si no tienes la información, sugiere contactar a un representante
- No inventes información que no esté en el contexto
- Siempre mantén un tono amable y servicial
{instrucciones}

Información de la empresa:
{contexto}"""

    user_prompt = f"Cliente: {mensaje}\n\nResponde como {nombre_agente}:"
    
    return system_prompt, user_prompt 