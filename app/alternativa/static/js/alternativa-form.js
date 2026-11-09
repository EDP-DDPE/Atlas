import { apiListarCircuitos, apiCalcularFatorK } from "./alternativa-api.js";

// ==================== FORM HELPERS =====================

export function limparFormulario() {
    const form = $("#formAlternativa")[0];
    form.reset();

    $("#preview_imagem").hide().attr("src", "");
    $("#imagem_alternativa").val("");

    $("#circuito_select").val(1).trigger("change.select2");
    $("#letra_select").val("A").trigger("change.select2");
}

export function preencherFormulario(data) {

    // selects
    $("#subgrupo_select").val(data.subgrupo_tarifario);
    atualizarCircuitos(data.id_edp,data.subgrupo_tarifario);
    $("#circuito_select").val(data.id_circuito).trigger("change.select2");
    $("#letra_select").val(data.letra_alternativa).trigger("change.select2");


    // campos texto
    $("#descricao").val(data.descricao);
    $("#observacao").val(data.observacao);

    // números
    $("#dem_p_antes").val(data.dem_p_ant);
    $("#dem_fp_antes").val(data.dem_fp_ant);
    $("#dem_p_depois").val(data.dem_p_dep);
    $("#dem_fp_depois").val(data.dem_fp_dep);
    $("#dem_disponivel").val(data.demanda_disponivel_ponto);
    $("#ERD").val(data.ERD);
    $("#custo_modular").val(data.custo_modular);

    // coordenadas
    $("#latitude_ponto_conexao").val(data.latitude_ponto_conexao);
    $("#longitude_ponto_conexao").val(data.longitude_ponto_conexao);

    // flags
    $("#flag_carga").prop("checked", data.flag_carga);
    $("#flag_geracao").prop("checked", data.flag_geracao);
    $("#flag_fluxo_reverso").prop("checked", data.flag_fluxo_reverso);
    $("#flag_menor_custo_global").prop("checked", data.flag_menor_custo_global);
    $("#flag_alternativa_escolhida").prop("checked", data.flag_alternativa_escolhida);

    // imagem
    if (data.imagem_base64) {
        $("#preview_imagem").attr("src", "data:image/jpeg;base64," + data.imagem_base64).show();
    }
}

// ============= EVENTOS DO FORMULÁRIO (ERD + CIRCUITOS) ===================

export function inicializarEventosFormulario() {

    $("#subgrupo_select").change(() => {
        const sub = $("#subgrupo_select").val();
        const id_edp = $("#id_edp").val();
        atualizarCircuitos(id_edp, sub);
        atualizarERD();
    });

    $("#flag_carga, #flag_geracao").change(() => {
        atualizarERD();
    });
}

export function atualizarCircuitos(id_edp, subgrupo) {
    const select = $("#circuito_select");
    select.empty();
    select.append(new Option("Carregando lista....", 1));

    return apiListarCircuitos(id_edp, subgrupo)
        .then(resp => {
            select.empty();
            resp.circuitos.forEach(c => {
                select.append(new Option(c.nome, c.id));
            });
        }).catch(err => {
            console.error("Erro ao carregar circuitos:", err);
        });
}

// Aceita a casa decimal com vírgula ("1.234,56") ou com ponto ("1234.56")
function paraNumero(valor) {
    if (valor === null || valor === undefined) return NaN;

    let texto = String(valor).replace(/[R$\s]/g, "");
    if (texto.includes(",")) {
        texto = texto.replace(/\./g, "").replace(",", ".");
    }

    return parseFloat(texto);
}

function atualizarERD() {
    const sub = $("#subgrupo_select").val();
    const id_edp = $("#id_edp").val();
    const dataAbertura = $("#estudo_dados").data("data-abertura");

    const demAntes = Math.max(
        paraNumero($("#dem_p_antes").val()),
        paraNumero($("#dem_fp_antes").val())
    );

    const demDepois = Math.max(
        paraNumero($("#dem_p_depois").val()),
        paraNumero($("#dem_fp_depois").val())
    );

    const tipo = $("#flag_carga").is(":checked") ? 1 :
                 $("#flag_geracao").is(":checked") ? 0 : null;

    if (tipo === null) {
        $("#ERD").val("0");
        return;
    }

    const dif = demDepois - demAntes;

    apiCalcularFatorK(id_edp, sub, dataAbertura, tipo)
        .then(data => {
            const valor = data.k * dif;
            $("#ERD").val(valor.toFixed(2));
        });
}
