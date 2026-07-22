from typing import Optional

from pydantic import BaseModel


class ResumenProceso(BaseModel):
    dry_run: bool
    filas_leidas: int
    columnas_ignoradas: list[str]
    nuevos: int
    modificados: int
    sin_cambio: int
    eliminados: int
    inactivados: int
    lotes_con_error: int
    duplicados_removidos: int
    muestra_nuevos: list[str] = []
    muestra_modificados: list[str] = []
    muestra_eliminados: list[str] = []
    log: list[str] = []


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    api: str = "ok"
    supabase: bool
