"""Configuração com pydantic-settings.

``Settings`` lê variáveis de ambiente (e o arquivo ``.env``), converte os tipos e valida.
Se uma variável obrigatória faltar ou tiver tipo errado, a aplicação nem sobe.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'prorsc.db'}"
    jwt_secret: str = "troque-este-segredo-jwt-em-producao"
    jwt_ttl_minutos: int = 480
    hashids_salt: str = "troque-este-salt"
    bcrypt_rounds: int = 12
    # Texto separado por vírgula: "http://a,http://b"
    cors_origins: str = "http://localhost:9001"
    # Publicação em subpasta (ex.: "/prorsc_fastapi"): o Swagger passa a buscar o
    # openapi.json e a chamar a API com esse prefixo. Vazio = raiz do domínio.
    root_path: str = ""

    @property
    def lista_cors(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cria as configurações uma única vez (cache) e reaproveita nas próximas chamadas."""
    return Settings()
