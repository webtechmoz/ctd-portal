# Arquitectura

## Visao geral

Aplicacao **monolito** com:

1. **Paginas HTML** servidas pelo pyweber (`frontend/`).
2. **API JSON** em `/api/v1/*` (modulos em `app/api/`).
3. **SPA leve** no browser: cada pagina carrega `js/pages/*.js`, monta o shell (`js/shell.js`) e fala com a API via `js/api.js`.

Em producao o entrypoint e `main:app` (ASGI): lifespan corre `bootstrap_database()` e depois delega ao pyweber.

```
Browser  →  HTML/JS/CSS
               │
               ▼
         /api/v1/*  (JSON + cookie JWT)
               │
         services → repositories → SQLAlchemy → MySQL / Postgres
               │
         storage → R2 ou disco local (anexos)
```

## Arranque (boot)

Ordem em `app/db/bootstrap.py`:

1. Criar BD MySQL se local (`ensure_mysql_database`).
2. Criar engine SQLAlchemy.
3. Alembic `upgrade head` se `AUTO_MIGRATE=true`.
4. `settings.validate_for_boot()` — em producao exige `SECRET_KEY` forte, `DATABASE_URL` e R2.
5. `run_seed()` — ver seccao Seed.

Idempotente (lock) para multiplos workers / reloads.

## Camadas (`app/`)

| Pasta | Responsabilidade |
|-------|------------------|
| `api/` | Rotas HTTP, serializacao de resposta, auth na entrada |
| `schemas/` | Pydantic (entrada/saida) |
| `services/` | Regras de negocio (avaliacao, anexos, auth, seed, storage…) |
| `repositories/` | Queries SQLAlchemy |
| `models/` | ORM |
| `middleware/` | `require_auth`, erros de auth |
| `rbac_catalog.py` | Catalogo de permissoes e defaults por perfil |

Nao colocar logica de negocio nos handlers de API para alem de validacao/HTTP.

## Dominio

### Projecto (Pilar)

Dados mestre: identificacao, objectivos, actividades, rubricas orcamentais, riscos, proximos passos base, responsaveis.

Geridos em **Administracao → Projectos** (`/admin/projectos/...`).

### Avaliacao

Snapshot periodico de execucao sobre um pilar:

- % e estado das actividades (derivados)
- orcamento executado cumulativo
- proximos passos (cumulativos / concluidos)
- observacoes de riscos
- anexos do periodo

### Anexo

Ficheiro com `source_type` + `source_id` (hoje: `avaliacao`) e `source_label` para pesquisa/listagem global.

## Auth e RBAC

- Login: `POST /api/v1/auth/login` → cookie HttpOnly `access_token`.
- Em producao o cookie leva flag `Secure`.
- Dominio de email filtrado por `ALLOWED_EMAIL_DOMAIN` (virgula; vazio/`*`/`off` = sem restricao).
- Perfis sistema: `admin` (`*`), `member`, `visitor`.
- Permissoes em `app/rbac_catalog.py` — seed idempotente em cada boot.

## Seed

| O que | Quando |
|-------|--------|
| RBAC + catalogo (moedas, fases, areas, fontes) | Sempre |
| Utilizador admin (`SEED_ADMIN_*`) | So se `users` = 0 (ou CLI `--force-admin`) |
| Projectos demo + master | So com `SEED_SAMPLE_DATA=true` e **nunca** em `APP_ENV=production` |
| Avaliacoes | **Nunca** |

CLI: `python scripts/seed.py` · com demos: `python scripts/seed.py --sample`.

## Migrations

Pasta: `alembic/versions/`.

| Revisao | Conteudo |
|---------|----------|
| `0001_initial` | users, pilares, avaliacoes |
| `0002_indexes` | indices compostos |
| `0003_rbac` | permissions, roles, role_id |
| `0004_catalog` | catalog_options |
| `0005_anexos` | anexos |

Novas alteracoes de schema: criar migration Alembic; nao usar `create_all` em producao.

## Ficheiros / anexos

`app/services/storage.py`:

- Se R2 completo → boto3 S3-compatible.
- Senao → `UPLOAD_DIR` (default `uploads/`) — adequado so a desenvolvimento.
- Limite 12 MB; extensoes allowlist (PDF, Office, imagens, zip, csv, txt).

Fluxo tipico: submeter avaliacao → `POST /avaliacoes/{id}/anexos` (multipart) → metadados em `anexos` → download autenticado em `GET /anexos/{id}/download`.

## Compatibilidade

- `app/pyweber_compat.py` — shims para Python 3.14 + anotacoes string no OpenAPI do pyweber.
- `SSL_RELAX_X509_STRICT` — workaround local Windows/Python 3.13+ para HTTPS; **false** em producao.
