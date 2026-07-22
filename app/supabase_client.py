"""
Cliente Supabase (REST / PostgREST).

Portado del SupabaseClient del script de escritorio. Misma lógica de
paginación, upsert con on_conflict e inactivación; lo único que cambia
es que la URL/Key ya no se pasan desde una GUI sino que vienen de
`settings` (variables de entorno del servidor).
"""
from datetime import datetime, timezone

import requests

from app.config import settings


class SupabaseClient:
    def __init__(self, schema: str = None):
        self.base = settings.supabase_url.rstrip("/")
        self.schema = schema or settings.schema_name
        self.headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Profile": self.schema,
            "Content-Profile": self.schema,
        }

    def _endpoint(self, table: str) -> str:
        return f"{self.base}/rest/v1/{table}"

    def obtener_hashes(self, table: str, bk: str) -> dict[str, str]:
        hashes: dict[str, str] = {}
        offset, limit = 0, 1000
        while True:
            r = requests.get(
                self._endpoint(table),
                headers={**self.headers, "Range-Unit": "items", "Range": f"{offset}-{offset + limit - 1}"},
                params={"select": f"{bk},hash_fila", "activo": "eq.true"},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            for row in data:
                k, h = row.get(bk), row.get("hash_fila")
                if k:
                    hashes[str(k)] = h or ""
            if len(data) < limit:
                break
            offset += limit
        return hashes

    def obtener_todos(self, table: str, select: str = "*", params: dict = None) -> list[dict]:
        rows: list[dict] = []
        offset, limit = 0, 1000
        while True:
            headers = {**self.headers, "Range-Unit": "items", "Range": f"{offset}-{offset + limit - 1}"}
            p = {"select": select}
            if params:
                p.update(params)
            r = requests.get(self._endpoint(table), headers=headers, params=p, timeout=30)
            r.raise_for_status()
            data = r.json()
            if not data:
                break
            rows.extend(data)
            if len(data) < limit:
                break
            offset += limit
        return rows

    def upsert(self, table: str, rows: list[dict], keys_conflict: str = "secuencial") -> requests.Response:
        url_upsert = f"{self._endpoint(table)}?on_conflict={keys_conflict}"
        return requests.post(
            url_upsert,
            headers={**self.headers, "Prefer": "resolution=merge-duplicates"},
            json=rows,
            timeout=60,
        )

    def inactivar(self, table: str, bk: str, claves: list[str]) -> requests.Response:
        return requests.patch(
            self._endpoint(table),
            headers=self.headers,
            params={bk: f"in.({','.join(claves)})"},
            json={
                "activo": False,
                "fecha_inactivacion": datetime.now(timezone.utc).isoformat(),
                "razon_inactivacion": "ELIMINADO_DEL_ARCHIVO",
            },
            timeout=60,
        )

    def ping(self) -> bool:
        try:
            r = requests.get(
                self._endpoint(settings.table_name),
                headers=self.headers,
                params={"select": "id_trazabilidad", "limit": "1"},
                timeout=10,
            )
            return r.status_code == 200
        except Exception:
            return False
