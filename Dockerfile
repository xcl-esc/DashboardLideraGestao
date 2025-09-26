FROM python:3.10-slim
WORKDIR /django_extrator/LideraGestao
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000

# Comando para rodar o servidor Django (pode ser modificado)
# Este é o comando padrão, mas o docker-compose.yml vai substituí-lo
# por um comando mais específico.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]