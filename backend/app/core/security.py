"""Senhas (bcrypt) e tokens JWT (PyJWT)."""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings

ALGORITMO = "HS256"


def gerar_hash_senha(senha: str) -> str:
    salt = bcrypt.gensalt(rounds=get_settings().bcrypt_rounds)
    return bcrypt.hashpw(senha.encode(), salt).decode()


def senha_confere(senha: str, hash_senha: str) -> bool:
    try:
        # Aceita hashes "$2y$" gerados pelo PHP/Laravel.
        return bcrypt.checkpw(senha.encode(), hash_senha.encode())
    except ValueError:
        return False


def criar_token(usuario_id: int) -> str:
    agora = datetime.now(UTC)
    cfg = get_settings()
    dados = {
        "sub": str(usuario_id),  # "subject": a quem o token pertence
        "iat": agora,  # emitido em
        "exp": agora + timedelta(minutes=cfg.jwt_ttl_minutos),  # expira em
    }
    return jwt.encode(dados, cfg.jwt_secret, algorithm=ALGORITMO)


def ler_token(token: str) -> int:
    """Devolve o ID do usuário. Levanta ``jwt.PyJWTError`` se inválido ou expirado."""
    dados = jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITMO])
    return int(dados["sub"])
