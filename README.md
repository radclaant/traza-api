# Trazabilidad API

Backend que se pone en medio de la app de escritorio y Supabase.
La app de escritorio deja de tener el `service_role key` (que hoy
está hardcodeado en texto plano en `actualizador_trazabilidad_fixed3.py`
y por tanto visible para cualquiera que abra el .py o decompile el
.exe); ahora ese key vive solo en el servidor que corre esta API.

## Qué se portó del script original

Toda la lógica de negocio se movió tal cual, solo reorganizada:

| Original (en el .py) | Ahora en |
|---|---|
| `DEFAULT_SUPABASE_URL/KEY`, `SCHEMA_NAME`, etc. | `app/config.py` (variables de entorno) |
| `class SupabaseClient` | `app/supabase_client.py` |
| `DB_COLUMNS`, `COLUMN_MAP`, `TIMESTAMP_COLS` | `app/etl/column_map.py` |
| `_camel_a_snake`, `parsear_fecha_flexible`, `limpiar_df`, `leer_archivo_robusto`, `row_a_dict` | `app/etl/reader.py` |
| `normalizar_valor`, `calcular_hash_fila` | `app/etl/hashing.py` |
| `calcular_status_fila` + descarga de catálogos (fac_pro, auditoria, fact_radicado, historicos_rad) | `app/etl/status.py` |
| `procesar_archivo` (los 5 pasos) | `app/etl/pipeline.py` |
| Todo lo de tkinter (ventana, botones, log en pantalla) | **se elimina** — ya no aplica, la UI ahora solo llama al API |

## Endpoints

- `GET /health` — valida que la API está viva y que puede llegar a Supabase.
- `POST /trazabilidad/preview` — sube el archivo, calcula nuevos / modificados /
  sin cambio / eliminados **sin escribir nada en Supabase**. Útil para que la
  app de escritorio muestre el resumen antes de que el usuario confirme.
- `POST /trazabilidad/apply` — mismo cálculo, pero además aplica el upsert por
  lotes y, si `inactivar_eliminados=true`, inactiva lo que ya no está en el archivo.

Ambos endpoints reciben `multipart/form-data` con:
- `file`: el .xlsx/.csv/.html que hoy seleccionas en la GUI
- query param opcional `inactivar_eliminados` (default `true`)
- header `X-API-Key: <tu clave>`

Responden un JSON (`ResumenProceso`, ver `app/schemas.py`) con los mismos
números que hoy ves en el log de la app: nuevos, modificados, sin_cambio,
eliminados, inactivados, lotes_con_error, y un `log` con el detalle paso a paso.

## Cómo correr

```bash
python -m venv .venv && source .venv/bin/activate   # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
cp .env.example .env   # y completa SUPABASE_URL, SUPABASE_SERVICE_KEY, API_KEY
uvicorn app.main:app --reload --port 8000
```

Documentación interactiva (Swagger) en `http://localhost:8000/docs` — sirve
para probar los endpoints a mano antes de tocar la app de escritorio.

## Qué falta decidir / siguientes pasos

1. **Dónde vive esta API**: si corre en la misma red donde están los equipos
   de escritorio (un servidor local/oficina) o si se despliega en algún
   proveedor (Render, Railway, un VPS). Esto define si necesitas TLS/dominio
   público o basta con la red interna.
2. **Autenticación real**: `app/security.py` hoy compara contra una sola
   `API_KEY` fija — sirve para arrancar, pero cualquiera con esa key puede
   escribir en `fact_trazabilidad`. Ya tienes en `security.perfiles` /
   `public.devices` una base para autenticación por dispositivo/usuario con
   TOTP; cuando quieras, ese archivo es el único que hay que cambiar.
3. **Rotar el `service_role key` actual**: como estuvo embebido en el .py
   (y probablemente distribuido a varios equipos), conviene regenerarlo en
   Supabase una vez el API esté funcionando, para que la copia vieja quede
   inservible.
4. La app de escritorio: se simplifica a tkinter para elegir archivo +
   llamar a `/preview` y `/apply` con `requests`, mostrando el `log` y los
   contadores que devuelve la API en vez de calcularlos localmente.
