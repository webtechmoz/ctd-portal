# CTD Portal — Plano de Implementacao

> **Nota (2026-07):** este ficheiro e o **blueprint historico** do rebuild (fases 0–5).  
> Para o estado actual do codigo, usar:
> - [README.md](./README.md)
> - [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)
> - [docs/API.md](./docs/API.md)
> - [docs/FRONTEND.md](./docs/FRONTEND.md)
> - [docs/AVALIACAO.md](./docs/AVALIACAO.md)
> - [docs/DEPLOY.md](./docs/DEPLOY.md)
>
> Varias fases do plano ja estao feitas (RBAC, catalogo, avaliacao redesenhada, anexos).  
> O stub `POST /uploads/avatar` e o email Resend continuam por implementar. Actualizar este PLAN apenas se for reabrir o roadmap de fases.

Documento base para o rebuild do portal da Comissao de Transformacao Digital (GAPI).
Tudo o que se implementar deve seguir este plano; desvios devem actualizar este ficheiro primeiro.

---

## 1. Avaliacao do projecto legado (`projects-ctd`)

### O que e
Portal de avaliacao periodica dos pilares de digitalizacao GAPI (meuCredito, DHIS2, Starlink, Microsoft 365/SharePoint, PHC).

Fluxos principais:
1. Login
2. Submeter avaliacao (formulario em 8 secoes)
3. Ver dashboard do ultimo resultado por pilar
4. Painel admin (pilares, utilizadores, avaliacoes, relatorios) — parcialmente mock no legado

### Problemas a eliminar
| Problema | Decisao |
|----------|---------|
| Pyweber controla eventos do DOM (onclick, scrape de `#ids`) | Backend so expoe API JSON; frontend vanilla trata UI |
| Schema duplo (v1 denormalizado + v2 normalizado) + 2 DBs | Um schema unico: modelo v2 (Pilar master + Avaliacao delta) |
| Credenciais hardcoded / JWT com password no payload | `.env` + claims minimos (`sub`, `role`, `jti`, `exp`) |
| Sem RBAC real | `admin` / `member` / `visitor` com guards nas rotas |
| Admin HTML estatico + localStorage (`script.js`) | Admin consome a mesma API |
| `create_all_tables()` em cada request | Alembic migrations |
| Sem emails / uploads | Resend + Cloudflare R2 |
| Sem API OpenAPI util | Rotas tipadas pyweber → `/docs` |

### O que reutilizar (conceito / logica, nao codigo acoplado)
- Dominio e linguagem: Pilar, Avaliacao, Actividades, Orcamento, Riscos, Proximos passos, KPIs
- Modelo normalizado v2 (`admin_data.py` / `admin_repo.py`) como base do schema
- Estrutura das 8 secoes do formulario de avaliacao
- Formula de resumo do dashboard (`build_dash_resumo`: progresso, % orcamento, estados de actividades, riscos altos)
- Auth: bcrypt + JWT + blacklist + dominio `@gapi.co.mz`
- Branding GAPI / CTD (cores e layout adaptados, sem emoji — so Bootstrap Icons)

---

## 2. Stack alvo

| Camada | Tecnologia |
|--------|------------|
| Runtime API | `pyweber==1.3.1` (rotas JSON + servir frontend estatico) |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic — **automatico no boot** (`bootstrap_database`) |
| Validacao | Pydantic v2 |
| Auth | JWT em cookie `access_token` + bcrypt + token blacklist |
| DB local | MySQL 8 (campos separados; cria DB se nao existir) |
| DB producao | PostgreSQL (Railway `DATABASE_URL`, normalizado para `+psycopg`) |
| Hosting | Railway + **Railpack** (Nixpacks deprecado) |
| Email | Resend |
| Ficheiros | Cloudflare R2 (S3-compatible) |
| Frontend | HTML + JS vanilla |
| CSS | Tailwind CSS |
| Icons / modais | Bootstrap Icons + Bootstrap 5 (JS modal se necessario) |
| Datas | Flatpickr |

**Regra de UX:** nenhum emoji no projecto. Icones via `bi bi-*` (Bootstrap Icons).

---

## 3. Arquitectura

