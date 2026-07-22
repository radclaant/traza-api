"""
Cálculo de la columna `status` a partir de los catálogos fac_pro,
auditoria, fact_radicado e historicos_rad. Misma regla de negocio del
script de escritorio, separada en dos funciones: `cargar_catalogos`
(hace las llamadas a Supabase) y `calcular_status` (pura, fácil de
testear sin red).
"""
from typing import Callable, Optional

import pandas as pd

from app.supabase_client import SupabaseClient

LogFn = Optional[Callable[[str], None]]


def cargar_catalogos(client: SupabaseClient, log_fn: LogFn = None) -> dict:
    try:
        problems_raw = client.obtener_todos("fac_pro", "secuencial,estado", {"estado": "eq.true"})
        problems = {row["secuencial"] for row in problems_raw if row.get("secuencial")}
        if log_fn:
            log_fn(f"Problemas activos cargados: {len(problems)}")
    except Exception as e:
        if log_fn:
            log_fn(f"Error cargando fac_pro: {e}")
        problems = set()

    try:
        audits_raw = client.obtener_todos("auditoria", "secuencial,fecha_retorno")
        audits = {row["secuencial"]: row for row in audits_raw if row.get("secuencial")}
        if log_fn:
            log_fn(f"Auditorías cargadas: {len(audits)}")
    except Exception as e:
        if log_fn:
            log_fn(f"Error cargando auditoria: {e}")
        audits = {}

    try:
        radicados_raw = client.obtener_todos(
            "fact_radicado", "numero_envio_radicado,id_fecha_radicado,fecha_carga"
        )
        radicados = {}
        for r in radicados_raw:
            envio = r.get("numero_envio_radicado")
            if envio:
                envio_str = str(envio).strip()
                if envio_str.endswith(".0"):
                    envio_str = envio_str[:-2]
                radicados[envio_str] = r
        if log_fn:
            log_fn(f"Envíos de fact_radicado cargados: {len(radicados)}")
    except Exception as e:
        if log_fn:
            log_fn(f"Error cargando fact_radicado: {e}")
        radicados = {}

    try:
        historicos_raw = client.obtener_todos("historicos_rad", "numero_envio")
        historicos = {}
        for h in historicos_raw:
            envio = h.get("numero_envio")
            if envio:
                envio_str = str(envio).strip()
                if envio_str.endswith(".0"):
                    envio_str = envio_str[:-2]
                historicos[envio_str] = h
        if log_fn:
            log_fn(f"Envíos de historicos_rad cargados: {len(historicos)}")
    except Exception as e:
        if log_fn:
            log_fn(f"Error cargando historicos_rad: {e}")
        historicos = {}

    return {"problems": problems, "audits": audits, "radicados": radicados, "historicos": historicos}


def calcular_status(row: pd.Series, catalogos: dict) -> str:
    problems = catalogos["problems"]
    audits = catalogos["audits"]
    radicados = catalogos["radicados"]
    historicos = catalogos["historicos"]

    sec = str(row.get("secuencial", "")).strip()

    if sec == "X":
        return "SIN FACTURAR"
    if sec == "ZQTE":
        return "CIERRE ESPECIAL"
    if sec in problems:
        return "PROBLEMA"

    if sec in audits:
        f_ret = audits[sec].get("fecha_retorno")
        if f_ret is None or str(f_ret).strip() in ("", "None", "null"):
            return "AUDITORIA"
        return "AUDITORIA RETORNADO"

    envio_raw = row.get("numero_envio_radicado")
    if pd.notna(envio_raw) and str(envio_raw).strip() not in ("", "nan", "None", "null"):
        envio = str(envio_raw).strip()
        if envio.endswith(".0"):
            envio = envio[:-2]

        is_radicado = False
        if envio in historicos:
            is_radicado = True
        elif envio in radicados:
            id_fecha_rad = radicados[envio].get("id_fecha_radicado")
            if id_fecha_rad is not None and str(id_fecha_rad).strip() not in ("", "None", "null", "0"):
                is_radicado = True

        if is_radicado:
            return "RADICADO"

        if envio in radicados:
            f_carga = radicados[envio].get("fecha_carga")
            if f_carga is not None and str(f_carga).strip() not in ("", "None", "null"):
                return "ENVIO TRANSFERIDO"

        return "ENVIO INICIALIZADO"

    return "SIN TRAMITE"
