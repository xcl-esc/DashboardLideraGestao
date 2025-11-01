function getChartData(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !canvas.dataset.config) {
        console.error(`Canvas com ID '${canvasId}' ou atributo data-config não encontrado ou vazio.`);
        return { labels: ['Erro'], data: [0], titulo: 'Dados não carregados' };
    }
    try {
        return JSON.parse(canvas.dataset.config);
    } catch (e) {
        console.error(`Erro ao fazer parse do JSON para o canvas ${canvasId}:`, e);
        return { labels: ['Erro'], data: [0], titulo: 'Erro de JSON' };
    }
}

document.addEventListener('DOMContentLoaded', () => {
    
    //GRÁFICO DE BARRAS
    const dadosBarra = getChartData('graficoBarra');
    const ctxBarra = document.getElementById('graficoBarra');

    if (ctxBarra && dadosBarra.data.length > 0) {
        new Chart(ctxBarra, {
            type: 'bar',
            data: {
                labels: dadosBarra.labels,
                datasets: [{
                    label: 'Processos',
                    data: dadosBarra.data,
                    backgroundColor: ['#667eea', '#764ba2', '#4ade80', '#f59e0b', '#06b6d4', '#ec4899']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: dadosBarra.titulo,
                        font: { size: 16 }
                    }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }

    // GRÁFICO DE LINHA
    const dadosLinha = getChartData('graficoLinha');
    const ctxLinha = document.getElementById('graficoLinha');

    if (ctxLinha && dadosLinha.data.length > 0) {
        new Chart(ctxLinha, {
            type: 'line',
            data: {
                labels: dadosLinha.labels,
                datasets: [{
                    label: dadosLinha.titulo,
                    data: dadosLinha.data,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'top' },
                    title: {
                        display: true,
                        text: dadosLinha.titulo,
                        font: { size: 16 }
                    }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }

    // GRÁFICO DE PIZZA
    const dadosPizza = getChartData('graficoPizza');
    const ctxPizza = document.getElementById('graficoPizza');

    const coresPizza = ['#10b981', '#ef4444', '#f59e0b', '#3b82f6']; 

    if (ctxPizza && dadosPizza.data.length > 0) {
        new Chart(ctxPizza, {
            type: 'pie',
            data: {
                labels: dadosPizza.labels,
                datasets: [{
                    data: dadosPizza.data,
                    backgroundColor: coresPizza.slice(0, dadosPizza.labels.length)
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                    title: {
                        display: true,
                        text: dadosPizza.titulo,
                        font: { size: 16 }
                    }
                }
            }
        });
    }
});