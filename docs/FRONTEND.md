# Frontend

## Principio

Cada rota HTML e um shell estatico. A logica vive em `js/pages/*.js` (ES modules). O backend nao controla eventos de UI.

## Mapa pagina → script

| URL | HTML | JS |
|-----|------|-----|
| `/` | `frontend/index.html` | `js/pages/home.js` |
| `/login` | `login.html` | `login.js` |
| `/avaliacao` | `avaliacao.html` | `avaliacao.js` |
| `/avaliacoes` | `avaliacoes.html` | `avaliacoes.js` |
| `/relatorios` | `relatorios.html` | `relatorios.js` |
| `/anexos` | `anexos.html` | `anexos.js` |
| `/projectos` | `projectos.html` | `projectos.js` |
| `/situacao` | `situacao.html` | `situacao.js` |
| `/dashboard` | `dashboard.html` | `dashboard.js` |
| `/admin` | `admin/index.html` | `admin.js` |
| `/admin/projectos/novo` | `admin/projecto-form.html` | `projecto-form.js` |
| `/admin/projectos/{id}` | idem | idem |

## Shell e boot

Padrao HTML recomendado (evita FOUC):

```html
<div id="app">
  <div class="boot-loading loader-block">…</div>
  <div id="app-content" hidden>
    <!-- conteudo da pagina -->
  </div>
</div>
<script type="module" src="/js/pages/….js"></script>
```

`bootPage({ page, title, subtitle })` em `js/shell.js`:

1. Valida sessao (`requireSession`).
2. Remove o loader.
3. Monta sidebar + topbar.
4. Move `#app-content` para `.shell-content`.

IDs de navegacao: `home`, `projectos`, `avaliacoes`, `anexos`, `situacao`, `resultados`, `admin` (condicional).

CSS FOUC: `body:not(.app-body) #app > *:not(.boot-loading)` esconde conteudo ate o shell.

## Modulos partilhados

| Ficheiro | Uso |
|----------|-----|
| `js/api.js` | `api()`, `apiForm()`, `formatBytes()` |
| `js/auth.js` | login/logout/sessao |
| `js/ui.js` | toast, loading |
| `js/components/dates.js` | flatpickr `Y-m-d` / `d/m/Y` |
| `js/components/styled-select.js` | selects com menu em `document.body` |
| `js/components/list-kit.js` | pesquisa + paginacao client-side |
| `js/components/pilar-picker.js` | selector de projecto |
| `js/components/modal.js` | abrir/fechar modais |

## Estilos

- Design system: `css/app.css` (variaveis `--primary`, `--accent`, etc.).
- Sem Tailwind em runtime (mencao historica no PLAN); CSS e manual.
- Icones: Bootstrap Icons CDN.

## Convencoes UI

- Sem emoji.
- Preferir listas/seccoes a “cards” decorativos desnecessarios.
- Formularios longos: blocos `.aval-block` / `.form-section`.
- Tabelas de avaliacao: `.aval-table` a 100% de largura.
- Selects dentro de overflow: sempre `enhanceSelect` / styled-select (portal fixed).

## Admin

- Utilizadores, perfis/permissoes, projectos, listas de sistema.
- Criacao/edicao de projecto e **pagina dedicada**, nao modal unico.
- Nested modais para actividade / rubrica / risco no form do projecto.
