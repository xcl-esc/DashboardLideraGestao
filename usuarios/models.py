from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password


class Usuario(models.Model):
    NIVEL_CHOICES = [
        ("admin", "Administrador"),
        ("gestor", "Gestor"),
        ("tecnico", "Técnico"),
        ("dev", "Desenvolvedor"),
    ]

    nome = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, default="gestor")
    senha = models.CharField(max_length=128, default='123456')


    def set_senha(self, senha_plana):
        self.senha = make_password(senha_plana)

    def verificar_senha(self, senha_plana):
        return check_password(senha_plana, self.senha)
    
    def __str__(self):
        return f"{self.nome} ({self.nivel})"
