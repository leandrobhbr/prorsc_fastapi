"""Configuração do Gunicorn para uma aplicação ASGI.

O Gunicorn gerencia os processos (sobe, reinicia, recicla) e cada worker roda o Uvicorn,
que executa a aplicação assíncrona. O Apache faz proxy de /api/ para cá.
"""

import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8002")

# Worker ASGI: cada processo atende muitas requisições ao mesmo tempo (async/await).
worker_class = "uvicorn_worker.UvicornWorker"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))

timeout = 30
accesslog = "-"
errorlog = "-"
forwarded_allow_ips = "127.0.0.1"
