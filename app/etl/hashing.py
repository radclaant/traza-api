import hashlib
from datetime import datetime

import pandas as pd


def normalizar_valor(v):
    if pd.isna(v) or v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    if isinstance(v, (pd.Timestamp, datetime)):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    return str(v).strip()


def calcular_hash_fila(row: pd.Series, cols: list[str]) -> str:
    partes = [f"{c}={normalizar_valor(row[c])}" for c in cols if c in row.index]
    texto = "|".join(partes)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()
