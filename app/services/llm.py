import os
import openai

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def generar_respuesta_llm(prompt: str) -> str:
    # Por ahora, usa OpenAI GPT-3.5/4, pero se puede cambiar fácilmente
    if not OPENAI_API_KEY:
        return "[Error: No se configuró OPENAI_API_KEY]"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Eres un agente de ventas AI."},
                      {"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.2,
            api_key=OPENAI_API_KEY
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Error al consultar LLM: {str(e)}]" 