# CTD Portal

Portal da **Comissao de Transformacao Digital (GAPI)** — gestao de projectos (pilares), acompanhamento de execucao periodico, anexos e resultados.

## Stack

| Camada | Tecnologia |
|--------|------------|
| API / paginas | [pyweber](https://pypi.org/project/pyweber/) 1.3.1 |
| ASGI (prod) | uvicorn |
| ORM | SQLAlchemy 2 + Alembic |
| BD local | MySQL (`MYSQL_*`) |
| BD producao | PostgreSQL Railway (`DATABASE_URL`) |
| Auth | JWT em cookie `access_token` + RBAC |
| Ficheiros | Cloudflare R2 (prod) / `uploads/` (dev) |
| Frontend | HTML + vanilla JS (ES modules), CSS proprio, Bootstrap Icons, Flatpickr |

## Documentacao

| Documento | Conteudo |
|-----------|----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Estrutura, boot, camadas, seed |
| [docs/API.md](docs/API.md) | Endpoints `/api/v1` |
| [docs/FRONTEND.md](docs/FRONTEND.md) | Paginas, shell, convencoes UI |
| [docs/AVALIACAO.md](docs/AVALIACAO.md) | Formulario e regras de acompanhamento |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Railway, env, checklist de producao |
| [PLAN.md](PLAN.md) | Blueprint historico (fases iniciais) — referencia, nao estado actual |

## Setup local

1. Copiar ambiente:

```bash
copy .env.example .env
```

Preencher pelo menos `MYSQL_PASSWORD` e `SECRET_KEY`.  
Para dados demo de projectos: `SEED_SAMPLE_DATA=true` (default no `.env.example`).

2. Instalar e arrancar:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Migrations e seed (RBAC + catalogo + admin se BD vazia) correm no boot.

Alternativa igual a producao:

```bash
uvicorn main:app --host 0.0.0.0 --port 8800 --reload
```

3. Abrir `http://localhost:8800/login`  
   Credenciais: valores de `SEED_ADMIN_*` no `.env`.

Seed so de projectos demo (local):

```bash
python scripts/seed.py --sample
```

**Avaliacoes nunca sao seed.** Em producao, projectos demo tambem nao.

## Estrutura rapida

```
ctd-portal/
├── main.py              # rotas HTML + ASGI lifespan
├── config/settings.py   # env
├── app/                 # API, models, services, RBAC
├── alembic/versions/    # schema (auto no boot)
├── frontend/            # HTML
├── js/                  # ES modules (pages + components)
├── css/  assets/
├── uploads/             # anexos locais (dev)
├── docs/                # documentacao
└── scripts/seed.py
```

## Convencoes

- API JSON em `/api/v1/*`; UI nao e autoritativa para autorizacao.
- Schema so via Alembic (`AUTO_MIGRATE=true` no boot).
- Sem emoji no UI — usar Bootstrap Icons (`bi bi-*`).
- Estaticos: `pw_app.static("css", "js", "assets")` → `/css`, `/js`, `/assets`.

## Producao (resumo)

Ver [docs/DEPLOY.md](docs/DEPLOY.md). Obrigatorio: `APP_ENV=production`, `DATABASE_URL`, `SECRET_KEY` forte, R2 completo, `SEED_SAMPLE_DATA=false`.
