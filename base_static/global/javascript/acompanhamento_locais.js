(function () {
    'use strict';

    const config = window.ACOMPANHAMENTO_LOCAIS_CONFIG || {};
    const endpoints = config.endpoints || {};
    const els = {};

    function $(id) {
        return document.getElementById(id);
    }

    function formatNumber(value) {
        return new Intl.NumberFormat('pt-BR').format(value ?? 0);
    }

    function formatDateBr(isoDate) {
        if (!isoDate) return '-';
        const [year, month, day] = isoDate.split('-');
        return `${day}/${month}/${year}`;
    }

    async function fetchJson(url) {
        const response = await fetch(url, {
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin',
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || 'Falha ao carregar dados.');
        }
        return data;
    }

    function setLoading(active) {
        els.loadingOverlay.classList.toggle('active', active);
    }

    function showError(message) {
        els.alertBox.textContent = message;
        els.alertBox.hidden = false;
    }

    function hideError() {
        els.alertBox.hidden = true;
        els.alertBox.textContent = '';
    }

    function renderLocaisStatus(data) {
        const resumo = data.resumo || {};
        els.kpiLocaisNaoIniciados.textContent = formatNumber(resumo.nao_iniciados);
        els.kpiLocaisAndamento.textContent = formatNumber(resumo.em_andamento);
        els.kpiLocaisFinalizados.textContent = formatNumber(resumo.finalizados);

        const map = {
            nao_iniciado: els.listaLocaisNaoIniciados,
            em_andamento: els.listaLocaisAndamento,
            finalizado: els.listaLocaisFinalizados,
        };

        Object.entries(map).forEach(([status, container]) => {
            const items = (data.por_status && data.por_status[status]) || [];
            container.innerHTML = '';

            if (!items.length) {
                container.innerHTML = '<li class="dash-locais-empty">Nenhum local nesta categoria.</li>';
                return;
            }

            items.forEach((item) => {
                const li = document.createElement('li');
                const paInfo = item.pa
                    ? `<span class="dash-locais-pa">${item.pa}</span>`
                    : '<span class="dash-locais-pa dash-locais-pa-aviso">PA não vinculado</span>';
                li.innerHTML = `
                    <div class="dash-locais-item-top">
                        <strong>${item.nome_local}</strong>
                        ${paInfo}
                    </div>
                    <div class="dash-locais-item-meta">
                        <span>Prazo: ${formatDateBr(item.data_inicio)} – ${formatDateBr(item.data_fim)}</span>
                        <span>Horário: ${item.horario_inicio} – ${item.horario_fim}</span>
                        <span>Bipagens: ${formatNumber(item.total_bipagens)}</span>
                    </div>
                `;
                container.appendChild(li);
            });
        });
    }

    async function loadStatusLocais() {
        const data = await fetchJson(endpoints.statusLocais);
        renderLocaisStatus(data);
    }

    async function refreshDashboard() {
        hideError();
        setLoading(true);
        try {
            await loadStatusLocais();
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }

    function cacheElements() {
        els.loadingOverlay = $('dash-loading');
        els.alertBox = $('dash-alert');
        els.kpiLocaisNaoIniciados = $('kpi-locais-nao-iniciados');
        els.kpiLocaisAndamento = $('kpi-locais-andamento');
        els.kpiLocaisFinalizados = $('kpi-locais-finalizados');
        els.listaLocaisNaoIniciados = $('lista-locais-nao-iniciados');
        els.listaLocaisAndamento = $('lista-locais-andamento');
        els.listaLocaisFinalizados = $('lista-locais-finalizados');
        els.btnRefresh = $('btn-refresh');
    }

    document.addEventListener('DOMContentLoaded', () => {
        cacheElements();
        els.btnRefresh.addEventListener('click', refreshDashboard);
        refreshDashboard();
    });
})();
