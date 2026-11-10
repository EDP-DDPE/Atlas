// triagem.js — modal de análise: detalhes, descrição, arquivos e decisão
import { showNotification } from "./utils.js";
import { loadOvs, loadNotas } from "./table.js";

let podeDeletar = false;
let somenteLeitura = false;

// Endpoints por tipo (ov / nota)
const API = {
    ov: {
        detalhes: id => `/analises_ovs_notas/api/ovs/${id}/detalhes`,
        status:   id => `/analises_ovs_notas/ovs/${id}/status`,
    },
    nota: {
        detalhes: id => `/analises_ovs_notas/api/notas/${id}/detalhes`,
        status:   id => `/analises_ovs_notas/notas/${id}/status`,
    },
};

const DOC_API = {
    ov: {
        download: docId => `/analises_ovs_notas/ovs/documentos/${docId}/download`,
        del:      docId => `/analises_ovs_notas/ovs/documentos/${docId}`,
    },
    nota: {
        download: docId => `/analises_ovs_notas/notas/documentos/${docId}/download`,
        del:      docId => `/analises_ovs_notas/notas/documentos/${docId}`,
    },
};

const esc = (v) => String(v ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#039;");

// ---------------------------------------------------------------------------
// Abertura do modal
// ---------------------------------------------------------------------------
export function abrirTriagem(tipo, id, label, modo = "analisar") {
    somenteLeitura = modo === "ver";

    $("#triagemTipo").val(tipo);
    $("#triagemId").val(id);
    $("#triagemLabel").text(label);
    $("#triagemStatus").val("");

    // modo visualização: esconde decisão e salvar
    $("#triagemTitulo").text(somenteLeitura ? "Visualização" : "Análise");
    $("#colDecisao").toggle(!somenteLeitura);
    $("#btnSalvarTriagem").toggle(!somenteLeitura);
    $("#btnCriarEstudo").hide();
    // encerramento manual: só Notas, só no modo Analisar
    $("#blocoEncerramentoManual").toggle(tipo === "nota" && !somenteLeitura);
    cancelarEncerramento();
    $("#colInfo").toggleClass("col-md-6", !somenteLeitura)
                 .toggleClass("col-md-12", somenteLeitura);

    $("#analiseInfo").html('<p class="text-muted mb-0">Carregando...</p>');
    $("#analiseDescricao").val("");
    $("#analiseDocs").empty();
    $("#analiseHistorico").empty();

    new bootstrap.Modal(document.getElementById("modalTriagem")).show();
    carregarDetalhes(tipo, id);
}

function carregarDetalhes(tipo, id) {
    $("#analiseLoading").show();
    $.get(API[tipo].detalhes(id))
        .done(resp => {
            podeDeletar = !somenteLeitura && !!(resp.permissoes && resp.permissoes.deletar);
            $("#btnCriarEstudo")
                .toggle(!somenteLeitura && !!resp.pode_criar_estudo
                        && !!(resp.permissoes && resp.permissoes.criar))
                .prop("disabled", false);
            renderInfo(tipo, resp.info);
            renderHistorico(resp.historico);
            renderDescricao(resp.descricao);
            renderDocs(tipo, resp.documentos);
        })
        .fail(xhr => {
            const msg = (xhr.responseJSON && xhr.responseJSON.message) || "Erro ao carregar detalhes.";
            $("#analiseInfo").html(`<p class="text-danger mb-0">${esc(msg)}</p>`);
            showNotification(msg, "danger");
        })
        .always(() => $("#analiseLoading").hide());
}

// ---------------------------------------------------------------------------
// Render das seções
// ---------------------------------------------------------------------------
function renderInfo(tipo, info) {
    if (!info) {
        $("#analiseInfo").html('<p class="text-muted mb-0">Sem informações.</p>');
        return;
    }
    const edp = (info.edp && info.edp.empresa) || "-";
    const linhas = tipo === "ov"
        ? [
            ["EDP", edp],
            ["OV", info.numero],
            ["Data Solicitação", info.data_solicitacao || "-"],
            ["Data Planejamento", info.data_planejamento || "-"],
          ]
        : [
            ["EDP", edp],
            ["Nota", info.numero],
            ["Data Solicitação", info.data_solicitacao || "-"],
            ["Data Vencimento", info.data_vencimento || "-"],
          ];

    $("#analiseInfo").html(
        linhas.map(([k, v]) => `<p class="mb-1"><strong>${k}:</strong> ${esc(v ?? "-")}</p>`).join("")
    );
}

function renderHistorico(hist) {
    const $tb = $("#analiseHistorico").empty();

    if (!hist || !hist.length) {
        $tb.append(`<tr><td colspan="5" class="text-center text-muted py-3">Nenhum status registrado.</td></tr>`);
        return;
    }

    // vem do backend do mais recente para o mais antigo.
    // "atual" vem do backend (em Notas, ENCE/NREJ prevalecem mesmo não sendo o mais recente)
    hist.forEach(h => {
        const atual = h.atual
            ? ' <span class="badge bg-light text-dark border ms-1">atual</span>'
            : "";
        $tb.append(`
            <tr>
                <td>
                    <span class="badge bg-${esc(h.classe)}"><i class="bi ${esc(h.icone)}"></i> ${esc(h.status)}</span>${atual}
                </td>
                <td>${esc(h.data ?? "-")}</td>
                <td>${esc((h.edp && h.edp.empresa) || "-")}</td>
                <td>${esc(h.responsavel ?? "-")}</td>
                <td>${esc(h.registrado_em ?? "-")}</td>
            </tr>`);
    });
}

function renderDescricao(texto) {
    if (texto === null || texto === undefined) {
        $("#analiseDescricao")
            .val("Arquivo de descrição (_descricao.txt) não encontrado nesta pasta.")
            .addClass("text-muted");
    } else {
        $("#analiseDescricao").val(texto).removeClass("text-muted");
    }
}

function renderDocs(tipo, docs) {
    const $tb = $("#analiseDocs").empty();

    if (!docs || !docs.length) {
        $tb.append(`<tr><td colspan="4" class="text-center text-muted py-3">Nenhum arquivo na pasta.</td></tr>`);
        return;
    }

    docs.forEach(d => {
        const btnDel = podeDeletar
            ? `<button class="btn btn-sm btn-outline-danger ms-1"
                       title="Excluir arquivo"
                       onclick="apagarDoc('${tipo}', ${d.id}, this)">
                   <i class="bi bi-trash"></i>
               </button>`
            : "";

        const destaque = d.eh_descricao
            ? '<i class="bi bi-file-earmark-text text-primary me-1" title="Arquivo de descrição"></i>'
            : '';

        $tb.append(`
            <tr>
                <td>${destaque}${esc(d.nome)}</td>
                <td><span class="badge bg-light text-dark border">${esc((d.tipo || "").toUpperCase())}</span></td>
                <td>${esc(d.data ?? "-")}</td>
                <td class="text-end">
                    <a class="btn btn-sm btn-outline-primary" title="Baixar"
                       href="${DOC_API[tipo].download(d.id)}" data-no-loading="true">
                        <i class="bi bi-download"></i>
                    </a>
                    ${btnDel}
                </td>
            </tr>`);
    });
}

// ---------------------------------------------------------------------------
// Exclusão de arquivo
// ---------------------------------------------------------------------------
export function apagarDoc(tipo, docId, btn) {
    if (!confirm("Remover este arquivo? Esta ação não pode ser desfeita.")) return;

    $.ajax({
        url: DOC_API[tipo].del(docId),
        method: "DELETE",
        success: () => {
            showNotification("Arquivo removido.", "success");
            $(btn).closest("tr").remove();
            if (!$("#analiseDocs tr").length) {
                $("#analiseDocs").append(
                    `<tr><td colspan="4" class="text-center text-muted py-3">Nenhum arquivo na pasta.</td></tr>`
                );
            }
        },
        error: xhr => {
            const msg = (xhr.responseJSON && xhr.responseJSON.message) || "Erro ao remover.";
            showNotification(msg, "danger");
        },
    });
}

// ---------------------------------------------------------------------------
// Salvar decisão (status)
// ---------------------------------------------------------------------------
export function salvarTriagem() {
    const tipo = $("#triagemTipo").val();
    const id = $("#triagemId").val();
    const status = $("#triagemStatus").val();

    if (!status) { showNotification("Selecione uma decisão.", "warning"); return; }

    $.ajax({
        url: API[tipo].status(id),
        method: "POST",
        data: JSON.stringify({ status }),
        contentType: "application/json",
        success: function () {
            bootstrap.Modal.getInstance(document.getElementById("modalTriagem")).hide();
            showNotification("Status registrado!", "success");
            tipo === "ov" ? loadOvs() : loadNotas();
        },
        error: function (xhr) {
            const msg = (xhr.responseJSON && xhr.responseJSON.message) || "Erro ao salvar.";
            showNotification(msg, "danger");
        }
    });
}

// ---------------------------------------------------------------------------
// Encerramento manual de Nota (ENCE / NREJ) — quando o robô falha
// ---------------------------------------------------------------------------
let encerramentoStatus = null;

const hojeISO = () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

export function iniciarEncerramento(status) {
    encerramentoStatus = status;
    const ence = status === "ENCE";
    $("#confirmEncerramentoTitulo").text(
        ence ? "Encerrar a nota (ENCE)?" : "Rejeitar a nota (NREJ)?"
    );
    $("#encerramentoDataSap").attr("max", hojeISO()).val("");
    $("#btnConfirmarEncerramento")
        .removeClass("btn-secondary btn-danger")
        .addClass(ence ? "btn-secondary" : "btn-danger")
        .text(ence ? "Confirmar encerramento" : "Confirmar rejeição")
        .prop("disabled", false);
    $("#confirmEncerramento").show();
    $("#encerramentoDataSap").trigger("focus");
}

export function cancelarEncerramento() {
    encerramentoStatus = null;
    $("#confirmEncerramento").hide();
    $("#encerramentoDataSap").val("");
}

export function confirmarEncerramento() {
    const id = $("#triagemId").val();
    const dataSap = $("#encerramentoDataSap").val();   // yyyy-mm-dd

    if (!encerramentoStatus) return;
    if (!dataSap) { showNotification("Informe a data em que a nota foi encerrada no SAP.", "warning"); return; }
    if (dataSap > hojeISO()) { showNotification("A data do SAP não pode ser futura.", "warning"); return; }

    const $btn = $("#btnConfirmarEncerramento").prop("disabled", true);

    $.ajax({
        url: `/analises_ovs_notas/notas/${id}/encerramento_manual`,
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ status: encerramentoStatus, data_sap: dataSap }),
        success: resp => {
            bootstrap.Modal.getInstance(document.getElementById("modalTriagem")).hide();
            showNotification(resp.message || "Status registrado!", "success");
            loadNotas();
        },
        error: xhr => {
            const msg = (xhr.responseJSON && xhr.responseJSON.message) || "Erro ao registrar.";
            showNotification(msg, "danger");
            $btn.prop("disabled", false);
        },
    });
}

export function criarEstudo() {
    const tipo = $("#triagemTipo").val();
    const id = $("#triagemId").val();
    const $btn = $("#btnCriarEstudo").prop("disabled", true);

    $.ajax({
        url: `/analises_ovs_notas/${tipo}/${id}/criar_estudo`,
        method: "POST",
        contentType: "application/json",
        data: "{}",
        success: resp => { window.location.href = resp.redirect; },
        error: xhr => {
            const msg = (xhr.responseJSON && xhr.responseJSON.message) || "Erro ao abrir o cadastro de estudo.";
            showNotification(msg, "danger");
            $btn.prop("disabled", false);
        },
    });
}

// expõe para os onclick inline do HTML
window.abrirTriagem = abrirTriagem;
window.salvarTriagem = salvarTriagem;
window.apagarDoc = apagarDoc;
window.criarEstudo = criarEstudo;
window.iniciarEncerramento = iniciarEncerramento;
window.cancelarEncerramento = cancelarEncerramento;
window.confirmarEncerramento = confirmarEncerramento;