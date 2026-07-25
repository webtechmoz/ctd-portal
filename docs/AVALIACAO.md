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

### Seccoes

1. **Cabecalho** — selector de projecto + resumo (objectivos, orcamento, riscos master, KPIs).
2. **Execucao de actividades** — so `%` editavel; estado e datas reais calculados; progresso global = media.
3. **Execucao orcamental** — valor executado cumulativo por rubrica; cards planeado / executado / %.
4. **Proximos passos** — cumulativos (nao concluidos da avaliacao anterior + novos); checkbox “Concluido”; prazo com flatpickr (data ≥ hoje).
5. **Riscos do periodo** — lista (nao tabela); textarea de observacao a largura total.
6. **Anexos** — ficheiros seleccionados no cliente; upload apos `POST /avaliacoes`.

Removido do formulario (campos ainda existem na BD por legado, mas nao sao preenchidos pela UI):

- estado_geral / desafios / licoes / recomendacoes / comentarios / assinatura / fecho manual.

## Regras de calculo

| Campo | Regra |
|-------|--------|
| Estado actividade | `0` → pendente; `1–99` → em_progresso; `100` → concluida |
| Datas inicio/fim | Automaticas quando % > 0 / = 100; read-only na UI |
| Minimo de % | Baseline da avaliacao anterior; validado no **submit** (cliente + servidor), nao ao digitar |
| Orcamento | Cumulativo; minimo = valor da avaliacao anterior; validado no submit |
| Progresso global | Media simples das % das actividades |

## Arquivo (`/avaliacoes`)

- Lista: data, projecto, progresso, autor.
- Detalhe: hero + actividades + orcamento + passos + riscos + anexos (sem blocos vazios legados).

## Anexos globais (`/anexos`)

Listagem com pesquisa e paginacao no servidor; coluna de referencia (`source_label` → link para avaliacao).

## API relacionada

Ver [API.md](API.md) — seccao Avaliacoes e Anexos.

Baseline: `GET /avaliacoes/latest/{pilar_id}`.
