"""
API que reemplaza la conexión directa de la app de escritorio a
Supabase. La app de escritorio deja de tener el service_role key: en
su lugar sube el archivo a esta API (con su propia API key) y esta
API es la única que le habla a Supabase.

Correr localmente:
    uvicorn app.main:app --reload --port 8000

Documentación interactiva en /docs una vez levantado.
"""
import shutil
import tempfile
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.etl.pipeline import procesar_archivo
from app.schemas import HealthResponse, ResumenProceso
from app.security import verificar_api_key
from app.supabase_client import SupabaseClient

app = FastAPI(title="Trazabilidad API", version="0.1.0")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    ok = SupabaseClient().ping()
    return HealthResponse(supabase=ok)


def _guardar_temporal(file: UploadFile) -> str:
    sufijo = Path(file.filename or "archivo").suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(delete=False, suffix=sufijo) as tmp:
        shutil.copyfileobj(file.file, tmp)
        return tmp.name


def _procesar(file: UploadFile, inactivar_eliminados: bool, dry_run: bool) -> ResumenProceso:
    temp_path = _guardar_temporal(file)
    try:
        return procesar_archivo(temp_path, inactivar_eliminados=inactivar_eliminados, dry_run=dry_run)
    except KeyError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {e}")
    finally:
        Path(temp_path).unlink(missing_ok=True)


@app.post(
    "/trazabilidad/preview",
    response_model=ResumenProceso,
    dependencies=[Depends(verificar_api_key)],
)
def preview(file: UploadFile, inactivar_eliminados: bool = True) -> ResumenProceso:
    """Calcula el diff (nuevos/modificados/sin cambio/eliminados) SIN escribir en Supabase."""
    return _procesar(file, inactivar_eliminados, dry_run=True)


@app.post(
    "/trazabilidad/apply",
    response_model=ResumenProceso,
    dependencies=[Depends(verificar_api_key)],
)
def apply(file: UploadFile, inactivar_eliminados: bool = True) -> ResumenProceso:
    """Aplica los cambios en Supabase (upsert de nuevos/modificados y, opcionalmente, inactivación)."""
    return _procesar(file, inactivar_eliminados, dry_run=False)
