# Acompanhamento de execucao (avaliacao)

Documento de **estado actual** do formulario e regras.  
O ficheiro antigo `FORM_AVALIACAO.md` ficou como historico de discussao UX; este e a referencia operacional.

## Objectivo

Registar o progresso de um **periodo** sobre dados mestre do projecto (pilar).

| Camada | Quem | Conteudo |
|--------|------|----------|
| Master | Admin (`projectos.manage`) | Objectivos, actividades, rubricas, riscos, passos base |
| Avaliacao | Member/Admin | % execucao, orcamento cumulativo, passos, obs. riscos, anexos |

## UI (`/avaliacao`)

Ficheiros: `frontend/avaliacao.html`, `js/pages/avaliacao.js`.

### Modos

| Modo | URL | Submit |
|------|-----|--------|
| Nova avaliacao | `/avaliacao?pilar={id}` | `POST /avaliacoes` |
| Editar avaliacao | `/avaliacao?pilar={id}&edit={avaliacao_id}` | `PATCH /avaliacoes/{id}` |

Entrada de edicao: botao **Editar** no arquivo (`/avaliacoes`), disponivel enquanto a avaliacao nao estiver validada (ou apos reabertura).

Na edicao, o formulario **pre-carrega** a partir de `GET /avaliacoes/{id}`:

- % e datas reais das actividades
- valores orcamentais executados
- observacoes de risco do periodo
- proximos passos (descricao, responsavel, prazo, estado concluido)

A baseline de minimos (`%` / orcamento) vem de `GET /avaliacoes/latest/{pilar_id}`, **excluindo** a propria avaliacao em edicao quando esta e a mais recente.

### Seccoes

1. **Cabecalho** — selector de projecto + resumo (objectivos, orcamento, riscos master, KPIs).
2. **Execucao de actividades** — `%` e datas reais editaveis (flatpickr); estado derivado da `%`; progresso global = media.
3. **Execucao orcamental** — valor executado cumulativo por rubrica; cards planeado / executado / %.
4. **Proximos passos** — ver regras abaixo.
5. **Riscos do periodo** — lista (nao tabela); textarea de observacao a largura total (preenchida na edicao).
6. **Anexos** — ficheiros seleccionados no cliente; upload apos create/update (`POST /avaliacoes/{id}/anexos`).

Removido do formulario (campos ainda existem na BD por legado, mas nao sao preenchidos pela UI):

- estado_geral / desafios / licoes / recomendacoes / comentarios / assinatura / fecho manual.

## Proximos passos

### Nova avaliacao

- Mostra passos master em aberto (nao concluidos na avaliacao anterior).
- **+ Adicionar** cria linhas novas (sem `passo_id`) com botao de apagar.
- No submit, passos novos sem `passo_id` criam registo master no pilar e ficam marcados como `criado_nesta_avaliacao`.

### Edicao

- Carrega os passos ligados a essa avaliacao (incluindo concluidos).
- Botao **apagar** (lixo) aparece **apenas** em passos criados naquela avaliacao (`removivel` / `criado_nesta_avaliacao`).
- Passos base do projecto / seed **nao** mostram apagar.
- Ao actualizar sem um passo removivel, o link e removido e o registo master e apagado se nao estiver ligado a outras avaliacoes.
- Prazo ≥ hoje e exigido em avaliacoes **novas**; na edicao permite-se prazos ja passados (dados historicos).

## Regras de calculo

| Campo | Regra |
|-------|--------|
| Estado actividade | `0` → pendente; `1–99` → em_progresso; `100` → concluida |
| Datas inicio/fim | Sugeridas pela `%` quando vazias; o utilizador pode ajustar |
| Minimo de % | Baseline da avaliacao anterior; validado no **submit** (cliente + servidor), nao ao digitar |
| Orcamento | Cumulativo; minimo = valor da avaliacao anterior; validado no submit |
| Progresso global | Media simples das % das actividades activas (canceladas excluidas) |

## Arquivo (`/avaliacoes`)

- Lista: data, projecto, progresso, autor, estado.
- Accao **Editar** → `/avaliacao?pilar=…&edit=…` (quando editavel).
- Detalhe: hero + actividades + orcamento + passos + riscos + anexos (sem blocos vazios legados).

## Anexos globais (`/anexos`)

Listagem com pesquisa e paginacao no servidor; coluna de referencia (`source_label` → link para avaliacao).

## API relacionada

Ver [API.md](API.md) — seccao Avaliacoes e Anexos.

- Detalhe / edicao: `GET` + `PATCH /avaliacoes/{id}`
- Baseline: `GET /avaliacoes/latest/{pilar_id}`
