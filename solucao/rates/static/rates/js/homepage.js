(() => {
    const ratesDataScript = document.getElementById('rates-data');
    const ratesData = ratesDataScript ? JSON.parse(ratesDataScript.textContent) : [];
    let chartInstance = null;
    let chartRendered = false;

    function switchTab(event, tabId) {
        const tabs = document.querySelectorAll('.tab');
        const tabContents = document.querySelectorAll('.tab-content');

        tabs.forEach(tab => tab.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));

        event.currentTarget.classList.add('active');
        document.getElementById(tabId).classList.add('active');

        if (tabId === 'chart-tab' && !chartRendered) {
            renderChart();
        }
    }

    function renderChart() {
        if (!ratesData.length) {
            return;
        }

        const canvas = document.getElementById('ratesChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        const diasCorridos = ratesData.map(rate => rate.dias_corridos);
        const diPre252 = ratesData.map(rate => rate.di_pre_252);
        const diPre360 = ratesData.map(rate => rate.di_pre_360);

        const chartConfig = {
            type: 'line',
            data: {
                labels: diasCorridos,
                datasets: [
                    {
                        label: 'DI x PRÉ 252',
                        data: diPre252,
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        borderWidth: 3,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        pointBackgroundColor: '#667eea',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        tension: 0.4,
                        fill: true
                    },
                    {
                        label: 'DI x PRÉ 360',
                        data: diPre360,
                        borderColor: '#764ba2',
                        backgroundColor: 'rgba(118, 75, 162, 0.1)',
                        borderWidth: 3,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        pointBackgroundColor: '#764ba2',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        tension: 0.4,
                        fill: true
                    }
                ]
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
                                return 'Dias Corridos: ' + context[0].label;
                            },
                            label: function (context) {
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(2) + '%';
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
                            text: 'Dias Corridos',
                            font: {
                                size: 14,
                                weight: '600'
                            },
                            color: '#333'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            font: {
                                size: 12
                            },
                            color: '#666'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Taxa de Juros (%)',
                            font: {
                                size: 14,
                                weight: '600'
                            },
                            color: '#333'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            font: {
                                size: 12
                            },
                            color: '#666',
                            callback: function (value) {
                                return value.toFixed(2) + '%';
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

        chartInstance = new Chart(ctx, chartConfig);
        chartRendered = true;
    }

    function resetZoom() {
        if (chartInstance) {
            chartInstance.resetZoom();
        }
    }

    window.switchTab = switchTab;
    window.resetZoom = resetZoom;
})();
