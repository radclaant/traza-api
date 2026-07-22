"""
Configuración centralizada.

Todo lo que antes vivía hardcodeado en el .py de escritorio
(DEFAULT_SUPABASE_URL, DEFAULT_SUPABASE_KEY, SCHEMA_NAME, TABLE_NAME, ...)
ahora se lee desde variables de entorno. El service_role key deja de
viajar dentro de un ejecutable de escritorio y vive solo aquí, en el
servidor que corre la API.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Auth de la propia API (lo que la app de escritorio debe mandar
    # en el header X-API-Key). Punto de partida simple; ver README
    # para la ruta de evolución hacia el esquema security.devices.
    api_key: str

    # Datamart
    schema_name: str = "datamart_traza"
    table_name: str = "fact_trazabilidad"
    business_key: str = "secuencial"
    batch_size: int = 200


settings = Settings()
