# Calculadora RSC-TAE de livre acesso — implementação em FastAPI

Calculadora de pontuação do **Reconhecimento de Saberes e Competências (RSC)** dos servidores
**Técnico-Administrativos em Educação (TAE)**. O servidor informa a escolaridade, escolhe
atividades do catálogo oficial de saberes (Anexos I a VI) e vê na hora a pontuação e os níveis
RSC atingidos.

**Demonstração online:** https://leandrocampos.dev/prorsc/ — usuário `teste@teste.com.br`, senha `123456`.

A mesma calculadora existe em três backends Python, com a mesma API e o mesmo frontend:

| Implementação | Repositório | Demo |
|---|---|---|
| Flask | [prorsc_flask](https://github.com/leandrobhbr/prorsc_flask) | [abrir](https://leandrocampos.dev/prorsc_flask/) |
| **FastAPI** (este) | [prorsc_fastapi](https://github.com/leandrobhbr/prorsc_fastapi) | [abrir](https://leandrocampos.dev/prorsc_fastapi/) |
| Django | [prorsc_django](https://github.com/leandrobhbr/prorsc_django) | [abrir](https://leandrocampos.dev/prorsc_django/) |

Derivada do [ProRSC-TAE](https://github.com/leandrobhbr/pro-rsc-tae), sistema completo oferecido
como Software Público Brasileiro.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12+ · FastAPI · Pydantic v2 · pydantic-settings · SQLAlchemy 2.0 **async** · Alembic · PyJWT |
| Banco | SQLite (aiosqlite, modo WAL) |
| Frontend | Vue 3 · Quasar 2 · Pinia · axios |
| Produção | Ubuntu 24.04 · Apache (proxy reverso) · Gunicorn + Uvicorn · systemd |
| Qualidade | pytest + pytest-asyncio + httpx · ruff · uv |

## Rodando localmente

Pré-requisitos: [uv](https://docs.astral.sh/uv/) e Node.js 22+.

```bash
# Backend → http://localhost:8002   (Swagger em http://localhost:8002/api/docs)
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head      # cria as tabelas (data/prorsc.db)
uv run python -m app.seed        # catálogo de 60 itens + usuários de demonstração
uv run uvicorn app.main:app --reload --port 8002

# Frontend → http://localhost:9001   (em outro terminal)
cd frontend
npm install
npm run dev
```

Usuário de demonstração: **teste@teste.com.br** / **123456**.

Testes e qualidade:

```bash
cd backend
uv run pytest            # testes unitários do cálculo + integração da API
uv run ruff check .      # lint
uv run ruff format .     # formatação
```

Publicação em servidor: veja **[docs/DEPLOY.md](docs/DEPLOY.md)** (Ubuntu + Apache + Gunicorn/Uvicorn).

## Estrutura

```
backend/
  app/
    main.py            # create_app(): FastAPI, CORS, handlers de erro, routers
    core/
      config.py        # Settings (pydantic-settings): variáveis de ambiente tipadas
      security.py      # bcrypt e JWT
      hashid.py        # IDs opacos na URL
    db/
      base.py          # DeclarativeBase + timestamps
      session.py       # engine async, sessões e a dependência get_db
    domain/calculo.py  # REGRAS DE NEGÓCIO em Python puro (sem FastAPI, sem banco)
    models/            # tabelas (SQLAlchemy 2.0, estilo Mapped[])
    schemas/           # Pydantic: entrada validada, saída documentada no OpenAPI
    services/          # casos de uso assíncronos (recebem a AsyncSession)
    api/
      deps.py          # dependências: sessão do banco, usuário logado
      routes/          # auth.py (login) e rsc.py (calculadora)
    errors.py          # exceções → JSON padronizado (401, 403, 404, 422)
    seed.py            # python -m app.seed
    data/catalogo_rsc.json
  alembic/             # migrations (template async)
  tests/               # pytest + httpx.AsyncClient
  gunicorn.conf.py
frontend/              # Vue 3 + Quasar (idêntico nas três implementações)
deploy/                # Apache, systemd, script de atualização
docs/DEPLOY.md
```

O fluxo de uma requisição:

```
HTTP → router (api/routes) → Depends: sessão + usuário → Pydantic valida o corpo
     → service (async) → domain/calculo.py
          └→ SQLAlchemy async → SQLite
```

## API

Prefixo `/api/v1`. Todas as rotas, exceto o login, exigem `Authorization: Bearer <token>`.
Documentação interativa gerada automaticamente em **`/api/docs`**.

| Método | Rota | Descrição |
|---|---|---|
| POST | `/login` | autentica com e-mail e senha e devolve o JWT |
| GET | `/rsc/catalogo` | catálogo de itens agrupado por requisito (I a VI) |
| GET | `/rsc` | meus cálculos, com total de pontos e melhor nível |
| POST | `/rsc` | cria um cálculo |
| GET | `/rsc/{id}` | dados, atividades e resultado do cálculo |
| POST | `/rsc/{id}/escolaridade` | altera escolaridade e nome; devolve o resultado |
| POST | `/rsc/{id}/nivel-selecionado` | define o nível pleiteado (validado pela escolaridade) |
| POST | `/rsc/atividade` | adiciona atividade (bloqueia item repetido) |
| PUT | `/rsc/atividade/{id}` | altera atividade |
| DELETE | `/rsc/atividade/{id}` | remove atividade |

Erros: `401` sem token; `403` cálculo de outro usuário; `404` não encontrado; `422` com
`{"errors": {"campo": ["mensagem"]}}` (validação) ou `{"errors": ["mensagem"]}` (regra).
Os IDs na URL são *hashids* (`/rsc/MMhbs5`), não números sequenciais.

## Regras do cálculo

| Nível | Escolaridade exigida | Pontos | Atividades | Exige pontuar em |
|---|---|---|---|---|
| RSC-I | Fund. incompleto | 10 | 1 | — |
| RSC-II | Fund. completo | 15 | 2 | — |
| RSC-III | Médio/Técnico | 25 | 2 | — |
| RSC-IV | Graduação | 30 | 3 | II, IV, V ou VI |
| RSC-V | Especialização | 52 | 5 | IV, V ou VI |
| RSC-VI | Mestrado | 75 | 7 | VI |

Cada atividade soma os pontos do item × quantidade e conta como um critério no seu requisito.
O nível pleiteado é sempre o correspondente à escolaridade; doutores não têm nível RSC.

## Como o FastAPI resolve cada parte

| Tema | No FastAPI (este projeto) |
|---|---|
| Inicialização | `create_app()` em `main.py`: monta `FastAPI`, middlewares, handlers e routers |
| Rotas | `APIRouter` com `@router.get`, `@router.post`...; parâmetros tipados dizem de onde vem cada dado |
| Validação | Pydantic v2: o corpo é convertido no modelo declarado; erro vira 422 automaticamente |
| Resposta | `response_model` filtra a saída e documenta o formato no OpenAPI |
| ORM | SQLAlchemy 2.0 **assíncrono** (`AsyncSession`, `await db.scalars(...)`) |
| Migrations | Alembic com template async (`alembic revision --autogenerate`, `alembic upgrade head`) |
| Autenticação | `HTTPBearer` + PyJWT dentro da dependência `get_current_user` |
| Injeção de dependências | `Depends()` nativo; `Annotated[...]` cria atalhos como `DB` e `UsuarioAtual` |
| Configuração | `pydantic-settings`: variáveis de ambiente validadas e tipadas |
| Erros | `@app.exception_handler(...)` converte exceções em JSON |
| Testes | `httpx.AsyncClient` + `ASGITransport`, `app.dependency_overrides` troca o banco |
| Documentação | Swagger UI e OpenAPI gerados a partir dos tipos (`/api/docs`) |
| Servidor de produção | Gunicorn + `UvicornWorker` (ASGI) |

## Equivalências entre as três implementações

| Conceito | Flask | FastAPI | Django |
|---|---|---|---|
| Agrupar rotas | `Blueprint` | `APIRouter` | app + `urls.py` |
| Definir rota | `@bp.get("/x")` | `@router.get("/x")` | `path("x", View.as_view())` |
| Validar entrada | marshmallow `Schema` | Pydantic `BaseModel` | DRF `Serializer` |
| ORM | SQLAlchemy | SQLAlchemy (async) | Django ORM |
| Migrations | Alembic (Flask-Migrate) | Alembic | `makemigrations` / `migrate` |
| Usuário logado | `current_user` (jwt-extended) | `Depends(get_current_user)` | `request.user` |
| Dependências | contexto global (`current_app`, `g`) | `Depends()` | middleware + `request` |
| Tratar erros | `@app.errorhandler` | `@app.exception_handler` | `EXCEPTION_HANDLER` do DRF |
| Comando de CLI | `@app.cli.command` | script Python | `management/commands` |
| Admin pronto | — | — | Django Admin |
| Documentação da API | — | OpenAPI automático em `/docs` | — (opcional: drf-spectacular) |
| Servidor | Gunicorn (WSGI) | Gunicorn + Uvicorn (ASGI) | Gunicorn (WSGI) |
| Regra de negócio | `app/domain/calculo.py` | `app/domain/calculo.py` | `rsc/domain/calculo.py` |

## Decisões técnicas

- **Regra de negócio isolada.** `domain/calculo.py` não importa framework nem banco: recebe
  dados simples e devolve um resultado. O arquivo é idêntico nas três implementações e é
  testado sem subir aplicação.
- **Async de ponta a ponta.** Rotas `async def`, sessão `AsyncSession` e driver `aiosqlite`.
  Enquanto uma requisição espera o banco, o mesmo processo atende outras. Atenção: uma
  chamada bloqueante (ex.: `time.sleep`, driver síncrono) dentro de `async def` trava o
  processo inteiro.
- **Carregamento explícito de relacionamentos.** No modo async não existe *lazy loading*:
  as atividades usam `lazy="selectin"` e a ida da atividade ao requerimento usa
  `lazy="raise"` + `selectinload(...)` explícito, para o erro aparecer cedo.
- **`expire_on_commit=False`.** Os objetos continuam legíveis depois do `commit` sem nova
  consulta ao banco.
- **Mensagens de validação em português.** O handler de `RequestValidationError` troca o
  formato padrão (`{"detail": [...]}`, em inglês) pelo formato `{"errors": {...}}` da API.
- **`Decimal` nos pontos**, **N+1 evitado**, **JWT sem estado**, **hashids com conferência
  de entidade**, **mensagem de login única**, **bcrypt compatível com hashes `$2y$` do PHP**,
  **SQLite com WAL e chaves estrangeiras** e **datas em UTC** — iguais às outras versões.

## Licença

Código sob **GNU GPL v2.0 ou posterior** ([LICENSE](LICENSE)), a mesma do ProRSC-TAE, do qual
este projeto deriva.
