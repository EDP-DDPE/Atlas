// columns.js — definição das colunas das tabelas de OVs e Notas
// get:  valor usado para filtrar/ordenar
// tipo: "num" | "texto" | "data" (dd/mm/aaaa) — define como ordenar
// filtro / ordena: false para desativar (ex.: Ações)

const estudoTexto = i => (i.estudo && i.estudo.num_doc) || "";
const edpTexto = i => (i.edp && i.edp.empresa) || "";
const statusTexto = i => (i.status && i.status.texto) || "";

export const COLUNAS = {
    ov: [
        { key: "edp",               label: "EDP",               tipo: "texto", get: edpTexto },
        { key: "ov",                label: "OV",                tipo: "texto", get: i => i.ov },
        { key: "data_solicitacao",  label: "Data Solicitação",  tipo: "data",  get: i => i.data_solicitacao },
        { key: "data_planejamento", label: "Data Planejamento", tipo: "data",  get: i => i.data_planejamento },
        { key: "data_importacao",   label: "Data Importação",   tipo: "data",  get: i => i.data_importacao },
        { key: "status",            label: "Status",            tipo: "texto", get: statusTexto },
        { key: "estudo",            label: "Estudo",            tipo: "texto", get: estudoTexto },
        { key: "acoes",             label: "Ações",             filtro: false, ordena: false },
    ],
    nota: [
        { key: "edp",              label: "EDP",              tipo: "texto", get: edpTexto },
        { key: "nota",             label: "Nota",             tipo: "texto", get: i => i.nota },
        { key: "data_solicitacao", label: "Data Solicitação", tipo: "data",  get: i => i.data_solicitacao },
        { key: "data_vencimento",  label: "Data Vencimento",  tipo: "data",  get: i => i.data_vencimento },
        { key: "data_importacao",  label: "Data Importação",  tipo: "data",  get: i => i.data_importacao },
        { key: "status",           label: "Status",           tipo: "texto", get: statusTexto },
        { key: "estudo",           label: "Estudo",           tipo: "texto", get: estudoTexto },
        { key: "acoes",            label: "Ações",            filtro: false, ordena: false },
    ],
};

// Ids dos elementos do cabeçalho de cada tabela
export const HEADER_IDS = {
    ov:   { header: "#headerOvs",   filtros: "#filterRowOvs" },
    nota: { header: "#headerNotas", filtros: "#filterRowNotas" },
};

// "dd/mm/aaaa" -> número comparável (aaaammdd); vazio -> null
function dataParaNumero(v) {
    const m = /^(\d{2})\/(\d{2})\/(\d{4})/.exec(String(v ?? ""));
    return m ? Number(m[3] + m[2] + m[1]) : null;
}

// Valor normalizado para ordenação
export function valorOrdenacao(col, item) {
    const v = col.get(item);
    if (col.tipo === "num")  return v === null || v === undefined || v === "" ? null : Number(v);
    if (col.tipo === "data") return dataParaNumero(v);
    return String(v ?? "").toLowerCase();
}

// Valor normalizado para filtro (texto)
export function valorFiltro(col, item) {
    return String(col.get(item) ?? "").toLowerCase();
}
