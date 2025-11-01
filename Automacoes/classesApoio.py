import logging
import os
import random
import re
import shutil
import sys
import time

from datetime import datetime, date
from textwrap import wrap

from logging.handlers import RotatingFileHandler
import glob
from datetime import datetime

import pandas as pd
import unicodedata
from Levenshtein import distance
from PyPDF2 import PdfMerger
from fpdf import FPDF
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, PageBreak, Paragraph, Spacer, Image, Frame, PageTemplate
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

class TempoAleatorio:
    def __init__(self):
        self.tempo = random.uniform(1, 2)

    def tempo_aleatorio(self):
        return self.tempo


class AlternadorDeAbas:
    def __init__(self, navegador):
        self.driver = navegador

    def atualizar_abas(self):
        """Atualiza a lista de abas abertas no navegador."""
        self.abas = self.driver.window_handles

    def alternar(self, sistema):
        """Alterna para a aba correspondente ao sistema especificado."""
        self.atualizar_abas()

        if sistema == 1:
            self.aba_atual = 0
        elif sistema == 2:
            self.aba_atual = 1
        elif sistema == 3:
            self.aba_atual = 2
        else:
            print("Sistema desconhecido. Mantendo a aba atual.")
            return

        if self.aba_atual < len(self.abas):
            self.driver.switch_to.window(self.abas[self.aba_atual])
        else:
            print(f"Não há abas suficientes. Número de abas abertas: {len(self.abas)}")

class StringNormalizer:
    def __init__(self):
        pass

    def normalize(self, text):
        if isinstance(text, list):
            return [self._normalize_string(s) for s in text]
        else:
            return self._normalize_string(text)

    def _normalize_string(self, text):
        text = text.upper()

        # Substituindo 'ç' por 'c'
        text = text.replace('Ç', 'C')

        # Removendo acentos
        text = ''.join(
            char for char in unicodedata.normalize('NFD', text)
            if unicodedata.category(char) != 'Mn'
        )

        # Removendo caracteres especiais
        text = ''.join(
            char for char in text if char.isalpha() or char.isspace()
        )

        return text

class MesIniMesFin:
    def __init__(self, data_dict):
        self.data_dict = data_dict

    def mes_ini_mes_fin(self):
        # Filtrando chaves que seguem o padrão regular (mês e ano)
        regular_keys = [key for key in self.data_dict.keys() if not key.startswith('Grat_')]

        # Retornando a primeira e a última chave do padrão regular
        first_key = regular_keys[0] if regular_keys else None
        last_key = regular_keys[-1] if regular_keys else None

        return first_key, last_key

class DataExtractor:
    def __init__(self, dic_calc):
        self.data_dict = dic_calc

    def extract(self):
        # Dicionário para converter mês em formato 'mesAno' para 'JAN', 'FEV', etc.
        month_conversion = {
            'jan': 'JAN', 'fev': 'FEV', 'mar': 'MAR', 'abr': 'ABR',
            'mai': 'MAI', 'jun': 'JUN', 'jul': 'JUL', 'ago': 'AGO',
            'set': 'SET', 'out': 'OUT', 'nov': 'NOV', 'dez': 'DEZ'
        }

        # Listas para armazenar os meses, anos e valores
        months = []
        years = []
        values = []

        for key, value in self.data_dict.items():
            if not key.startswith('Grat_'):
                month_year = key[:3], key[3:]  # Separando mês e ano
                months.append(month_conversion.get(month_year[0], month_year[0].upper()))
                years.append(month_year[1])
                values.append(value)

        return months, years, values

class ProcessoSubdivisaoNumerica:
    def __init__(self, texto):
        self.texto = texto

    def unidade_processo(self):
        # Pega os 5 caracteres que antecedem o ponto e preenche com zeros à esquerda, se necessário
        return self.texto.split('.')[0].zfill(5)

    def id_processo(self):
        # Pega os caracteres entre o ponto e a barra
        return self.texto.split('.')[1].split('/')[0]

    def ano_processo(self):
        # Primeiro, pega a parte da string que contém o ano (ex: "2023" de "/2023-71")
        ano_completo = self.texto.split('/')[1].split('-')[0]
        # Em seguida, pega apenas os dois últimos caracteres do ano (ex: "23" de "2023")
        return ano_completo[-2:]

class ProcessoSubdivisaoAdministrativo:
    def __init__(self, texto):
        # Remove todos os espaços para facilitar o processamento
        self.texto = re.sub(r'\s+', '', texto)

    def processar_processo(self):
        """
        Processa a string de entrada e extrai os componentes do processo.
        Suporta múltiplos formatos de entrada.

        Retorna:
            dict: Dicionário com os componentes do processo.
        """
        # Tentar primeiro o formato com ponto: "12345.123456/1234-12"
        pattern_com_ponto = r'^(\d+)\.(\d+)/(\d{2,4})-(\d+)$'
        match = re.match(pattern_com_ponto, self.texto)
        if match:
            unidade, identificador, ano_completo, digito = match.groups()
            return {
                'unidade': unidade.zfill(5),
                'identificador': identificador,
                'ano': ano_completo[-2:],  # Últimos dois dígitos do ano
                'digito': digito
            }

        # Tentar o formato sem ponto: "10280/100833/20-41"
        pattern_sem_ponto = r'^(\d+)/(\d+)/(\d{2,4})-(\d+)$'
        match = re.match(pattern_sem_ponto, self.texto)
        if match:
            unidade, identificador, ano_completo, digito = match.groups()
            return {
                'unidade': unidade.zfill(5),
                'identificador': identificador,
                'ano': ano_completo[-2:],  # Últimos dois dígitos do ano
                'digito': digito
            }

        # Se nenhum padrão corresponder, levantar erro
        raise ValueError("Formato inválido para o processo administrativo.")

    def unidade_processo(self):
        """
        Extrai a unidade do processo.
        """
        return self.processar_processo()['unidade']

    def id_processo(self):
        """
        Extrai o ID do processo.
        """
        return self.processar_processo()['identificador']

    def ano_processo(self):
        """
        Extrai o ano do processo.
        """
        return self.processar_processo()['ano']

    def digito_processo(self):
        """
        Extrai o dígito do processo.
        """
        return self.processar_processo()['digito']

class ProcessadorFinanceiro:
    def __init__(self, dados):
        self.dados = dados
        self.novo_dicionario = self.processar_dados()

    def processar_dados(self):
        # Extrair e somar gratificações
        for chave, valor in list(self.dados.items()):
            if chave.startswith("Grat_"):
                mes_ano = chave[5:]
                self.dados[mes_ano] = self.dados.get(mes_ano, 0) + valor
                del self.dados[chave]

        # Manter apenas as chaves que estavam no dicionário original (excluindo gratificações)
        meses_anos_originais = [chave for chave in self.dados.keys() if not chave.startswith("Grat_")]
        return {chave: self.dados[chave] for chave in meses_anos_originais}

    def converter_valores(self):
        esquerda = []
        direita = []

        # Converter os valores e separar em duas listas
        for valor in self.novo_dicionario.values():
            valor_str = "{:.2f}".format(valor)  # Formatar para garantir duas casas decimais
            partes = valor_str.split('.')
            esquerda.append(partes[0])
            direita.append(partes[1])

        return esquerda, direita

