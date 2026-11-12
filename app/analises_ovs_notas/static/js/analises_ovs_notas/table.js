// table.js — carrega e renderiza as duas tabelas
import { state } from "./main.js";
import { showLoading, hideLoading, initializeTooltips } from "./utils.js";
import { COLUNAS, HEADER_IDS } from "./columns.js";
import { aplicarFiltros } from "./filters.js";

// ---------- Cabeçalhos (título + ordenação + linha de filtro por coluna) ----------
export function renderHeaders() {
    Object.keys(COLUNAS).forEach(tipo => {
        const $h = $(HEADER_IDS[tipo].header).empty();
        const $f = $(HEADER_IDS[tipo].filtros).empty();

        COLUNAS[tipo].forEach(col => {
            const icone = col.ordena === false
                ? ""
                : `<i class="fas fa-sort sort-icon" data-sort="${col.key}" title="Ordenar"></i>`;
            $h.append(`
                <th data-column="${col.key}">
                    <div class="header-content">
                        <span>${col.label}</span>${icone}
                    </div>
                </th>`);

            $f.append(col.filtro === false
                ? `<th data-column="${col.key}"></th>`
                : `<th data-column="${col.key}">
                       <input type="text" class="filter-input" data-filter="${col.key}"
                              placeholder="Filtrar ${col.label}...">
                   </th>`);
        });
    });
}

const badge = (s) =>
    `<span class="badge bg-${s.classe}"><i class="bi ${s.icone}"></i> ${s.texto}</span>`;

const linkEstudo = (estudo) =>
    estudo && estudo.id
        ? `<a href="/estudo/${estudo.id}/alternativas/" class="btn btn-sm btn-outline-primary"
              title="Abrir alternativas do estudo">
              <i class="bi bi-box-arrow-up-right"></i> Estudo ${estudo.num_doc ?? ""}
           </a>`
        : `<span class="text-muted">-</span>`;

