from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from app.core.database import get_db
from app.services.cliente_manager import ClienteManager
from app.services.rag_clientes import RAGClientes

router = APIRouter(prefix="/clientes", tags=["clientes"])

@router.get("/")
async def listar_clientes(
    limite: int = Query(20, ge=1, le=100, description="Número máximo de clientes a retornar"),
    busqueda: Optional[str] = Query(None, description="Término de búsqueda (nombre, cédula o teléfono)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lista clientes con opción de búsqueda.
    
    - **limite**: Número máximo de clientes a retornar (1-100)
    - **busqueda**: Término de búsqueda opcional
    """
    try:
        if busqueda:
            clientes = await ClienteManager.buscar_clientes(busqueda, db, limite)
        else:
            clientes = await ClienteManager.obtener_clientes_top(db, limite)
        
        return {
            "clientes": clientes,
            "total": len(clientes),
            "busqueda": busqueda
        }
        
    except Exception as e:
        logging.error(f"Error listando clientes: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{cedula}")
async def obtener_cliente(
    cedula: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene información detallada de un cliente por su cédula.
    
    - **cedula**: Cédula del cliente
    """
    try:
        cliente = await ClienteManager.obtener_cliente_por_cedula(cedula, db)
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        return {"cliente": cliente.to_dict()}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo cliente {cedula}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{cedula}/historial")
async def obtener_historial_cliente(
    cedula: str,
    limite: int = Query(50, ge=1, le=200, description="Número máximo de compras a retornar"),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el historial completo de compras de un cliente.
    
    - **cedula**: Cédula del cliente
    - **limite**: Número máximo de compras a retornar (1-200)
    """
    try:
        resultado = await ClienteManager.obtener_historial_compras(cedula, db, limite)
        
        if not resultado["exito"]:
            if "no encontrado" in resultado.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            else:
                raise HTTPException(status_code=400, detail=resultado.get("error", "Error obteniendo historial"))
        
        return {
            "cliente": resultado["cliente"],
            "historial": resultado["historial"],
            "total_registros": resultado["total_registros"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo historial de cliente {cedula}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{cedula}/estadisticas")
async def obtener_estadisticas_cliente(
    cedula: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene estadísticas detalladas de un cliente.
    
    - **cedula**: Cédula del cliente
    """
    try:
        resultado = await ClienteManager.obtener_estadisticas_cliente(cedula, db)
        
        if not resultado["exito"]:
            if "no encontrado" in resultado.get("error", "").lower():
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
            else:
                raise HTTPException(status_code=400, detail=resultado.get("error", "Error obteniendo estadísticas"))
        
        return {
            "cliente": resultado["cliente"],
            "estadisticas": resultado["estadisticas"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo estadísticas de cliente {cedula}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/top/compradores")
async def obtener_top_compradores(
    limite: int = Query(10, ge=1, le=50, description="Número de top compradores a retornar"),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene los clientes con mayor valor de compras.
    
    - **limite**: Número de clientes a retornar (1-50)
    """
    try:
        clientes = await ClienteManager.obtener_clientes_top(db, limite)
        
        return {
            "top_compradores": clientes,
            "total": len(clientes)
        }
        
    except Exception as e:
        logging.error(f"Error obteniendo top compradores: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/{cedula}/consulta")
async def consultar_historial_cliente(
    cedula: str,
    pregunta: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Realiza una consulta específica sobre el historial de un cliente usando RAG.
    
    - **cedula**: Cédula del cliente
    - **pregunta**: Objeto con la pregunta a realizar
    
    Ejemplo de body:
    ```json
    {
        "pregunta": "¿Qué productos ha comprado este cliente en los últimos 3 meses?"
    }
    ```
    """
    try:
        if "pregunta" not in pregunta:
            raise HTTPException(status_code=400, detail="Campo 'pregunta' es requerido")
        
        resultado = await RAGClientes.consultar_historial_cliente(
            cedula=cedula,
            pregunta=pregunta["pregunta"],
            db=db
        )
        
        if not resultado["encontrado"]:
            if "no encontré información" in resultado["respuesta"]:
                raise HTTPException(status_code=404, detail="Cliente no encontrado")
        
        return {
            "respuesta": resultado["respuesta"],
            "encontrado": resultado["encontrado"],
            "cliente": resultado.get("cliente"),
            "total_compras": resultado.get("total_compras"),
            "valor_total": resultado.get("valor_total")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en consulta RAG de cliente {cedula}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/buscar")
async def buscar_clientes_avanzado(
    criterios: dict,
    db: AsyncSession = Depends(get_db)
):
    """
    Búsqueda avanzada de clientes con múltiples criterios.
    
    Ejemplo de body:
    ```json
    {
        "nombre": "Juan",
        "limite": 20
    }
    ```
    """
    try:
        nombre = criterios.get("nombre", "")
        limite = criterios.get("limite", 20)
        
        if not nombre:
            raise HTTPException(status_code=400, detail="Campo 'nombre' es requerido")
        
        resultado = await RAGClientes.buscar_cliente_por_nombre(nombre, db)
        
        return {
            "respuesta": resultado["respuesta"],
            "clientes_encontrados": resultado["encontrados"],
            "total": resultado["total"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error en búsqueda avanzada de clientes: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor") 