```
Browser (vanilla JS)
    |  fetch JSON + pages estaticas
Pyweber (main.py)
    |-- /api/*     → controllers → services → repositories → SQLAlchemy
    |-- /*         → frontend HTML/JS/CSS (static)
    |-- /docs      → OpenAPI (dev / admin)
Alembic → MySQL (local) | PostgreSQL (Railway)
Resend (emails) | R2 (avatars / anexos)
```

Principios:
1. **Pyweber nao manipula eventos de UI.** Sem `TemplateEvents`, sem `e.template.querySelector` para negocio.
2. **Servicos contem regra de negocio.** Controllers so validam/auth e serializam.
3. **Um schema.** Pilar = dados mestre; Avaliacao = snapshot periodico de execucao.
4. **Frontend desacoplado.** `frontend/js/api.js` e o unico cliente HTTP.

---

## 4. Estrutura do repositorio

```
ctd-portal/
├── PLAN.md                 # este plano (fonte de verdade)
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── alembic.ini
├── main.py                 # entry: app, static, registo de rotas API + pages
├── config/
│   └── settings.py         # env, DB URL, JWT, Resend, R2, CORS
├── app/
│   ├── api/                # rotas pyweber (JSON)
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── pilares.py
│   │   ├── avaliacoes.py
│   │   ├── dashboard.py
│   │   ├── reports.py
│   │   └── uploads.py
│   ├── schemas/            # Pydantic request/response
│   ├── models/             # SQLAlchemy ORM
│   ├── repositories/       # acesso a dados
│   ├── services/           # auth, email, storage, avaliacao, dashboard
│   ├── middleware/         # auth guard, CORS, erros
│   └── db/
│       ├── base.py
│       └── session.py
├── alembic/
│   ├── env.py
│   └── versions/
├── frontend/               # HTML shells apenas
│   ├── index.html
│   ├── login.html
│   ├── avaliacao.html
│   ├── dashboard.html
│   └── admin/
├── css/                    # → URL /css/...
├── js/                     # → URL /js/...
├── assets/                 # → URL /assets/...
├── scripts/
│   └── seed.py
└── tests/
```

---

## 5. Modelo de dados (canonical)

### Enums
- `UserRole`: `admin` | `member` | `visitor`
- `UserStatus`: `active` | `inactive`
- `PilarStatus`: `activo` | `inactivo`
- `Prioridade`: `alta` | `media` | `baixa`
- `Probabilidade` / `Impacto`: `alta|media|baixa` / `alto|medio|baixo`
- `ActividadeEstado`: `pendente` | `em_progresso` | `concluida`

### Tabelas

**users**
`id`, `name`, `email` (unique), `password_hash`, `role`, `status`, `profile_image_key`, `created_at`, `updated_at`

**token_blacklist**
`jti` (PK), `expires_at`

**pilares**
`id`, `nome`, `descricao`, `area`, `fase`, `obj_geral`, `kpis`, `beneficios`, `plano_obs`, `parceiros`, `orc_aprovado`, `orc_moeda`, `orc_fonte`, `data_inicio`, `data_fim_prevista`, `periodicidade_dias`, `dias_aberto`, `proxima_avaliacao`, `prazo_limite`, `status`, timestamps

**pilar_responsaveis** — `pilar_id`, `user_id` (unique pair)

**pilar_objectivos** — `pilar_id`, `descricao`, `ordem`

**pilar_actividades** — planeamento base: nome, responsavel, prioridade, datas previstas, descricao, obs, ordem

**pilar_orcamento_categorias** — categoria, valor_alocado, obs, ordem

**pilar_riscos** — descricao, probabilidade, impacto, mitigacao, ordem

**pilar_proximos_passos** — descricao, responsavel, prazo, ordem

**avaliacoes**
`id`, `pilar_id`, `user_id`, `estado_geral`, `desafios`, `licoes`, `orc_obs`, `recomendacoes`, `comentarios`, `progresso`, `assinatura`, `data_sub`, timestamps

**avaliacao_actividades** — FK `avaliacao_id` + `pilar_actividade_id`; estado, pct, datas reais, obs

