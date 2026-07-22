"""
Lectura robusta del archivo (Excel/CSV/HTML-disfrazado-de-xls) y
limpieza/normalización de columnas. Portado del script de escritorio;
`log_fn` sigue existiendo con la misma firma (Callable[[str], None])
pero ahora escribe a una lista en memoria en vez de al widget de log,
para que el resultado se pueda devolver en la respuesta HTTP.
"""
import io
import os
import re
import shutil
import tempfile
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import pandas as pd

from app.etl.column_map import COLUMN_MAP, DB_COLUMNS, TIMESTAMP_COLS

LogFn = Optional[Callable[[str], None]]


def _camel_a_snake(nombre: str) -> str:
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n"), ("°", "")]:
        nombre = nombre.replace(a, b).replace(a.upper(), b.upper())
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", nombre.strip())
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s.lower()


def parsear_fecha_flexible(serie: pd.Series, log_fn: LogFn = None) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie

    serie_str = serie.astype(str).str.strip()
    serie_str = serie_str.str.replace(r"\s*/\s*", "/", regex=True)
    serie_str = serie_str.str.replace(r"\s*-\s*", "-", regex=True)
    serie_str = serie_str.str.replace(r"\s+", " ", regex=True)

    vacios_mask = serie_str.isin(["", "nan", "None", "NaT", "none", "NAT", "NaN"])

    formatos = [
        "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y",
        "%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y %I:%M %p",
        "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y",
    ]

    resultado = pd.Series(pd.NaT, index=serie.index, dtype="datetime64[ns]")
    formatos_usados = []

    for fmt in formatos:
        pendientes_mask = resultado.isna() & ~vacios_mask
        if not pendientes_mask.any():
            break
        intento = pd.to_datetime(serie_str.where(pendientes_mask, other=""), format=fmt, errors="coerce")
        nuevas = intento.notna() & pendientes_mask
        if nuevas.any():
            resultado = resultado.where(~nuevas, other=intento)
            formatos_usados.append(f"{fmt}({int(nuevas.sum())})")

    pendientes_mask = resultado.isna() & ~vacios_mask
    if pendientes_mask.any():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fallback = pd.to_datetime(serie_str.where(pendientes_mask, other=""), errors="coerce", dayfirst=True)
        nuevas = fallback.notna() & pendientes_mask
        if nuevas.any():
            resultado = resultado.where(~nuevas, other=fallback)
            formatos_usados.append(f"inferencia({int(nuevas.sum())})")

    resultado[vacios_mask] = pd.NaT

    if log_fn:
        total_datos = int((~vacios_mask).sum())
        parseadas = int(resultado.notna().sum())
        sin_parsear = total_datos - parseadas
        resumen = ", ".join(formatos_usados) if formatos_usados else "ninguno"
        log_fn(f"Formatos usados: [{resumen}] | Parseadas: {parseadas}/{total_datos}")
        if sin_parsear > 0:
            muestras = serie_str[resultado.isna() & ~vacios_mask].head(3).tolist()
            log_fn(f"Sin parsear ({sin_parsear}): {muestras}")

    return resultado


def limpiar_df(df: pd.DataFrame, log_fn: LogFn = None, verbose: bool = True) -> pd.DataFrame:
    df = df.copy()
    df.columns = [_camel_a_snake(str(c)) for c in df.columns]

    if COLUMN_MAP:
        df.rename(columns={k.lower(): v for k, v in COLUMN_MAP.items()}, inplace=True)

    _log = log_fn if verbose else None
    for col in TIMESTAMP_COLS:
        if col in df.columns:
            df[col] = parsear_fecha_flexible(df[col], _log)

    return df


def row_a_dict(row: pd.Series) -> dict:
    d = {}
    for col, val in row.items():
        if col not in DB_COLUMNS:
            continue
        if pd.isna(val) or str(val).strip() in ("", "nan", "None", "NaT"):
            d[col] = None
        elif isinstance(val, (pd.Timestamp, datetime)):
            d[col] = val.isoformat() if not pd.isnull(val) else None
        elif isinstance(val, float):
            try:
                d[col] = int(val) if val == int(val) else val
            except (ValueError, OverflowError):
                d[col] = val
        else:
            d[col] = str(val).strip() if str(val).strip() else None
    if "activo" not in d:
        d["activo"] = True
    return d


def leer_archivo_robusto(filepath: str, log_fn: LogFn = None) -> pd.DataFrame:
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"temp_trazabilidad_{int(time.time())}.html")

    try:
        shutil.copy2(filepath, temp_path)
        try:
            return pd.read_excel(temp_path, dtype=str)
        except Exception:
            if log_fn:
                log_fn("Formato binario rechazado, forzando limpieza de HTML...")

            with open(temp_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tablas = pd.read_html(io.StringIO(content), flavor="lxml")
            if not tablas:
                raise ValueError("No se encontró ninguna tabla en el archivo HTML.")

            df_raw = max(tablas, key=len)

            columnas_reales = [
                "Nro", "Aseguradora", "AseguradoraContrato", "Tipo", "Sede", "Identificacion",
                "Paciente", "Ingreso", "Atencion", "FechaIngreso", "FechaEgreso", "SedeServicio",
                "IdServicio", "Servicio", "TipoCita", "UnidadFuncinal", "Cama", "Estado",
                "AltaRegente", "Regente", "AltaFacturadorDX", "FacturadorDx", "AltaFacturadorCX",
                "FacturadorCX", "Secuencial", "FechaCierre", "UsuarioCierre", "NomUsuarioCierra",
                "VUsuarioEnvio", "NomUsuarioEnvia", "FechaEnvio", "UsuarioActual", "NomUsuarioActual",
                "Proceso", "TotalSinRadicar", "NumeroEnvioRadicado", "FechaEnvioRips",
                "DocumentoGeneraRips", "NomUsuarioGeneraRips", "UltimoComentario", "Autorizacion",
            ]

            df = df_raw.iloc[2:].copy()
            if len(df.columns) > len(columnas_reales):
                df = df.iloc[:, : len(columnas_reales)]
            df.columns = columnas_reales
            df = df.reset_index(drop=True).astype(str)

            if log_fn:
                log_fn(f"Tabla recuperada por fallback HTML. Filas: {len(df)}")
            return df
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
