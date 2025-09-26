function setSpeed(id, targetValue, targetAngle) {
    const needle = document.getElementById(`needle-${id}`);
    const score = document.getElementById(`score-${id}`);
    
    if (!needle || !score) {
        console.error(`Elementos não encontrados para ID: ${id}`);
        return;
    }
    
    let currentValue = 0;
    const duration = 1500; // 1.5 segundos
    const steps = 60; // 60 frames
    const increment = targetValue / steps;
    const intervalTime = duration / steps;

    const interval = setInterval(() => {
        if (currentValue >= targetValue) {
            clearInterval(interval);
            // Garante o valor exato no final
            needle.style.transform = `rotate(${targetAngle}deg)`;
            score.textContent = `${Math.round(targetValue)}%`;
        } else {
            currentValue += increment;
            const currentAngle = (currentValue * 1.8) - 90;
            needle.style.transform = `rotate(${currentAngle}deg)`;
            score.textContent = `${Math.round(currentValue)}%`;
        }
    }, intervalTime);
}

// Função para inicializar todos os velocímetros
function initVelocimetros() {
    // Esta função será chamada por cada velocímetro individualmente
    console.log('Velocímetros inicializados');
}

document.addEventListener('DOMContentLoaded', function() {
    initVelocimetros();
});