**avaliacao_orcamentos** — FK `avaliacao_id` + `categoria_id`; valor_executado, forma_execucao, obs

**avaliacao_riscos** — FK `avaliacao_id` + `risco_id`; observacao (e opcionalmente probabilidade/impacto actualizados no periodo)

**avaliacao_proximos_passos** — FK `avaliacao_id` + `passo_id`; alcancado, observacao

Indices: FKs, `users.email`, `avaliacoes(pilar_id, data_sub DESC)`, `token_blacklist.expires_at`.

---

## 6. API REST (contrato)

Prefixo: `/api/v1`

### Auth
| Metodo | Rota | Auth | Descricao |
|--------|------|------|-----------|
| POST | `/auth/login` | public | email + password → cookie JWT + body user |
| POST | `/auth/logout` | auth | blacklist jti, clear cookie |
| GET | `/auth/me` | auth | utilizador actual |

### Users (admin)
| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/users` | listar (filtros role/status) |
| POST | `/users` | criar (+ email boas-vindas opcional via Resend) |
| GET | `/users/{id}` | detalhe |
| PATCH | `/users/{id}` | actualizar |
| PATCH | `/users/{id}/password` | reset / change |
| DELETE | `/users/{id}` | soft → `inactive` |

### Pilares
| Metodo | Rota | Roles |
|--------|------|-------|
| GET | `/pilares` | auth |
| POST | `/pilares` | admin |
| GET | `/pilares/{id}` | auth (inclui nested master) |
| PATCH | `/pilares/{id}` | admin |
| DELETE | `/pilares/{id}` | admin (inactivar) |
| CRUD nested | `/pilares/{id}/objectivos\|actividades\|orcamento\|riscos\|proximos-passos` | admin |
| PUT | `/pilares/{id}/responsaveis` | admin |

### Avaliacoes
| Metodo | Rota | Roles |
|--------|------|-------|
| GET | `/pilares/{id}/avaliacoes` | auth |
| GET | `/avaliacoes/{id}` | auth |
| POST | `/avaliacoes` | admin, member |
| PATCH | `/avaliacoes/{id}` | admin / autor |

Payload de create inclui filhos (actividades/orcamento/riscos/passos) num unico transaction.

### Dashboard / Reports
| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/pilares/{id}/dashboard` | ultimo snapshot + KPIs calculados |
| GET | `/reports/overview` | admin: contagens, proximas avaliacoes |
| GET | `/reports/export/{pilar_id}` | export (fase posterior) |

### Uploads
| Metodo | Rota | Descricao |
|--------|------|-----------|
| POST | `/uploads/avatar` | multipart → R2 → actualiza `profile_image_key` |
| GET | `/uploads/signed-url` | URL assinada de leitura (se privado) |

Respostas de erro padronizadas:
```json
{ "error": { "code": "VALIDATION_ERROR", "message": "...", "details": [] } }
```

---

## 7. Frontend (paginas e responsabilidades)

**Shell:** sidebar + topbar (`js/shell.js`) em todas as paginas autenticadas.

| Pagina | Ficheiro | Responsabilidade |
|--------|----------|------------------|
| Login | `frontend/login.html` | form → `POST /auth/login` |
| Home / Dashboard | `frontend/index.html` | Visao geral, KPIs, atalhos |
| Base de projectos | `frontend/projectos.html` | Dados mestre do pilar (leitura; CRUD admin Fase 4) |
| Avaliacoes | `frontend/avaliacoes.html` | Lista + entrada para nova avaliacao |
| Nova avaliacao | `frontend/avaliacao.html` | So acompanhamento: execucao, orcamento executado, passos, obs riscos, fecho |
| Ponto de situacao | `frontend/situacao.html` | Prazos / proximas avaliacoes |
| Resultados | `frontend/dashboard.html` | KPIs da ultima avaliacao por pilar |
| Admin | `frontend/admin/index.html` | Cadastro mestre + users (Fase 4) |
| Logout | `POST /auth/logout` + clear cookie + `location.replace(/login)` |

**Separacao de dados:**
- **Projecto (admin):** contexto, objectivos, actividades planeadas, rubricas, riscos, proximos passos base
- **Avaliacao (member/admin):** deltas de execucao no periodo — nao re-cadastra o master