class BeneficioInicial:
    def __init__(self, data_final, valor_final, data_inicial, caminho_planilha):
        self.data_final = data_final
        self.valor_final = valor_final
        self.data_inicial = data_inicial
        self.planilha = pd.read_excel(caminho_planilha, sheet_name='Planilha1')  # Carregando a planilha

    def calcular_beneficio_inicial(self):
        """
        Calcula o valor inicial com base no valor final, data final, data inicial e as taxas da planilha.
        """
        # Converter strings de data para o formato ano-mês
        self.data_final = pd.Period(self.data_final, freq='M')
        self.data_inicial = pd.Period(self.data_inicial, freq='M')

        # Inicializar o valor inicial com o valor final
        valor_inicial = self.valor_final

        # Exibir anos, taxas e valores calculados regressivamente
        print("Ano, Taxa, Valor Após Aplicação da Taxa")

        # Aplicar taxas anuais regressivamente, exceto para o ano da data inicial
        for ano in range(self.data_final.year, self.data_inicial.year, -1):
            if ano - 1 == self.data_inicial.year:  # Aplicar taxa mensal do ano inicial no ano seguinte
                data_busca_inicial = pd.to_datetime(str(self.data_inicial.year) + '-' + str(self.data_inicial.month) + '-01')
                if data_busca_inicial in self.planilha['INÍCIO BENEFICIO'].values:
                    taxa_mensal_inicial = self.planilha.loc[self.planilha['INÍCIO BENEFICIO'] == data_busca_inicial, 'PERCENTUAL MÊS'].values[0]
                    valor_inicial /= (1 + taxa_mensal_inicial)
                    print(f"{ano} (taxa do ano subsequente ao inicial), {taxa_mensal_inicial}, {valor_inicial}")
            else:
                if ano in self.planilha['ANO'].values:
                    taxa_anual = self.planilha.loc[self.planilha['ANO'] == ano, 'PERCENTUAL ANO'].values[0]
                    valor_inicial /= (1 + taxa_anual)
                    print(f"{ano}, {taxa_anual}, {valor_inicial}")

        return round(valor_inicial, 2)


# class MessageHandler:
    """
    Gerencia mensagens na interface gráfica com formatação colorida.

    Esta classe permite exibir mensagens no componente TextEdit da interface
    com cores diferentes conforme o tipo de mensagem (info, warning, error).
    """

    def __init__(self, text_edit, callback=None):
        """
        Inicializa o manipulador de mensagens.

        Args:
            text_edit: Um widget QTextEdit para exibir as mensagens
            callback: Função opcional a ser chamada após adicionar uma mensagem
        """
        self.text_edit = text_edit  # Assume-se que é um QTextEdit ou widget similar
        self.callback = callback

    def add_message(self, message, message_type="info"):
        """
        Adiciona uma mensagem ao TextEdit com formatação de cor.

        Args:
            message: Texto da mensagem a ser exibida
            message_type: Tipo da mensagem ("info", "warning" ou "error")
        """
        # Formatação da hora
        timestamp = time.strftime("[%d/%m/%Y %H:%M:%S]")
        message_with_time = f"{timestamp} {message}"

        try:
            self.text_edit.append(message_with_time)

            # Garantir que o cursor fique visível
            self.text_edit.ensureCursorVisible()

            # Chamar o callback se fornecido
            if self.callback:
                self.callback()

        except Exception as e:
            print(f"Erro ao adicionar mensagem no log: {str(e)}")
            # Tenta um fallback mais simples
            try:
                self.text_edit.append(message_with_time)
            except:
                print(f"Erro crítico ao registrar mensagem: {message_with_time}")


class TempoExecucao:
    """
    Utilidade para medir e registrar o tempo de execução de operações.
    """

    def __init__(self, message_handler=None):
        """
        Inicializa o medidor de tempo.

        Args:
            message_handler: Instância opcional de MessageHandler para registrar tempos
        """
        self.inicio = None
        self.message_handler = message_handler

    def iniciar(self):
        """Inicia a contagem de tempo."""
        self.inicio = time.time()

    def finalizar(self, descricao="Operação"):
        """
        Finaliza a contagem e registra o tempo decorrido.

        Args:
            descricao: Descrição da operação medida

        Returns:
            float: Tempo decorrido em segundos
        """
        if self.inicio is None:
            if self.message_handler:
                self.message_handler.add_message("Erro: cronômetro não foi iniciado", "error")
            return 0

        tempo_decorrido = time.time() - self.inicio

        if self.message_handler:
            self.message_handler.add_message(
                f"{descricao} concluída em {tempo_decorrido:.2f} segundos",
                "info"
            )

        return tempo_decorrido


