pra iniciar (powershell):

.\venv\Scripts\activate.ps1

cd (aqui vc cola o path da pasta LideraGestao que estará dentro da pasta DJANGO_EXTRATOR)

python manage.py runserver

email="teste@teste.com" ou testegestor@email.com

senha("123456")  testegestor123

caso a senha e email nao funcionem:

python manage.py makemigrations

python manage.py migrate

python manage.py runserver

se ainda assim, nao funcionar:
del db.sqlite3

python manage.py migrate

python manage.py shell

Digite isso no terminal apos aparecer >>> :

from usuarios.models import Usuario
u = Usuario(nome="OutroTeste", email="Outro@teste.com")
u.set_senha("123456")
u.save()

exit()

agora: python manage.py runserver

problemas com bibliotecas se o dowload der problema com cache
pip install --no-cache-dir nome da biblioteca
ou pip install -r requirements.txt
ou pip install --no-cache-dir -r requirements.txt

ctrl 0 reset de zoom

problemas de carregamento pode ser cache ctrl f5 ou ctrl shft requirements


