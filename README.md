# LideraGestao

Sistema Django para gerenciamento de um dashboard para o desempenho de técnicos:

## 🛠 Tecnologias e Dependências

- Python 3.x  
- Django 5.x  
- Bibliotecas principais: `django-extensions`, `django-apscheduler`, `pandas`, `plotly`, `selenium`, `requests`, `python-dotenv`  
- Front-end: HTML, CSS, JavaScript  
- Containers: Docker


## Como rodar o projeto

1. Clone o repositório:
```bash
git clone https://github.com/xcl-esc/DashboardLideraGestao.git

Todas as dependências estão listadas no arquivo [`requirements.txt`](requirements.txt) e podem ser instaladas com:
pip install -r requirements.txt

cd DashboardLideraGestao

Conta de teste

Ao criar uma conta use o codigo "123GESTOR" para ter acesso a todas as ab abas.


## Observações

O arquivo .env não está no repositório, configure suas variáveis de ambiente locais.

O banco de dados usado é SQLite por padrão, mas pode ser configurado para PostgreSQL.

Certifique-se de ter o Docker rodando caso queira que ele atualize as tabelas.