class Singleton(type):
    """
    Metaclasse para implementar o padrão Singleton.

    Garante que uma classe tenha apenas uma instância e fornece um ponto
    global para acessá-la.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
import sys
import re

if sys.platform == "win32":
    import pygetwindow as gw

class PrimeiroPlanoNavegador:
    def __init__(self, navegador, title_pattern):
        self.driver = navegador
        self.title_pattern = title_pattern

    def enviar_primeiro_plano(self):
        if sys.platform == "win32": # Obtém todas as janelas abertas
                
            try:
                import pygetwindow as gw # Importação local e condicional
            except ImportError:
                print("pygetwindow não instalado. Recurso de primeiro plano indisponível.")
                return

            todas_janelas = gw.getAllWindows()

            # Filtra as janelas que correspondem ao padrão de título usando expressão regular
            chrome_windows = [janela for janela in todas_janelas if re.search(self.title_pattern, janela.title)]

            if chrome_windows:
                for window in chrome_windows:
                    try:
                        window.activate()
                        break
                    except Exception as e:
                        print(f'Não foi possível ativar a janela: {e}')
                        continue

            # Maximiza a janela do navegador
        self.driver.maximize_window()

class CalculadoraDias:
    def __init__(self, data1, data2):
        self.data1 = self.converte_data(data1)
        self.data2 = self.converte_data(data2)

    def converte_data(self, data):
        # Checa se a data já é do tipo date ou datetime, e se for, retorna ela mesma
        if isinstance(data, datetime):
            return data.date()
        elif isinstance(data, date):
            return data
        # Se for uma string, converte para datetime.date
        elif isinstance(data, str):
            return datetime.strptime(data, '%Y-%m-%d').date()
        else:
            raise ValueError("Formato de data não suportado.")

    def diferenca_dias(self):
        # Calcula a diferença de dias entre as datas
        return abs((self.data2 - self.data1).days)

class ExtraiNumerais:
    def __init__(self, texto):
        self.texto = texto

    def extrair_numerais(self):
        numerais = ''
        for caractere in self.texto:
            if caractere.isdigit():
                numerais += caractere
        return numerais

class ProcessaValores:
    def __init__(self, dados):
        self.dados = dados
        self.resultado = self.processa_dados()

    def soma_valores_nov(self):
        # Soma nov2022 com Grat_nov2022, se existirem
        for ano in range(2000, 2100):  # Verifica uma faixa de anos plausível
            nov_key = f'nov{ano}'
            grat_nov_key = f'Grat_nov{ano}'
            if nov_key in self.dados and grat_nov_key in self.dados:
                self.dados[nov_key] += self.dados.pop(grat_nov_key)

    def separa_valores(self):
        # Separa valores antes e depois da casa decimal
        resultado_temp = {}
        for chave, valor in self.dados.items():
            mes, ano = chave[:3], chave[3:]
            valor_inteiro, valor_decimal = divmod(int(valor * 100), 100)
            if ano not in resultado_temp:
                resultado_temp[ano] = {}
            if mes not in resultado_temp[ano]:
                resultado_temp[ano][mes] = {}
            resultado_temp[ano][mes]["antes"] = valor_inteiro
            resultado_temp[ano][mes]["depois"] = valor_decimal
        return resultado_temp

    def processa_dados(self):
        self.soma_valores_nov()
        return self.separa_valores()

    def soma_total_valores(self):
        # Esta função soma todos os valores do dicionário
        total = sum(self.dados.values())
        return total

class MaiorCincoAnos:
    def __init__(self, mes_inicial, ano_inicial, mes_final, ano_final):
        self.mes_inicial = mes_inicial
        self.ano_inicial = ano_inicial
        self.mes_final = mes_final
        self.ano_final = ano_final

    def mes_para_numero(self, mes):
        months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
        return months.index(mes) + 1

    def calcular_maior_cinco_anos(self):
        mes_inicial_numero = self.mes_para_numero(self.mes_inicial)
        mes_final_numero = self.mes_para_numero(self.mes_final)

        # Calcula a diferença total em meses
        total_meses = (int(self.ano_final) - int(self.ano_inicial)) * 12 + (mes_final_numero - mes_inicial_numero)
        total_meses += 1
        # Verifica se a diferença é maior ou igual a 62 meses
        return total_meses >= 62

class ComparaNomes:
    def __init__(self, nome1, nome2):
        self.nome1 = nome1
        self.nome2 = nome2

    def fazer_comparacao(self):
        teste1 = self.nome1.strip().upper().replace(" ", "")
        teste2 = self.nome2.strip().upper().replace(" ", "")

        # Calcular a distância de Levenshtein
        dist = distance(teste1, teste2)

        # Decidir com base na distância
        if dist <= 3:
            return True
        else:
            return False

class DeclaracaoNaoAjuizamento:
    def __init__(self, nome_bene, processo, cpf, caminho_imagem='img/brasao.png'):
        self.nome_bene = nome_bene
        self.cpf = cpf
        self.processo = processo
        self.caminho_imagem = caminho_imagem

    def gerar_declaracao(self):
        pasta_pdf = "pdfs"
        nome_arquivo = "{}_{}.pdf".format(self.nome_bene.replace(" ", "_"), self.processo.replace("/", "_"))
        caminho_completo = os.path.join(pasta_pdf, nome_arquivo)

        c = canvas.Canvas(caminho_completo, pagesize=letter)

        # Adicionando o brasão
        c.drawImage(self.caminho_imagem, 42, 650, width=60, height=60)  # Ajuste as dimensões conforme necessário

        c.setFont("Helvetica-Bold", 12)

        # Ajustando a posição do cabeçalho
        c.drawString(110, 710, "MINISTÉRIO DA GESTÃO E DA INOVAÇÃO EM SERVIÇOS PÚBLICOS")
        c.drawString(110, 695, "Secretaria de Gestão de Pessoas")
        c.drawString(110, 680, "Diretoria de Centralização de Serviços de Inativos Pensionistas e Órgãos Extintos")
        c.drawString(110, 665, "Coordenação-Geral de Pagamentos")
        c.drawString(110, 650, "Coordenação de Pagamentos de Aposentadorias e Pensões")
        c.drawString(110, 635, "Setor de Exercícios Anteriores")

        # Título
        c.setFont("Helvetica-Bold", 14)
        c.drawString(250, 590, "DECLARAÇÃO")

        # Corpo do texto
        c.setFont("Helvetica", 12)
        texto = ("Eu {}, CPF nº {} declaro para os devidos fins de cumprimento da Portaria "
                 "Conjunta nº 2 de 30 de novembro de 2012 do então Ministério do Planejamento Orçamento "
                 "e Gestão que não ajuizei e não ajuizarei ação judicial pleiteando a mesma vantagem no curso "
                 "do processo administrativo de pagamento de exercícios anteriores de nº SEI {} com vistas a "
                 "receber administrativamente o montante a que faço jus na forma de pagamento de exercícios anteriores.").format(
            self.nome_bene, self.formata_cpf(self.cpf), self.processo)

        # Ajustando o tamanho da fonte para o texto
        tamanho_fonte = self.ajustar_tamanho_fonte(c, texto, 460, 12)
        c.setFont("Helvetica", tamanho_fonte)

        # Justificando o texto
        y_atual = self.justificar_texto(c, texto, 72, 540, 460, tamanho_fonte)

        # Local e data
        c.drawString(72, y_atual - 40, "Local: _____________________________ Data: ____/____/____")

        # Linha para assinatura
        c.line(100, y_atual - 90, 500, y_atual - 90)

        # Centralizando o nome para assinatura
        self.centralizar_texto(c, self.nome_bene, y_atual - 110, letter[0], tamanho_fonte)

        c.save()
        return str(caminho_completo)

    def ajustar_tamanho_fonte(self, c, texto, largura_maxima, tamanho_fonte_max, tamanho_fonte_min=10,
                              fonte='Helvetica'):
        tamanho_fonte = tamanho_fonte_max
        c.setFont(fonte, tamanho_fonte)
        while c.stringWidth(texto, fonte, tamanho_fonte) > largura_maxima and tamanho_fonte > tamanho_fonte_min:
            tamanho_fonte -= 1
            c.setFont(fonte, tamanho_fonte)
        return max(tamanho_fonte, tamanho_fonte_min)

    def centralizar_texto(self, c, texto, y, largura_pagina, tamanho_fonte, fonte='Helvetica'):
        largura_texto = c.stringWidth(texto, fonte, tamanho_fonte)
        x = (largura_pagina - largura_texto) / 2
        c.drawString(x, y, texto)

    def salva_anexo_email_SEI(self, arquiv):
        time.sleep(3)
        if sys.platform == "win32":
            from pywinauto.application import Application
            app = Application().connect(title_re="Abrir")
            time.sleep(0.5)
            dlg = app.window(title_re="Abrir")
            time.sleep(0.5)

            # Obter o caminho absoluto do script Python atual
            caminho_script_atual = os.path.abspath(os.path.dirname(__file__))

            # Concatenar com o subdiretório 'pdfs'

            caminho = os.path.join(caminho_script_atual, arquiv)
            dlg.type_keys(caminho)
            time.sleep(0.5)
            # dlg3.type_keys('{TAB}')
            # dlg3.type_keys('{TAB}')
            dlg.type_keys('{ENTER}')
            time.sleep(0.5)
        return True

    def justificar_texto(self, c, texto, x, y, max_width, font_size):
        linhas = wrap(texto, 80)
        for i, linha in enumerate(linhas):
            palavras = linha.split()
            if len(palavras) <= 1 or i == len(linhas) - 1:  # Não justifica a última linha
                c.drawString(x, y, linha)
                y -= font_size * 1.2
                continue

            espaco_normal = c.stringWidth(" ", "Helvetica", font_size)
            espaco_total = max_width - sum([c.stringWidth(palavra, "Helvetica", font_size) for palavra in palavras])
            espaco_adicional = espaco_total / (len(palavras) - 1) - espaco_normal

            x_temp = x
            for palavra in palavras[:-1]:
                c.drawString(x_temp, y, palavra)
                x_temp += c.stringWidth(palavra, "Helvetica", font_size) + espaco_normal + espaco_adicional
            c.drawString(x_temp, y, palavras[-1])
            y -= font_size * 1.2
        return y

    def formata_cpf(self, cpf):
        """Formata uma string de CPF no formato 000.000.000-00, garantindo que tenha 11 dígitos."""
        cpf_preenchido = cpf.zfill(11)  # Preenche com zeros à esquerda para garantir 11 dígitos
        return f"{cpf_preenchido[:3]}.{cpf_preenchido[3:6]}.{cpf_preenchido[6:9]}-{cpf_preenchido[9:]}"

class AbreArquivoNavegador:
    def __init__(self, arquivo):
        self.arquivo = arquivo

    def abrir_arquivo(self):
        if sys.platform == "win32":
            from pywinauto.application import Application
            app = Application().connect(title_re="Abrir")
            time.sleep(0.5)
            dlg = app.window(title_re="Abrir")
            time.sleep(0.5)

            # Verifica se o script está rodando como um executável
            if getattr(sys, 'frozen', False):
                caminho_script_atual = os.path.dirname(sys.executable)
            else:
                caminho_script_atual = os.path.abspath(os.path.dirname(__file__))

            # Concatenar com o subdiretório 'pdfs'
            pasta = os.path.join(caminho_script_atual)
            caminho = os.path.join(pasta, self.arquivo)
            caminho_com_formato_dlg = caminho.replace(" ", "{SPACE}")
            dlg.type_keys(caminho_com_formato_dlg)
            time.sleep(0.5)
            dlg.type_keys('{ENTER}')
            time.sleep(1)

class PDFManager:
    def __init__(self, destination_directory, new_filename):
        self.destination_directory = destination_directory
        self.new_filename = new_filename
        # Definindo o diretório de downloads baseado no sistema operacional
        if os.name == 'nt':  # Windows


            # Diretório base do projeto (onde está o script principal)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            print(base_dir)

            # Caminho para a pasta 'downloads' na raiz do projeto
            self.download_directory = os.path.join(base_dir, 'downloads')

        else:  # macOS e Linux
            self.download_directory = os.path.join(os.environ['HOME'], 'downloads')

    def espera_pdf_salvar(self, nome_arquivo='Sigepe.pdf', timeout=30):
        """Espera até que um arquivo PDF específico seja salvo no diretório de downloads.

        Args:
            nome_arquivo (str): Nome do arquivo PDF a ser esperado.
            timeout (int): Tempo máximo de espera em segundos.

        Returns:
            bool: True se o arquivo foi encontrado, False caso contrário.
        """
        caminho_arquivo = os.path.join(self.download_directory, nome_arquivo)
        tempo_inicio = time.time()
        while True:
            if os.path.exists(caminho_arquivo):
                return True
            elif time.time() - tempo_inicio > timeout:
                print("Timeout: o arquivo PDF não foi encontrado.")
                return False
            else:
                time.sleep(1)

    def find_and_move_latest_pdf(self):
        nome_arquivo = 'Sigepe.pdf'  # Define o nome do arquivo a ser buscado e movido

        if not os.path.exists(self.destination_directory):
            os.makedirs(self.destination_directory)

        if self.espera_pdf_salvar(nome_arquivo):
            caminho_original = os.path.join(self.download_directory, nome_arquivo)
            new_path = os.path.join(self.destination_directory, self.new_filename)
            shutil.move(caminho_original, new_path)
            print(f"Arquivo PDF movido: {new_path}")
        else:
            print("Nenhum arquivo PDF encontrado.")

class ValidadorCPF:
    def __init__(self, entrada):
        self.entrada = entrada

    def validar_cpf(self, cpf):
        cpf = ''.join(filter(str.isdigit, cpf))
        cpf = cpf.zfill(11)  # Preenche com zeros à esquerda até completar 11 dígitos

        if len(cpf) != 11 or len(set(cpf)) == 1:
            return False

        def calcular_digito(soma):
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto

        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        if int(cpf[9]) != calcular_digito(soma):
            return False
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        if int(cpf[10]) != calcular_digito(soma):
            return False
        return True

    def processar_cpfs(self):
        cpfs = self.entrada.split()
        cpfs_validos = []
        for cpf in cpfs:
            if self.validar_cpf(cpf):
                cpfs_validos.append(cpf)
            else:
                return f"CPF inválido: {cpf}"
        return cpfs_validos

class PdfFichaFinanceira:
    def __init__(self, infobeneficio, dataframe):
        self.df = dataframe
        self.nome = infobeneficio.nome_inst_str
        self.matricula = infobeneficio.matricula_inst

    def gerar_pdf_ficha_financeira(self):
        pdf = FPDF(orientation='L')
        pdf.add_page()

        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Informações extraídas do SIAPE - Sistema Integrado de Administração de Recursos Humanos', 0, 1, 'C')
        pdf.ln(10)

        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, f'Nome: {self.nome}', 0, 1)
        pdf.cell(0, 10, f'Matrícula: {self.matricula}', 0, 1)
        current_time = datetime.now().strftime('%d/%m/%Y %H:%M')
        pdf.cell(0, 10, f'Data de Extração: {current_time}', 0, 1)  # Inclui a data de extração
        pdf.ln(5)

        col_widths = {
            'R/D': 9, 'Rubrica': 15, 'Nome Rubrica': 130,
            'Seq./Ass.': 18, 'Mês-Ano/Perc.': 28, 'Prazo/Fração': 26,
            'Valor': 20, 'Mês': 10, 'Ano': 12
        }

        centralize_cols = ['R/D', 'Rubrica', 'Seq./Ass.', 'Mês-Ano/Perc.', 'Prazo/Fração', 'Valor', 'Mês', 'Ano']  # Colunas a serem centralizadas

        last_month = None
        for idx, row in self.df.iterrows():
            current_month = row['Mês']
            if current_month != last_month:
                if last_month is not None:
                    pdf.add_page()
                pdf.set_font('Arial', 'B', 10)
                for col_name, width in col_widths.items():
                    align = 'C' if col_name in centralize_cols else 'L'  # Centraliza se especificado
                    pdf.cell(width, 10, col_name, border=1, align=align)
                pdf.ln()
                last_month = current_month

            pdf.set_font('Arial', '', 10)
            for col_name, width in col_widths.items():
                align = 'C' if col_name in centralize_cols else 'L'  # Centraliza se especificado
                pdf.cell(width, 10, str(row[col_name]), border=1, align=align)
            pdf.ln()

        pdf.output('ficha_financeira.pdf')
        return True

class PdfFichaFinanceiraOficial:
    def __init__(self, mat_inst, ano_mes):
        self.mat_inst = mat_inst
        self.ano_mes = ano_mes

    def armazenar_pdf_ficha(self):
        if sys.platform == "win32":
            from pywinauto.application import Application
            app = Application().connect(title=u'Salvar como', timeout=5)
            dlg = app[u'Salvar como']

            arquiv = self.mat_inst + self.ano_mes + ".pdf"
            arquiv = arquiv.replace(" ", "{SPACE}")
            caminho_script_atual = os.path.abspath(os.path.dirname(__file__))
            pasta = os.path.join(caminho_script_atual, 'FichasFinanceiras')

            caminho = os.path.join(pasta, arquiv)
            dlg.type_keys(caminho)
            time.sleep(1)
            dlg.type_keys('{ENTER}')
            time.sleep(2)

class PdfMerge:
    def __init__(self, input_dir, output_dir, output_filename='merged.pdf'):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.output_filename = output_filename

    def merge_pdfs(self):
        # Lista os arquivos PDF na pasta de entrada, ordenando pela data de criação
        files = [os.path.join(self.input_dir, f) for f in os.listdir(self.input_dir) if f.endswith('.pdf')]
        files.sort(key=os.path.getctime)

        merger = PdfMerger()

        # Adiciona os arquivos ao objeto merger
        for pdf in files:
            merger.append(pdf)

        # Salva o PDF unido na pasta de saída
        output_path = os.path.join(self.output_dir, self.output_filename)
        merger.write(output_path)
        merger.close()

        # Após unir os PDFs, apaga os arquivos originais
        for pdf in files:
            os.remove(pdf)

        print(f'Merged PDF saved as {output_path}. Original files deleted.')

class InterfacePrimeiroPlano:
    def bring_window_to_front(self):
        self.activateWindow()
        self.raise_()

class NormalizaValoresMonetarios:
    def __init__(self, string_valor):
        self.string_valor = string_valor

    def normalizar_string_para_monetario(self):
        # Remover caracteres indesejados: espaços, símbolos monetários e pontos
        caracteres_indesejados = [' ', 'R$', '€', '$', '¥', '£']
        for caractere in caracteres_indesejados:
            self.string_valor = self.string_valor.replace(caractere, '')

        # Remover caracteres não numéricos
        self.string_valor = ''.join(filter(str.isdigit, self.string_valor))

        # Substituir a vírgula por ponto
        self.string_valor = self.string_valor.replace(',', '.')

        # Converter a string em float e dividir por 100
        valor_float = float(self.string_valor) / 100

        # Formatar o valor com duas casas decimais
        valor_formatado = "{:.2f}".format(valor_float)

        return valor_formatado

class DivideValorParaSIAPE:
    def __init__(self, valor):
        self.valor = valor

    def dividir_string_valor(self):
        # Remover caracteres indesejados: espaços e símbolos monetários
        caracteres_indesejados = [' ', 'R$', '€', '$', '¥', '£']
        for caractere in caracteres_indesejados:
            valor = self.valor.replace(caractere, '')

        # Substituir a vírgula por ponto se estiver presente
        valor = valor.replace(',', '.')

        # Separar os números antes e depois do ponto flutuante
        partes = valor.split('.')
        numero_esquerda = str(partes[0])
        numero_direita = partes[1] if len(partes) > 1 else '00'

        # Garantir que a string à direita tenha duas casas decimais
        numero_direita = numero_direita.ljust(2, '0')

        return numero_esquerda, numero_direita

class VerificaSequenciaMesAno:
    def __init__(self, lista_string, lista_int):
        self.lista_meses = lista_string
        self.int_list = lista_int

    def verificar_mes_ano(self):
        # Lista de meses válidos
        meses = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

        # Verifica se as listas têm o mesmo tamanho
        if len(self.lista_meses) != len(self.int_list):
            return "As listas não têm o mesmo tamanho."

        lista_anos = [int(i) for i in self.int_list]
        # Verifica por erros de digitação em meses e anos
        for mes in self.lista_meses:
            if mes not in meses:
                return f"Erro de digitação no mês: {mes}."

        for ano in lista_anos:
            if not (1900 <= ano <= 2100):  # Intervalo arbitrário, ajuste conforme necessário
                return f"Erro de digitação no ano: {ano}."

        # Verifica sequência lógica
        for i in range(1, len(self.lista_meses)):
            indice_mes_atual = meses.index(self.lista_meses[i])
            indice_mes_anterior = meses.index(self.lista_meses[i - 1])

            if (indice_mes_atual <= indice_mes_anterior and lista_anos[i] == lista_anos[i - 1]) or \
                    (lista_anos[i] < lista_anos[i - 1]) or \
                    (indice_mes_atual == 0 and lista_anos[i] != lista_anos[i - 1] + 1) or \
                    (indice_mes_atual != 0 and lista_anos[i] != lista_anos[i - 1]):
                return f"Erro detectado entre {self.lista_meses[i - 1]} {lista_anos[i - 1]} e {self.lista_meses[i]} {lista_anos[i]}."

        return "Sequência correta."

class SeparadorDeInformacoes:
    def __init__(self, dados):
        self.dados = dados

    def separar_informacoes(self):
        # Extraindo as listas do dicionário original
        mesFol = self.dados['mesFol']
        compFol = self.dados['compFol']
        valorEsq = self.dados['valorEsq']
        valorDir = self.dados['valorDir']

        # Criando um dicionário vazio para armazenar as informações separadas
        informacoes_separadas = {}

        # Iterando sobre os elementos para popular o novo dicionário
        for i in range(len(compFol)):
            ano = compFol[i]
            mes = mesFol[i].lower()
            antes = int(valorEsq[i])
            depois = int(valorDir[i])

            if ano not in informacoes_separadas:
                informacoes_separadas[ano] = {}

            informacoes_separadas[ano][mes] = {
                'antes': antes,
                'depois': depois
            }

        return informacoes_separadas

class TimeFormatter:
    def __init__(self, total_time):
        self.total_time = total_time

    def format_time(self):
        hours = int(self.total_time // 3600)
        minutes = int((self.total_time % 3600) // 60)
        seconds = int(self.total_time % 60)

        if hours > 0:
            return f'{hours}h {minutes}min {seconds}seg'
        elif minutes > 0:
            return f'{minutes}min {seconds}seg'
        else:
            return f'{seconds}seg'

class GerenciadorArquivos:
    def __init__(self, diretorio_raiz):
        """
        Inicializa o Gerenciador de Arquivos com o diretório raiz.

        Args:
            diretorio_raiz (str): O caminho do diretório raiz onde os arquivos estão localizados.
        """
        self.diretorio_raiz = diretorio_raiz

    def renomear_arquivo_por_sequencia(self, sequencia):
        """
        Encontra e renomeia um arquivo no diretório cuja sequência numérica esteja no nome.
        O arquivo será renomeado para a sequência seguida da extensão .pdf.

        Args:
            sequencia (str): A sequência numérica a ser buscada no nome do arquivo.

        Returns:
            str: O novo nome do arquivo se renomeado com sucesso, ou uma mensagem de erro.
        """
        try:
            # Lista todos os arquivos no diretório
            arquivos = os.listdir(self.diretorio_raiz)

            # Busca pelo arquivo que contém a sequência
            for arquivo in arquivos:
                if sequencia in arquivo and arquivo.endswith('.pdf'):
                    # Define o novo nome do arquivo
                    novo_nome = f"{sequencia}.pdf"
                    caminho_antigo = os.path.join(self.diretorio_raiz, arquivo)
                    caminho_novo = os.path.join(self.diretorio_raiz, novo_nome)

                    # Renomeia o arquivo
                    os.rename(caminho_antigo, caminho_novo)
                    return f"Arquivo renomeado com sucesso: {novo_nome}"

            # Caso nenhum arquivo seja encontrado
            return f"Nenhum arquivo contendo a sequência '{sequencia}' foi encontrado no diretório {self.diretorio_raiz}."

        except Exception as e:
            return f"Ocorreu um erro ao tentar renomear o arquivo: {str(e)}"

class PlanilhaPSS:
    def __init__(self, mat_inst, mat_pen, nome_pen, processo, caminho_imagem='brasao.png'):
        self.mat_inst = mat_inst
        self.nome_pen = nome_pen
        self.mat_pen = mat_pen
        self.processo = processo
        self.caminho_csv = os.path.join(os.path.dirname(__file__), "planilhaPss", "Pasta2.csv")
        self.caminho_imagem = os.path.join(os.path.dirname(__file__), caminho_imagem)
        self.pasta_pdf = os.path.join(os.path.dirname(__file__), "pdfs")

    def gerar_planilha(self):
        # Criar diretório para PDFs se não existir
        os.makedirs(self.pasta_pdf, exist_ok=True)

        # Nome do arquivo PDF
        nome_arquivo = f"{self.nome_pen.replace(' ', '_')}_{self.processo.replace('/', '_')}.pdf"
        caminho_completo = os.path.join(self.pasta_pdf, nome_arquivo)

        # Verificar se o arquivo CSV existe
        if not os.path.exists(self.caminho_csv):
            raise FileNotFoundError(f"Arquivo CSV não encontrado: {self.caminho_csv}")

        # Ler o arquivo CSV
        df = pd.read_csv(self.caminho_csv, sep=";", encoding="utf-8")

        # Remover colunas "MAT_INST" e "MAT_PEN"
        df = df.drop(columns=["MAT_INST", "MAT_PEN"], errors='ignore')
        df.columns = df.columns.str.strip()

        # Converter "VALOR CORRIGIDO" para número e calcular total
        df["VALOR CORRIGIDO"] = df["VALOR CORRIGIDO"].str.replace(",", ".").astype(float)
        total_valor_corrigido = df["VALOR CORRIGIDO"].sum()

        # Criar documento PDF
        doc = SimpleDocTemplate(caminho_completo, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Estilo centralizado para o título
        title_style = ParagraphStyle(name="TitleCentered", parent=styles["Title"], alignment=1)

        # Cabeçalho e numeração de página
        def add_page_number(canvas, doc):
            canvas.setFont("Helvetica", 9)
            page_number = f"Página {doc.page}"
            canvas.drawRightString(A4[0] - 40, 20, page_number)
            canvas.drawString(40, 20, f"Processo: {self.processo}")

        doc.addPageTemplates([
            PageTemplate(
                id='pagina',
                frames=[Frame(40, 40, A4[0] - 80, A4[1] - 100, id='frame')],
                onPage=add_page_number
            )
        ])

        # Adicionar imagem do brasão com menor espaçamento no topo
        if os.path.exists(self.caminho_imagem):
            img = Image(self.caminho_imagem, width=70, height=70)
            elements.append(img)
        elements.append(Spacer(1, 2))

        # Estilos personalizados
        title_style = ParagraphStyle(name="TitleCentered", parent=styles["Title"], alignment=1)
        bold_small_style = ParagraphStyle(name="BoldSmall", parent=styles["Normal"], fontSize=9, leading=12,
                                          fontName="Helvetica-Bold")

        # Cabeçalho e título
        elements.append(Paragraph("MINISTÉRIO DA GESTÃO E INOVAÇÃO EM SERVIÇOS PÚBLICOS", styles["Title"]))
        elements.append(Paragraph("Secretaria de Gestão de Pessoas", styles["Normal"]))
        elements.append(Paragraph("Diretoria de Centralização de Serviços de Inativos Pensionistas e Órgãos Extintos",
                                  styles["Normal"]))
        elements.append(Paragraph("Coordenação-Geral de Pagamentos", styles["Normal"]))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"INTERESSADO(A): {self.nome_pen}", bold_small_style))
        elements.append(Paragraph(f"MATRÍCULA SIAPE: {self.mat_pen}", bold_small_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("Memória de Cálculo", title_style))
        elements.append(Spacer(1, 5))

        # Ajustar títulos das colunas com quebras de texto
        df.columns = [col.replace(" ", "\n") for col in df.columns]

        # Converter DataFrame para lista e adicionar totalização
        data = [df.columns.tolist()] + df.values.tolist()
        data.append(["TOTAL", "", "", "", "", "", f"{total_valor_corrigido:.2f}"])

        # Ajustar largura das colunas para caber melhor na página
        col_widths = [60, 70, 70, 70, 70, 70, 70]

        # Criar e formatar tabela
        table = Table(data, repeatRows=1, colWidths=col_widths)
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),  # Destaque para o total
        ])
        table.setStyle(style)

        # Adicionar tabela ao documento com paginação automática
        elements.append(table)
        elements.append(PageBreak())

        doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
        return caminho_completo

class TermoCiencia:
    def __init__(self, nome_bene, mat_bene, processo, cpf, caminho_imagem='brasao.png'):
        self.nome_bene = nome_bene
        self.mat_bene = mat_bene
        self.cpf = cpf
        self.processo = processo
        self.caminho_imagem = caminho_imagem
        self.pasta_pdf = os.path.join(os.path.dirname(__file__), "pdfs")

    def gerar_termo(self):
        # Criar diretório para PDFs se não existir
        os.makedirs(self.pasta_pdf, exist_ok=True)

        nome_arquivo = f"{self.nome_bene.replace(' ', '_')}_{self.processo.replace('/', '_')}.pdf"
        caminho_completo = os.path.join(self.pasta_pdf, nome_arquivo)

        print(caminho_completo)

        c = canvas.Canvas(caminho_completo, pagesize=letter)

        # Adicionando o brasão
        c.drawImage(self.caminho_imagem, 42, 650, width=60, height=60)  # Ajuste as dimensões conforme necessário

        c.setFont("Helvetica-Bold", 12)

        # Ajustando a posição do cabeçalho
        c.drawString(110, 710, "MINISTÉRIO DA GESTÃO E DA INOVAÇÃO EM SERVIÇOS PÚBLICOS")
        c.drawString(110, 695, "Secretaria de Gestão de Pessoas")
        c.drawString(110, 680, "Diretoria de Centralização de Serviços de Inativos Pensionistas e Órgãos Extintos")
        c.drawString(110, 665, "Coordenação-Geral de Pagamentos")

        # Título
        c.setFont("Helvetica-Bold", 14)
        c.drawString(250, 590, "Termo de Ciência")

        # Corpo do texto
        c.setFont("Helvetica", 12)
        texto = ("Eu {}, CPF nº {}, matrícula SIAPE {}, concordo com a implantação do desconto relacionado ao processo administrativo {} "
                 "de reposição ao erário especificado nos autos, no valor correspondente a 10% do meu vencimento bruto, "
                 "nos termos do Art. 46 da lei 8112/90.").format(
            self.nome_bene, self.formata_cpf(self.cpf),self.mat_bene, self.processo)

        # Ajustando o tamanho da fonte para o texto
        tamanho_fonte = self.ajustar_tamanho_fonte(c, texto, 460, 12)
        c.setFont("Helvetica", tamanho_fonte)

        # Justificando o texto
        y_atual = self.justificar_texto(c, texto, 72, 540, 460, tamanho_fonte)

        # Local e data
        c.drawString(72, y_atual - 40, "Local: _____________________________ Data: ____/____/____")

        # Linha para assinatura
        c.line(100, y_atual - 90, 500, y_atual - 90)

        # Centralizando o nome para assinatura
        self.centralizar_texto(c, self.nome_bene, y_atual - 110, letter[0], tamanho_fonte)

        c.save()
        return str(caminho_completo)

    def ajustar_tamanho_fonte(self, c, texto, largura_maxima, tamanho_fonte_max, tamanho_fonte_min=10,
                              fonte='Helvetica'):
        tamanho_fonte = tamanho_fonte_max
        c.setFont(fonte, tamanho_fonte)
        while c.stringWidth(texto, fonte, tamanho_fonte) > largura_maxima and tamanho_fonte > tamanho_fonte_min:
            tamanho_fonte -= 1
            c.setFont(fonte, tamanho_fonte)
        return max(tamanho_fonte, tamanho_fonte_min)

    def centralizar_texto(self, c, texto, y, largura_pagina, tamanho_fonte, fonte='Helvetica'):
        largura_texto = c.stringWidth(texto, fonte, tamanho_fonte)
        x = (largura_pagina - largura_texto) / 2
        c.drawString(x, y, texto)

    def salva_anexo_email_SEI(self, arquiv):
        time.sleep(3)
        if sys.platform == "win32":
            from pywinauto.application import Application
            app = Application().connect(title_re="Abrir")
            time.sleep(0.5)
            dlg = app.window(title_re="Abrir")
            time.sleep(0.5)

            # Obter o caminho absoluto do script Python atual
            caminho_script_atual = os.path.abspath(os.path.dirname(__file__))

            # Concatenar com o subdiretório 'pdfs'

            caminho = os.path.join(caminho_script_atual, arquiv)
            dlg.type_keys(caminho)
            time.sleep(0.5)
            # dlg3.type_keys('{TAB}')
            # dlg3.type_keys('{TAB}')
            dlg.type_keys('{ENTER}')
            time.sleep(0.5)
        return True

    def justificar_texto(self, c, texto, x, y, max_width, font_size):
        linhas = wrap(texto, 80)
        for i, linha in enumerate(linhas):
            palavras = linha.split()
            if len(palavras) <= 1 or i == len(linhas) - 1:  # Não justifica a última linha
                c.drawString(x, y, linha)
                y -= font_size * 1.2
                continue

            espaco_normal = c.stringWidth(" ", "Helvetica", font_size)
            espaco_total = max_width - sum([c.stringWidth(palavra, "Helvetica", font_size) for palavra in palavras])
            espaco_adicional = espaco_total / (len(palavras) - 1) - espaco_normal

            x_temp = x
            for palavra in palavras[:-1]:
                c.drawString(x_temp, y, palavra)
                x_temp += c.stringWidth(palavra, "Helvetica", font_size) + espaco_normal + espaco_adicional
            c.drawString(x_temp, y, palavras[-1])
            y -= font_size * 1.2
        return y

    def formata_cpf(self, cpf):
        """Formata uma string de CPF no formato 000.000.000-00, garantindo que tenha 11 dígitos."""
        cpf_preenchido = cpf.zfill(11)  # Preenche com zeros à esquerda para garantir 11 dígitos
        return f"{cpf_preenchido[:3]}.{cpf_preenchido[3:6]}.{cpf_preenchido[6:9]}-{cpf_preenchido[9:]}"

class ExtraiAnoMes:
    def __init__(self, data):
        self.data = data

    def extrai_ano_mes(self):

        if isinstance(self.data, str):
            data_obj = datetime.strptime(self.data, '%Y-%m-%d')
            ano = data_obj.year
            mes_num = data_obj.month
        elif isinstance(self.data, date):
            ano = self.data.year
            mes_num = self.data.month
        else:
            raise TypeError("O argumento deve ser uma string ou um objeto datetime.date")

        meses = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 'SET', 'OUT', 'NOV', 'DEZ']
        mes_str = meses[mes_num - 1]

        return ano, mes_str


class GerenciadorArquivos:
    """
    Classe responsável por gerenciar arquivos PDF gerados pela automação.
    Realiza operações como renomear, mover e excluir arquivos das pastas temporárias.
    Versão modificada para suportar o processamento de múltiplos arquivos temporários.
    """

    def __init__(self, pasta_temporaria=None, pasta_destino=None):
        """
        Inicializa o gerenciador de arquivos com as pastas de origem e destino.

        Args:
            pasta_temporaria: Caminho para a pasta temporária onde os arquivos são inicialmente salvos.
                            Se não fornecido, será usado 'temporario' na raiz do projeto.
            pasta_destino: Caminho para a pasta de destino onde os arquivos serão movidos.
                         Se não fornecido, será usado 'fichas_instituidor' na raiz do projeto.
        """
        # Configuração do logger
        self.logger = self._configurar_logger()

        # Obter o diretório base (raiz do projeto)
        self.base_path = os.path.dirname(os.path.abspath(__file__))

        # Definir pastas de origem e destino
        self.pasta_temporaria = pasta_temporaria or os.path.join(self.base_path, 'temporario')
        self.pasta_destino = pasta_destino or os.path.join(self.base_path, 'fichas_instituidor')

        # Verificar se as pastas existem e criar se necessário
        self._verificar_diretorios()

    def _configurar_logger(self):
        """
        Configura o logger para registrar as operações realizadas.

        Returns:
            logging.Logger: Logger configurado.
        """
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        # Verificar se o logger já tem handlers para evitar duplicação
        if not logger.handlers:
            # Criar o diretório de logs se não existir
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
            os.makedirs(log_dir, exist_ok=True)

            # Configurar o formato da mensagem
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%d/%m/%Y %H:%M:%S'
            )

            # Handler para arquivo
            file_handler = RotatingFileHandler(
                os.path.join(log_dir, 'gerenciador_arquivos.log'),
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

            # Handler para console
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    def _verificar_diretorios(self):
        """
        Verifica se os diretórios de origem e destino existem e os cria se necessário.
        """
        for diretorio in [self.pasta_temporaria, self.pasta_destino]:
            if not os.path.exists(diretorio):
                os.makedirs(diretorio)
                self.logger.info(f"Diretório criado: {diretorio}")

    def obter_arquivo_temporario(self):
        """
        Obtém o último arquivo adicionado na pasta temporária.

        Modificado para retornar o arquivo mais recente quando há múltiplos arquivos.

        Returns:
            str: Caminho completo para o arquivo encontrado.
            None: Se nenhum arquivo for encontrado.
        """
        arquivos = glob.glob(os.path.join(self.pasta_temporaria, '*.*'))

        if len(arquivos) == 0:
            self.logger.warning(f"Nenhum arquivo encontrado em {self.pasta_temporaria}")
            return None

        # Ordenar por data de modificação - pegar o mais recente
        arquivos.sort(key=os.path.getmtime, reverse=True)
        self.logger.info(f"Arquivo mais recente encontrado: {arquivos[0]}")

        return arquivos[0]

    def listar_arquivos_por_padrao(self, padrao):
        """
        Lista todos os arquivos na pasta temporária que correspondem a um padrão.

        Args:
            padrao (str): Padrão para filtrar os arquivos (ex: "matricula_*_temp.pdf")

        Returns:
            list: Lista de caminhos completos para os arquivos encontrados.
        """
        arquivos = glob.glob(os.path.join(self.pasta_temporaria, padrao))
        return arquivos

    def renomear_arquivo_temporario(self, arquivo_origem, novo_nome):
        """
        Renomeia um arquivo na pasta temporária.

        Args:
            arquivo_origem (str): Caminho completo do arquivo a ser renomeado
            novo_nome (str): Novo nome do arquivo, sem o caminho

        Returns:
            str: Caminho completo do arquivo renomeado
            None: Se ocorrer algum erro
        """
        try:
            novo_caminho = os.path.join(self.pasta_temporaria, novo_nome)
            os.rename(arquivo_origem, novo_caminho)
            self.logger.info(f"Arquivo renomeado: {arquivo_origem} -> {novo_caminho}")
            return novo_caminho
        except Exception as e:
            self.logger.error(f"Erro ao renomear arquivo: {str(e)}")
            return None

    def processar_arquivo(self, matricula_inst, arquivo_especifico=None, sobrescrever=False, sufixo=None):
        """
        Processa um arquivo, renomeando-o e movendo-o para a pasta de destino.

        Modificado para permitir processar um arquivo específico e adicionar um sufixo opcional.

        Args:
            matricula_inst (str): Matrícula do instituidor que será usada para renomear o arquivo.
            arquivo_especifico (str, optional): Caminho de um arquivo específico a processar.
                                              Se None, pega o mais recente da pasta temporária.
            sobrescrever (bool): Indica se deve sobrescrever o arquivo no destino caso já exista.
            sufixo (str, optional): Sufixo opcional para adicionar ao nome do arquivo (ex: "_2020_2024")

        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário.
            str: Mensagem descrevendo o resultado da operação.
        """
        try:
            # Obter o arquivo a ser processado
            arquivo_temporario = arquivo_especifico or self.obter_arquivo_temporario()

            if not arquivo_temporario:
                return False, "Nenhum arquivo para processar."

            # Extrair a extensão do arquivo
            _, extensao = os.path.splitext(arquivo_temporario)

            # Criar o nome do arquivo de destino
            if sufixo:
                nome_arquivo_destino = f"{matricula_inst}{extensao}"
            else:
                nome_arquivo_destino = f"{matricula_inst}{extensao}"

            caminho_destino = os.path.join(self.pasta_destino, nome_arquivo_destino)

            # Verificar se já existe um arquivo com o mesmo nome no destino
            if os.path.exists(caminho_destino) and not sobrescrever:
                # Adicionar timestamp ao nome do arquivo para evitar sobrescrita
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if sufixo:
                    nome_arquivo_destino = f"{matricula_inst}{sufixo}_{timestamp}{extensao}"
                else:
                    nome_arquivo_destino = f"{matricula_inst}_{timestamp}{extensao}"
                caminho_destino = os.path.join(self.pasta_destino, nome_arquivo_destino)
                self.logger.info(f"Arquivo já existe no destino. Criando novo nome: {nome_arquivo_destino}")

            # Mover e renomear o arquivo
            shutil.move(arquivo_temporario, caminho_destino)

            mensagem = f"Arquivo movido com sucesso de {arquivo_temporario} para {caminho_destino}"
            self.logger.info(mensagem)

            return True, mensagem

        except Exception as e:
            mensagem = f"Erro ao processar arquivo: {str(e)}"
            self.logger.error(mensagem)
            return False, mensagem

    def limpar_pasta_temporaria(self):
        """
        Remove todos os arquivos da pasta temporária.

        Returns:
            int: Número de arquivos removidos.
        """
        try:
            arquivos = glob.glob(os.path.join(self.pasta_temporaria, '*.*'))
            contador = 0

            for arquivo in arquivos:
                os.remove(arquivo)
                self.logger.info(f"Arquivo removido: {arquivo}")
                contador += 1

            return contador
        except Exception as e:
            self.logger.error(f"Erro ao limpar pasta temporária: {str(e)}")
            return 0

    def salvar_arquivo_na_pasta_temporaria(self, conteudo, nome_arquivo):
        """
        Salva conteúdo em um arquivo na pasta temporária.

        Args:
            conteudo (bytes): Conteúdo a ser salvo no arquivo.
            nome_arquivo (str): Nome do arquivo a ser criado.

        Returns:
            str: Caminho completo do arquivo criado.
            None: Se ocorrer algum erro.
        """
        try:
            caminho_completo = os.path.join(self.pasta_temporaria, nome_arquivo)

            with open(caminho_completo, 'wb') as arquivo:
                arquivo.write(conteudo)

            self.logger.info(f"Arquivo salvo na pasta temporária: {caminho_completo}")
            return caminho_completo

        except Exception as e:
            self.logger.error(f"Erro ao salvar arquivo na pasta temporária: {str(e)}")
            return None


# Função de conveniência modificada
def processar_pdf_instituidor(matricula_inst, arquivo_especifico=None, sobrescrever=False, sufixo=None):
    """
    Função de conveniência para processar o PDF do instituidor.

    Args:
        matricula_inst (str): Matrícula do instituidor.
        arquivo_especifico (str, optional): Caminho para um arquivo específico.
        sobrescrever (bool): Indica se deve sobrescrever o arquivo no destino caso já exista.
        sufixo (str, optional): Sufixo opcional para o nome do arquivo.

    Returns:
        bool: True se a operação foi bem-sucedida, False caso contrário.
        str: Mensagem descrevendo o resultado da operação.
    """
    gerenciador = GerenciadorArquivos()
    sucesso, mensagem = gerenciador.processar_arquivo(
        matricula_inst,
        arquivo_especifico=arquivo_especifico,
        sobrescrever=sobrescrever,
        sufixo=sufixo
    )

    if sucesso:
        print(f"✅ {mensagem}")
    else:
        print(f"❌ {mensagem}")

    return sucesso, mensagem