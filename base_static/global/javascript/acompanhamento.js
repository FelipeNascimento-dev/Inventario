(function () {
    'use strict';

    const config = window.ACOMPANHAMENTO_CONFIG || {};
    const endpoints = config.endpoints || {};

    const state = {
        page: 1,
        limit: 50,
        pa: '',
        status: '',
        charts: {},
    };

    const els = {};

    function $(id) {
        return document.getElementById(id);
    }

    function formatNumber(value) {
        return new Intl.NumberFormat('pt-BR').format(value ?? 0);
    }

    function formatPercent(value) {
        return `${Number(value ?? 0).toFixed(1)}%`;
    }

    function statusClass(status) {
        const normalized = (status || '').toLowerCase();
        if (normalized === 'aberto') return 'dash-status-aberto';
        if (normalized === 'fechado') return 'dash-status-fechado';
        if (normalized.includes('aguardando')) return 'dash-status-aguardando';
        if (normalized === 'invalidado') return 'dash-status-invalidado';
        return 'dash-status-outro';
    }

    function buildQuery(params) {
        const search = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value !== '' && value !== null && value !== undefined) {
                search.set(key, value);
            }
        });
        const query = search.toString();
        return query ? `?${query}` : '';
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

    function renderKpis(resumo) {
        els.kpiTorres.textContent = formatNumber(resumo.total_torres);
        els.kpiLotes.textContent = formatNumber(resumo.total_lotes);
        els.kpiSeriais.textContent = formatNumber(resumo.total_seriais);
        els.kpiFechados.textContent = formatPercent(resumo.pct_fechados);
        els.kpiAbertos.textContent = formatPercent(resumo.pct_abertos);
        els.kpiInvalidados.textContent = formatPercent(resumo.pct_invalidados);
    }

    function aggregateStatusFromQuantidades(rows) {
        const totals = {};
        rows.forEach((row) => {
            const status = row.status_lote || 'Sem status';
            totals[status] = (totals[status] || 0) + (row.qtd || 0);
        });
        return totals;
    }

    function aggregatePaFromQuantidades(rows) {
        const totals = {};
        rows.forEach((row) => {
            const pa = row.PA || 'Sem PA';
            totals[pa] = (totals[pa] || 0) + (row.qtd || 0);
        });
        return totals;
    }

    function destroyChart(key) {
        if (state.charts[key]) {
            state.charts[key].destroy();
            delete state.charts[key];
        }
    }

    function renderStatusChart(quantidades) {
        destroyChart('status');
        const totals = aggregateStatusFromQuantidades(quantidades);
        const labels = Object.keys(totals);
        const values = Object.values(totals);

        state.charts.status = new Chart(els.chartStatus, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: ['#ffc107', '#c62828', '#ef5350', '#9b1c1c', '#ef9a9a'],
                    borderWidth: 2,
                    borderColor: '#fff',
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' },
                    tooltip: {
                        callbacks: {
                            label(context) {
                                const total = values.reduce((acc, item) => acc + item, 0);
                                const pct = total ? ((context.raw / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${formatNumber(context.raw)} (${pct}%)`;
                            },
                        },
                    },
                },
            },
        });
    }

    function renderPaChart(quantidades) {
        destroyChart('pa');
        const totals = aggregatePaFromQuantidades(quantidades);
        const sorted = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 15);
        const labels = sorted.map(([pa]) => pa);
        const values = sorted.map(([, qtd]) => qtd);

        state.charts.pa = new Chart(els.chartPa, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Lotes',
                    data: values,
                    backgroundColor: '#ef9a9a',
                    borderColor: '#c62828',
                    borderWidth: 1,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    x: {
                        ticks: {
                            callback(value) {
                                return formatNumber(value);
                            },
                        },
                    },
                },
            },
        });
    }

    function renderUsuarioChart(contagem) {
        destroyChart('usuario');
        const sorted = [...contagem].sort((a, b) => b.total_seriais - a.total_seriais).slice(0, 12);
        const labels = sorted.map((item) => item.username);
        const values = sorted.map((item) => item.total_seriais);

        state.charts.usuario = new Chart(els.chartUsuario, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Seriais bipados',
                    data: values,
                    backgroundColor: '#c62828',
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        ticks: {
                            callback(value) {
                                return formatNumber(value);
                            },
                        },
                    },
                },
            },
        });
    }

    function renderStackedPaStatusChart(quantidades) {
        destroyChart('stacked');
        const paSet = new Set();
        const statusSet = new Set();
        const matrix = {};

        quantidades.forEach((row) => {
            const pa = row.PA || 'Sem PA';
            const status = row.status_lote || 'Sem status';
            paSet.add(pa);
            statusSet.add(status);
            matrix[`${pa}||${status}`] = row.qtd || 0;
        });

        const pas = [...paSet].sort();
        const statuses = [...statusSet].sort();
        const colors = {
            aberto: '#ffc107',
            fechado: '#c62828',
            invalidado: '#9b1c1c',
            'aguardando validação': '#ef5350',
        };

        const datasets = statuses.map((status) => ({
            label: status,
            data: pas.map((pa) => matrix[`${pa}||${status}`] || 0),
            backgroundColor: colors[status] || '#6c757d',
        }));

        state.charts.stacked = new Chart(els.chartStacked, {
            type: 'bar',
            data: { labels: pas, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { stacked: true },
                    y: {
                        stacked: true,
                        ticks: {
                            callback(value) {
                                return formatNumber(value);
                            },
                        },
                    },
                },
            },
        });
    }

    function renderTable(data) {
        const { items = [], page, limit, total, total_pages: totalPages } = data;
        els.tableBody.innerHTML = '';

        if (!items.length) {
            els.tableBody.innerHTML = '<tr><td colspan="4" class="dash-empty">Nenhum lote encontrado.</td></tr>';
        } else {
            items.forEach((item) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${item.id}</td>
                    <td><span class="dash-status-badge ${statusClass(item.status)}">${item.status || '-'}</span></td>
                    <td>${item.group_user || '-'}</td>
                    <td>${item.username || '-'}</td>
                `;
                els.tableBody.appendChild(row);
            });
        }

        const start = total ? (page - 1) * limit + 1 : 0;
        const end = Math.min(page * limit, total);
        els.tableMeta.textContent = `Exibindo ${formatNumber(start)}–${formatNumber(end)} de ${formatNumber(total)} registros`;
        els.pageInput.value = page;
        els.pageInput.max = totalPages || 1;
        els.pageTotal.textContent = formatNumber(totalPages || 1);
        els.btnPrev.disabled = page <= 1;
        els.btnNext.disabled = page >= (totalPages || 1);
        state.page = page;
        state.limit = limit;
    }

    async function loadResumo() {
        const query = buildQuery({ pa: state.pa });
        const resumo = await fetchJson(`${endpoints.resumo}${query}`);
        renderKpis(resumo);
    }

    function filterQuantidadesByPa(rows) {
        if (!state.pa) {
            return rows;
        }
        return rows.filter((row) => row.PA === state.pa);
    }

    async function loadCharts() {
        const [quantidades, contagem] = await Promise.all([
            fetchJson(endpoints.quantidades),
            fetchJson(endpoints.contagemUsuario),
        ]);
        const filtered = filterQuantidadesByPa(quantidades);
        renderStatusChart(filtered);
        renderPaChart(filtered);
        renderStackedPaStatusChart(filtered);
        renderUsuarioChart(contagem);
    }

    async function loadTable() {
        const query = buildQuery({
            page: state.page,
            limit: state.limit,
            pa: state.pa,
            status: state.status,
        });
        const data = await fetchJson(`${endpoints.lotes}${query}`);
        renderTable(data);
    }

    async function refreshDashboard() {
        hideError();
        setLoading(true);
        try {
            await Promise.all([loadResumo(), loadCharts(), loadTable()]);
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }

    function bindEvents() {
        els.btnRefresh.addEventListener('click', refreshDashboard);

        els.filterPa.addEventListener('change', () => {
            state.pa = els.filterPa.value;
            state.page = 1;
            refreshDashboard();
        });

        els.filterStatus.addEventListener('change', () => {
            state.status = els.filterStatus.value;
            state.page = 1;
            refreshDashboard();
        });

        els.filterLimit.addEventListener('change', () => {
            state.limit = parseInt(els.filterLimit.value, 10);
            state.page = 1;
            loadTable().catch((error) => showError(error.message));
        });

        els.btnPrev.addEventListener('click', () => {
            if (state.page > 1) {
                state.page -= 1;
                loadTable().catch((error) => showError(error.message));
            }
        });

        els.btnNext.addEventListener('click', () => {
            state.page += 1;
            loadTable().catch((error) => showError(error.message));
        });

        els.pageInput.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter') {
                return;
            }
            const target = parseInt(els.pageInput.value, 10);
            const maxPage = parseInt(els.pageInput.max, 10) || 1;
            if (target >= 1 && target <= maxPage) {
                state.page = target;
                loadTable().catch((error) => showError(error.message));
            }
        });
    }

    function cacheElements() {
        els.loadingOverlay = $('dash-loading');
        els.alertBox = $('dash-alert');
        els.kpiTorres = $('kpi-torres');
        els.kpiLotes = $('kpi-lotes');
        els.kpiSeriais = $('kpi-seriais');
        els.kpiFechados = $('kpi-fechados');
        els.kpiAbertos = $('kpi-abertos');
        els.kpiInvalidados = $('kpi-invalidados');
        els.chartStatus = $('chart-status');
        els.chartPa = $('chart-pa');
        els.chartStacked = $('chart-stacked');
        els.chartUsuario = $('chart-usuario');
        els.tableBody = $('dash-table-body');
        els.tableMeta = $('dash-table-meta');
        els.pageInput = $('dash-page-input');
        els.pageTotal = $('dash-page-total');
        els.btnPrev = $('dash-btn-prev');
        els.btnNext = $('dash-btn-next');
        els.filterPa = $('filter-pa');
        els.filterStatus = $('filter-status');
        els.filterLimit = $('filter-limit');
        els.btnRefresh = $('btn-refresh');
    }

    document.addEventListener('DOMContentLoaded', () => {
        cacheElements();
        bindEvents();
        refreshDashboard();
    });
})();