Modulos JS:
- `api.js` — fetch base, credentials, tratamento de 401
- `auth.js` — sessao, redirect, logout
- `shell.js` — sidebar / layout
- `ui.js` — toast, loader com `bi` icons
- `pages/*` — logica por pagina
- Flatpickr em campos de data

---

## 8. Servicos externos

### Config (`.env`)
```
APP_ENV=local|production
SECRET_KEY=
JWT_TTL_HOURS=8
AUTO_MIGRATE=true

# Local MySQL (campos separados — a app faz CREATE DATABASE IF NOT EXISTS)
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=...
MYSQL_DATABASE=ctd_portal

# Producao Railway (referencia no painel):
# DATABASE_URL=${{Postgres.DATABASE_URL}}
# Valor tipico: postgresql://user:pass@host:5432/railway
# A app normaliza para: postgresql+psycopg://...

CORS_ORIGINS=http://localhost:8800
ALLOWED_EMAIL_DOMAIN=gapi.co.mz

RESEND_API_KEY=
RESEND_FROM=CTD GAPI <noreply@...>

R2_ENDPOINT_URL=https://<accountid>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=ctd-portal
```

Leituras publicas: sem custom domain usamos **URLs assinadas (presigned)** via boto3 — nao e preciso `R2_PUBLIC_BASE_URL`.

### Resolucao da URL SQLAlchemy
1. Se `DATABASE_URL` estiver definida → Postgres (Railway); normalizar `postgres://` / `postgresql://` → `postgresql+psycopg://`
2. Caso contrario → montar URL MySQL a partir de `MYSQL_*` e garantir que a database existe

### Resend
- Boas-vindas com credenciais (criar user)
- Lembrete de janela de avaliacao (fase 2)
- Confirmacao de submissao (fase 2)

### R2
- Avatars (`users/{id}/avatar.*`)
- Anexos futuros de avaliacao (fase 2)
- Cliente via `boto3` (S3 API)

### Railway
- Builder: **Railpack** (`railway.toml` → `builder = "RAILPACK"`). Nixpacks esta deprecado.
- `DATABASE_URL=${{Postgres.DATABASE_URL}}` (sem driver SQLAlchemy; formatado na app)
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
  - `main:app` e o wrapper ASGI (lifespan) — **nao** o `if __name__`
  - No `lifespan.startup` corre `bootstrap_database()` (migrations)
  - Pedidos HTTP/WS sao delegados ao `pw_app` (Pyweber)
- Local sem uvicorn: `python main.py` (bootstrap no `__main__` + `pw_app.run`)
- Volume nao necessario (ficheiros no R2)

### Migrations no boot
- `app/db/bootstrap.py` → idempotente (seguro lifespan uvicorn + `__main__`)
- `ensure_mysql_database` (local) → engine → `alembic upgrade head`
- `AUTO_MIGRATE=true` por defeito; deploy **nao** depende de comando manual
- Preferir 1 worker uvicorn no deploy (evita race de migrate em multi-worker)

---

## 9. Auth e permissoes

| Recurso | visitor | member | admin |
|---------|---------|--------|-------|
| Ver dashboard / pilares | sim | sim | sim |
| Submeter avaliacao | nao | sim (so se for `pilar_responsavel`) | sim |
| CRUD pilares / users | nao | nao | sim |
| Relatorios admin | nao | nao | sim |

Regras (confirmadas):
- **Sessao:** JWT apenas em cookie `httpOnly` `access_token` (sem Bearer no frontend actual; Bearer fica reservado a APIs externas futuras)
- Login so se `status=active` e email `*@gapi.co.mz`
- JWT claims: `sub` (user id), `role`, `jti`, `exp` — **nunca** password
- Logout → insert `jti` em `token_blacklist`
- **RBAC no backend em todas as rotas `/api/v1/*`** — 401 sem cookie valido; 403 role / ownership insuficiente (o frontend esconde UI, mas nunca e a unica barreira)
- Member so cria/edita avaliacao de pilares onde consta em `pilar_responsaveis`
- Avaliacao = **deltas do master do pilar** (sem criar actividades/riscos ad-hoc no form; master altera-se no admin)
- Pages HTML: JS redirecciona para `/login` se `/auth/me` falhar

