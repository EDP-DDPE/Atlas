// main.js — ponto de entrada da Triagem
import { loadOvs, loadNotas, renderHeaders } from "./table.js";
import { setupFilters } from "./filters.js";
import { initializeTooltips } from "./utils.js";
import "./triagem.js";

export const state = {
    ovs:   { data: [], filtered: [], colFilters: {}, sort: { key: null, dir: "asc" } },
    notas: { data: [], filtered: [], colFilters: {}, sort: { key: null, dir: "asc" } },
    permissoes: {}
};

window.refreshAll = function () {
    loadOvs();
    loadNotas();
};

$(document).ready(function () {
    renderHeaders();   // precisa vir antes do setupFilters (cria os inputs e ícones)
    setupFilters();
    loadOvs();
    loadNotas();
    initializeTooltips();
});