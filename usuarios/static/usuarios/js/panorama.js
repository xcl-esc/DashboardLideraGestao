// Função auxiliar para obter e parsear os dados do canvas
function getChartData(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !canvas.dataset.config) {
        // Se a tag canvas ou os dados não existirem (erro na view ou HTML)
        console.error(`Canvas com ID '${canvasId}' ou atributo data-config não encontrado ou vazio.`);
        return { labels: ['Erro'], data: [0], titulo: 'Dados não carregados' };
    }
    // O atributo dataset.config contém a string JSON gerada pelo Django
    try {
        return JSON.parse(canvas.dataset.config);
    } catch (e) {
        console.error(`Erro ao fazer parse do JSON para o canvas ${canvasId}:`, e);
        return { labels: ['Erro'], data: [0], titulo: 'Erro de JSON' };
    }
}

// Garante que o script só rode após o DOM estar pronto
document.addEventListener('DOMContentLoaded', () => {

    // ==========================
    // GRÁFICO DE BARRAS
    // ==========================
    const dadosBarra = getChartData('graficoBarra');
    const ctxBarra = document.getElementById('graficoBarra');

    if (ctxBarra && dadosBarra.data.length > 0) {
        new Chart(ctxBarra, {
            type: 'bar',
            data: {
                labels: dadosBarra.labels, // Dados dinâmicos do Django
                datasets: [{
                    label: 'Processos',
                    data: dadosBarra.data, // Dados dinâmicos do Django
                    backgroundColor: ['#667eea', '#764ba2', '#4ade80', '#f59e0b', '#06b6d4', '#ec4899']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: dadosBarra.titulo, // Título dinâmico do Django
                        font: { size: 16 }
                    }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }


    // ==========================
    // GRÁFICO DE LINHA
    // ==========================
    const dadosLinha = getChartData('graficoLinha');
    const ctxLinha = document.getElementById('graficoLinha');

    if (ctxLinha && dadosLinha.data.length > 0) {
        new Chart(ctxLinha, {
            type: 'line',
            data: {
                labels: dadosLinha.labels, // Dados dinâmicos do Django
                datasets: [{
                    label: dadosLinha.titulo,
                    data: dadosLinha.data, // Dados dinâmicos do Django
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
                        text: dadosLinha.titulo, // Título dinâmico do Django
                        font: { size: 16 }
                    }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }

    // ==========================
    // GRÁFICO DE PIZZA
    // ==========================
    const dadosPizza = getChartData('graficoPizza');
    const ctxPizza = document.getElementById('graficoPizza');
    
    // Cores para o gráfico de pizza
    const coresPizza = ['#10b981', '#ef4444', '#f59e0b', '#3b82f6']; 

    if (ctxPizza && dadosPizza.data.length > 0) {
        new Chart(ctxPizza, {
            type: 'pie',
            data: {
                labels: dadosPizza.labels, // Dados dinâmicos do Django
                datasets: [{
                    data: dadosPizza.data, // Dados dinâmicos do Django
                    backgroundColor: coresPizza.slice(0, dadosPizza.labels.length)
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' },
                    title: {
                        display: true,
                        text: dadosPizza.titulo, // Título dinâmico do Django
                        font: { size: 16 }
                    }
                }
            }
        });
    }
});