# Deploy (Railway)

## Runtime

- Builder: **Railpack** (`railway.toml`)
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Lifespan ASGI em `main.py` → `bootstrap_database()` (migrate + seed seguro)

Nao usar `python main.py` em producao (isso e o servidor de desenvolvimento do pyweber).

## Variaveis obrigatorias

| Variavel | Valor / notas |
|----------|----------------|
| `APP_ENV` | `production` |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
| `SECRET_KEY` | string longa aleatoria (≥ 24 chars; nao usar exemplos) |
| `SEED_ADMIN_EMAIL` | email `@gapi.co.mz` (ou dominio configurado) |
| `SEED_ADMIN_PASSWORD` | **forte** — passwords de exemplo sao rejeitadas no 1.º seed |
| `SEED_SAMPLE_DATA` | `false` |
| `R2_ENDPOINT_URL` | `https://<accountid>.r2.cloudflarestorage.com` |
| `R2_ACCESS_KEY_ID` | |
| `R2_SECRET_ACCESS_KEY` | |
| `R2_BUCKET` | ex. `ctd-portal` |

Opcionais uteis: `JWT_TTL_HOURS`, `ALLOWED_EMAIL_DOMAIN`, `SEED_ADMIN_NAME`, `RESEND_*` (ainda nao usados no fluxo principal).

## O que o boot faz em producao

1. Migrations Alembic ate `head`.
2. Validacao fail-fast (secret, DB, R2).
3. Seed: RBAC + catalogo + admin **so se BD vazia**.
4. **Nao** cria projectos nem avaliacoes demo.

## Checklist antes do go-live

- [ ] Postgres ligado e `DATABASE_URL` injectada
- [ ] `APP_ENV=production`
- [ ] `SECRET_KEY` unica e forte
- [ ] R2 criado e 4 variaveis preenchidas (testar upload de anexo)
- [ ] `SEED_SAMPLE_DATA=false`
- [ ] Password admin forte (ou criar admin depois do 1.º boot vazio)
- [ ] Dominio / HTTPS no Railway (cookie `Secure`)
- [ ] Preferir **1 worker** uvicorn no arranque (evita corrida em migrate); ou aceitar risco baixo com lock de bootstrap
- [ ] Health: `GET /api/v1/health`

## Anexos

Disco do contentor Railway e **efemero**. Sem R2, o arranque em producao **falha de proposito**. Em local, sem R2, os ficheiros vao para `UPLOAD_DIR`.

## Rollback / schema

- Novas tabelas/colunas: sempre migration em `alembic/versions/`.
- Nao apagar migrations ja aplicadas em producao.

## Apos o deploy

1. Abrir `/login` com o admin seed (se BD estava vazia).
2. Criar projectos reais em `/admin/projectos/novo`.
3. Submeter uma avaliacao de teste com anexo e confirmar em `/anexos`.
