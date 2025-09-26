import os
import sqlite3
import pandas as pd
import plotly.graph_objects as go
import random
import json
import time
import logging
from pathlib import Path
from datetime import date, timedelta

from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.conf import settings
from django.views import View
from django.contrib import messages
from dotenv import load_dotenv
from workalendar.america import Brazil

from .models import Usuario
from .config_caixas import RESPONSAVEIS_POR_CAIXA, METAS_POR_CAIXA, BASE_PATH
from Automacoes.captura_processos import CapturaProcessos
from Automacoes.db_processos import GerenciadorDB
from Automacoes.passivoteste import AutomacaoPassivo

load_dotenv(override=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

CODIGOS_NIVEL = {
    "123ADMIN": "admin",
    "123DEV": "dev",
    "123GESTOR": "gestor",
    "123TEC": "tecnico",
}


def extracoes(request):
    """View para executar automações de extração de dados."""
    mensagens = []

    if request.method == "POST":
        automacoes_selecionadas = request.POST.getlist("automacoes")

        try:
            USUARIO = os.getenv("USER_EMAIL")
            SENHA = os.getenv("USER_PASSWORD")
            UNIDADE = os.getenv("UNIDADE")
            BASES_DADOS_DIR = settings.BASES_DADOS_DIR

            db = GerenciadorDB(base_dir=BASES_DADOS_DIR, unidade=UNIDADE)

            automacao_sei = AutomacaoPassivo(
                usuario=USUARIO,
                senha=SENHA,
                unidade=UNIDADE
            )

            if not automacao_sei._inicializar_navegador():
                mensagens.append("Erro ao iniciar o navegador.")
                return render(request, "usuarios/extracoes.html", {
                    "mensagens": mensagens
                })

            if not automacao_sei._realizar_login():
                mensagens.append("Erro no login. Verifique as credenciais.")
                return render(request, "usuarios/extracoes.html", {
                    "mensagens": mensagens
                })

            automacao_sei._fechar_tela_aviso()
            automacao_sei._selecionar_unidade_mgi()
            mensagens.append("Login e seleção da unidade realizados com sucesso.")

            driver_logado = automacao_sei.driver

            # Executa automações selecionadas
            if "passivo" in automacoes_selecionadas:
                mensagens.append("Automação 'passivo' executada com sucesso!")

            if "captura" in automacoes_selecionadas:
                captura = CapturaProcessos(driver_logado, db)
                captura.capturar_caixa('técnicos')
                mensagens.append(
                    f"Captura de processos da unidade '{UNIDADE}' finalizada."
                )

        except Exception as e:
            mensagens.append(f"Erro durante execução: {e}")

        finally:
            # Fecha conexões e navegador
            try:
                if 'db' in locals() and db:
                    db.fechar()
                    mensagens.append("Conexão com o banco fechada.")
            except Exception:
                pass

            try:
                if 'driver_logado' in locals() and driver_logado:
                    time.sleep(2)
                    driver_logado.quit()
                    mensagens.append("Navegador fechado com sucesso.")
            except Exception:
                pass

    return render(request, "usuarios/extracoes.html", {"mensagens": mensagens})


def login_view(request):
    """View para autenticação de usuários."""
    if request.method == 'POST':
        email = request.POST.get("email")
        senha = request.POST.get("senha")

        try:
            usuario = Usuario.objects.get(email=email)
            if usuario.verificar_senha(senha):
                request.session["usuario_id"] = usuario.id
                return redirect("home")
            else:
                return render(request, "usuarios/login.html", {
                    "erro": "Senha incorreta"
                })
        except Usuario.DoesNotExist:
            return render(request, "usuarios/login.html", {
                "erro": "Usuário não encontrado"
            })

    return render(request, "usuarios/login.html")


def cadastro_view(request):
    """View para cadastro de novos usuários."""
    if request.method == "POST":
        nome = request.POST.get("nome")
        sobrenome = request.POST.get("sobrenome")
        email = request.POST.get("email")
        senha = request.POST.get("senha")
        confirma_senha = request.POST.get("confirme-senha")
        codigo = request.POST.get("codigo")

        nome_completo = f"{nome} {sobrenome}".strip()

        if senha != confirma_senha:
            messages.error(request, "A senha e a confirmação de senha não coincidem.")
            return render(request, "usuarios/cadastro.html")

        if not all([nome, sobrenome, email, senha, confirma_senha]):
             messages.error(request, "Por favor, preencha todos os campos obrigatórios.")
             return render(request, "usuarios/cadastro.html")
                           
        nivel = CODIGOS_NIVEL.get(codigo, "tecnico")

        usuario = Usuario(nome=nome_completo, email=email, nivel=nivel)
        usuario.set_senha(senha)
        usuario.save()

        messages.success(request, "Cadastro realizado com sucesso! Faça seu login.")

        return redirect("login")

    return render(request, "usuarios/cadastro.html")

class HomeView(View):
    """View principal da aplicação."""

    def get(self, request):
        usuario_id = request.session.get("usuario_id")
        usuario = Usuario.objects.get(id=usuario_id) if usuario_id else None
        caixa_escolhida = request.GET.get('caixa', '')

        context = {
            'usuario': usuario,
            'caixas': RESPONSAVEIS_POR_CAIXA.keys(),
            'caixa_escolhida': caixa_escolhida,
            'cidade_clima': 'Brasília',
            'openweather_api_key': settings.OPENWEATHER_API_KEY,
        }
        return render(request, 'usuarios/home.html', context)

def panorama_view(request):
    """View para exibir panorama geral dos processos, fornecendo dados para Chart.js."""
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.get(id=usuario_id) if usuario_id else None

    # Controle de acesso
    if not usuario or usuario.nivel not in ["admin", "dev", "gestor"]:
        return HttpResponseForbidden(
            "Você não tem permissão para acessar o Panorama."
        )

    # Simulação de dados
    caixa_escolhida = request.GET.get("caixa", "DEMO")
    caixas = ["CGPAG-ANIST", "CGPAG-REPER", "CGPAG-CIVRES", "CGPAG-GERAL"]
    tecnicos = ["Ana", "Carlos", "Fernanda", "João", "Marcos"]

    passivos = 30
    concluidos = 50
    concluidos_por_caixa = {c: random.randint(5, 20) for c in caixas}
    concluidos_por_tecnico = {t: random.randint(3, 15) for t in tecnicos}
    
    # ----------------------------------------------------
    # PREPARAÇÃO DOS DADOS PARA CHART.JS (JSON SERIALIZÁVEL)
    # ----------------------------------------------------

    # 1. Gráfico de Barras (Caixas)
    dados_barra = {
        'labels': list(concluidos_por_caixa.keys()),
        'data': list(concluidos_por_caixa.values()),
        'titulo': 'Processos Concluídos por Caixa (Ontem)'
    }

    # 2. Gráfico de Linha (Usamos dados dos Técnicos para simular)
    dados_linha = {
        'labels': list(concluidos_por_tecnico.keys()),
        'data': list(concluidos_por_tecnico.values()),
        'titulo': 'Desempenho por Técnico (Processos Concluídos)'
    }

    # 3. Gráfico de Pizza (Passivos x Concluídos)
    dados_pizza = {
        'labels': ["Passivos", "Concluídos"],
        'data': [passivos, concluidos],
        'titulo': 'Distribuição Geral de Processos'
    }

    # Transforma os dicionários Python em strings JSON seguras para injeção no template
    dados_barra_json = json.dumps(dados_barra)
    dados_linha_json = json.dumps(dados_linha)
    dados_pizza_json = json.dumps(dados_pizza)
    
    return render(request, "usuarios/panorama.html", {
        "caixas": caixas,
        "caixa_escolhida": caixa_escolhida,
        "dados_barra_json": dados_barra_json,
        "dados_linha_json": dados_linha_json,
        "dados_pizza_json": dados_pizza_json,
    })


def get_dados_caixa(caixa_escolhida, tecnico_escolhido="Geral"):
    """Função auxiliar para obter dados de uma caixa específica."""
    if not caixa_escolhida:
        return None

    db_path = BASE_PATH / f"{caixa_escolhida}_tecnicos.db"

    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT * FROM processos", conn)
        conn.close()
    except Exception:
        return None

    df['data'] = pd.to_datetime(df['data']).dt.date

    # Filtragem por técnico
    responsaveis = RESPONSAVEIS_POR_CAIXA.get(caixa_escolhida, [])
    if tecnico_escolhido == "Geral":
        df_para_analise = df[df['email'].isin(responsaveis)]
    else:
        df_para_analise = df[df['tecnico'] == tecnico_escolhido]

    # Cálculo de métricas
    concluidos = df_para_analise[df_para_analise["concluido"] == 1]
    processos_concluidos = len(concluidos)
    hoje = date.today()
    processos_hoje = len(df_para_analise[
        (df_para_analise["data"] == hoje) & 
        (df_para_analise["concluido"] == 1)
    ])

    # Cálculo de dias úteis e metas
    cal = Brazil()
    cal.subdiv = "DF"
    inicio_mes = hoje.replace(day=1)
    fim_mes = (inicio_mes.replace(
        month=inicio_mes.month % 12 + 1, day=1
    ) - timedelta(days=1))
    dias_uteis = cal.get_working_days_delta(inicio_mes, fim_mes)

    if tecnico_escolhido == "Geral":
        meta_diaria = METAS_POR_CAIXA.get(caixa_escolhida, 4) * len(responsaveis)
    else:
        meta_diaria = METAS_POR_CAIXA.get(caixa_escolhida, 4)
    
    meta_mensal = dias_uteis * meta_diaria

    # Cálculo para velocímetros
    if meta_diaria > 0:
        percentual_dia = min(100, int((processos_hoje / meta_diaria) * 100))
    else:
        percentual_dia = 0
    angulo_dia = (percentual_dia * 1.8) - 90

    if meta_mensal > 0:
        percentual_mes = min(100, int((processos_concluidos / meta_mensal) * 100))
    else:
        percentual_mes = 0
    angulo_mes = (percentual_mes * 1.8) - 90

    return {
        'processos_hoje': processos_hoje,
        'processos_concluidos': processos_concluidos,
        'dias_uteis': dias_uteis,
        'meta_diaria': meta_diaria,
        'meta_mensal': meta_mensal,
        'percentual_dia': percentual_dia,
        'angulo_dia': angulo_dia,
        'percentual_mes': percentual_mes,
        'angulo_mes': angulo_mes,
        'responsaveis': responsaveis,
        'df_para_analise': df_para_analise
    }


def dashboard_view(request):
    """View para dashboard com métricas e gráficos."""
    caixa_escolhida = request.GET.get("caixa")
    tecnico_escolhido = request.GET.get("tecnico", "Geral")

    if not caixa_escolhida:
        return render(request, "usuarios/dashboard.html", {
            "caixas": RESPONSAVEIS_POR_CAIXA.keys()
        })

    dados = get_dados_caixa(caixa_escolhida, tecnico_escolhido)
    if not dados:
        return render(request, "usuarios/dashboard.html", {
            "caixas": RESPONSAVEIS_POR_CAIXA.keys(),
            "erro": f"Arquivo do banco para '{caixa_escolhida}' não encontrado!"
        })

    # Gráfico de processos do dia
    fig_dia = go.Figure(go.Indicator(
        mode="gauge+number",
        value=dados['processos_hoje'],
        title={'text': f"Processos do Dia (Meta: {dados['meta_diaria']})"},
        gauge={
            'axis': {'range': [0, dados['meta_diaria'] + 2]},
            'bar': {'color': 'blue'},
            'steps': [
                {'range': [0, dados['meta_diaria']*0.5], 'color': 'red'},
                {'range': [dados['meta_diaria']*0.5, dados['meta_diaria']], 'color': 'orange'},
                {'range': [dados['meta_diaria'], dados['meta_diaria']+2], 'color': 'green'}
            ]
        }
    ))
    fig_dia.update_layout(width=400, height=300)

    # Gráfico de processos do mês
    fig_mes = go.Figure(go.Indicator(
        mode="gauge+number",
        value=dados['processos_concluidos'],
        title={'text': f"Concluídos no Mês (Meta: {dados['meta_mensal']})"},
        gauge={
            'axis': {'range': [0, dados['meta_mensal'] + 20]},
            'bar': {'color': 'black'},
            'steps': [
                {'range': [0, dados['meta_mensal']*0.5], 'color': 'red'},
                {'range': [dados['meta_mensal']*0.5, dados['meta_mensal']], 'color': 'orange'},
                {'range': [dados['meta_mensal'], dados['meta_mensal']+20], 'color': 'green'}
            ]
        }
    ))
    fig_mes.update_layout(width=400, height=300)

    context = {
        "caixas": RESPONSAVEIS_POR_CAIXA.keys(),
        "caixa_escolhida": caixa_escolhida,
        "tecnico_escolhido": tecnico_escolhido,
        "grafico_dia": fig_dia.to_html(full_html=False),
        "grafico_mes": fig_mes.to_html(full_html=False),
        "processos_concluidos": dados['processos_concluidos'],
        "dias_uteis": dados['dias_uteis'],
        "meta_mensal": dados['meta_mensal'],
        "percentual_dia": dados['percentual_dia'],
        "angulo_dia": dados['angulo_dia'],
        "percentual_mes": dados['percentual_mes'],
        "angulo_mes": dados['angulo_mes'],
    }

    return render(request, "usuarios/dashboard.html", context)


def desempenho_view(request):
    """View para análise de desempenho."""
    caixa_escolhida = request.GET.get("caixa")
    tecnico_escolhido = request.GET.get("tecnico", "Geral")

    if not caixa_escolhida:
        return render(request, "usuarios/desempenho.html", {
            "caixas": RESPONSAVEIS_POR_CAIXA.keys()
        })

    dados = get_dados_caixa(caixa_escolhida, tecnico_escolhido)
    if not dados:
        return render(request, "usuarios/desempenho.html", {
            "caixas": RESPONSAVEIS_POR_CAIXA.keys(),
            "erro": f"Arquivo do banco para '{caixa_escolhida}' não encontrado!"
        })

    context = {
        "caixas": RESPONSAVEIS_POR_CAIXA.keys(),
        "caixa_escolhida": caixa_escolhida,
        "tecnico_escolhido": tecnico_escolhido,
        "percentual_dia": dados['percentual_dia'],
        "angulo_dia": dados['angulo_dia'],
        "percentual_mes": dados['percentual_mes'],
        "angulo_mes": dados['angulo_mes'],
        "processos_hoje": dados['processos_hoje'],
        "processos_concluidos": dados['processos_concluidos'],
        "meta_diaria": dados['meta_diaria'],
        "meta_mensal": dados['meta_mensal'],
    }

    return render(request, "usuarios/desempenho.html", context)


# def velocimetro1(request):
#     """View para velocímetro de exemplo."""
#     context = {"score": 10}
#     return render(request, "usuarios/velocimetro1.html", context)