---

## 10. Fases de implementacao

### Fase 0 — Scaffold
- [x] Estrutura de pastas
- [x] `PLAN.md`, `README.md`, `requirements.txt`, `.env.example`, `.gitignore`
- [x] Stubs `main.py`, `config/settings.py`, pacotes `app/*`
- [x] MySQL por campos + normalizacao Postgres Railway + Railpack + auto-migrate no boot

### Fase 1 — Fundacao
1. [x] Models ORM + migration Alembic `0001_initial`
2. [x] Auth API (login/logout/me) cookie + helpers RBAC
3. [x] Seed script admin + pilares
4. [x] `frontend/login.html` + `api.js` / `auth.js` + home com sessao
5. [ ] Correr localmente: preencher `MYSQL_PASSWORD` no `.env`, `python scripts/seed.py`, `python main.py`

### Fase 2 — Pilares + Dashboard read
1. CRUD pilares + nested master
2. `GET /pilares/{id}/dashboard` (pode devolver vazio)
3. Paginas home + dashboard (consumo API)
4. Tailwind + Bootstrap Icons + Flatpickr no layout base

### Fase 3 — Avaliacoes
1. [x] `POST /avaliacoes` transaccional (deltas do master)
2. [x] Guard: member so se `pilar_responsavel` (admin sempre)
3. [x] Pagina `avaliacao.html` (8 secoes, JS puro)
4. [x] Dashboard alimentado com ultimo snapshot
5. [x] Recalculo `proxima_avaliacao` / `prazo_limite` apos submit
6. [x] Seed com master sample (actividades, orcamento, riscos, passos)

### Fase 4 — Admin + Users
1. Users CRUD + email Resend boas-vindas
2. Admin shell (pilares, users, avaliacoes, perfil)
3. Upload avatar → R2
4. RBAC no frontend (esconder accoes) alinhado com backend

### Fase 5 — Producao
1. Validar migrations automaticas contra Postgres Railway
2. Env vars Railway (`DATABASE_URL`, secrets, Resend, R2)
3. Cookies `Secure` / `SameSite` em HTTPS
4. Relatorios basicos + limpeza blacklist
5. Testes de API criticos (auth, submit avaliacao, 403)

---

## 11. Criterios de qualidade

- Nenhuma logica de negocio em handlers de evento Pyweber DOM
- Nenhuma password em JWT ou logs
- Migrations aplicadas no boot (sem `create_all` como fonte de verdade; sem migrate manual no deploy)
- Respostas API tipadas (Pydantic) e documentadas em `/docs`
- Frontend sem emoji; icones `bi`
- Codigo agnostico MySQL/Postgres (tipos via SQLAlchemy; URL resolvida em `settings`)
- Autorizacao sempre no backend (nao confiar so no frontend)
- Erros silenciosos (`except: pass`) proibidos nos servicos

---

## 12. Decisoes confirmadas

1. Auth frontend: **cookie JWT apenas**. Bearer so se no futuro houver clientes API externos; backend valida permissoes em qualquer caso.
2. Member so avalia pilares onde e `pilar_responsavel`.
3. Avaliacao = so deltas do master do pilar (admin gere o master).
4. Export PDF/Excel: adiar (decidir na Fase 5).

---

## 13. Mapa legado → novo

| Legado | Novo |
|-------|------|
| `components/*` + `TemplateEvents` | `frontend/js/pages/*` |
| `services/form_services.py` (DOM scrape) | `POST /api/v1/avaliacoes` JSON |
| `database/avaliacao_repo.py` (v1) | descartar; usar models v2 |
| `database/admin_repo.py` (v2) | reescrever em SQLAlchemy |
| `services/auth_services.py` | `app/services/auth_service.py` (sem password no token) |
| `templates/admin.html` mock | `frontend/admin/` + API |
| `static/script.js` localStorage | eliminar |
| Dual DB / URL unica hardcoded | MySQL `MYSQL_*` local + `DATABASE_URL` Railway |
