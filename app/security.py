"""
Autenticación de la API.

Punto de partida: header X-API-Key fijo, comparado contra la variable
de entorno API_KEY. Es intencionalmente simple para poder arrancar
rápido; en tu esquema `security` ya tienes devices/users/TOTP — si
más adelante quieres que cada equipo de escritorio se autentique con
su propio device (en vez de una key compartida), este es el único
archivo que hay que tocar: cambia `verificar_api_key` por una consulta
a `security.perfiles` / `public.devices` y listo, el resto de la API
no se entera del cambio.
"""
from fastapi import Header, HTTPException, status

from app.config import settings


async def verificar_api_key(x_api_key: str = Header(...)) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida o ausente (header X-API-Key).",
        )
