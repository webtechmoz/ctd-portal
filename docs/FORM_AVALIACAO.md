# Formulario de avaliacao — historico de discussao

> **Estado:** documento de inventário / propostas UX (legado).  
> **Referencia actual:** [AVALIACAO.md](AVALIACAO.md).

O formulario em producao ja nao usa secoes colapsaveis verdes nem os campos de fecho (resumo, desafios, licoes, recomendacoes, comentarios, assinatura).  
Anexos, passos cumulativos, validacao no servidor e layout em blocos `.aval-block` estao implementados — ver `AVALIACAO.md` e o codigo em `frontend/avaliacao.html` + `js/pages/avaliacao.js`.

---

# Formulario de Avaliacao — inventario e propostas (arquivo)

Documento original para discutir o redesenho do formulario de avaliacao periodica.

## 1. Objectivo do formulario

Registar o **acompanhamento de execucao** de um periodo, sobre dados mestre do projecto (pilar) ja cadastrados na **Base de projectos**.

| Camada | Responsavel | Conteudo |
|--------|-------------|----------|
| Master (projecto) | Admin / `projectos.manage` | Contexto, objectivos, actividades planeadas, rubricas, riscos base, proximos passos base |
| Avaliacao (periodo) | Member/Admin responsavel | Estado de execucao, valores executados, obs. do periodo, progresso |

## 2. Estrutura antiga (referencia)

Secoes colapsaveis com campos narrativos (estado_geral, desafios, licoes, fecho) — **removidos da UI**.

## 3. Payload API

Ver [API.md](API.md). Campos narrativos ainda aceites no schema com default vazio para compatibilidade.

## 4–6. Propostas UX

Muitas propostas (tabelas densas, progresso automatico, orcamento cumulativo, riscos em lista) foram adoptadas. Detalhe actual em [AVALIACAO.md](AVALIACAO.md).
