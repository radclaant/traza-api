"""
Orquestación del proceso completo: leer archivo -> limpiar -> calcular
status -> calcular hash -> comparar contra la BD -> (si no es dry_run)
aplicar upsert/inactivación.

Es el mismo flujo de `procesar_archivo` del script de escritorio,
reescrito para no depender de tkinter: en vez de escribir a un widget
de log, junta los mensajes en una lista y devuelve un ResumenProceso
al final. El desktop app ahora solo necesita mostrar ese resumen.
"""
from pathlib import Path

from app.config import settings
from app.etl.column_map import BUSINESS_KEY, DB_COLUMNS, HASH_COLUMNS
from app.etl.hashing import calcular_hash_fila
from app.etl.reader import leer_archivo_robusto, limpiar_df, row_a_dict
from app.etl.status import calcular_status, cargar_catalogos
from app.schemas import ResumenProceso
from app.supabase_client import SupabaseClient


def procesar_archivo(filepath: str, inactivar_eliminados: bool, dry_run: bool) -> ResumenProceso:
    log: list[str] = []

    def log_fn(msg: str) -> None:
        log.append(msg)

    log_fn(f"Archivo: {Path(filepath).name}")
    log_fn("[1/5] Leyendo archivo…")
    df = leer_archivo_robusto(filepath, log_fn)
    filas_leidas = len(df)
    log_fn(f"Se leen {filas_leidas} filas")

    df = limpiar_df(df, log_fn)

    cols_archivo = set(df.columns)
    cols_ignoradas = sorted(cols_archivo - DB_COLUMNS - {"hash_fila"})
    if cols_ignoradas:
        log_fn(f"Columnas ignoradas (no están en la BD): {cols_ignoradas}")

    if BUSINESS_KEY not in df.columns:
        raise KeyError(
            f"Columna clave '{BUSINESS_KEY}' no encontrada. Columnas en archivo: {sorted(df.columns)}"
        )

    total_previo = len(df)
    df[BUSINESS_KEY] = df[BUSINESS_KEY].astype(str).str.strip()
    df = df.drop_duplicates(subset=[BUSINESS_KEY], keep="last")
    duplicados_removidos = total_previo - len(df)
    if duplicados_removidos:
        log_fn(f"Se eliminaron {duplicados_removidos} filas duplicadas (mismo secuencial)")

    log_fn("[1.5/5] Descargando catálogos de novedades y radicaciones…")
    client = SupabaseClient(settings.schema_name)
    catalogos = cargar_catalogos(client, log_fn)
    df["status"] = df.apply(lambda r: calcular_status(r, catalogos), axis=1)

    log_fn("[2/5] Calculando hashes del archivo…")
    hash_cols = HASH_COLUMNS if HASH_COLUMNS else list(df.columns)
    df["hash_fila"] = df.apply(lambda r: calcular_hash_fila(r, hash_cols), axis=1)

    log_fn("[3/5] Consultando hashes en la base de datos…")
    hashes_bd = client.obtener_hashes(settings.table_name, BUSINESS_KEY)
    log_fn(f"Registros en BD: {len(hashes_bd)}")

    log_fn("[4/5] Comparando cambios…")
    nuevos, modificados = [], []
    sin_cambio = 0
    for _, row in df.iterrows():
        clave = str(row[BUSINESS_KEY])
        hash_viejo = hashes_bd.get(clave, "")
        if not hash_viejo:
            nuevos.append(row)
        elif row["hash_fila"] != hash_viejo:
            modificados.append(row)
        else:
            sin_cambio += 1

    claves_archivo = set(df[BUSINESS_KEY].tolist())
    eliminados = list(set(hashes_bd.keys()) - claves_archivo)
    log_fn(f"Nuevos: {len(nuevos)} | Modificados: {len(modificados)} | Sin cambio: {sin_cambio} | No en archivo: {len(eliminados)}")

    lotes_con_error = 0
    inactivados = 0
    total_upsert = nuevos + modificados

    if dry_run:
        log_fn("Modo preview: no se aplicó ningún cambio en Supabase.")
    else:
        log_fn("[5/5] Aplicando cambios en Supabase…")
        if total_upsert:
            for i in range(0, len(total_upsert), settings.batch_size):
                lote = total_upsert[i: i + settings.batch_size]
                payload = [row_a_dict(r) for r in lote]
                r = client.upsert(settings.table_name, payload)
                if r.status_code not in (200, 201):
                    log_fn(f"Error en lote {i // settings.batch_size + 1}: {r.status_code} — {r.text[:200]}")
                    lotes_con_error += 1
                else:
                    log_fn(f"Lote {i // settings.batch_size + 1}: {len(lote)} registros aplicados")

        if inactivar_eliminados and eliminados:
            for i in range(0, len(eliminados), settings.batch_size):
                lote = eliminados[i: i + settings.batch_size]
                r = client.inactivar(settings.table_name, BUSINESS_KEY, lote)
                if r.status_code not in (200, 204):
                    log_fn(f"Error inactivando lote: {r.status_code}")
                    lotes_con_error += 1
                else:
                    inactivados += len(lote)

    return ResumenProceso(
        dry_run=dry_run,
        filas_leidas=filas_leidas,
        columnas_ignoradas=cols_ignoradas,
        nuevos=len(nuevos),
        modificados=len(modificados),
        sin_cambio=sin_cambio,
        eliminados=len(eliminados),
        inactivados=inactivados,
        lotes_con_error=lotes_con_error,
        duplicados_removidos=duplicados_removidos,
        muestra_nuevos=[str(r[BUSINESS_KEY]) for r in nuevos[:10]],
        muestra_modificados=[str(r[BUSINESS_KEY]) for r in modificados[:10]],
        muestra_eliminados=eliminados[:10],
        log=log,
    )