const esc = (v) => String(v ?? "").replace(/'/g, "\\'");

const botoes = (tipo, i, label) => {
    const ver = `
        <button class="btn btn-sm btn-outline-secondary me-1"
            onclick="abrirTriagem('${tipo}', ${i.id}, '${label}', 'ver')">
            <i class="bi bi-eye"></i> Visualizar
        </button>`;

    if (i.status && i.status.encerrado) return ver;

    const pode = state.permissoes.editar;
    return ver + `
        <button class="btn btn-sm btn-primary"
            onclick="abrirTriagem('${tipo}', ${i.id}, '${label}', 'analisar')"
            ${pode ? "" : "disabled"}>
            <i class="bi bi-clipboard-check"></i> Analisar
        </button>`;
};

// ---------- Paginação (mesmo visual do "listar": Anterior | página | Próximo) ----------
const PAGINACAO = {
    ov:   { estado: () => state.ovs,   suf: "Ovs",   render: () => renderOvs() },
    nota: { estado: () => state.notas, suf: "Notas", render: () => renderNotas() },
};

/** Devolve só os itens da página atual (e corrige a página se ela "sobrou"). */
function paginaAtual(st) {
    const totalPaginas = Math.max(1, Math.ceil(st.filtered.length / st.perPage));
    st.page = Math.min(Math.max(1, st.page), totalPaginas);
    const ini = (st.page - 1) * st.perPage;
    return st.filtered.slice(ini, ini + st.perPage);
}

function renderPaginacao(tipo, qtdNaPagina) {
    const { estado, suf, render } = PAGINACAO[tipo];
    const st = estado();
    const total = st.filtered.length;
    const totalPaginas = Math.max(1, Math.ceil(total / st.perPage));
    const ini = qtdNaPagina ? (st.page - 1) * st.perPage + 1 : 0;
    const fim = qtdNaPagina ? ini + qtdNaPagina - 1 : 0;

    $(`#start${suf}`).text(ini);
    $(`#end${suf}`).text(fim);
    $(`#total${suf}`).text(total);
    $(`#page${suf}`).text(`Página ${st.page} de ${totalPaginas}`);

    const botao = (label, p, disabled = false, active = false) => `
        <li class="page-item ${disabled ? "disabled" : ""} ${active ? "active" : ""}">
            <a class="page-link" href="#" data-page="${p}">${label}</a>
        </li>`;

    const $pag = $(`#pagination${suf}`).html(
        botao("Anterior", st.page - 1, st.page === 1) +
        botao(st.page, st.page, false, true) +
        botao("Próximo", st.page + 1, st.page >= totalPaginas)
    );

    $pag.find("a").on("click", function (e) {
        e.preventDefault();
        const $li = $(this).closest("li");
        if ($li.hasClass("disabled") || $li.hasClass("active")) return;
        const nova = parseInt($(this).data("page"), 10);
        if (!isNaN(nova)) {
            st.page = nova;
            render();
        }
    });
}

/** Troca de "Exibir N registros" (chamado pelo filters.js). */
export function setupPageSize() {
    Object.entries(PAGINACAO).forEach(([tipo, { estado, suf, render }]) => {
        $(`#pageSize${suf}`).val(String(estado().perPage)).off("change").on("change", function () {
            estado().perPage = parseInt($(this).val(), 10) || 25;
            estado().page = 1;
            render();
        });
    });
}

// ---------- OVs ----------
export function loadOvs() {
    showLoading();
    return $.get("/analises_ovs_notas/api/ovs")
        .done(resp => {
            state.permissoes = resp.permissoes || {};
            state.ovs.data = resp.items || [];
            aplicarFiltros("ov", true);   // mantém filtros/ordenação/página atuais
        })
        .fail(() => alert("Erro ao carregar OVs."))
        .always(hideLoading);
}

export function renderOvs() {
    const $tb = $("#tableBodyOvs");
    const pagina = paginaAtual(state.ovs);
    renderPaginacao("ov", pagina.length);

    if (!pagina.length) {
        $tb.html(`<tr><td colspan="8" class="text-center text-muted py-3">Nenhuma OV.</td></tr>`);
        return;
    }
    // monta tudo numa string só (bem mais leve que vários .append)
    $tb.html(pagina.map(i => `
            <tr>
                <td>${(i.edp && i.edp.empresa) ?? "-"}</td>
                <td>${i.ov ?? ""}</td>
                <td>${i.data_solicitacao ?? "-"}</td>
                <td>${i.data_planejamento ?? "-"}</td>
                <td>${i.data_importacao ?? "-"}</td>
                <td>${badge(i.status)}</td>
                <td>${linkEstudo(i.estudo)}</td>
                <td>${botoes("ov", i, esc(i.ov))}</td>
            </tr>`).join(""));
    initializeTooltips();
}

// ---------- Notas ----------
export function loadNotas() {
    return $.get("/analises_ovs_notas/api/notas")
        .done(resp => {
            state.permissoes = resp.permissoes || {};
            state.notas.data = resp.items || [];
            aplicarFiltros("nota", true); // mantém filtros/ordenação/página atuais
        })
        .fail(() => alert("Erro ao carregar Notas."));
}

export function renderNotas() {
    const $tb = $("#tableBodyNotas");
    const pagina = paginaAtual(state.notas);
    renderPaginacao("nota", pagina.length);

    if (!pagina.length) {
        $tb.html(`<tr><td colspan="8" class="text-center text-muted py-3">Nenhuma Nota.</td></tr>`);
        return;
    }
    $tb.html(pagina.map(i => `
            <tr>
                <td>${(i.edp && i.edp.empresa) ?? "-"}</td>
                <td>${i.nota ?? ""}</td>
                <td>${i.data_solicitacao ?? "-"}</td>
                <td>${i.data_vencimento ?? "-"}</td>
                <td>${i.data_importacao ?? "-"}</td>
                <td>${badge(i.status)}</td>
                <td>${linkEstudo(i.estudo)}</td>
                <td>${botoes("nota", i, esc(i.nota))}</td>
            </tr>`).join(""));
    initializeTooltips();
}