document.addEventListener("DOMContentLoaded", () => {
    const climaEl = document.getElementById("clima");
    const cidade = climaEl.dataset.cidade;
    const apiKey = climaEl.dataset.apikey;
    const unidade = "metric";

    fetch(`https://api.openweathermap.org/data/2.5/weather?q=Brasília,BR&units=metric&lang=pt_br&appid=36dc18cce9c97e6f5c4d7477fb14c07c`)
        .then(response => response.json())
        .then(data => {
            document.getElementById("cidade").innerText = data.name;
            document.getElementById("temperatura").innerText = Math.round(data.main.temp);
            document.getElementById("descricao").innerText = data.weather[0].description;

            const icone = data.weather[0].icon;
            document.getElementById("icone-clima").src = `https://openweathermap.org/img/wn/${icone}@2x.png`;
        })
        .catch(err => console.error("Erro ao buscar clima:", err));
});