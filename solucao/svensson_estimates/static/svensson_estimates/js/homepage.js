(() => {
    let myChart = null;
    let selectedAttemptId = null;
    let editingAttemptId = null;
    let attemptsData = [];
    let xAxisMode = 'corridos'; // 'corridos' | 'uteis'
    let lastSvenssonData = null;

    const pageDataEl = document.getElementById('svensson-page-data');
    const currentDate = pageDataEl?.dataset.selectedDate || null;
    const ratesDataScript = document.getElementById('svensson-rates-data');
    const baseRatesData = ratesDataScript ? JSON.parse(ratesDataScript.textContent) : [];

    function renderMathInTooltips(root = document) {
        if (!window.renderMathInElement) {
            return;
        }
        const tooltipNodes = root.querySelectorAll('.tooltip');
        tooltipNodes.forEach(node => {
            window.renderMathInElement(node, {
                delimiters: [
                    { left: '\\[', right: '\\]', display: true },
                    { left: '\\(', right: '\\)', display: false },
                    { left: '$$', right: '$$', display: true }
                ],
                throwOnError: false
            });
        });
    }

    window.addEventListener('load', () => renderMathInTooltips());

    function toggleImproveButton() {
        const improveDropdown = document.getElementById('improveDropdown');
        const dropdownMenu = document.getElementById('improveDropdownMenu');
        if (!improveDropdown) return;
        const shouldShow = Boolean(selectedAttemptId);
        improveDropdown.style.display = shouldShow ? 'inline-block' : 'none';
        if (!shouldShow && dropdownMenu) {
            dropdownMenu.style.display = 'none';
        }
    }

    function setImproveButtonLoading(isLoading) {
        const improveBtn = document.getElementById('improveButton');
        const dropdownMenu = document.getElementById('improveDropdownMenu');
        if (!improveBtn) return;
        improveBtn.disabled = isLoading;
        improveBtn.textContent = isLoading ? 'Melhorando...' : '🚀 Melhorar estimativa';
        if (isLoading && dropdownMenu) {
            dropdownMenu.style.display = 'none';
        }
    }

    function toggleImproveDropdown() {
        const dropdownMenu = document.getElementById('improveDropdownMenu');
        if (!dropdownMenu) return;
        dropdownMenu.style.display = dropdownMenu.style.display === 'block' ? 'none' : 'block';
    }

    function selectImproveStrategy(strategy) {
        const dropdownMenu = document.getElementById('improveDropdownMenu');
        if (dropdownMenu) {
            dropdownMenu.style.display = 'none';
        }
        improveSelectedAttempt(strategy);
    }

    document.addEventListener('click', (event) => {
        const dropdown = document.getElementById('improveDropdown');
        const dropdownMenu = document.getElementById('improveDropdownMenu');
        if (!dropdown || !dropdownMenu) return;
        if (!dropdown.contains(event.target)) {
            dropdownMenu.style.display = 'none';
        }
    });

    function renderChart(svenssonData = null) {
        if (svenssonData !== null) {
            lastSvenssonData = svenssonData;
        } else if (lastSvenssonData) {
            svenssonData = lastSvenssonData;
        }

        const canvas = document.getElementById('ratesChart');
        if (!canvas || !baseRatesData.length) {
            return;
        }

        const ctx = canvas.getContext('2d');
        const isDiasUteis = xAxisMode === 'uteis';
        const xLabel = isDiasUteis ? 'Dias Úteis' : 'Dias Corridos';

        const diPre252Data = baseRatesData.map(point => ({
            x: isDiasUteis ? point.dias_uteis : point.dias_corridos,
            y: point.di_pre_252,
            dias_corridos: point.dias_corridos,
            dias_uteis: point.dias_uteis
        }));

        const datasets = [
            {
                label: 'DI x PRÉ 252',
                data: diPre252Data,
                borderColor: '#667eea',
                backgroundColor: '#667eea',
                borderWidth: 0,
                pointRadius: 5,
                pointHoverRadius: 7,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                tension: 0,
                fill: false,
                showLine: false
            }
        ];

        if (svenssonData && svenssonData.curve) {
            const curveLabel = svenssonData.params_type === 'final'
                ? 'Curva Svensson (Parâmetros Finais)'
                : 'Curva Svensson (Parâmetros Iniciais)';
            const curveColor = svenssonData.params_type === 'final' ? '#28a745' : '#ffc107';
            const curvePoints = (svenssonData.curve || [])
                .map(point => ({
                    x: isDiasUteis ? point.dias_uteis : point.dias_corridos,
                    y: point.taxa * 100.0
                }))
                .sort((a, b) => a.x - b.x);

            const getCurveY = (xValue) => {
                if (!curvePoints.length) return null;
                if (xValue <= curvePoints[0].x) return curvePoints[0].y;
                if (xValue >= curvePoints[curvePoints.length - 1].x) return curvePoints[curvePoints.length - 1].y;

                for (let i = 1; i < curvePoints.length; i++) {
                    const prev = curvePoints[i - 1];
                    const curr = curvePoints[i];
                    if (xValue === curr.x) return curr.y;
                    if (xValue < curr.x) {
                        const ratio = (xValue - prev.x) / (curr.x - prev.x);
                        return prev.y + ratio * (curr.y - prev.y);
                    }
                }
                return null;
            };

            datasets.push({
                label: curveLabel,
                data: curvePoints,
                borderColor: curveColor,
                backgroundColor: 'transparent',
                borderWidth: 3,
                pointRadius: 0,
                pointHoverRadius: 4,
                tension: 0,
                fill: false,
                showLine: true
            });

            const residualData = diPre252Data
                .map(point => {
                    const svenssonValue = getCurveY(point.x);
                    if (svenssonValue === null || svenssonValue === undefined) return null;
                    return {
                        x: point.x,
                        y: point.y - svenssonValue
                    };
                })
                .filter(point => point !== null);

            const residualWeightedData = diPre252Data
                .map(point => {
                    const svenssonValue = getCurveY(point.x);
                    if (svenssonValue === null || svenssonValue === undefined) return null;
                    if (!point.dias_corridos) return null;
                    const diFactor = Math.pow(1 + point.y / 100, point.dias_uteis / 252);
                    const svenssonFactor = Math.pow(1 + svenssonValue / 100, point.dias_uteis / 252);
                    const diff = (1 / diFactor) - svenssonFactor;
                    const weightedResidual = Math.sqrt((1 / point.dias_corridos) * Math.pow(diff, 2));
                    return {
                        x: point.x,
                        y: weightedResidual
                    };
                })
                .filter(point => point !== null);

            datasets.push({
                label: 'Resíduo',
                data: residualData,
                type: 'bar',
                yAxisID: 'y1',
                backgroundColor: 'rgba(255, 99, 132, 0.35)',
                borderColor: '#ff6384',
                borderWidth: 1,
                borderSkipped: false,
                parsing: false
            });

            datasets.push({
                label: 'Resíduo ponderado (1/duration)',
                data: residualWeightedData,
                type: 'bar',
                yAxisID: 'y1',
                backgroundColor: 'rgba(54, 162, 235, 0.35)',
                borderColor: '#36a2eb',
                borderWidth: 1,
                borderSkipped: false,
                parsing: false
            });
        }

        const chartConfig = {
            type: 'scatter',
            data: {
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            font: {
                                size: 14,
                                weight: '600'
                            },
                            padding: 20,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        padding: 12,
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        },
                        borderColor: 'rgba(255, 255, 255, 0.2)',
                        borderWidth: 1,
                        callbacks: {
                            title: function (context) {
                                return xLabel + ': ' + context[0].parsed.x;
                            },
                            label: function (context) {
                                const value = context.parsed.y;
                                const suffix = context.dataset.yAxisID === 'y1' ? ' %' : '%';
                                return context.dataset.label + ': ' + value.toFixed(2) + suffix;
                            }
                        }
                    },
                    zoom: {
                        zoom: {
                            drag: {
                                enabled: true,
                                backgroundColor: 'rgba(102, 126, 234, 0.2)',
                                borderColor: '#667eea',
                                borderWidth: 2
                            },
                            wheel: {
                                enabled: true,
                                speed: 0.1
                            },
                            pinch: {
                                enabled: true
                            },
                            mode: 'xy'
                        },
                        pan: {
                            enabled: true,
                            mode: 'xy',
                            modifierKey: 'ctrl'
                        },
                        limits: {
                            x: { min: 'original', max: 'original' },
                            y: { min: 'original', max: 'original' }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: xLabel,
                            font: {
                                size: 14,
                                weight: 'bold'
                            },
                            padding: 10
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            font: {
                                size: 12
                            }
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Taxa (%)',
                            font: {
                                size: 14,
                                weight: 'bold'
                            },
                            padding: 10
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        },
                        ticks: {
                            font: {
                                size: 12
                            },
                            callback: function (value) {
                                return value.toFixed(2) + '%';
                            }
                        }
                    },
                    y1: {
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Resíduo (%)',
                            font: {
                                size: 14,
                                weight: 'bold'
                            },
                            padding: 10
                        },
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            font: {
                                size: 12
                            },
                            callback: function (value) {
                                return value.toFixed(2) + ' %';
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        };

        myChart = new Chart(ctx, chartConfig);
    }

    function resetZoom() {
        if (myChart) {
            myChart.resetZoom();
        }
    }

    function updateXAxisToggleButton() {
        const toggleBtn = document.getElementById('toggleXAxisButton');
        if (!toggleBtn) return;
        toggleBtn.textContent = xAxisMode === 'uteis' ? 'Eixo X: Dias Úteis' : 'Eixo X: Dias Corridos';
    }

    function toggleXAxis() {
        xAxisMode = xAxisMode === 'corridos' ? 'uteis' : 'corridos';
        updateXAxisToggleButton();
        if (myChart) {
            myChart.destroy();
        }
        renderChart();
    }

    async function loadAttempts() {
        if (!currentDate) return;

        try {
            const response = await fetch(`/svensson/api/attempts/?date=${currentDate}`);
            const data = await response.json();

            attemptsData = data.attempts || [];
            const listContainer = document.getElementById('attemptsList');

            if (data.attempts && data.attempts.length > 0) {
                listContainer.innerHTML = data.attempts.map(attempt => {
                    const hasFinal = [
                        attempt.beta0_final,
                        attempt.beta1_final,
                        attempt.beta2_final,
                        attempt.beta3_final,
                        attempt.lambda1_final,
                        attempt.lambda2_final
                    ].every(value => value !== null && value !== undefined);
                    const statusClass = hasFinal ? 'status-final' : 'status-initial';
                    const statusText = hasFinal ? 'Final' : 'Inicial';
                    const isSelected = selectedAttemptId === attempt.id;

                    return `
                        <div class="attempt-item ${isSelected ? 'selected' : ''}" onclick="selectAttempt(${attempt.id})">
                            <div class="attempt-info">
                                <div>
                                    <span class="attempt-status ${statusClass}">${statusText}</span>
                                    ${new Date(attempt.created_at).toLocaleString('pt-BR')}
                                </div>
                                <div class="attempt-params">
                                    β0=${(hasFinal ? attempt.beta0_final : attempt.beta0_initial).toFixed(4)}, β1=${(hasFinal ? attempt.beta1_final : attempt.beta1_initial).toFixed(4)}, β2=${(hasFinal ? attempt.beta2_final : attempt.beta2_initial).toFixed(4)}, β3=${(hasFinal ? attempt.beta3_final : attempt.beta3_initial).toFixed(4)}, 
                                    λ1=${(hasFinal ? attempt.lambda1_final : attempt.lambda1_initial).toFixed(4)}, λ2=${(hasFinal ? attempt.lambda2_final : attempt.lambda2_initial).toFixed(4)}
                                </div>
                                ${attempt.observation ? `<div class="attempt-params">${attempt.observation}</div>` : ''}
                            </div>
                            <div class="attempt-actions">
                                <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); editAttempt(${attempt.id})">✏️ Editar</button>
                                <button class="btn btn-danger btn-sm" onclick="event.stopPropagation(); deleteAttempt(${attempt.id})">🗑️ Excluir</button>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                listContainer.innerHTML = '<div class="no-attempts">Nenhuma tentativa cadastrada para esta data.</div>';
            }

            toggleImproveButton();
        } catch (error) {
            console.error('Error loading attempts:', error);
            document.getElementById('attemptsList').innerHTML = '<div class="no-attempts">Erro ao carregar tentativas.</div>';
        }
    }

    function updateErrorMetrics(attemptId) {
        const metricsContainer = document.getElementById('errorMetricsContent');

        if (!attemptId) {
            metricsContainer.innerHTML = '<div class="no-metrics">Nenhuma tentativa selecionada</div>';
            return;
        }

        const attempt = attemptsData.find(a => a.id === attemptId);

        if (!attempt) {
            metricsContainer.innerHTML = '<div class="no-metrics">Erro ao carregar métricas</div>';
            return;
        }

        const rmse = attempt.rmse_final !== null ? attempt.rmse_final : attempt.rmse_initial;
        const rmseType = attempt.rmse_final !== null ? 'Final' : 'Inicial';

        const mae = attempt.mae_final !== null ? attempt.mae_final : attempt.mae_initial;
        const maeType = attempt.mae_final !== null ? 'Final' : 'Inicial';

        const r2 = attempt.r2_final !== null ? attempt.r2_final : attempt.r2_initial;
        const r2Type = attempt.r2_final !== null ? 'Final' : 'Inicial';

        const objFunc = attempt.objective_function_final !== null ? attempt.objective_function_final : attempt.objective_function_initial;
        const objFuncType = attempt.objective_function_final !== null ? 'Final' : 'Inicial';

        if (rmse === null && mae === null && r2 === null && objFunc === null) {
            metricsContainer.innerHTML = '<div class="no-metrics">Métricas não disponíveis</div>';
            return;
        }

        const rmseFormatted = rmse !== null ? (rmse < 0.0001 ? rmse.toExponential(4) : rmse.toFixed(6)) : 'N/A';
        const maeFormatted = mae !== null ? (mae < 0.0001 ? mae.toExponential(4) : mae.toFixed(6)) : 'N/A';
        const r2Formatted = r2 !== null ? r2.toFixed(6) : 'N/A';
        const objFuncFormatted = objFunc !== null ? (objFunc < 0.0001 ? objFunc.toExponential(4) : objFunc.toFixed(6)) : 'N/A';

        metricsContainer.innerHTML = `
            <div class="error-metrics-content">
                <div class="error-metric-item">
                    <div class="error-metric-label">
                        RMSE (${rmseType})
                        <span class="tooltip">\\[ \\text{RMSE} = \\sqrt{\\frac{1}{n} \\sum_{i=1}^{n} e_i^2} \\]</span>
                    </div>
                    <div class="error-metric-value">${rmseFormatted}</div>
                </div>
                <div class="error-metric-item">
                    <div class="error-metric-label">
                        MAE (${maeType})
                        <span class="tooltip">\\[ \\text{MAE} = \\frac{1}{n} \\sum_{i=1}^{n} \\lvert e_i \\rvert \\]</span>
                    </div>
                    <div class="error-metric-value">${maeFormatted}</div>
                </div>
                <div class="error-metric-item">
                    <div class="error-metric-label">
                        R² (${r2Type})
                        <span class="tooltip">\\[ R^2 = 1 - \\frac{SS_{\\text{res}}}{SS_{\\text{tot}}} \\]</span>
                    </div>
                    <div class="error-metric-value">${r2Formatted}</div>
                </div>
                <div class="error-metric-item">
                    <div class="error-metric-label">
                        Objective Function (${objFuncType})
                        <span class="tooltip">\\[ \\text{Obj} = \\sum_{i=1}^{n} \\frac{1}{d_i} \\, e_i^2 \\]</span>
                    </div>
                    <div class="error-metric-value">${objFuncFormatted}</div>
                </div>
            </div>
        `;

        renderMathInTooltips(metricsContainer);
    }

    async function selectAttempt(attemptId) {
        selectedAttemptId = attemptId;
        await loadAttempts();
        toggleImproveButton();
        updateErrorMetrics(attemptId);

        try {
            const response = await fetch(`/svensson/api/attempts/${attemptId}/curve/`);
            const data = await response.json();

            if (myChart) {
                myChart.destroy();
            }
            renderChart(data);
        } catch (error) {
            console.error('Error loading Svensson curve:', error);
            alert('Erro ao carregar a curva Svensson.');
        }
    }

    function openCreateModal() {
        editingAttemptId = null;
        const title = document.getElementById('modalTitle');
        const form = document.getElementById('attemptForm');
        const modal = document.getElementById('attemptModal');
        if (title) title.textContent = 'Nova Tentativa Linear';
        if (form) form.reset();
        if (modal) modal.classList.add('show');
    }

    async function editAttempt(attemptId) {
        editingAttemptId = attemptId;

        try {
            const response = await fetch(`/svensson/api/attempts/?date=${currentDate}`);
            const data = await response.json();
            const attempt = data.attempts.find(a => a.id === attemptId);

            if (attempt) {
                const form = document.getElementById('attemptForm');
                const modal = document.getElementById('attemptModal');
                const title = document.getElementById('modalTitle');
                if (title) title.textContent = 'Editar Tentativa Linear';
                if (form) {
                    form.beta0_initial.value = attempt.beta0_initial;
                    form.beta1_initial.value = attempt.beta1_initial;
                    form.beta2_initial.value = attempt.beta2_initial;
                    form.beta3_initial.value = attempt.beta3_initial;
                    form.lambda1_initial.value = attempt.lambda1_initial;
                    form.lambda2_initial.value = attempt.lambda2_initial;
                    form.observation.value = attempt.observation || '';
                }
                if (modal) modal.classList.add('show');
            }
        } catch (error) {
            console.error('Error loading attempt for editing:', error);
            alert('Erro ao carregar tentativa para edição.');
        }
    }

    async function deleteAttempt(attemptId) {
        if (!confirm('Tem certeza que deseja excluir esta tentativa?')) {
            return;
        }

        try {
            const response = await fetch(`/svensson/api/attempts/${attemptId}/delete/`, {
                method: 'DELETE'
            });

            if (response.ok) {
                if (selectedAttemptId === attemptId) {
                    selectedAttemptId = null;
                    if (myChart) {
                        myChart.destroy();
                    }
                    renderChart();
                    updateErrorMetrics(null);
                    toggleImproveButton();
                }
                await loadAttempts();
            } else {
                alert('Erro ao excluir tentativa.');
            }
        } catch (error) {
            console.error('Error deleting attempt:', error);
            alert('Erro ao excluir tentativa.');
        }
    }

    async function improveSelectedAttempt(strategy = 'local_search') {
        if (!selectedAttemptId) {
            return;
        }

        setImproveButtonLoading(true);
        try {
            const response = await fetch(`/svensson/api/attempts/${selectedAttemptId}/improve/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ strategy })
            });

            const data = await response.json();

            if (response.ok || response.status === 202) {
                await selectAttempt(selectedAttemptId);
                if (!data.improved) {
                    alert('Nenhuma melhora encontrada com a estratégia atual.');
                } else {
                    alert(`Tentativa melhorada com sucesso! ${data.strategy} - ${data.iterations} iterações`);
                }
            } else {
                alert('Erro ao melhorar tentativa: ' + (data.error || 'Erro desconhecido'));
            }
        } catch (error) {
            console.error('Error improving attempt:', error);
            alert('Erro ao melhorar tentativa.');
        } finally {
            setImproveButtonLoading(false);
        }
    }

    function closeModal() {
        const modal = document.getElementById('attemptModal');
        if (modal) {
            modal.classList.remove('show');
        }
        editingAttemptId = null;
    }

    const attemptForm = document.getElementById('attemptForm');
    if (attemptForm) {
        attemptForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const formData = new FormData(e.target);
            const payload = {
                date: currentDate,
                beta0_initial: parseFloat(formData.get('beta0_initial')),
                beta1_initial: parseFloat(formData.get('beta1_initial')),
                beta2_initial: parseFloat(formData.get('beta2_initial')),
                beta3_initial: parseFloat(formData.get('beta3_initial')),
                lambda1_initial: parseFloat(formData.get('lambda1_initial')),
                lambda2_initial: parseFloat(formData.get('lambda2_initial')),
                observation: formData.get('observation') || ''
            };

            try {
                let response;
                if (editingAttemptId) {
                    response = await fetch(`/svensson/api/attempts/${editingAttemptId}/update/`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });
                } else {
                    response = await fetch('/svensson/api/attempts/create/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(payload)
                    });
                }

                if (response.ok) {
                    closeModal();
                    await loadAttempts();

                    if (editingAttemptId && editingAttemptId === selectedAttemptId) {
                        await selectAttempt(editingAttemptId);
                    }
                } else {
                    const error = await response.json();
                    alert('Erro ao salvar tentativa: ' + (error.error || 'Erro desconhecido'));
                }
            } catch (error) {
                console.error('Error saving attempt:', error);
                alert('Erro ao salvar tentativa.');
            }
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        updateXAxisToggleButton();
        renderChart();
        renderMathInTooltips();
        if (currentDate) {
            loadAttempts();
        }
    });

    window.toggleImproveDropdown = toggleImproveDropdown;
    window.selectImproveStrategy = selectImproveStrategy;
    window.toggleXAxis = toggleXAxis;
    window.resetZoom = resetZoom;
    window.selectAttempt = selectAttempt;
    window.openCreateModal = openCreateModal;
    window.editAttempt = editAttempt;
    window.deleteAttempt = deleteAttempt;
    window.improveSelectedAttempt = improveSelectedAttempt;
    window.closeModal = closeModal;
})(); 
