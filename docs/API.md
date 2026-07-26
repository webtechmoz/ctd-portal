# API (`/api/v1`)

Todas as rotas (excepto login/health) exigem sessao autenticada via cookie `access_token`, salvo indicacao em contrario.

Respostas de erro tipicas:

```json
{ "error": { "code": "CODE", "message": "...", "details": [] } }
```

Cliente JS: `js/api.js` (`api`, `apiForm` para multipart).

---

## Health

| Metodo | Path | Auth | Notas |
|--------|------|------|-------|
| GET | `/api/v1/health` | Nao | `{ status, app, env }` |

---

## Auth

| Metodo | Path | Notas |
|--------|------|-------|
| POST | `/auth/login` | body: email, password → cookie |
| POST | `/auth/logout` | limpa cookie / blacklist jti |
| GET | `/auth/me` | utilizador + permissoes |
| PATCH | `/auth/password` | alterar palavra-passe (`account.change_password`) |

---

## Utilizadores e perfis

| Metodo | Path | Permissao tipica |
|--------|------|------------------|
| GET/POST | `/users` | users.view / users.manage |
| PATCH | `/users/{user_id}` | users.manage |
| GET | `/permissions` | roles.manage |
| GET/POST | `/roles` | roles.manage |
| PATCH | `/roles/{role_id}` | roles.manage |

---

## Catalogo (listas de sistema)

Usado em formularios (moeda, fase, area, fonte).

| Metodo | Path |
|--------|------|
| GET/POST | `/catalog` |
| GET | `/catalog/{category}` |
| PATCH/DELETE | `/catalog/item/{opt_id}` |

---

## Pilares (projectos)

| Metodo | Path | Notas |
|--------|------|-------|
| GET | `/pilares` | listagem activa (consulta) |
| POST | `/pilares` | criar (projectos.manage) |
| GET | `/admin/pilares` | listagem admin |
| GET | `/pilares/{pilar_id}` | detalhe + master |
| PATCH | `/pilares/{pilar_id}` | actualizar |
| DELETE | `/pilares/{pilar_id}` | apagar (regras no service) |

Payload de create/update inclui nested: objectivos, actividades, orcamento_categorias, riscos, proximos_passos.

---

## Avaliacoes

| Metodo | Path | Notas |
|--------|------|-------|
| GET | `/avaliacoes` | arquivo (lista) |
| POST | `/avaliacoes` | submeter periodo |
| GET | `/avaliacoes/{id}` | detalhe (actividades, orcamento, riscos, passos, anexos) |
| GET | `/avaliacoes/latest/{pilar_id}` | baseline da avaliacao anterior |
| POST | `/avaliacoes/{id}/anexos` | multipart `files` (varios) |

### Regras no create (servidor)

- `%` de actividade nao pode ser inferior a da avaliacao anterior.
- Valor orcamental executado e **cumulativo** e nao pode descer relativamente ao anterior.
- Estado da actividade derivado da %: `0` pendente, `<100` em_progresso, `100` concluida.
- Progresso global = media das %.
- Proximos passos novos sem `passo_id` criam registo master no pilar.

---

## Anexos

| Metodo | Path | Notas |
|--------|------|-------|
| GET | `/anexos` | query: `q`, `page`, `page_size`, `source_type` |
| GET | `/anexos/{id}` | metadados |
| GET | `/anexos/{id}/download` | stream do ficheiro |

Cada item inclui `source_label`, `source_url` (ex. `/avaliacoes?ver=…`), autor e tamanho.

---

## Dashboard / relatorios

| Metodo | Path | Notas |
|--------|------|-------|
| GET | `/pilares/{pilar_id}/dashboard` | |
| GET | `/reports/overview` | portefolio |
| GET | `/reports/avaliacoes` | query: `pilar_id`, `status`, `from`, `to` |
| GET | `/reports/avaliacoes/export.xlsx` | mesmos filtros |

## Projectos Excel

| Metodo | Path | Notas |
|--------|------|-------|
| GET | `/pilares/export.xlsx` | query opcional `ids=1,2` |
| GET | `/pilares/import-template.xlsx` | modelo vazio |
| POST | `/pilares/import` | multipart `file`; `?dry_run=1` |

---

## Uploads (legado / stub)

| Metodo | Path | Estado |
|--------|------|--------|
| POST | `/uploads/avatar` | `NOT_IMPLEMENTED` |

Usar endpoints de anexos para ficheiros de avaliacao.

---

## Modulos de registo

`app/api/__init__.py` → `register_api_routes(app)` importa:

`auth`, `users`, `roles`, `catalog`, `pilares`, `avaliacoes`, `anexos`, `notifications`, `dashboard`, `reports`, `uploads`.
