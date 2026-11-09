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

// ---------- OVs ----------
export function loadOvs() {
    showLoading();
    return $.get("/analises_ovs_notas/api/ovs")
        .done(resp => {
            state.permissoes = resp.permissoes || {};
            state.ovs.data = resp.items || [];
            aplicarFiltros("ov");   // mantém filtros/ordenação atuais
        })
        .fail(() => alert("Erro ao carregar OVs."))
        .always(hideLoading);
}

export function renderOvs() {
    const pode = state.permissoes.editar;
    const $tb = $("#tableBodyOvs").empty();
    if (!state.ovs.filtered.length) {
        $tb.append(`<tr><td colspan="8" class="text-center text-muted py-3">Nenhuma OV.</td></tr>`);
        return;
    }
    state.ovs.filtered.forEach(i => {
        $tb.append(`
            <tr>
                <td>${(i.edp && i.edp.empresa) ?? "-"}</td>
                <td>${i.ov ?? ""}</td>
                <td>${i.data_solicitacao ?? "-"}</td>
                <td>${i.data_planejamento ?? "-"}</td>
                <td>${i.data_importacao ?? "-"}</td>
                <td>${badge(i.status)}</td>
                <td>${linkEstudo(i.estudo)}</td>
                <td>${botoes("ov", i, esc(i.ov))}</td>
            </tr>`);
    });
    initializeTooltips();
}

// ---------- Notas ----------
export function loadNotas() {
    return $.get("/analises_ovs_notas/api/notas")
        .done(resp => {
            state.permissoes = resp.permissoes || {};
            state.notas.data = resp.items || [];
            aplicarFiltros("nota"); // mantém filtros/ordenação atuais
        })
        .fail(() => alert("Erro ao carregar Notas."));
}

export function renderNotas() {
    const pode = state.permissoes.editar;
    const $tb = $("#tableBodyNotas").empty();
    if (!state.notas.filtered.length) {
        $tb.append(`<tr><td colspan="8" class="text-center text-muted py-3">Nenhuma Nota.</td></tr>`);
        return;
    }
    state.notas.filtered.forEach(i => {
        $tb.append(`
            <tr>
                <td>${(i.edp && i.edp.empresa) ?? "-"}</td>
                <td>${i.nota ?? ""}</td>
                <td>${i.data_solicitacao ?? "-"}</td>
                <td>${i.data_vencimento ?? "-"}</td>
                <td>${i.data_importacao ?? "-"}</td>
                <td>${badge(i.status)}</td>
                <td>${linkEstudo(i.estudo)}</td>
                <td>${botoes("nota", i, esc(i.nota))}</td>
            </tr>`);
    });
    initializeTooltips();
}