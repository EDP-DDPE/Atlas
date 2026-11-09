// filters.js — busca global, filtro por situação, filtro por coluna e ordenação (por aba)
import { state } from "./main.js";
import { debounce } from "./utils.js";
import { renderOvs, renderNotas } from "./table.js";
import { COLUNAS, HEADER_IDS, valorOrdenacao, valorFiltro } from "./columns.js";

const CONTROLES = {
    ov:   { busca: "#searchOvs",   situacao: "#filterSituacaoOvs",   estado: () => state.ovs,   render: () => renderOvs() },
    nota: { busca: "#searchNotas", situacao: "#filterSituacaoNotas", estado: () => state.notas, render: () => renderNotas() },
};

const colunaPorKey = (tipo, key) => COLUNAS[tipo].find(c => c.key === key);

// ---------------------------------------------------------------------------
// Aplica filtros + ordenação e redesenha a tabela
// ---------------------------------------------------------------------------
export function aplicarFiltros(tipo) {
    const ctl = CONTROLES[tipo];
    const st = ctl.estado();
    const termo = ($(ctl.busca).val() || "").trim().toLowerCase();
    const sit = $(ctl.situacao).val();
    const colsBusca = COLUNAS[tipo].filter(c => c.filtro !== false);
    const filtrosAtivos = Object.entries(st.colFilters).filter(([, v]) => v);

    let lista = st.data.filter(i => {
        if (sit && !(i.status && i.status.situacao === sit)) return false;
        if (termo && !colsBusca.some(c => valorFiltro(c, i).includes(termo))) return false;
        return filtrosAtivos.every(([key, v]) => {
            const col = colunaPorKey(tipo, key);
            return !col || valorFiltro(col, i).includes(v);
        });
    });

    if (st.sort.key) {
        const col = colunaPorKey(tipo, st.sort.key);
        const dir = st.sort.dir === "desc" ? -1 : 1;
        lista = [...lista].sort((a, b) => {
            const va = valorOrdenacao(col, a);
            const vb = valorOrdenacao(col, b);
            // vazios sempre no fim
            if (va === null || va === "") return (vb === null || vb === "") ? 0 : 1;
            if (vb === null || vb === "") return -1;
            if (va < vb) return -1 * dir;
            if (va > vb) return 1 * dir;
            return 0;
        });
    }

    st.filtered = lista;
    ctl.render();
}

// ---------------------------------------------------------------------------
// Ícones de ordenação
// ---------------------------------------------------------------------------
function atualizarIconesOrdenacao(tipo) {
    const st = CONTROLES[tipo].estado();
    $(`${HEADER_IDS[tipo].header} .sort-icon`).each(function () {
        const key = $(this).data("sort");
        $(this).removeClass("fa-sort fa-sort-up fa-sort-down")
            .addClass(st.sort.key !== key ? "fa-sort" : (st.sort.dir === "asc" ? "fa-sort-up" : "fa-sort-down"));
    });
}

// ---------------------------------------------------------------------------
// Limpar filtros
// ---------------------------------------------------------------------------
export function limparFiltros(tipo) {
    const ctl = CONTROLES[tipo];
    const st = ctl.estado();
    $(ctl.busca).val("");
    $(ctl.situacao).val("");
    $(`${HEADER_IDS[tipo].filtros} .filter-input`).val("");
    st.colFilters = {};
    st.sort = { key: null, dir: "asc" };
    atualizarIconesOrdenacao(tipo);
    aplicarFiltros(tipo);
}
window.limparFiltros = limparFiltros;

// ---------------------------------------------------------------------------
// Liga os eventos (chamado depois de montar os cabeçalhos)
// ---------------------------------------------------------------------------
export function setupFilters() {
    Object.keys(CONTROLES).forEach(tipo => {
        const ctl = CONTROLES[tipo];
        const ids = HEADER_IDS[tipo];

        $(ctl.busca).off("input").on("input", debounce(() => aplicarFiltros(tipo), 300));
        $(ctl.situacao).off("change").on("change", () => aplicarFiltros(tipo));

        // filtro por coluna
        $(`${ids.filtros} .filter-input`).off("input").on("input", debounce(e => {
            const key = $(e.target).data("filter");
            ctl.estado().colFilters[key] = $(e.target).val().trim().toLowerCase();
            aplicarFiltros(tipo);
        }, 300));

        // ordenação: clicar alterna asc -> desc; outra coluna começa em asc
        $(`${ids.header} .sort-icon`).off("click").on("click", function () {
            const st = ctl.estado();
            const key = $(this).data("sort");
            st.sort = (st.sort.key === key)
                ? { key, dir: st.sort.dir === "asc" ? "desc" : "asc" }
                : { key, dir: "asc" };
            atualizarIconesOrdenacao(tipo);
            aplicarFiltros(tipo);
        });
    });
}
