# from log_config import setup_logging
import time
from datetime import datetime
import math
import timeit
import requests
import re
import os
import sys
import locale
import logging
import pandas as pd
from enum import Enum
from tenacity import retry, stop_after_attempt, wait_fixed, wait_exponential, retry_if_exception_type, retry_if_result

from datetime import datetime

from num2words import num2words
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.common.exceptions import NoAlertPresentException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from .classesApoio import (MesIniMesFin, DataExtractor, MessageHandler, AbrirArquivos, PrimeiroPlanoNavegador,
                          ExtraiNumerais, ProcessaValores, AlternadorDeAbas, NormalizaValoresMonetarios,
                          DivideValorParaSIAPE, ProcessoSubdivisaoNumerica, VerificaSequenciaMesAno, TempoAleatorio,
                          GerenciadorArquivos)
from pywinauto.application import Application

# # Configurar logging usando setup_logging
# setup_logging()

class TotalNotFoundException(Exception):
    pass

class StatusLogin(Enum):
    """Enum para representar os possíveis resultados do login."""
    SUCESSO = 1
    CREDENCIAIS_INVALIDAS = 2
    ERRO = 0

class LoginSei:
    """
    Classe responsável por realizar o login no Sistema Eletrônico de Informações (SEI).
    """
    # Constantes da classe
    URL_LOGIN = ('https://colaboragov.sei.gov.br/sip/modulos/MF/login_especial/login_especial.php?sigla_orgao_sistema=MGI&sigla_sistema=SEI')
    TIMEOUT_PADRAO = 5
    TIMEOUT_ALERTA = 3
    ORGAO = 'MGI'

    def __init__(self, navegador, usuario, senha):
        """
        Inicializa a classe com as informações necessárias para login.

        Args:
            navegador: Instância do WebDriver do Selenium
            usuario: Nome de usuário para login
            senha: Senha do usuário
        """
        self.driver = navegador
        self.usuario = usuario
        self.senha = senha
        self.wait = WebDriverWait(self.driver, self.TIMEOUT_PADRAO)

    def logar_sei(self):
        """
        Realiza o processo de login no sistema SEI.

        Returns:
            StatusLogin: Enum representando o status do login
                         (SUCESSO, CREDENCIAIS_INVALIDAS ou ERRO)
        """
        logging.info('Iniciando o processo de login no SEI.')

        try:
            self._acessar_pagina_login()
            self._preencher_formulario_login()
            return self._verificar_resultado_login()
        except Exception as e:
            logging.error(f'Erro durante o processo de login: {e}')
            return StatusLogin.ERRO

    def _acessar_pagina_login(self):
        """
        Acessa a página de login do SEI.

        Raises:
            Exception: Se houver erro ao acessar o link
        """
        try:
            self.driver.get(self.URL_LOGIN)
            logging.info(f'Acessando o link: {self.URL_LOGIN}')
        except Exception as e:
            logging.error(f'Erro ao acessar o link: {e}')
            raise

    def _preencher_formulario_login(self):
        """
        Preenche o formulário de login com usuário, senha e seleciona o órgão.

        Raises:
            TimeoutException: Se não encontrar os elementos do formulário
            Exception: Para outros erros inesperados
        """
        try:
            # Preenche usuário
            campo_usuario = self.wait.until(EC.element_to_be_clickable((By.ID, 'txtUsuario')))
            campo_usuario.send_keys(self.usuario)
            logging.info('Campo de usuário encontrado e preenchido.')

            # Preenche senha
            campo_senha = self.wait.until(EC.element_to_be_clickable((By.ID, 'pwdSenha')))
            campo_senha.send_keys(self.senha)
            logging.info('Campo de senha encontrado e preenchido.')

            # Seleciona órgão
            dropdown = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="selOrgao"]')))
            dropdown.send_keys(self.ORGAO)
            logging.info('Dropdown do órgão selecionado.')

            # Clica no botão de acesso
            botao_acessar = self.wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="Acessar"]')))
            botao_acessar.click()
            logging.info('Botão acessar clicado.')
        except TimeoutException as e:
            logging.error(f'Timeout ao preencher os campos de login: {e}')
            raise
        except Exception as e:
            logging.error(f'Erro inesperado durante o login: {e}')
            raise

    def _verificar_resultado_login(self):
        """
        Verifica se o login foi bem-sucedido ou se houve algum alerta de erro.

        Returns:
            StatusLogin: Enum representando o status do login
                        (SUCESSO ou CREDENCIAIS_INVALIDAS)
        """
        try:
            # Verifica se existe algum alerta indicando usuário ou senha inválidos
            wait_alerta = WebDriverWait(self.driver, self.TIMEOUT_ALERTA)
            alerta = wait_alerta.until(EC.alert_is_present())
            alerta.accept()
            logging.warning('Usuário ou senha inválida, alerta presente e tratado.')
            return StatusLogin.CREDENCIAIS_INVALIDAS
        except TimeoutException:
            logging.info('Login bem-sucedido, sem alertas.')
            return StatusLogin.SUCESSO
        except NoAlertPresentException:
            logging.info('Nenhum alerta presente após tentativa de login.')
            return StatusLogin.SUCESSO

    def verificar_login_bem_sucedido(self):
        """
        Método adicional que verifica se o login foi realmente bem-sucedido
        verificando a presença do elemento 'Controle de Processos' na barra de menu
        e a ausência da mensagem de erro.

        Returns:
            bool: True se o login foi bem-sucedido, False caso contrário
        """
        try:
            # Verifica primeiro se apareceu uma página de erro
            try:
                erro_element = self.driver.find_element(By.XPATH,
                                                        "//div[@id='divInfraBarraLocalizacao' and contains(text(), 'Erro')]")
                if erro_element:
                    logging.warning('Página de erro encontrada após tentativa de login.')
                    return False
            except NoSuchElementException:
                # Se não encontrou o elemento de erro, segue para verificar o login bem-sucedido
                pass

            # Busca pela imagem com title="Controle de Processos"
            self.wait.until(EC.presence_of_element_located(
                (By.XPATH, "//img[@title='Controle de Processos']")
            ))
            logging.info('Login confirmado pela presença do elemento "Controle de Processos".')
            return True
        except TimeoutException:
            logging.warning('Elemento "Controle de Processos" não encontrado, possível falha no login.')
            return False

class TelaAviso:
    def __init__(self, navegador):
        self.driver = navegador

    # Remove a tela de aviso após logar no SEI
    def fechar_tela_aviso_sei(self):
        logging.info('Tentando fechar a tela de aviso do SEI.')
        try:
            close_btn = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH, '/html/body/div[7]/div[2]/div[1]/div[3]/img'))
            )
            self.driver.execute_script("arguments[0].click();", close_btn)
            logging.info('Tela de aviso fechada com sucesso.')
        except TimeoutException:
            logging.warning('Nenhuma tela de aviso encontrada para fechar.')

class SelecaoUnidade:
    def __init__(self, janela, navegador, unidade):
        self.driver = navegador
        self.unidade = unidade
        self.janela = janela

    def selecionar_unidade_sei(self):
        logging.info('Iniciando o processo de seleção da unidade no SEI.')

        # Verifica se a unidade de interesse já está selecionada
        try:
            # Espera até que o elemento esteja clicável
            elemento = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'div.nav-item:nth-child(3) > div:nth-child(1) > a:nth-child(1)'))
            )

            # Verifica se o texto do elemento é igual à variável 'unidade'
            if elemento.text == self.unidade:
                logging.info(f'Unidade {self.unidade} já está selecionada.')
                return
            else:
                logging.info(f'Unidade atual {elemento.text} não corresponde à unidade desejada {self.unidade}. '
                             f'Iniciando processo de seleção.')
                # Caso a unidade de interesse não esteja selecionada prossegue para a seleção
                # Clica no campo superior à direita para direcionar à página de seleção de unidade
                try:
                    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, 'div.nav-item:nth-child(3) > div:nth-child(1) > a:nth-child(1)'))).click()
                    logging.info('Campo de seleção de unidade clicado.')
                    time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
                    # Escolhe o MGI como órgão
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="selInfraOrgaoUnidade"]'))).send_keys(
                        'MGI')  # Escolhe Unidade
                    logging.info('Órgão MGI selecionado.')
                    time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
                except TimeoutException:
                    logging.warning('Timeout ao tentar clicar no campo de seleção de unidade.')
                    pass

                # Faz uma lista com todas as unidades da página e itera sobre elas até encontrar a de interesse
                rows = self.driver.find_elements(By.XPATH, '/html/body/div[1]/div/div[2]/form/div[3]/table/tbody/tr')
                found = False

                for row in rows[1:]:
                    try:
                        second_column_text = row.find_element(By.XPATH, "./td[2]").text
                        if self.unidade in second_column_text:
                            logging.info(f"Texto '{self.unidade}' encontrado na linha da tabela.")
                            first_column_radiobutton = row.find_element(By.XPATH, "./td[1]//input[@type='radio']")
                            is_checked = first_column_radiobutton.get_attribute('checked')

                            if is_checked:
                                logging.info(f"A unidade '{self.unidade}' já está selecionada. Confirmando seleção.")
                                self.driver.find_element(By.XPATH,
                                                         '/html/body/div[1]/nav/div/div[3]/div[2]/div[4]/a/img').click()
                            else:
                                logging.info(f"Selecionando a unidade '{self.unidade}' através do botão de rádio.")
                                self.driver.execute_script("arguments[0].click();", first_column_radiobutton)

                            found = True
                            break
                        else:
                            logging.debug(
                                f"Unidade '{second_column_text}' não corresponde à unidade desejada '{self.unidade}'. Continuando a busca.")
                    except NoSuchElementException as e:
                        logging.error(f"Erro ao processar uma linha da tabela: {str(e)}")
                        continue

                if not found:
                    logging.warning(f"Unidade '{self.unidade}' não encontrada. Verifique sua habilitação.")
                    self.janela.message_handler.add_message("Unidade não encontrada, verifique sua habilitação",
                                                            "error")

                time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except TimeoutException:
            logging.error('Timeout ao tentar localizar o elemento de seleção de unidade.')
            return

# class VisualizacaoDetalhada:
#     def __init__(self, navegador):
#         self.driver = navegador

#     def visualizar_detalhado(self):
#         logging.info('Iniciando o processo de visualização detalhada.')
#         time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

#         try:
#             WebDriverWait(self.driver, 10).until(
#                 EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/div/div[2]/form/div/div[4]/div[1]/a'))).click()
#             logging.info('Botão de visualização detalhada clicado com sucesso.')
#             time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
#         except TimeoutException:
#             logging.error("Elemento de visualização detalhada não encontrado ou não clicável dentro do tempo limite.")

class VisualizacaoDetalhada:
    def __init__(self, navegador):
        self.driver = navegador

    def visualizar_detalhado(self):
        logging.info('Iniciando o processo de visualização detalhada.')
        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(text(), "Visualização detalhada")]'))).click()
            logging.info('Botão de visualização detalhada clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except TimeoutException:
            logging.error("Elemento de visualização detalhada não encontrado ou não clicável dentro do tempo limite.")

class PaginaControleProcessos:
    def __init__(self, navegador):
        self.driver = navegador

    def acessar_controle_processos(self):
        logging.info('Iniciando o acesso à página de controle de processos.')
        self.driver.switch_to.default_content()

        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="lnkControleProcessos"]/img'))).click()
            logging.info('Link de controle de processos clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except TimeoutException:
            logging.error("Elemento de controle de processos não foi encontrado ou não era clicável dentro do tempo limite.")

        logging.info('Acessando a visualização detalhada dos processos.')
        VisualizacaoDetalhada(self.driver).visualizar_detalhado()

class IconesBarraProcessoSei:
    def __init__(self, navegador, cod_icone):
        self.driver = navegador
        self.cod_icone = cod_icone

    def clicar_icone_barra(self):
        logging.info(f'Iniciando o clique no ícone da barra com código: {self.cod_icone}.')
        time.sleep(2)
        self.driver.switch_to.default_content()

        try:
            WebDriverWait(self.driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, 'ifrArvore')))
            logging.info('Switch para o iframe ifrArvore bem-sucedido.')
            process = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'infraArvoreNoSelecionado')))
            process.click()
            logging.info('Elemento de processo na árvore selecionado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except TimeoutException:
            logging.error("Um dos elementos não foi encontrado dentro do tempo limite ao tentar clicar no processo na árvore.")
            return

        logging.info('Navegando para o frame de exibição de documentos.')
        try:
            IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()
            logging.info('Navegação para o frame de documentos realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao navegar para o frame de documentos: {str(e)}')
            return

        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f'//img[@title="{self.cod_icone}"]'))).click()
            logging.info(f'Ícone com título "{self.cod_icone}" clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except TimeoutException:
            logging.error("Elemento do ícone não foi encontrado ou não era clicável dentro do tempo limite.")

class ControlePrazosSei:
    def __init__(self, navegador, prazo):
        self.driver = navegador
        self.prazo = prazo

    def inserir_prazo(self):
        logging.info('Iniciando o processo de inserção de prazo.')
        wait = WebDriverWait(self.driver, 10)

        self.driver.switch_to.default_content()
        try:
            IframesSei(self.driver, 'Arvore documentos').navegar_iframes_sei()
            logging.info('Navegação para o iframe "Arvore documentos" realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao navegar para o iframe "Arvore documentos": {str(e)}')
            return

        try:
            wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '.infraArvoreNoSelecionado, .infraArvoreNo, .noVisitado'))).click()
            logging.info('Elemento de árvore selecionado com sucesso.')
        except TimeoutException:
            logging.error('Elemento de árvore não foi encontrado ou não era clicável dentro do tempo limite.')
            return

        try:
            IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()
            logging.info('Navegação para o frame de exibição de documentos realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao navegar para o frame de exibição de documentos: {str(e)}')
            return

        logging.info('Iniciando o clique no ícone de controle de prazo.')
        IconesBarraProcessoSei(self.driver, "Controle de Prazo").clicar_icone_barra()
        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

        if self.prazo == "0":
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="btnExcluir"]'))).click()
                logging.info('Botão excluir clicado com sucesso.')
                time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
                alert = wait.until(EC.alert_is_present())
                alert.accept()
                logging.info('Alerta de exclusão aceito.')
                return
            except TimeoutException:
                logging.error('Botão excluir não foi encontrado ou não era clicável dentro do tempo limite.')
                return

        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="divOptDias"]/div/label'))).click()
            logging.info('Opção de definir prazo em dias clicada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except TimeoutException:
            logging.error('Elemento para definir prazo em dias não foi encontrado ou não era clicável dentro do tempo limite.')
            return

        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="txtDias"]'))).click()
            logging.info('Campo de dias do prazo clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except TimeoutException:
            logging.error('Campo de dias do prazo não foi encontrado ou não era clicável dentro do tempo limite.')
            return

        try:
            prazo_dias = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'txtDias')))
            prazo_dias.send_keys(self.prazo)
            logging.info(f'Prazo de {self.prazo} dias inserido com sucesso.')
        except TimeoutException:
            logging.error('Campo de dias do prazo não foi encontrado ou não era clicável dentro do tempo limite.')
            return

        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="sbmDefinirControlePrazo"]'))).click()
            logging.info('Botão para definir o controle de prazo clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except TimeoutException:
            logging.error('Botão para definir o controle de prazo não foi encontrado ou não era clicável dentro do tempo limite.')

class MarcadorSei:
    def __init__(self, integrador_selenium, navegador, marcador):
        self.driver = navegador
        self.marcador = marcador
        self.integrador = integrador_selenium

    def procurar_marcador_sei(self):
        logging.info(f'Iniciando a procura pelo marcador: {self.marcador}.')
        # Procura e clica no marcador de interesse, observe que aqui utilizamos o LINK_TEXT para fugir da questão
        # que pode modificar a depender de como foi aberta a página, mas o texto é sempre o mesmo.
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Ver por marcadores"))).click()
            logging.info('Link "Ver por marcadores" clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f'//*[@onclick="filtrarMarcador({self.marcador})"]'))).click()
            logging.info(f'Marcador "{self.marcador}" selecionado com sucesso.')
            self.integrador.log(f'Marcador "{self.marcador}" selecionado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except TimeoutException:
            logging.error(f'Não foi possível encontrar ou clicar no marcador "{self.marcador}" dentro do tempo limite.')
            self.integrador.log("Não há processos para o marcador")

class ProcessoSei:
    def __init__(self, navegador, processo):
        self.driver = navegador
        self.processo = processo

    # Método para acessar um processo específico
    def acessa_processo_sei_especifico(self):
        logging.info(f'Iniciando o acesso ao processo específico: {self.processo}.')
        # Busca por um processo específico
        self.driver.switch_to.default_content()
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="txtPesquisaRapida"]'))).click()
            logging.info('Campo de pesquisa rápida clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
            busca_proc = self.driver.find_element(By.XPATH, '//*[@id="txtPesquisaRapida"]')
            busca_proc.send_keys(self.processo)
            logging.info(f'Número do processo "{self.processo}" inserido com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
            busca_proc.send_keys(Keys.ENTER)
            logging.info('Comando ENTER enviado para iniciar a busca pelo processo.')
            # Confirmação se está na pagina do processo
            processo = NumeroProcesso(self.driver).obter_numero_processo()
            if processo == self.processo:
                return True
        except TimeoutException:
            logging.error('Um dos elementos não foi encontrado ou não era clicável dentro do tempo limite.')
            return False

class MenuDocumentosSei:
    def __init__(self, navegador):
        self.driver = navegador

    def acessa_frame_arvore_documentos_sei(self):
        logging.info('Iniciando o acesso ao frame da árvore de documentos no SEI.')
        self.driver.switch_to.default_content()
        try:
            WebDriverWait(self.driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, 'ifrVisualizacao')))
            logging.info('Switch para o frame "ifrVisualizacao" realizado com sucesso.')
            elemento = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="divArvoreAcoes"]/a[3]/img'))
            )
            elemento.click()
            logging.info('Elemento da árvore de ações clicado com sucesso.')
        except TimeoutException:
            logging.error('O elemento não foi encontrado no tempo especificado.')

MAX_RETRIES = 3
RETRY_INTERVAL = 2  # segundos

class RelatorioCgben:
    def __init__(self, navegador):
        self.driver = navegador

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_fixed(RETRY_INTERVAL))  # Repete até 3 vezes com intervalo de 2 segundos entre tentativas
    def access_table_in_nested_iframes(self):
        """
        Acessa a tabela dentro de iframes aninhados, recarregando se necessário.
        """
        logging.info('Iniciando acesso à tabela dentro de iframes aninhados.')
        # Clica no elemento 'relat[-1]' no iframe 'ifrArvore'
        try:
            relat = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Relatório")
            relat[-1].click()
            logging.info('Elemento "Relatório" clicado com sucesso no iframe "ifrArvore".')
        except IndexError:
            logging.error('Elemento "Relatório" não encontrado. Certifique-se de que o relatório está disponível. Recarregando...')
            raise  # Gera uma exceção para acionar a nova tentativa
        except Exception as e:
            logging.error(f'Erro ao clicar no elemento "Relatório": {str(e)}')
            raise

        # Retorna ao contexto do documento principal (importante!)
        self.driver.switch_to.default_content()

        # Tenta acessar o iframe 'ifrVisualizacao'
        try:
            WebDriverWait(self.driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, 'ifrVisualizacao')))
            logging.info('Switch para o iframe "ifrVisualizacao" realizado com sucesso.')
        except TimeoutException:
            logging.error("Iframe 'ifrVisualizacao' não encontrado. Recarregando...")
            raise  # Gera uma exceção para acionar a nova tentativa

        # Tenta acessar o iframe 'ifrArvoreHtml'
        try:
            WebDriverWait(self.driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, 'ifrArvoreHtml')))
            logging.info('Switch para o iframe "ifrArvoreHtml" realizado com sucesso.')
        except TimeoutException:
            logging.error("Iframe 'ifrArvoreHtml' não encontrado. Recarregando...")
            raise  # Gera uma exceção para acionar a nova tentativa

        # Tenta encontrar a tabela
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, 'table')))
            logging.info('Tabela encontrada com sucesso dentro do iframe "ifrArvoreHtml".')
        except TimeoutException:
            logging.error("Tabela não encontrada. Recarregando...")
            raise  # Gera uma exceção para acionar a nova tentativa

    def extrai_dados_relatorio_cgben(self):
        logging.info('Iniciando extração de dados do relatório CGBEN.')

        try:
            TodasPastasArvoreDocumentos(self.driver).expandir_todas_pastas()
            logging.info('Todas as pastas da árvore de documentos foram expandidas com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao expandir todas as pastas da árvore de documentos: {str(e)}')
            return

        try:
            self.access_table_in_nested_iframes()
            logging.info('Acesso à tabela dentro dos iframes aninhados realizado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao acessar tabela nos iframes aninhados: {str(e)}')
            return

        tabelas = self.driver.find_elements(By.TAG_NAME, 'table')

        # Vamos guardar as matrículas encontradas aqui
        matriculas_encontradas = []

        # Loop para percorrer todas as tabelas
        for i, tabela in enumerate(tabelas):
            linhas = tabela.find_elements(By.TAG_NAME, 'tr')

            for linha in linhas:
                if "Matrícula SIAPE:" in linha.text:
                    logging.info(f"Encontrado na tabela {i + 1}: {linha.text}")

                    # Usamos Regex para pegar o número da matrícula na linha
                    match = re.search(r'Matrícula SIAPE:\s*(\d{6,8})', linha.text)
                    if match:
                        matricula = match.group(1)
                        matriculas_encontradas.append(matricula)
                        logging.info(f"Matrícula encontrada: {matricula}")

        # Verificar se encontrou alguma matrícula
        if len(matriculas_encontradas) >= 2:
            benef_mat = matriculas_encontradas[0]
            inst_mat = matriculas_encontradas[1]
            logging.info(f"Matrícula da beneficiária: {benef_mat}")
            logging.info(f"Matrícula do instituidor: {inst_mat}")
            return benef_mat, inst_mat
        else:
            logging.warning('Número insuficiente de matrículas encontradas para determinar beneficiária e instituidor.')
            return None, None

class NumeroProcesso:
    def __init__(self, navegador):
        self.driver = navegador

    def obter_numero_processo(self):
        try:
            WebDriverWait(self.driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, 'ifrArvore')))
            process = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'infraArvoreNoSelecionado'))).text.strip()
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
            return process
        except TimeoutException:
            print("Um dos elementos não foi encontrado dentro do tempo limite.")
            return None

    def obter_nome_tecnico(self):
        try:
            # Aguarda e muda para o frame 'ifrArvore'
            WebDriverWait(self.driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, 'ifrArvore')))

            # Aguarda o elemento do processo e clica
            process = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'infraArvoreNoSelecionado')))
            process.click()

            # Simula comportamento humano
            time.sleep(TempoAleatorio().tempo_aleatorio())

            # Navega para o frame de documentos
            IframesSei(self.driver, 'Exibe frame documentos').navegar_iframes_sei()

            # Aguarda a presença do elemento contendo as informações de técnico
            elemento_div = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.ID, "divArvoreInformacao"))
            )

            # Procura todos os elementos <a> dentro do div
            elementos_a = elemento_div.find_elements(By.TAG_NAME, "a")

            # Itera sobre os elementos <a> para encontrar o técnico
            for elemento in elementos_a:
                alt_texto = elemento.get_attribute('alt')
                title_texto = elemento.get_attribute('title')

                # Verifica se o técnico está atribuído (considerando que ele possui email ou nome nos atributos)
                if "@" in elemento.text:
                    nome_tecnico = alt_texto if alt_texto else title_texto
                    IframesSei(self.driver, 'Arvore documentos').navegar_iframes_sei()
                    return nome_tecnico.strip() if nome_tecnico else "processo sem atribuição"



        except Exception as e:

            print(f"Erro ao obter nome do técnico: {e}")

            return "processo sem atribuição"

class TodasPastasArvoreDocumentos:
    def __init__(self, navegador):
        self.driver = navegador

    def expandir_todas_pastas(self):
        logging.info('Iniciando a expansão de todas as pastas na árvore de documentos.')
        try:
            self.driver.switch_to.default_content()
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
            IframesSei(self.driver, 'Arvore documentos').navegar_iframes_sei()
            logging.info('Navegação para o iframe "Arvore documentos" realizada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

            # Espera até que o elemento com o XPath especificado esteja presente. O tempo máximo de espera é 10 segundos.
            elemento = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, '//img[@title="Abrir todas as Pastas"]'))
            )
            elemento.click()
            logging.info('Clique no botão "Abrir todas as Pastas" realizado com sucesso.')

            # Espera um pouco para o clique ter efeito
            time.sleep(2)

        except TimeoutException:
            logging.warning('A árvore já está expandida ou o elemento "Abrir todas as Pastas" não está presente.')
        except Exception as e:
            logging.error(f'Ocorreu um erro durante a expansão das pastas: {str(e)}')

class PlanilhaCalculoExante:
    def __init__(self, navegador, processo, info_beneficio, dic_calc):
        self.driver = navegador
        self.processo = processo
        self.info_beneficio = info_beneficio
        self.dic_calc = dic_calc

    def incluir_planilha_calculo(self):
        logging.info('Iniciando a inclusão da planilha de cálculo ex-ante.')
        main_window_handle = self.driver.current_window_handle
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        try:
            IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()
            logging.info('Navegação para o iframe "Exibe frame documentos" realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao navegar para o iframe "Exibe frame documentos": {str(e)}')
            return

        try:
            self.driver.find_element(By.XPATH, '//*[@id="divArvoreAcoes"]/a[1]/img').click()
            logging.info('Botão para iniciar a criação da planilha de cálculo clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except Exception as e:
            logging.error(f'Erro ao clicar no botão de criação da planilha de cálculo: {str(e)}')
            return

        try:
            self.driver.find_element(By.XPATH, '//*[@id="txtFiltro"]').send_keys('Planilha de Cálculo (Exercícios Anteriores)', Keys.TAB)
            logging.info('Filtro "Planilha de Cálculo (Exercícios Anteriores)" inserido com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

            elemento = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Planilha de Cálculo (Exercícios Anteriores)')]")
            elemento.click()
            logging.info('Elemento "Planilha de Cálculo (Exercícios Anteriores)" clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except Exception as e:
            logging.error(f'Erro ao selecionar a planilha de cálculo: {str(e)}')
            return

        try:
            self.driver.find_element(By.XPATH, '//*[@id="divOptProtocoloDocumentoTextoBase"]/div/label').click()
            logging.info('Opção de protocolo de documento base selecionada.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

            self.driver.find_element(By.XPATH, '//*[@id="txtProtocoloDocumentoTextoBase"]').send_keys("35549491")
            logging.info('Número do protocolo de documento base inserido com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

            self.driver.find_element(By.XPATH, '//*[@id="divOptRestrito"]/div/label').click()
            logging.info('Opção de restrição selecionada.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

            drop = Select(self.driver.find_element(By.XPATH, '//*[@id="selHipoteseLegal"]'))
            drop.select_by_visible_text("Informação Pessoal (Art. 31 da Lei nº 12.527/2011)")
            logging.info('Hipótese legal "Informação Pessoal" selecionada.')
        except Exception as e:
            logging.error(f'Erro ao preencher as informações iniciais da planilha: {str(e)}')
            return

        # Passo 1: Armazene os identificadores de janela atuais antes de abrir a nova janela
        janelas_existentes = self.driver.window_handles

        try:
            self.driver.find_element(By.XPATH, '//*[@id="btnSalvar"]').click()
            logging.info('Botão "Salvar" clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        except Exception as e:
            logging.error(f'Erro ao clicar no botão "Salvar": {str(e)}')
            return

        # Passo 3: Aguarde até que uma nova janela esteja disponível e então obtenha os identificadores novamente
        try:
            WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) == len(janelas_existentes) + 1)
            novas_janelas = self.driver.window_handles
            logging.info('Nova janela detectada após salvar a planilha.')
        except TimeoutException:
            logging.error('Timeout ao aguardar a nova janela ser aberta após salvar a planilha.')
            return

        # Passo 4: Encontre o novo identificador de janela e alterne para ele
        nova_janela = [janela for janela in novas_janelas if janela not in janelas_existentes][0]
        self.driver.switch_to.window(nova_janela)
        logging.info('Alternado para a nova janela com a planilha de cálculo.')

        try:
            self.driver.maximize_window()
            frame = self.driver.find_elements(By.CLASS_NAME, 'cke_wysiwyg_frame')
            self.driver.switch_to.frame(frame[2])
            logging.info('Switch para o frame de edição da planilha realizado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

            # Preenchendo os campos na planilha
            self.driver.find_element(By.XPATH, '/html/body/table[1]/tbody/tr[3]/td[2]').send_keys(self.processo)
            logging.info(f'Número do processo {self.processo} inserido com sucesso na planilha.')
        except Exception as e:
            logging.error(f'Erro ao interagir com o frame de edição da planilha: {str(e)}')
            return

        # Resto do código para preenchimento dos valores da planilha e totalizações
        try:
            # Pegando todas as chaves que representam meses
            primeiro_mes, ultimo_mes = MesIniMesFin(self.dic_calc).mes_ini_mes_fin()
            frase = f"Pagamento retroativo de {primeiro_mes.upper()} até {ultimo_mes.upper()}."
            logging.info('Frase montada para pagamento retroativo: ' + frase)

            self.driver.find_element(By.XPATH, '/html/body/table[1]/tbody/tr[4]/td[2]').click()
            self.driver.find_element(By.XPATH, '/html/body/table[1]/tbody/tr[4]/td[2]').send_keys(frase)
            logging.info('Frase sobre o pagamento retroativo inserida com sucesso.')

            # Código subsequente para preencher a planilha...
        except Exception as e:
            logging.error(f'Erro ao preencher a planilha de cálculo: {str(e)}')
            return

        # Finalização
        try:
            self.driver.switch_to.default_content()
            self.driver.find_element(By.XPATH, '//*[@id="cke_145_label"]').click()
            logging.info('Planilha de cálculo concluída e janela fechada com sucesso.')
            time.sleep(2)
            self.driver.close()
            self.driver.switch_to.window(main_window_handle)
            logging.info('Retornado à janela principal após o fechamento da planilha.')
        except Exception as e:
            logging.error(f'Erro ao finalizar a inclusão da planilha de cálculo: {str(e)}')
            return

        return frase

    def _preencher_campo(self, linha, coluna, valor):
        xpath = f'/html/body/table[3]/tbody/tr[{linha}]/td[{coluna}]/p'
        try:
            self.driver.find_element(By.XPATH, xpath).click()
            self.driver.find_element(By.XPATH, xpath).send_keys(valor, Keys.TAB)
            logging.info(f'Campo linha {linha}, coluna {coluna} preenchido com valor: {valor}')
        except Exception as e:
            logging.error(f'Erro ao preencher campo linha {linha}, coluna {coluna} com valor {valor}: {str(e)}')

def iframe_retry_decorator(max_tentativas=3, delay_segundos=2):
    """
    Decorator que utiliza o Tenacity para implementar retry em operações com iframes.
    Em caso de falha, recarrega a página antes de tentar novamente.

    Args:
        max_tentativas (int): Número máximo de tentativas
        delay_segundos (int): Tempo de espera entre tentativas em segundos
    """

    def decorator(func):
        @retry(
            stop=stop_after_attempt(max_tentativas),
            wait=wait_fixed(delay_segundos),
            retry=retry_if_exception_type((TimeoutException, StaleElementReferenceException)),
            before_sleep=lambda retry_state: _before_retry(retry_state, func.__name__)
        )
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except (TimeoutException, StaleElementReferenceException) as e:
                logging.warning(f"Erro ao acessar iframe '{self.iframe}': {str(e)}")
                self.driver.refresh()
                raise  # Re-lança a exceção para o Tenacity gerenciar o retry

        return wrapper

    return decorator

def _before_retry(retry_state, method_name):
    """Função executada antes de cada nova tentativa"""
    exception = retry_state.outcome.exception()
    attempt = retry_state.attempt_number
    logging.info(f"Tentativa {attempt} falhou para o método '{method_name}'. "
                 f"Próxima tentativa em {retry_state.next_action.sleep} segundos.")

class IframesSei:
    def __init__(self, navegador, iframe):
        self.driver = navegador
        self.iframe = iframe

    @iframe_retry_decorator(max_tentativas=3, delay_segundos=2)
    def navegar_iframes_sei(self):
        logging.info(f'Iniciando a navegação para o iframe: {self.iframe}')

        if self.iframe == "Arvore documentos":
            self.driver.switch_to.default_content()
            WebDriverWait(self.driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.NAME, 'ifrArvore')))
            logging.info('Switch para o iframe "Arvore documentos" realizado com sucesso.')
            return True

        elif self.iframe == "Exibe frame documentos":
            self.driver.switch_to.default_content()
            WebDriverWait(self.driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it((By.NAME, 'ifrVisualizacao')))
            logging.info('Switch para o iframe "Exibe frame documentos" realizado com sucesso.')

        elif self.iframe == "Exibe documentos":
            WebDriverWait(self.driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, 'ifrArvoreHtml')))
            logging.info('Switch para o iframe "Exibe documentos" realizado com sucesso.')

class PaginaMovimentacoes:
    def __init__(self, navegador, processo):
        self.driver = navegador
        self.processo = processo

    def acessar_movimentacoes(self):
        ProcessoSei(self.driver, self.processo).acessa_processo_sei_especifico()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        IframesSei(self.driver, "Arvore documentos").navegar_iframes_sei()
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="divConsultarAndamento"]/a'))).click()
            time.sleep(2)  # Simula comportamento humano
        except TimeoutException:
            print("Não foi possível clicar em consultar andamento.")
            self.driver.refresh()
            raise

        IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='ancTipoHistorico']")))
            element_text = element.text

            if 'Ver histórico completo' in element_text:
                element.click()
        except TimeoutException:
            print("Não foi possível clicar em histórico")
            self.driver.refresh()
            raise
class DocumentoExternoSei:
    def __init__(self, navegador, tipo, nome_arvore, arquivo):
        self.driver = navegador
        self.nome_arvore = nome_arvore
        self.arquivo = arquivo
        self.tipo = tipo

    def incluir_documento_externo(self):
        logging.info(f'Iniciando a inclusão do documento externo: {self.nome_arvore}.')
        wait = WebDriverWait(self.driver, 10)
        self.driver.implicitly_wait(5)
        # self.driver.switch_to.default_content()
        tempo_espera = 0.5

        try:
            IframesSei(self.driver, 'Arvore documentos').navegar_iframes_sei()
            logging.info('Navegação para o iframe "Arvore documentos" realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao navegar para o iframe "Arvore documentos": {str(e)}')
            return

        try:
            wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '.infraArvoreNoSelecionado, .infraArvoreNo, .noVisitado'))).click()
            logging.info('Elemento da árvore de documentos clicado com sucesso.')
        except TimeoutException:
            logging.error('Elemento da árvore de documentos não foi encontrado ou não era clicável dentro do tempo limite.')
            return

        self.driver.switch_to.default_content()
        try:
            IframesSei(self.driver, 'Exibe frame documentos').navegar_iframes_sei()
            logging.info('Navegação para o iframe "Exibe frame documentos" realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao navegar para o iframe "Exibe frame documentos": {str(e)}')
            return

        try:
            IconesBarraProcessoSei(self.driver, "Incluir Documento").clicar_icone_barra()
            logging.info('Ícone "Incluir Documento" clicado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao clicar no ícone "Incluir Documento": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

        try:
            # Clica no elemento para selecionar a série do documento
            element = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="tblSeries"]/tbody/tr[1]/td/a[2]'))
            )
            element.click()
            logging.info('Elemento para selecionar a série do documento clicado com sucesso.')

            # Seleciona o tipo de série do documento
            element = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="selSerie"]'))
            )
            element.send_keys(self.tipo)
            logging.info(f'Tipo de série do documento "{self.tipo}" selecionado com sucesso.')

            time.sleep(tempo_espera)
            time.sleep(tempo_espera)
            time.sleep(tempo_espera)
            time.sleep(tempo_espera)
            # Insere a data de elaboração
            element = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="txtDataElaboracao"]'))
            )
            element.send_keys(datetime.now().strftime('%d/%m/%Y'))
            logging.info('Data de elaboração inserida com sucesso.')

            time.sleep(tempo_espera)
            time.sleep(tempo_espera)
            # Insere o nome da árvore do documento
            element = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="txtNomeArvore"]'))
            )
            element.send_keys(self.nome_arvore)
            logging.info(f'Nome da árvore do documento "{self.nome_arvore}" inserido com sucesso.')

            time.sleep(tempo_espera)
            # Seleciona a opção "Documento nato"
            element = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="divOptNato"]/div/label'))
            )
            element.click()
            logging.info('Opção "Documento nato" selecionada com sucesso.')
            time.sleep(tempo_espera)

            # Seleciona a opção de restrição
            element = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="divOptRestrito"]/div/label'))
            )
            element.click()
            logging.info('Opção de restrição selecionada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

            # Seleciona a hipótese legal
            element = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="selHipoteseLegal"]'))
            )
            drop = Select(element)
            drop.select_by_visible_text("Informação Pessoal (Art. 31 da Lei nº 12.527/2011)")
            logging.info('Hipótese legal "Informação Pessoal" selecionada com sucesso.')


        except Exception as e:
            logging.error(f'Erro ao preencher as informações do documento externo: {str(e)}')
            return

        try:
            self.driver.find_element(By.XPATH, '//*[@id="lblArquivo"]').click()
            logging.info('Botão para incluir arquivo clicado com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

            inclui_arquivo = AnexoSei(self.arquivo)
            inclui_arquivo.inserir_anexo()
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
            logging.info(f'Arquivo "{self.arquivo}" anexado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao anexar o arquivo "{self.arquivo}": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

        try:
            # Aguardar até que o elemento com a classe 'infraTd' esteja presente (até 30 segundos)
            element = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, 'infraTd')))
            logging.info('Elemento "infraTd" encontrado com sucesso, pronto para salvar.')
            # Clicar no botão "Salvar"
            self.driver.find_element(By.XPATH, '//*[@id="btnSalvar"]').click()
            logging.info('Botão "Salvar" clicado com sucesso para incluir o documento externo.')
            time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
            # Aguardar até que o elemento com o ID 'divArvoreInformacao' esteja presente (até 30 segundos)
            element = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.ID, 'divArvoreInformacao'))
            )
            logging.info('Elemento "divArvoreInformacao" encontrado com sucesso.')
        except TimeoutException:
            logging.error('Elemento "infraTd" ou botão "Salvar" não foi encontrado dentro do tempo limite.')
        except Exception as e:
            logging.error(f'Erro inesperado ao salvar o documento externo: {str(e)}')

class AnexoSei:
    def __init__(self, arquivo):
        self.arquivo = arquivo

    def inserir_anexo(self):
        logging.info(f'Iniciando a inserção do anexo: {self.arquivo}.')
        try:
            app = Application().connect(title_re="Abrir")
            time.sleep(0.5)
            dlg = app.window(title_re="Abrir")
            time.sleep(0.5)

            # Verificar se o caminho já é absoluto
            if os.path.isabs(self.arquivo):
                # Se já é caminho absoluto, usar diretamente
                caminho = self.arquivo
                logging.info(f'Usando caminho absoluto fornecido: {caminho}')
            else:
                # Se é caminho relativo, construir baseado no diretório do script
                if getattr(sys, 'frozen', False):
                    caminho_script_atual = os.path.dirname(sys.executable)
                else:
                    caminho_script_atual = os.path.abspath(os.path.dirname(__file__))

                # Usar o arquivo como caminho relativo ao diretório do script
                caminho = os.path.join(caminho_script_atual, self.arquivo)
                logging.info(f'Construindo caminho relativo: {caminho}')

            # Verificar se o arquivo existe antes de tentar anexar
            if not os.path.exists(caminho):
                logging.error(f'ERRO: Arquivo não encontrado no caminho: {caminho}')
                raise FileNotFoundError(f'Arquivo não encontrado: {caminho}')

            caminho_com_formato_dlg = caminho.replace(" ", "{SPACE}")

            dlg.type_keys(caminho_com_formato_dlg)
            logging.info(f'Caminho do arquivo inserido na janela de diálogo: {caminho}.')
            time.sleep(0.5)
            dlg.type_keys('{ENTER}')
            logging.info('Arquivo anexado com sucesso.')

        except Exception as e:
            logging.error(f'Erro ao inserir o anexo "{self.arquivo}": {str(e)}')
            raise  # Re-propagar a exceção para que seja tratada pela classe pai

class DocumentosArvoreSei:
    def __init__(self, navegador, texto_parcial):
        self.driver = navegador
        self.texto_parcial = texto_parcial


    def clicar_no_documento(self):

        logging.info(f'Iniciando busca pelo documento com o texto parcial: {self.texto_parcial}.')
        elementos = self.driver.find_elements(By.CLASS_NAME, "infraArvoreNo")
        elementos_filtrados = [elem for elem in elementos if self.texto_parcial in elem.text]
        print("Clica documento")
        print(len(elementos))
        print(len(elementos_filtrados))

        if elementos_filtrados:
            try:
                # Clica no último elemento encontrado
                elementos_filtrados[-1].click()
                logging.info(f'Documento com texto parcial "{self.texto_parcial}" clicado com sucesso.')
                time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
                return True
            except Exception as e:
                logging.error(f'Erro ao clicar no documento com texto parcial "{self.texto_parcial}": {str(e)}')
                return False
        else:
            logging.warning(f'Nenhum documento encontrado com o texto parcial "{self.texto_parcial}".')
            return False

    def extrair_numeroSEI_do_ultimo_elemento(self):
        logging.info(f'Iniciando extração do número entre parênteses para o último elemento com texto parcial: {self.texto_parcial}.')
        elementos = self.driver.find_elements(By.CLASS_NAME, "infraArvoreNo")
        elementos_filtrados = [elem for elem in elementos if self.texto_parcial in elem.text]
        print("Clica documento")
        print(len(elementos))
        print(len(elementos_filtrados))
        if elementos_filtrados:
            try:
                # Pega o texto do último elemento filtrado
                texto_ultimo_elemento = elementos_filtrados[-1].text
                # Usa regex para capturar o número entre parênteses no final do texto
                match = re.search(r'\((\d+)\)$', texto_ultimo_elemento)
                if match:
                    numero = match.group(1)
                    logging.info(f'Número extraído com sucesso: {numero}')
                    return numero
                else:
                    logging.warning(f'Nenhum número entre parênteses encontrado no texto: "{texto_ultimo_elemento}".')
                    return None
            except Exception as e:
                logging.error(f'Erro ao extrair número do último elemento: {str(e)}')
                return None
        else:
            logging.warning(f'Nenhum elemento encontrado com o texto parcial "{self.texto_parcial}".')
            return None

    def extrair_qtd_elementos(self):
        self.driver.switch_to.default_content()
        IframesSei(self.driver, "Arvore documentos").navegar_iframes_sei()
        time.sleep(0.5)
        logging.info(
            f"Iniciando extração do número entre parênteses para o último elemento com texto parcial: {self.texto_parcial}.")
        elementos = self.driver.find_elements(By.CLASS_NAME, "infraArvoreNo")
        elementos_filtrados = [elem for elem in elementos if self.texto_parcial in elem.text]
        print(elementos)
        print(elementos_filtrados)

        # Conta o número de elementos filtrados
        qtd_elementos = len(elementos_filtrados)

        logging.info(f"Quantidade de elementos encontrados com o texto parcial: {qtd_elementos}")

        # Retorna a quantidade de elementos encontrados
        return qtd_elementos

class CapturaDadosPlanilha:
    def __init__(self, navegador, processo):
        self.driver = navegador
        self.numero_processo = processo

    def capturar_dados_planilha(self):
        logging.info(f'Iniciando a captura de dados da planilha para o processo: {self.numero_processo}.')
        try:
            TodasPastasArvoreDocumentos(self.driver).expandir_todas_pastas()
            logging.info('Expansão de todas as pastas na árvore de documentos realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao expandir todas as pastas na árvore de documentos: {str(e)}')

class TrocaMarcadorSEi:
    def __init__(self, navegador, mensagem, remover, inserir=""):
        self.driver = navegador
        self.mensagem = mensagem
        self.remover = remover
        self.inserir = inserir

    # Opção 1: Usar o decorador diretamente com os parâmetros
    @retry(
        retry=(retry_if_result(lambda x: x is False) | retry_if_exception_type(TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def _verifica_marcador_inserido(self):
        """
        Verifica se o marcador foi inserido corretamente.
        Retorna True se encontrado, False se não encontrado.
        """
        logging.info(f'Verificando presença do marcador com title contendo "{self.inserir}"...')
        wait = WebDriverWait(self.driver, 3)

        try:
            time.sleep(1)  # Tempo para garantir que a página atualizou
            xpath_busca = f'//img[contains(@title, "{self.inserir}")]'
            elemento = wait.until(EC.presence_of_element_located((By.XPATH, xpath_busca)))
            logging.info(f'Elemento com title contendo "{self.inserir}" encontrado com sucesso.')
            return True
        except TimeoutException:
            logging.warning(f'Elemento com title contendo "{self.inserir}" NÃO foi encontrado nesta tentativa.')
            # Aqui você pode escolher entre:
            # 1. Retornar False (o retry vai tentar novamente)
            return False
            # 2. Ou re-lançar a exceção (o retry também vai tentar novamente)
            # raise

    def trocar_marcador(self):
        """
        Realiza a troca de marcador no sistema SEI.
        """
        logging.info(f'Iniciando a troca de marcador: Remover "{self.remover}", Inserir "{self.inserir}".')
        wait = WebDriverWait(self.driver, 3)

        # Navegação inicial
        try:
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            IframesSei(self.driver, 'Arvore documentos').navegar_iframes_sei()
            logging.info('Navegação para o iframe "Arvore documentos" realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao navegar para o iframe "Arvore documentos": {str(e)}')
            return False

        # Clique no elemento da árvore
        try:
            wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '.infraArvoreNoSelecionado, .infraArvoreNo, .noVisitado'))).click()
            logging.info('Elemento da árvore de documentos clicado com sucesso.')
        except TimeoutException:
            logging.error(
                'Elemento da árvore de documentos não foi encontrado ou não era clicável dentro do tempo limite.')
            return False

        self.driver.switch_to.default_content()

        # Navegação para frame de documentos
        try:
            IframesSei(self.driver, 'Exibe frame documentos').navegar_iframes_sei()
            logging.info('Navegação para o iframe "Exibe frame documentos" realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao navegar para o iframe "Exibe frame documentos": {str(e)}')
            return False

        # Abrir gerenciador de marcadores
        try:
            IconesBarraProcessoSei(self.driver, "Gerenciar Marcador").clicar_icone_barra()
            logging.info('Ícone "Gerenciar Marcador" clicado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao clicar no ícone "Gerenciar Marcador": {str(e)}')
            return False

        time.sleep(TempoAleatorio().tempo_aleatorio())

        # Remover marcador existente se especificado
        if self.remover != "":
            try:
                table = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'table')))
                rows = table.find_elements(By.TAG_NAME, "tr")
                logging.info('Tabela de marcadores carregada com sucesso.')

                for row in rows[1:]:
                    try:
                        if row.find_element(By.XPATH, "td[2]").text.strip() == self.remover:
                            target_link = row.find_element(By.XPATH, "td[6]//a[img[@src='/infra_css/svg/remover.svg']]")
                            ActionChains(self.driver).move_to_element(target_link).click(target_link).perform()
                            logging.info(f'Marcador "{self.remover}" removido com sucesso.')

                            alert = wait.until(EC.alert_is_present())
                            alert.accept()

                            if self.inserir == "":
                                return True

                            time.sleep(TempoAleatorio().tempo_aleatorio())
                            break
                    except Exception as e:
                        logging.debug(f'Erro ao processar linha da tabela: {str(e)}')
                        continue

            except TimeoutException:
                logging.error('Tabela de marcadores não foi encontrada dentro do tempo limite.')
                return False

        # Adicionar novo marcador se especificado
        if self.inserir != "":
            try:
                # Clicar no botão adicionar
                try:
                    wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="btnAdicionar"]'))).click()
                    logging.info('Botão "Adicionar" clicado com sucesso.')
                except:
                    logging.warning('Botão "Adicionar" não encontrado, tentando continuar...')

                time.sleep(TempoAleatorio().tempo_aleatorio())

                # Selecionar marcador no dropdown
                dropdown = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".dd-select")))
                dropdown.click()
                logging.info('Dropdown de seleção de marcador aberto com sucesso.')

                items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".dd-option-text")))
                time.sleep(0.6)

                marcador_encontrado = False
                for item in items:
                    if item.text == self.inserir:
                        time.sleep(0.6)
                        item.click()
                        logging.info(f'Marcador "{self.inserir}" selecionado com sucesso.')
                        marcador_encontrado = True
                        break

                if not marcador_encontrado:
                    logging.error(f'Marcador "{self.inserir}" não foi encontrado na lista.')
                    return False

            except TimeoutException:
                logging.error('Erro ao adicionar o novo marcador ou ao selecionar o marcador na lista.')
                return False

            # Inserir mensagem e salvar
            try:
                time.sleep(TempoAleatorio().tempo_aleatorio())
                wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="txaTexto"]'))).send_keys(self.mensagem)
                logging.info(f'Mensagem "{self.mensagem}" inserida com sucesso.')

                wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="sbmSalvar"]'))).click()
                logging.info('Botão "Salvar" clicado com sucesso.')
            except TimeoutException:
                logging.error('Erro ao inserir a mensagem ou clicar no botão "Salvar".')
                return False

        # Verificar se o marcador foi inserido (com retry)
        try:
            IframesSei(self.driver, 'Arvore documentos').navegar_iframes_sei()
            logging.info('Navegação para o iframe "Arvore documentos" realizada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao navegar para o iframe "Arvore documentos": {str(e)}')
            return False

        # Verificar marcador com retry
        try:
            resultado = self._verifica_marcador_inserido()
            if not resultado:
                logging.error('Falha ao verificar a existência do marcador após múltiplas tentativas.')
                return False
        except Exception as e:
            logging.error(f'Erro ao verificar o marcador com retry: {str(e)}')
            return False

        # Finalizar retornando ao controle de processos
        try:
            IconesBarraProcessoSei(self.driver, "Controle de Processos").clicar_icone_barra()
            logging.info('Ícone "Controle de Processos" clicado com sucesso, finalizando a troca de marcador.')
            self.driver.switch_to.default_content()
        except Exception as e:
            logging.error(f'Erro ao clicar no ícone "Controle de Processos": {str(e)}')
            return False

        return True

class IncluiNotaTecnicaExante:
    def __init__(self, navegador, dados_nottec):
        self.driver = navegador
        self.dados_nota_tecnica = dados_nottec

    def incluir_nota_tecnica_exante(self):
        logging.info('Iniciando a inclusão da Nota Técnica Exante.')
        self.driver.implicitly_wait(5)
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('ifrArvore')

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            # Espera até que o elemento com o XPath especificado esteja presente. O tempo máximo de espera é 10 segundos.
            elemento = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH, '//img[@title="Abrir todas as Pastas"]'))
            )
            elemento.click()
            logging.info('Clique em "Abrir todas as Pastas" realizado com sucesso.')
        except TimeoutException:
            logging.error("O elemento para abrir todas as pastas não foi encontrado no tempo especificado.")

        try:
            protoc_comp = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Comprovante de lançamento em módulo")
            planil_calc = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Planilha de Cálculo")

            ultimo_protocol = protoc_comp[-1]
            ultima_planilha = planil_calc[-1]

            protocol_txt = ultimo_protocol.text.strip()
            planilha_txt = ultima_planilha.text.strip()
            logging.info(f'Últimos elementos obtidos: Protocolo "{protocol_txt}", Planilha "{planilha_txt}".')
        except IndexError:
            logging.error('Erro ao buscar os últimos comprovantes ou planilhas disponíveis. Verifique se eles estão presentes.')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            protocol = ExtraiNumerais(protocol_txt).extrair_numerais()
            planilha = ExtraiNumerais(planilha_txt).extrair_numerais()
            logging.info(f'Numerais extraídos: Protocolo "{protocol}", Planilha "{planilha}".')
        except Exception as e:
            logging.error(f'Erro ao extrair numerais dos textos obtidos: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('ifrVisualizacao')
        try:
            self.driver.find_element(By.XPATH, '/html/body/div[1]/div/div/div[2]/div/a[1]/img').click()
            logging.info('Clique no ícone para incluir Nota Técnica realizado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao clicar no ícone para incluir Nota Técnica: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.XPATH, '//*[@id="txtFiltro"]').send_keys('Nota Técnica', Keys.TAB, Keys.ENTER)
            logging.info('Filtro "Nota Técnica" aplicado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao aplicar filtro "Nota Técnica": {str(e)}')
            return

        processador = ProcessaValores(self.dados_nota_tecnica['dicCalc'])
        soma_total = processador.soma_total_valores()
        logging.info(f'Valor total calculado: {soma_total}.')

        try:
            self.driver.find_element(By.XPATH, '//*[@id="divOptProtocoloDocumentoTextoBase"]/div/label').click()
            time.sleep(TempoAleatorio().tempo_aleatorio())
            if soma_total < 30000:
                self.driver.find_element(By.XPATH, '//*[@id="txtProtocoloDocumentoTextoBase"]').send_keys("35550049")
            elif soma_total >= 30000:
                self.driver.find_element(By.XPATH, '//*[@id="txtProtocoloDocumentoTextoBase"]').send_keys("35550639")
            logging.info('Protocolo do documento base inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir protocolo do documento base: {str(e)}')
            return

        try:
            self.driver.find_element(By.ID, 'txtNomeArvore').send_keys(' de Exercícios Anteriores')
            self.driver.find_element(By.XPATH, '//*[@id="divOptRestrito"]/div/label').click()
            time.sleep(TempoAleatorio().tempo_aleatorio())
            drop = Select(self.driver.find_element(By.XPATH, '//*[@id="selHipoteseLegal"]'))
            drop.select_by_visible_text("Informação Pessoal (Art. 31 da Lei nº 12.527/2011)")
            logging.info('Campos da Nota Técnica preenchidos com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao preencher os campos da Nota Técnica: {str(e)}')
            return

        try:
            processo_Sei = self.dados_nota_tecnica['numSei']
            proc_Siape = self.dados_nota_tecnica['numSiape']
            objeto = self.dados_nota_tecnica['objeto']
            interessado = self.dados_nota_tecnica['nomeBenef']
            orgao = self.dados_nota_tecnica['orgao']
            mat_bene = self.dados_nota_tecnica['matBene']

            # Preparar a data e valores em texto
            dados = processador.resultado
            ordem_meses = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
                           'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12}

            anos = sorted(dados.keys())
            meses_primeiro_ano = sorted(dados[anos[0]].keys(), key=lambda x: ordem_meses[x])
            meses_ultimo_ano = sorted(dados[anos[-1]].keys(), key=lambda x: ordem_meses[x])

            mes_inicio = meses_primeiro_ano[0].upper()
            ano_inicio = anos[0]
            mes_fim = meses_ultimo_ano[-1].upper()
            ano_fim = anos[-1]

            meses_completos = {
                "JAN": "Janeiro", "FEV": "Fevereiro", "MAR": "Março", "ABR": "Abril",
                "MAI": "Maio", "JUN": "Junho", "JUL": "Julho", "AGO": "Agosto",
                "SET": "Setembro", "OUT": "Outubro", "NOV": "Novembro", "DEZ": "Dezembro"
            }

            mes_inicio_nome = meses_completos[mes_inicio]
            mes_fim_nome = meses_completos[mes_fim]

            if mes_inicio == mes_fim and ano_inicio == ano_fim:
                data_texto = f"{mes_inicio_nome} de {ano_inicio}"
            else:
                data_texto = f"{mes_inicio_nome} de {ano_inicio} a {mes_fim_nome} de {ano_fim}"

            locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
            valor_formatado = locale.currency(soma_total, grouping=True, symbol=True)
            valor_extenso = num2words(soma_total, lang='pt_BR', to='currency')
            logging.info(f'Data e valores formatados: {data_texto}, {valor_formatado}, {valor_extenso}.')
        except Exception as e:
            logging.error(f'Erro ao preparar os dados para inclusão da Nota Técnica: {str(e)}')
            return

        # Resto do código para preencher os campos na Nota Técnica
        # Adicionando logging em cada etapa da inclusão dos dados no frame e preenchimento dos campos.

        return

class NivelDetalheTecnicos:
    def __init__(self, navegador):
        self.driver = navegador

    def detalhar_nivel_tecnicos(self):
        logging.info("Configurando nível de detalhe para padronizar a tabela.")
        try:
            # 1. Clicar no botão para abrir a janela de configuração
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="ancNivelDetalhe"]'))).click()
            time.sleep(2) 
        except TimeoutException:
            logging.error("Falha ao clicar em 'Configurar Nível de Detalhe'. Botão não encontrado.")
            return

        # 2. Alternar para o iframe da janela de configuração
        try:
            # O nome do iframe é 'modal-frame', conforme o seu código anterior
            WebDriverWait(self.driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it((By.NAME, 'modal-frame')))
            logging.info("Alternado para o iframe 'modal-frame'.")
        except TimeoutException:
            logging.error("Janela de nível de detalhe (iframe 'modal-frame') não encontrada.")
            return

        # 3. Desmarcar todos os checkboxes e marcar apenas o de 'Atribuição'
        try:
            checkboxes = self.driver.find_elements(By.CLASS_NAME, 'infraCheckboxInput')
            checkbox_atribuicao = self.driver.find_element(By.ID, 'chkSinAtribuicao')

            # Desmarcar todos os outros checkboxes
            for checkbox in checkboxes:
                if checkbox.is_selected():
                    self.driver.execute_script("arguments[0].click();", checkbox)
                    time.sleep(0.1) # Pequena pausa para garantir a desmarcação

            # Marcar o checkbox de Atribuição (se ele não estiver marcado)
            if not checkbox_atribuicao.is_selected():
                self.driver.execute_script("arguments[0].click();", checkbox_atribuicao)

            logging.info("Configuração de nível de detalhe alterada: Apenas 'Atribuição' selecionado.")
        
        except NoSuchElementException as e:
            logging.error(f"Não foi possível encontrar um dos checkboxes ou o checkbox de Atribuição: {e}")
            self.driver.switch_to.default_content()
            return
        
        # 4. Clicar no botão Salvar
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="divInfraBarraComandosSuperior"]/button'))).click()
            time.sleep(1)
            logging.info("Botão 'Salvar' clicado com sucesso.")
        except TimeoutException:
            logging.error("Não foi possível clicar no botão salvar da janela de configurar nível de detalhe.")
        
        # 5. Voltar para o contexto da página principal
        self.driver.switch_to.default_content()
        logging.info("Voltado para o contexto da página principal.")

class NivelDeDetalheProcesso:
    def __init__(self, navegador):
        self.driver = navegador

    def definir_nivel_detalhe(self):
        logging.info('Iniciando a definição do nível de detalhe do processo.')
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="ancNivelDetalhe"]'))).click()
            logging.info('Elemento "Nível de Detalhe" clicado com sucesso.')
            time.sleep(2)  # Simula comportamento humano
        except TimeoutException:
            logging.error("Elemento 'Nível de Detalhe' não encontrado ou não clicável dentro do tempo limite.")
            return

        try:
            WebDriverWait(self.driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it((By.NAME, 'modal-frame')))
            logging.info('Switch para o iframe "modal-frame" realizado com sucesso.')
        except TimeoutException:
            logging.error("Iframe 'modal-frame' não encontrado dentro do tempo limite.")
            return

        checkboxes = self.driver.find_elements(By.CLASS_NAME, 'infraCheckboxInput')
        for checkbox in checkboxes:
            if not checkbox.is_selected():  # Checa se o checkbox já está marcado
                self.driver.execute_script("arguments[0].click();", checkbox)  # Marca o checkbox
                logging.info('Checkbox marcado com sucesso.')

        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="divInfraBarraComandosSuperior"]/button'))).click()
            logging.info('Botão de confirmação clicado com sucesso.')
            time.sleep(1)  # Simula comportamento humano
        except TimeoutException:
            logging.error("Botão de confirmação não encontrado ou não clicável dentro do tempo limite.")
        finally:
            self.driver.switch_to.default_content()
            logging.info('Switch para o conteúdo principal realizado com sucesso.')

class BotaoProximaPagina:
    def __init__(self, navegador):
        self.driver = navegador

    def is_next_button_present(self):
        """
        Verifica se o botão 'Próxima página' está presente na página.
        """
        logging.info('Verificando se o botão "Próxima página" está presente.')
        try:
            self.driver.find_element(By.XPATH, '//*[@id="lnkInfraProximaPaginaSuperior"]/img')
            logging.info('Botão "Próxima página" encontrado.')
            return True
        except NoSuchElementException:
            logging.warning('Botão "Próxima página" não encontrado.')
            return False

class IncluiDocumentoInternoSei:
    def __init__(self, navegador, tipo_doc, protocolo, nome_arvore):
        self.driver = navegador
        self.tipo_doc = tipo_doc
        self.protocolo = protocolo
        self.nome_arvore = nome_arvore


    def incluir_documento_interno_sei(self):
        logging.info(f'Iniciando a inclusão do documento interno: Tipo "{self.tipo_doc}", Protocolo "{self.protocolo}".')
        self.driver.implicitly_wait(5)
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('ifrArvore')
        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            IconesBarraProcessoSei(self.driver, "Incluir Documento").clicar_icone_barra()
            logging.info('Ícone "Incluir Documento" clicado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao clicar no ícone "Incluir Documento": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.XPATH, '//*[@id="txtFiltro"]').send_keys(self.tipo_doc, Keys.TAB, Keys.ENTER)
            logging.info(f'Documento do tipo "{self.tipo_doc}" filtrado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao filtrar documento do tipo "{self.tipo_doc}": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.XPATH, '//*[@id="divOptProtocoloDocumentoTextoBase"]/div/label').click()
            logging.info('Opção de protocolo de documento base selecionada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.driver.find_element(By.XPATH, '//*[@id="txtProtocoloDocumentoTextoBase"]').send_keys(self.protocolo)
            logging.info(f'Protocolo "{self.protocolo}" inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir protocolo do documento base: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.ID, 'txtNomeArvore').send_keys(self.nome_arvore)
            logging.info(f'Nome da árvore "{self.nome_arvore}" inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir o nome da árvore "{self.nome_arvore}": {str(e)}')
            return

        try:
            self.driver.find_element(By.XPATH, '//*[@id="divOptRestrito"]/div/label').click()
            logging.info('Opção de restrição selecionada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())
            drop = Select(self.driver.find_element(By.XPATH, '//*[@id="selHipoteseLegal"]'))
            drop.select_by_visible_text("Informação Pessoal (Art. 31 da Lei nº 12.527/2011)")
            logging.info('Hipótese legal "Informação Pessoal" selecionada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao selecionar a hipótese legal: {str(e)}')
            return
        time.sleep(TempoAleatorio().tempo_aleatorio())
        # Armazena as janelas abertas antes de clicar no botão "Salvar"
        janelas_antes = set(self.driver.window_handles)


        # Armazena a janela original e os handles existentes antes de acionar a abertura do novo conteúdo
        janela_original = self.driver.current_window_handle
        handles_antes = self.driver.window_handles.copy()

        try:
            # Clica no botão "Salvar"
            self.driver.find_element(By.XPATH, '//*[@id="btnSalvar"]').click()
            logging.info('Botão "Salvar" clicado com sucesso, documento interno incluído.')
        except Exception as e:
            logging.error(f'Erro ao clicar no botão "Salvar": {str(e)}')

        # Aguarda até que uma nova janela seja aberta
        WebDriverWait(self.driver, 10).until(
            lambda driver: len(set(driver.window_handles) - set(handles_antes)) == 1
        )

        # Obtém a nova janela que foi aberta
        nova_janela = list(set(self.driver.window_handles) - set(handles_antes))[0]

        # Muda para a nova janela
        self.driver.switch_to.window(nova_janela)
        self.driver.maximize_window()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        self.driver.refresh()
        time.sleep(TempoAleatorio().tempo_aleatorio())



        # Configura o locale para pt_BR (pode variar de sistema para sistema)
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        except locale.Error:
            print("Locale pt_BR.UTF-8 não disponível.")
        return janela_original

class IncluiEditalDou:
    def __init__(self, navegador, tipo, protocolo, nome_arvore, dados_edital, caminho):
        self.driver = navegador
        self.tipo = tipo
        self.protocolo = protocolo
        self.nome_arvore = nome_arvore
        self.dados_edital = dados_edital
        self.caminho = caminho

    def incluir_edital_dou(self):
        logging.info('Iniciando a inclusão do Edital DOU.')
        locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
        janela_original = IncluiDocumentoInternoSei(self.driver, self.tipo, self.protocolo,
                                                    self.nome_arvore).incluir_documento_interno_sei()

        time.sleep(TempoAleatorio().tempo_aleatorio())

        wait = WebDriverWait(self.driver, 10)
        try:
            iframe1 = wait.until(EC.presence_of_element_located((By.XPATH, '//iframe[@title="Corpo do Texto"]')))
            self.driver.switch_to.frame(iframe1)
            logging.info('Mudança para o iframe "Corpo do Texto" realizada com sucesso.')
        except TimeoutException:
            logging.error('Iframe "Corpo do Texto" não encontrado dentro do tempo limite.')
            return

        try:
            nota_tec = self.dados_edital['nota_tec']
            data_nota_tec = self.dados_edital['data_nota_tec']
            numero_processo = self.dados_edital['numero_processo']
            texto1_novo = (
                f"A Coordenação-Geral de Pagamentos da Diretoria de Centralização de Serviços de Inativos, Pensionistas e "
                f"Órgãos Extintos - DECIPEX, nos termos da legislação vigente e considerando a impossibilidade de "
                f"comunicação com os servidores relacionados no Anexo I, ficam NOTIFICADOS do teor da <b>{nota_tec}</b> de "
                f"{data_nota_tec}, constante nos autos do processo {numero_processo} com a manifestação sobre a apresentação"
                f" da Declaração de Não Ajuizamento de Ação Judicial, faltante nos processos especificados, no prazo de 30 "
                f"(trinta) dias a contar da data da publicação deste Edital, pertinente para a continuidade para a concessão"
                f" de valores referente a exercícios anteriores."
            )
            self.driver.execute_script("document.querySelector('body > p:nth-child(4)').innerHTML = arguments[0];",
                                       texto1_novo)
            logging.info('Texto principal do edital inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir o texto principal do edital: {str(e)}')
            return

        # Caminho para o arquivo CSV
        caminho_arquivo = self.caminho

        try:
            # Ler o arquivo CSV
            dados = pd.read_csv(caminho_arquivo, sep=',', dtype={'CPF': str})
            logging.info(f'Arquivo CSV "{caminho_arquivo}" lido com sucesso.')
        except FileNotFoundError:
            logging.error(f'Arquivo CSV "{caminho_arquivo}" não encontrado.')
            return
        except Exception as e:
            logging.error(f'Erro ao ler o arquivo CSV "{caminho_arquivo}": {str(e)}')
            return

        # Função para aplicar a máscara no CPF
        def mascarar_cpf(cpf):
            cpf = ''.join(filter(str.isdigit, cpf))
            if len(cpf) <= 11 and cpf.isdigit():
                cpf = cpf.zfill(11)
                return f"XXX.{cpf[3:6]}.{cpf[6:9]}-XX"
            else:
                raise ValueError(f"CPF inválido: {cpf}")

        # Iterar sobre as linhas do DataFrame e inserir os dados na tabela
        try:
            for index, row in dados.iterrows():
                nome = row['Nome']
                cpf = mascarar_cpf(row['CPF'])
                processo = row['processo']

                # Selecionar a célula inicial
                nome_celula = self.driver.find_element(By.CSS_SELECTOR,
                                                       'body > table > tbody > tr:nth-child(2) > td:nth-child(1)')
                nome_celula.send_keys(nome)
                nome_celula.send_keys(Keys.TAB)

                # Selecionar a célula do CPF
                cpf_celula = self.driver.switch_to.active_element
                cpf_celula.send_keys(cpf)
                cpf_celula.send_keys(Keys.TAB)

                # Selecionar a célula do processo
                processo_celula = self.driver.switch_to.active_element
                processo_celula.send_keys(processo)

                # Enviar TAB apenas se não for a última linha
                if index < len(dados) - 1:
                    processo_celula.send_keys(Keys.TAB)
            logging.info('Dados do CSV inseridos na tabela do edital com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir os dados na tabela do edital: {str(e)}')
            return

        self.driver.switch_to.default_content()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            salvar_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '#cke_149_label')))
            salvar_button.click()
            logging.info('Botão "Salvar" clicado com sucesso.')
        except TimeoutException:
            logging.error('Botão "Salvar" não encontrado ou não era clicável dentro do tempo limite.')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        # Fechar a janela atual
        self.driver.close()
        logging.info('Janela do Edital DOU fechada com sucesso.')

        # Mudar o foco de volta para a janela original
        self.driver.switch_to.window(janela_original)
        logging.info('Foco retornado para a janela original com sucesso.')

class IncluiNotaTecnicaEspecifica:
    def __init__(self, navegador, tipo, protocolo, nome_arvore, dados_nota_tec):
        self.driver = navegador
        self.tipo = tipo
        self.protocolo = protocolo
        self.nome_arvore = nome_arvore
        self.dados_nota_tec = dados_nota_tec

    def incluir_nota_tecnica_especifica(self):
        logging.info('Iniciando a inclusão da Nota Técnica Específica.')
        janela_original = IncluiDocumentoInternoSei(self.driver, self.tipo, self.protocolo, self.nome_arvore).incluir_documento_interno_sei()
        wait = WebDriverWait(self.driver, 10)
        try:
            iframe1 = wait.until(EC.presence_of_element_located((By.XPATH, '//iframe[@title="Título do Documento"]')))
            self.driver.switch_to.frame(iframe1)
            logging.info('Mudança para o iframe "Título do Documento" realizada com sucesso.')
            localiza_nota_tecnica = self.driver.find_element(By.CSS_SELECTOR, 'body > p:nth-child(1)')
            numero_nota_tecnica = localiza_nota_tecnica.text.strip()
            logging.info(f'Número da Nota Técnica localizado: {numero_nota_tecnica}')
        except TimeoutException:
            logging.error('Iframe "Título do Documento" não encontrado dentro do tempo limite.')
            return

        self.driver.switch_to.default_content()
        try:
            iframe2 = wait.until(EC.presence_of_element_located((By.XPATH, '//iframe[@title="Corpo do Texto"]')))
            self.driver.switch_to.frame(iframe2)
            logging.info('Mudança para o iframe "Corpo do Texto" realizada com sucesso.')
        except TimeoutException:
            logging.error('Iframe "Corpo do Texto" não encontrado dentro do tempo limite.')
            return
        total_mens = 115
        total_edit = 33
        diferenca = total_mens - total_edit
        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            # Atualizando o texto do primeiro parágrafo
            texto1_novo = (
                f"Esta nota técnica aborda a situação de {total_mens} aposentados e pensionistas com direito a "
                f"valores de exercícios anteriores, mas que estão pendentes devido à falta da declaração de não "
                f"ajuizamento em seus respectivos processos SEI. Esta declaração, exigida pelo art. 4, alínea G, "
                f"da Portaria Conjunta n° 02 de 30/11/2012, é essencial para a continuidade dos procedimentos "
                f"administrativos de concessão destes valores.")
            self.driver.execute_script("document.querySelector('body > p:nth-child(2)').innerText = arguments[0];", texto1_novo)
            logging.info('Texto do primeiro parágrafo atualizado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao atualizar o texto do primeiro parágrafo: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            # Atualizando o texto do segundo parágrafo
            texto2_novo = (
                f"Em conformidade com os procedimentos desta Diretoria e a Lei 9.784 de 29 de janeiro de 1999, "
                f"foi concedida a oportunidade aos interessados de apresentar a declaração através de "
                f"correspondência eletrônica pelo aplicativo SouGov, inicialmente com um prazo de 30 dias. "
                f"Contudo, dos processos em questão, apenas {diferenca} interessados cumpriram com esta exigência.")
            self.driver.execute_script("document.querySelector('body > p:nth-child(4) > span').innerText = arguments[0];", texto2_novo)
            logging.info('Texto do segundo parágrafo atualizado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao atualizar o texto do segundo parágrafo: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            # Atualizando o texto do terceiro parágrafo
            texto3_novo = (
                f"Diante deste cenário, recomenda-se a publicação de um novo edital no Diário Oficial da União, "
                f"reiterando a necessidade da apresentação da declaração e estabelecendo novamente um prazo de "
                f"30 dias a partir da data de publicação, visando prevenir o arquivamento dos processos "
                f"restantes, totalizando {total_edit} interessados a serem alcançados por este edital.")
            self.driver.execute_script("document.querySelector('body > p:nth-child(5) > span').innerText = arguments[0];", texto3_novo)
            logging.info('Texto do terceiro parágrafo atualizado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao atualizar o texto do terceiro parágrafo: {str(e)}')
            return

        self.driver.switch_to.default_content()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            salvar_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'cke_button__save_label')))
            salvar_button.click()
            logging.info('Botão "Salvar" clicado com sucesso.')
        except TimeoutException:
            logging.error('Botão "Salvar" não encontrado ou não era clicável dentro do tempo limite.')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        # Fechar a janela atual
        self.driver.close()
        logging.info('Janela da Nota Técnica Específica fechada com sucesso.')

        # Mudar o foco de volta para a janela original
        self.driver.switch_to.window(janela_original)
        logging.info('Foco retornado para a janela original com sucesso.')
        return numero_nota_tecnica

class UnidadasCaixaSei:
    def __init__(self, navegador):
        self.driver = navegador

    def tempo_aleatorio(self):
        # Função temporária para simular comportamento humano
        return time.uniform(1, 3)

    def get_unidades(self):
        unidades = []
        logging.info('Iniciando a obtenção das unidades da caixa.')

        try:
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, 'div.nav-item:nth-child(3) > div:nth-child(1) > a:nth-child(1)'))).click()
            logging.info('Clicou no elemento de seleção de unidade com sucesso.')
            time.sleep(self.tempo_aleatorio())  # Simula comportamento humano

            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="selInfraOrgaoUnidade"]'))).send_keys('MGI')
            logging.info('Unidade "MGI" selecionada com sucesso.')
            time.sleep(self.tempo_aleatorio())  # Simula comportamento humano

        except TimeoutException:
            logging.error("Elemento de seleção de unidade não encontrado ou não clicável dentro do tempo limite.")
            return unidades

        try:
            rows = self.driver.find_elements(By.XPATH, '/html/body/div[1]/div/div[2]/form/div[3]/table/tbody/tr')
            for row in rows[1:]:  # Começando de 1 para pular o cabeçalho da tabela
                try:
                    second_column_text = row.find_element(By.XPATH, "./td[2]").text
                    unidades.append(second_column_text)
                    logging.info(f'Unidade encontrada: {second_column_text}')
                except NoSuchElementException as e:
                    logging.warning(f'Erro ao processar uma linha: {str(e)}')
                    continue
        except Exception as e:
            logging.error(f'Erro ao tentar obter as unidades: {str(e)}')

        logging.info('Obtenção das unidades concluída.')
        return unidades

class PlanilhaTecnico:
    def __init__(self, janela, navegador):
        self.janela = janela
        self.driver = navegador
        logging.basicConfig(level=logging.INFO)

    def ler_planilha_tecnico(self):

        meses = []
        anos = []
        valores = []
        numero_esquerda = []
        numero_direita = []
        cota_esquerda = []
        cota_direita = []
        nome_benes = []
        mat_bene = []
        cot_parte = []
        mat_serv = ""
        valor2 = 0
        valor3 = 0

        self.driver.switch_to.default_content()
        IframesSei(self.driver, 'Exibe frame documentos').navegar_iframes_sei()
        IframesSei(self.driver, 'Exibe documentos').navegar_iframes_sei()

        try:
            assunto = self.driver.find_element(By.CSS_SELECTOR,
                                               "body > table:nth-child(6) > tbody > tr:nth-child(1) > "
                                               "td:nth-child(2)").get_attribute('textContent').strip()
            if not assunto:
                raise NoSuchElementException("Assunto não encontrado")
            logging.info(f"Assunto encontrado: {assunto}")
        except NoSuchElementException:
            logging.error("Assunto não encontrado na tabela.")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.janela.message_handler.add_message(f"Assunto não encontrado na tabela", "error")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            TrocaMarcadorSEi(self.driver, 'Assunto não encontrado na tabela', "CGPAG INTEGRA",
                             "INTEGRA - RETORNO").trocar_marcador()
            return

        try:
            objeto = self.driver.find_element(By.CSS_SELECTOR,
                                              "body > table:nth-child(6) > tbody > tr:nth-child(2) > "
                                              "td:nth-child(2)").get_attribute('textContent').strip()
            if not objeto:
                raise NoSuchElementException("Objeto não encontrado")
            logging.info(f"Objeto encontrado: {objeto}")
        except NoSuchElementException:
            logging.error("Objeto não encontrado na tabela.")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.janela.message_handler.add_message(f"Objeto não encontrado na tabela", "error")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            TrocaMarcadorSEi(self.driver, 'Objeto não encontrado na tabela', "CGPAG INTEGRA",
                             "INTEGRA - RETORNO").trocar_marcador()
            return

        if self.driver.find_element(By.CSS_SELECTOR,
                                    "body > table:nth-child(6) > tbody > tr:nth-child(4) > td:nth-child(2)").get_attribute(
            'textContent').strip():
            descricao = self.driver.find_element(By.CSS_SELECTOR,
                                                 "body > table:nth-child(6) > tbody > tr:nth-child(4) > "
                                                 "td:nth-child(2)").get_attribute('textContent').strip()
            logging.info(f"Descrição encontrada: {descricao}")
        else:
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.janela.message_handler.add_message(f"Objeto não encontrado na tabela", "error")
            logging.error("Objeto não encontrado na tabela")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            TrocaMarcadorSEi(self.driver, 'Descrição não encontrado na tabela', "CGPAG INTEGRA",
                             "INTEGRA - RETORNO").trocar_marcador()
            return

        if self.driver.find_element(By.CSS_SELECTOR,
                                    "body > table:nth-child(8) > tbody > tr:nth-child(2) > td:nth-child(2)").get_attribute(
            'textContent').strip():
            situacao_funcional = self.driver.find_element(By.CSS_SELECTOR,
                                                          "body > table:nth-child(8) > tbody > tr:nth-child(2) > "
                                                          "td:nth-child(2)").get_attribute('textContent').strip()
            logging.info(f"Situação Funcional encontrada: {situacao_funcional}")
        else:
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.janela.message_handler.add_message(f"Situação Funcional não encontrado na tabela", "error")
            logging.error("Situação Funcional não encontrado na tabela")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            TrocaMarcadorSEi(self.driver, 'Situação Funcional não encontrado na tabela', "CGPAG INTEGRA",
                             "INTEGRA - RETORNO").trocar_marcador()
            return

        if self.driver.find_element(By.CSS_SELECTOR,
                                    "body > table:nth-child(8) > tbody > tr:nth-child(3) > td:nth-child(2)").get_attribute(
            'textContent').strip():
            nome_serv = self.driver.find_element(By.CSS_SELECTOR,
                                                 "body > table:nth-child(8) > tbody > tr:nth-child(3) > "
                                                 "td:nth-child(2)").get_attribute('textContent').strip()
            logging.info(f"Nome encontrado: {nome_serv}")
        else:
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.janela.message_handler.add_message(f"Nome não encontrado na tabela", "error")
            logging.error("Nome não encontrado na tabela")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            TrocaMarcadorSEi(self.driver, 'Nome não encontrado na tabela', "CGPAG INTEGRA",
                             "INTEGRA - RETORNO").trocar_marcador()
            return

        if self.driver.find_element(By.CSS_SELECTOR,
                                    "body > table:nth-child(8) > tbody > tr:nth-child(4) > td:nth-child(2)").get_attribute(
            'textContent').strip():
            orgao = self.driver.find_element(By.CSS_SELECTOR,
                                             "body > table:nth-child(8) > tbody > tr:nth-child(4) > "
                                             "td:nth-child(2)").get_attribute('textContent').strip()
            logging.info(f"Órgão encontrado: {orgao}")
        else:
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.janela.message_handler.add_message(f"Órgão não encontrado na tabela", "error")
            logging.error("Órgão não encontrado na tabela")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            TrocaMarcadorSEi(self.driver, 'Órgão não encontrado na tabela', "CGPAG INTEGRA",
                             "INTEGRA - RETORNO").trocar_marcador()
            return

        if self.driver.find_element(By.CSS_SELECTOR,
                                    "body > table:nth-child(8) > tbody > tr:nth-child(5) > td:nth-child(2)").get_attribute(
            'textContent').strip():
            upag = self.driver.find_element(By.CSS_SELECTOR,
                                            "body > table:nth-child(8) > tbody > tr:nth-child(5) > "
                                            "td:nth-child(2)").get_attribute('textContent').strip()
            ultim_carac = upag[-1]
            upag1 = '0' * 8 + ultim_carac
            logging.info(f"UPAG encontrado: {upag}, UPAG ajustado: {upag1}")
        else:
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.janela.message_handler.add_message(f"UPAG não encontrado na tabela", "error")
            logging.error("UPAG não encontrado na tabela")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            TrocaMarcadorSEi(self.driver, 'UPAG não encontrado na tabela', "CGPAG INTEGRA",
                             "INTEGRA - RETORNO").trocar_marcador()
            return

        if self.driver.find_element(By.CSS_SELECTOR,
                                    "body > table:nth-child(8) > tbody > tr:nth-child(6) > td:nth-child(2)").get_attribute(
            'textContent').strip():
            mat_serv = self.driver.find_element(By.CSS_SELECTOR,
                                                "body > table:nth-child(8) > tbody > tr:nth-child(6) > "
                                                "td:nth-child(2)").get_attribute('textContent').strip()
            logging.info(f"Matrícula do servidor encontrada: {mat_serv}")

            if len(mat_serv) < 7:
                logging.warning("Matrícula do servidor possui menos de 7 dígitos")
                TrocaMarcadorSEi(self.driver, "Matrícula Instituidor ou Aposentado não pode ter menos de 7 dígitos",
                                 "CGPAG INTEGRA", "INTEGRA - RETORNO").trocar_marcador()
                return


        else:

            time.sleep(TempoAleatorio().tempo_aleatorio())

            self.janela.message_handler.add_message(f"Matrícula não encontrado na tabela", "error")

            logging.error("Matrícula não encontrada na tabela")

            time.sleep(TempoAleatorio().tempo_aleatorio())

            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()

            TrocaMarcadorSEi(self.driver, 'Matrícula não encontrado na tabela', "CGPAG INTEGRA",

                             "INTEGRA - RETORNO").trocar_marcador()

            return

        # Processamento da tabela

        tabela = self.driver.find_element(By.XPATH, '/html/body/table[5]')

        logging.info("Tabela encontrada para processamento.")

        total = 0

        linhas = tabela.find_elements(By.TAG_NAME, 'tr')

        num_linhas_processadas = 0

        for linha in linhas:

            # Ignorar as duas primeiras linhas (cabeçalho)

            if num_linhas_processadas < 2:
                num_linhas_processadas += 1

                continue

            # Extrair as células da linha

            celulas = linha.find_elements(By.TAG_NAME, 'td')

            # Verificar se todas as células estão vazias

            if all(not celula.text.strip() for celula in celulas):
                continue  # Pula para a próxima iteração se a linha estiver vazia

            # Verificar se a célula contém "TOTAL" e se há um valor na coluna à direita

            total_encontrado = False

            for i in range(len(celulas) - 1):

                if celulas[i].text.strip() == "TOTAL":

                    valor_direita = celulas[i + 1].text.strip()

                    if not valor_direita:
                        total_encontrado = True

                        self.janela.message_handler.add_message(f"Total dos valores não encontrado na tabela", "error")

                        logging.error("Total dos valores não encontrado na tabela")

                        time.sleep(TempoAleatorio().tempo_aleatorio())

                        PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()

                        TrocaMarcadorSEi(self.driver, 'Total dos valores não encontrado na tabela', "CGPAG INTEGRA",

                                         "INTEGRA - RETORNO").trocar_marcador()

                        raise TotalNotFoundException  # Interrompe o loop se não há valor na coluna à direita

                    tot_tab = NormalizaValoresMonetarios(valor_direita).normalizar_string_para_monetario()

                    logging.info(f"Valor TOTAL encontrado na tabela: {tot_tab}")

                    total_encontrado = True

                    break  # Sai do loop ao encontrar "TOTAL"

            if total_encontrado:
                break  # Sai do loop ao encontrar "TOTAL"

            # Continuar com o processamento da linha

            mes = celulas[0].text.strip()

            ano = celulas[1].text.strip()

            valor = celulas[4].text.strip()

            valor2 = NormalizaValoresMonetarios(valor).normalizar_string_para_monetario()

            logging.info(f"Processando linha: Mês: {mes}, Ano: {ano}, Valor: {valor2}")

            valEsq, valDir = DivideValorParaSIAPE(valor2).dividir_string_valor()

            # Adicionar os valores às listas correspondentes

            meses.append(mes)

            anos.append(ano)

            valores.append(valor)

            valor3 = float(valor3) + float(valor2)

            numero_esquerda.append(valEsq)

            numero_direita.append(valDir)

        if situacao_funcional == "Instituidor":

            tabela2 = self.driver.find_element(By.XPATH, '/html/body/table[6]')

            logging.info("Tabela de beneficiários encontrada para processamento.")

            total2 = 0

            linhas2 = tabela2.find_elements(By.TAG_NAME, 'tr')

            num_linhas_processadas2 = 0

            for linha2 in linhas2:

                # Ignorar as duas primeiras linhas (cabeçalho)

                if num_linhas_processadas2 < 2:
                    num_linhas_processadas2 += 1

                    continue

                # Extrair as células da linha

                celulas2 = linha2.find_elements(By.TAG_NAME, 'td')

                if all(not celula2.text.strip() for celula2 in celulas2):
                    continue  # Pula para a próxima iteração se a linha estiver vazia

                nome_bene = celulas2[0].text.strip()

                matinee = celulas2[1].text.strip()

                cot_parte2 = celulas2[2].text.strip()

                esquerdaCot, direitaCot = DivideValorParaSIAPE(cot_parte2).dividir_string_valor()

                logging.info(f"Beneficiário encontrado: Nome: {nome_bene}, Matrícula: {matinee}, Cota: {cot_parte2}")

                # Adicionar os valores às listas correspondentes

                nome_benes.append(nome_bene)

                mat_bene.append(matinee)

                cota_esquerda.append(esquerdaCot)

                cota_direita.append(direitaCot)

                time.sleep(2)

        folha_comp = [folha + str(comp) for folha, comp in zip(meses, anos)]

        valor4 = "{:.1f}".format(math.floor(valor3 * 100) / 100.0)

        tot_tab1 = "{:.1f}".format(math.floor(float(tot_tab) * 100) / 100.0)

        if abs(float(valor4) - float(tot_tab1)) > 0.5:
            time.sleep(TempoAleatorio().tempo_aleatorio())

            self.janela.message_handler.add_message(f"Diferença entre os valores somados e o Total na tabela", "error")

            logging.error("Diferença entre os valores somados e o Total na tabela")

            time.sleep(TempoAleatorio().tempo_aleatorio())

            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()

            TrocaMarcadorSEi(self.driver, 'Diferença entre os valores somados e o Total na tabela', "CGPAG INTEGRA",

                             "INTEGRA - RETORNO").trocar_marcador()

            return

        anos_int = list(map(int, anos))

        seq_mes_ano = VerificaSequenciaMesAno(meses, anos_int).verificar_mes_ano()

        if seq_mes_ano != "Sequência correta.":
            self.janela.message_handler.add_message(f"Sequência de meses ou ano incorreta na tabela", "error")

            logging.error("Sequência de meses ou ano incorreta na tabela")

            time.sleep(TempoAleatorio().tempo_aleatorio())

            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()

            TrocaMarcadorSEi(self.driver, 'Sequência de meses ou ano incorreta na tabela', "CGPAG INTEGRA",

                             "INTEGRA - RETORNO").trocar_marcador()

            return

        info_exer_ant = {'assunto': assunto, 'objeto': objeto, 'descricao': descricao,

                         'sit_func': situacao_funcional, 'orgao': orgao, 'upag': upag1, 'nome_serv': nome_serv,

                         'mat_serv': mat_serv,

                         'mesFol': meses, 'compFol': anos, 'nome_benes': nome_benes, 'matBene': mat_bene,

                         'valorEsq': numero_esquerda,

                         'valorDir': numero_direita, 'cotEsq': cota_esquerda, 'cotDir': cota_direita,

                         'total': tot_tab}

        logging.info("Tabela lida com sucesso.")

        self.janela.message_handler.add_message(f"Tabela lida com sucesso")

        time.sleep(TempoAleatorio().tempo_aleatorio())

        return info_exer_ant

class AcessoBlocoAssinatura:
    def __init__(self, integrador, navegador, bloco):
        self.integrador = integrador
        self.driver = navegador
        self.bloco = bloco

    def acessar_bloco_assinatura(self):
        self.driver.switch_to.default_content()
        self.click_element('//*[@id="lnkControleProcessos"]/img')
        self.click_element_menu('//a[contains(@href, "bloco_assinatura_listar")]')
        time.sleep(TempoAleatorio().tempo_aleatorio())

        # Clicar bloco
        WebDriverWait(self.driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, f"//a[normalize-space()={self.bloco}]"))
        ).click()

    def click_element_menu(self, xpath):
        try:
            # Espera até que o elemento com o href especificado esteja presente. O tempo máximo de espera é de 3 segundos.
            elemento = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            # Uma vez que o elemento esteja disponível, execute o script para clicar nele.
            self.driver.execute_script("arguments[0].click();", elemento)
        except TimeoutException:
            print("O elemento não foi encontrado no tempo especificado.")

    def click_element_menu(self, xpath):
        try:
            # Espera até que o elemento com o href especificado esteja presente. O tempo máximo de espera é de 3 segundos.
            elemento = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            # Uma vez que o elemento esteja disponível, execute o script para clicar nele.
            self.driver.execute_script("arguments[0].click();", elemento)
        except TimeoutException:
            print("O elemento não foi encontrado no tempo especificado.")

    def click_element(self, xpath):

        try:
            elemento = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            self.driver.execute_script("arguments[0].scrollIntoView();", elemento)
            elemento.click()
        except Exception as e:(f"Erro ao clicar: {e}")

class ExtraiDadosNotaTecnicaExante:
    def __init__(self, navegador):
        self.driver = navegador

    def extracao_dados_nt_exante(self):
        IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()
        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        IframesSei(self.driver, "Exibe documentos").navegar_iframes_sei()
        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        # Extrai número do processo administrativo
        proc_siape = self.driver.find_element(By.CSS_SELECTOR, "body > table:nth-child(13) > tbody > tr:nth-child(2) > td:nth-child(2)")
        proc_siape_num = proc_siape.text

        # Extrai Objeto do pagamento
        objeto_pag = self.driver.find_element(By.CSS_SELECTOR, "body > table:nth-child(13) > tbody > tr:nth-child(3) > td:nth-child(2)")
        objeto_pag_text = objeto_pag.text
        objeto_pag_num = ExtraiNumerais(objeto_pag_text).extrair_numerais()

        # Extrai matrícula do beneficiário
        mat_bene = self.driver.find_element(By.CSS_SELECTOR,
                                              "body > table:nth-child(13) > tbody > tr:nth-child(6) > td:nth-child(2)")
        mat_bene_num = mat_bene.text

        dados_nota_tecnica = {'proc_siape': proc_siape_num, 'objeto_pag': objeto_pag_num, 'mat_bene': mat_bene_num}

        return dados_nota_tecnica

class ExtraiDadosPlanilha_Calculo:
    def __init__(self, navegador):
        self.driver = navegador

    def extracao_dados_planilha(self):
        IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()
        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        IframesSei(self.driver, "Exibe documentos").navegar_iframes_sei()
        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

        if self.driver.find_element(By.CSS_SELECTOR,
                                    "body > table:nth-child(8) > tbody > tr:nth-child(4) > td:nth-child(2)").get_attribute(
            'textContent').strip():
            orgao = self.driver.find_element(By.CSS_SELECTOR,
                                             "body > table:nth-child(8) > tbody > tr:nth-child(4) > "
                                             "td:nth-child(2)").get_attribute('textContent').strip()
            logging.info(f"Órgão encontrado: {orgao}")
        else:
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.janela.message_handler.add_message(f"Órgão não encontrado na tabela", "error")
            logging.error("Órgão não encontrado na tabela")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            TrocaMarcadorSEi(self.driver, 'Órgão não encontrado na tabela', "CGPAG INTEGRA",
                             "INTEGRA - RETORNO").trocar_marcador()
            return

        if self.driver.find_element(By.CSS_SELECTOR,
                                    "body > table:nth-child(8) > tbody > tr:nth-child(5) > td:nth-child(2)").get_attribute(
            'textContent').strip():
            upag = self.driver.find_element(By.CSS_SELECTOR,
                                            "body > table:nth-child(8) > tbody > tr:nth-child(5) > "
                                            "td:nth-child(2)").get_attribute('textContent').strip()
            ultim_carac = upag[-1]
            upag1 = '0' * 8 + ultim_carac
            logging.info(f"UPAG encontrado: {upag}, UPAG ajustado: {upag1}")
        else:
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.janela.message_handler.add_message(f"UPAG não encontrado na tabela", "error")
            logging.error("UPAG não encontrado na tabela")
            time.sleep(TempoAleatorio().tempo_aleatorio())
            PrimeiroPlanoNavegador(self.driver, "SEI").enviar_primeiro_plano()
            TrocaMarcadorSEi(self.driver, 'UPAG não encontrado na tabela', "CGPAG INTEGRA",
                             "INTEGRA - RETORNO").trocar_marcador()
            return
        self.driver.switch_to.default_content()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        IframesSei(self.driver, "Arvore documentos").navegar_iframes_sei()
        return orgao, upag1

class TermoEncerramento:
    def __init__(self, navegador, tipo_doc, nome_arvore, tecnico):
        self.driver = navegador
        self.tipo_doc = tipo_doc
        self.nome_arvore = nome_arvore
        self.tecnico = tecnico

    def inserir_termo_encerramento(self):
        self.driver.implicitly_wait(5)
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('ifrArvore')
        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            IconesBarraProcessoSei(self.driver, "Incluir Documento").clicar_icone_barra()
            logging.info('Ícone "Incluir Documento" clicado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao clicar no ícone "Incluir Documento": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.XPATH, '//*[@id="txtFiltro"]').send_keys(self.tipo_doc, Keys.TAB, Keys.ENTER)
            logging.info(f'Documento do tipo "{self.tipo_doc}" filtrado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao filtrar documento do tipo "{self.tipo_doc}": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.ID, 'txtNomeArvore').send_keys(self.nome_arvore)
            logging.info(f'Nome da árvore "{self.nome_arvore}" inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir o nome da árvore "{self.nome_arvore}": {str(e)}')
            return

        try:
            self.driver.find_element(By.XPATH, '//*[@id="divOptRestrito"]/div/label').click()
            logging.info('Opção de restrição selecionada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())
            drop = Select(self.driver.find_element(By.XPATH, '//*[@id="selHipoteseLegal"]'))
            drop.select_by_visible_text("Informação Pessoal (Art. 31 da Lei nº 12.527/2011)")
            logging.info('Hipótese legal "Informação Pessoal" selecionada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao selecionar a hipótese legal: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        # Armazena as janelas abertas antes de clicar no botão "Salvar"
        janelas_antes = set(self.driver.window_handles)

        try:
            # Clica no botão "Salvar"
            self.driver.find_element(By.XPATH, '//*[@id="btnSalvar"]').click()
            logging.info('Botão "Salvar" clicado com sucesso, documento interno incluído.')
        except Exception as e:
            logging.error(f'Erro ao clicar no botão "Salvar": {str(e)}')
            return

        # Aguarda um tempo aleatório para simular o comportamento humano
        time.sleep(TempoAleatorio().tempo_aleatorio())

        # Aguarda até que uma nova janela seja aberta (esperando que uma nova janela seja adicionada)
        WebDriverWait(self.driver, 10).until(lambda driver: len(set(driver.window_handles) - janelas_antes) == 1)

        # Obtém a nova janela que foi aberta
        nova_janela = list(set(self.driver.window_handles) - janelas_antes)[0]

        # Muda para a nova janela
        self.driver.switch_to.window(nova_janela)
        self.driver.maximize_window()

        try:
            # Localiza o frame que deseja acessar
            frame = self.driver.find_elements(By.CLASS_NAME, 'cke_wysiwyg_frame')
            self.driver.switch_to.frame(frame[2])

            # Limpa e insere novo conteúdo na célula da tabela
            self.driver.find_element(By.XPATH, '/html/body/table[1]/tbody/tr[8]/td[1]').clear()
            self.driver.find_element(By.XPATH, '/html/body/table[1]/tbody/tr[8]/td[1]').send_keys("(X)")
            self.driver.find_element(By.XPATH, '/html/body/table[1]/tbody/tr[8]/td[2]').clear()
            self.driver.find_element(By.XPATH, '/html/body/table[1]/tbody/tr[8]/td[2]').click()
            self.driver.find_element(By.XPATH, '/html/body/table[1]/tbody/tr[8]/td[2]').send_keys("Outros motivos. Especificar: Ausência de documentos exigidos pela Portaria Conjunta SEGEP/SOF nº 02, de 30/11/2012, que regulamenta os critérios para pagamento de despesas de exercícios anteriores de pessoal, no âmbito da Administração Pública Federal direta, autárquica e fundacional, conforme especificado no Art.4º, alínea g.")

            # Limpa e insere novo conteúdo no parágrafo especificado
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.driver.find_element(By.XPATH, '/html/body/p[7]').clear()
            self.driver.find_element(By.XPATH, '/html/body/p[8]').click()
            self.driver.find_element(By.XPATH, '/html/body/p[8]').send_keys(
                "ELAINE DE SOUZA BARROS")
            self.driver.find_element(By.XPATH, '/html/body/p[9]').click()
            self.driver.find_element(By.XPATH, '/html/body/p[9]').send_keys(
                "Coordenadora Geral de Pagamentos")

            # Aguarda um tempo aleatório antes de sair do frame
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.driver.switch_to.default_content()

            # Clica em um elemento específico
            self.driver.find_element(By.XPATH, '//*[@id="cke_149_label"]').click()
            time.sleep(2)

            # Fecha a janela atual e retorna à janela original
            self.driver.close()
            self.driver.switch_to.window(janelas_antes.pop())

        except Exception as e:
            logging.error(f'Erro durante a manipulação da nova janela: {str(e)}')
            # Caso ocorra um erro, volte para a janela original
            self.driver.switch_to.window(janelas_antes.pop())

class InclusaoDocumentoBloco:
    def __init__(self, navegador, protocolos, documento, bloco):
        self.driver = navegador
        self.protocolos = protocolos
        self.documento = documento
        self.bloco = bloco

    def incluir_documento_bloco(self):
        time.sleep(TempoAleatorio().tempo_aleatorio())
        DocumentosArvoreSei(self.driver, self.documento).clicar_no_documento()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        IconesBarraProcessoSei(self.driver, "Incluir em Bloco de Assinatura").clicar_icone_barra()
        IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()

        # Definir o valor desejado
        valor = self.bloco

        # Localizar o elemento <select> pelo id usando a abordagem recomendada
        select_element = self.driver.find_element(By.ID, "selBloco")

        # Criar uma instância de Select a partir do elemento encontrado
        select = Select(select_element)

        # Selecionar a opção pelo valor (neste caso, o valor da variável 'valor')
        select.select_by_value(valor)
        time.sleep(TempoAleatorio().tempo_aleatorio())

        for protocolo in self.protocolos:
            # Espera pelo label associado ao checkbox com o title desejado
            label = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//label[@class='infraCheckboxLabel' and @title='{protocolo}']")
                )
            )

            # Opcional: verificar se o checkbox correspondente já está selecionado
            # Localiza o input associado ao label (o atributo "for" do label contém o id do input)
            checkbox = self.driver.find_element(By.XPATH, f"//input[@type='checkbox' and @title='{protocolo}']")

            # Se o checkbox não estiver selecionado, clica no label
            if not checkbox.is_selected():
                label.click()
        try:
            self.driver.find_element(By.XPATH, '//*[@id="sbmIncluir"]').click()
        except TimeoutException:
            return

class NotificacaoNumerada():
    def __init__(self, navegador, tipo_doc, protocolo, nota_tecnica, nome_arvore):
        self.driver = navegador
        self.tipo_doc = tipo_doc
        self.protocolo = protocolo
        self.nota_tecnica = nota_tecnica
        self.nome_arvore = nome_arvore

    def inserir_notificacao_numerada(self):
        # Configurar a localização para português do Brasil
        locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
        logging.info(
            f'Iniciando a inclusão do documento interno: Tipo "{self.tipo_doc}", Protocolo "{self.protocolo}".')
        self.driver.implicitly_wait(5)
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame('ifrArvore')
        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            IconesBarraProcessoSei(self.driver, "Incluir Documento").clicar_icone_barra()
            logging.info('Ícone "Incluir Documento" clicado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao clicar no ícone "Incluir Documento": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.XPATH, '//*[@id="txtFiltro"]').send_keys(self.tipo_doc, Keys.TAB, Keys.ENTER)
            logging.info(f'Documento do tipo "{self.tipo_doc}" filtrado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao filtrar documento do tipo "{self.tipo_doc}": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.XPATH, '//*[@id="divOptProtocoloDocumentoTextoBase"]/div/label').click()
            logging.info('Opção de protocolo de documento base selecionada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.driver.find_element(By.XPATH, '//*[@id="txtProtocoloDocumentoTextoBase"]').send_keys(self.protocolo)
            logging.info(f'Protocolo "{self.protocolo}" inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir protocolo do documento base: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.ID, 'txtNomeArvore').send_keys(self.nome_arvore)
            logging.info(f'Nome da árvore "{self.nome_arvore}" inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir o nome da árvore "{self.nome_arvore}": {str(e)}')
            return

        try:
            self.driver.find_element(By.XPATH, '//*[@id="divOptRestrito"]/div/label').click()
            logging.info('Opção de restrição selecionada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())
            drop = Select(self.driver.find_element(By.XPATH, '//*[@id="selHipoteseLegal"]'))
            drop.select_by_visible_text("Informação Pessoal (Art. 31 da Lei nº 12.527/2011)")
            logging.info('Hipótese legal "Informação Pessoal" selecionada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao selecionar a hipótese legal: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        # Armazena as janelas abertas antes de clicar no botão "Salvar"
        janelas_antes = set(self.driver.window_handles)

        try:
            # Clica no botão "Salvar"
            self.driver.find_element(By.XPATH, '//*[@id="btnSalvar"]').click()
            logging.info('Botão "Salvar" clicado com sucesso, documento interno incluído.')
        except Exception as e:
            logging.error(f'Erro ao clicar no botão "Salvar": {str(e)}')
            return

        # Aguarda um tempo aleatório para simular o comportamento humano
        time.sleep(TempoAleatorio().tempo_aleatorio())

        # Aguarda até que uma nova janela seja aberta (esperando que uma nova janela seja adicionada)
        WebDriverWait(self.driver, 10).until(lambda driver: len(set(driver.window_handles) - janelas_antes) == 1)

        # Obtém a nova janela que foi aberta
        nova_janela = list(set(self.driver.window_handles) - janelas_antes)[0]

        # Muda para a nova janela
        self.driver.switch_to.window(nova_janela)
        self.driver.maximize_window()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        self.driver.refresh()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            # Localiza o frame que deseja acessar
            frame = self.driver.find_elements(By.CLASS_NAME, 'cke_wysiwyg_frame')
            self.driver.switch_to.frame(frame[2])


            print("ponto1")

        except Exception as e:
            logging.error(f'Erro durante a manipulação da nova janela: {str(e)}')
            # Caso ocorra um erro, volte para a janela original
            self.driver.switch_to.window(janelas_antes.pop())

        # Obter a data atual
        data_atual = datetime.now().strftime('%d de %B de %Y')
        mes_ano_atual = datetime.now().strftime('%B/%Y')

        # Localizar o elemento pelo nome da classe
        try:
            element = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.CLASS_NAME, "Texto_Alinhado_Direita"))
            )

            # Aqui você atualiza o texto do elemento
            novo_texto = element.text.replace(element.text.split(",")[1].strip(), data_atual)
            self.driver.execute_script("arguments[0].innerText = arguments[1];", element, novo_texto)

        except Exception as e:
            print(f"Não foi possível encontrar/atualizar o elemento: {e}")

        # Localizar o elemento `<strong>` pelo contexto (neste caso, um `<td>` ou outro elemento que contém o texto relevante)
        element = self.driver.find_element(By.XPATH, "//p[contains(@class, 'Tabela_Texto_Centralizado')]//strong")
        # Atualizar o texto do elemento com o mês e o ano atuais
        self.driver.execute_script("arguments[0].innerText = arguments[1];", element, mes_ano_atual)

        # Localizar o elemento pelo contexto (exemplo: localizar a tag <strong> dentro do parágrafo)
        elements = self.driver.find_elements(By.XPATH, "//p[contains(@class, 'Tabela_Texto_Alinhado_Esquerda')]//strong")

        # Iterar sobre os elementos encontrados
        for element in elements:
            if "15 (quinze)" in element.text:  # Verificar se o texto contém "15 (quinze)"
                novo_texto = element.text.replace("15 (quinze)", "10 (dez)")
                self.driver.execute_script("arguments[0].innerText = arguments[1];", element, novo_texto)
                print(f"Texto atualizado para: {novo_texto}")
                break  # Parar após encontrar e substituir no elemento correto

        # Novo texto para substituir
        novo_texto1 = (f"Conforme as questões de fato e de direito explicitadas na Nota Técnica {self.nota_tecnica}, "
                      "informamos que foi instaurado o processo administrativo apuratório referenciado, para notificá-lo de que a "
                      "Vantagem Pessoal Parecer FC 03/89 possui natureza de VPNI e, como tal, deverá ser absorvida progressivamente "
                      "pelos aumentos que vierem a ser realizados no vencimento, salário ou provento.")

        # Localizar o elemento pelo seletor adequado (ajustar o XPath conforme necessário para sua página)
        # element = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Conforme as questões de fato e de direito')]")
        element = self.driver.find_element(By.XPATH,
                                           "//p[contains(text(), 'Conforme as questões de fato e de direito')]")
        # Localizar o elemento que deve ser excluído (ajustar o XPath conforme necessário)
        # element_to_remove = self.driver.find_element(By.XPATH,
        #                                         "//span[contains(text(), 'Vantagem Pessoal Parecer FC 03/89 possui natureza de VPNI')]")
        # # Excluir o elemento usando JavaScript
        # self.driver.execute_script("arguments[0].remove();", element_to_remove)


        # Substituir o texto existente pelo novo texto
        # self.driver.execute_script("arguments[0].innerText = arguments[1];", element, novo_texto1)
        self.driver.execute_script("arguments[0].innerText = arguments[1];", element, novo_texto1)

        novo_texto2 = ("Nesse sentido, informo que foi expedida Notificação anterior, dando ciência sobre a "
                        "redutibilidade da Vantagem Pessoal supramencionada, a qual foi comprovadamente recebida, por meio de "
                       "comunicação oficial.")
        # Localizar o elemento pelo seletor adequado (ajustar o XPath conforme necessário para sua página)
        # element2 = self.driver.find_element(By.XPATH, "/html/body/p[12]/span/span/span/span/span/span/span/span/span/span/span/span/span/span")
        element2 = self.driver.find_element(By.XPATH,
                                           "//p[contains(text(), 'Nesse sentido, o valor resultante do Reajuste')]")


        # Substituir o texto existente pelo novo texto
        self.driver.execute_script("arguments[0].innerText = arguments[1];", element2, novo_texto2)

        novo_texto3 = ("Sendo assim, em cumprimento ao art. 7º da Orientação Normativa nº 05/2013/SGP/MPO, "
                       "informo que será descontado dos seus vencimentos o reajuste concedido pela Medida Provisória n.° "
                       "1.170/2023, convertida na Lei n.° 14.673, de 2023, bem como nos próximos reajustes concedidos pela "
                       "União até que haja absorção total da referida Vantagem.")
        # Localizar o elemento pelo seletor adequado (ajustar o XPath conforme necessário para sua página)
        # element3 = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Pelo exposto, a contar do recebimento')]")
        element3 = self.driver.find_element(By.XPATH,
                                            "//p[contains(text(), 'Pelo exposto, a contar do recebimento')]")
        # Substituir o texto existente pelo novo texto
        self.driver.execute_script("arguments[0].innerText = arguments[1];", element3, novo_texto3)

        novo_texto4 = ("Pelo exposto, a contar do recebimento desta notificação, terá o prazo de 10 (dez) dias "
                       "consecutivos, para pessoalmente, ou por meio de advogado constituído, exercer o direito ao contraditório "
                       "e à ampla defesa.")
        # Localizar o elemento pelo seletor adequado (ajustar o XPath conforme necessário para sua página)
        # element4 = self.driver.find_element(By.XPATH, "//span[contains(text(), 'Por fim, salienta-se que as manifestações')]")
        element4 = self.driver.find_element(By.XPATH,
                                            "//p[contains(text(), 'Por fim, salienta-se que as manifestações')]")
        # Substituir o texto existente pelo novo texto
        self.driver.execute_script("arguments[0].innerText = arguments[1];", element4, novo_texto4)

        # Localizar o parágrafo 4
        paragrafo4 = self.driver.find_element(By.XPATH,
                                            "//p[contains(text(), 'Pelo exposto, a contar do recebimento')]")

        # Simular "Enter" ao final do parágrafo 4
        paragrafo4.send_keys(Keys.END, Keys.ENTER)

        novo_texto5 = ('Por fim, salienta-se que as manifestações devem ser direcionadas a esta Unidade, por '
                       'peticionamento, via Protocolo Eletrônico do Sistema SEI/ME, mediante simples cadastro, disponível no '
                       's í ti o : https://www.gov.br/pt-br/servicos/protocolar-documentos-junto-ao-ministerio-da-gestao-e-da- '
                       'inovacao-em-servicos-publicos, fazendo-se referência ao processo. No site, clique em "solicitar", em '
                       'seguida em "crie sua conta gov.br" e escolha uma forma de iniciar o cadastro, sendo a mais comum a opção '
                       'de CPF. Os demais passos para registro são autoexplicativos.')

        paragrafo4.send_keys(novo_texto5)

        # Localizar o elemento pelo XPath fornecido
        # element = self.driver.find_element(By.XPATH,
        #                               "/html/body/p[15]/span/span/span/span/span/span/span/span/span/span/span/span/span/span/span[3]/span/span/span/span/span/span/span/span/span/span/span")
        element6 = self.driver.find_element(By.XPATH,
                                            "//p[contains(text(), 'Nota Técnica SEI nº')]")
        # Substituir o conteúdo textual do elemento
        novo_texto6= f"Nota Técnica SEI nº {self.nota_tecnica}"
        self.driver.execute_script("arguments[0].innerText = arguments[1];", element6, novo_texto6)

        # Encontrar todos os parágrafos com a classe Texto_Centralizado_12
        paragraphs = self.driver.find_elements(By.XPATH, "//p[@class='Texto_Centralizado_12']")

        # Selecionar o último da lista
        p_element = paragraphs[-1]

        # Remover o p_element
        self.driver.execute_script("arguments[0].remove();", p_element)

        # Inserir o novo elemento
        parent_element = self.driver.find_element(By.TAG_NAME, "body")  # Por exemplo, insere no final do body
        final_html = "<p class='Texto_Centralizado_12'><strong>ELAINE DE SOUZA BARROS</strong><br>Coordenadora-Geral de Pagamentos</p>"
        self.driver.execute_script("arguments[0].insertAdjacentHTML('beforeend', arguments[1]);", parent_element,
                                   final_html)

        time.sleep(TempoAleatorio().tempo_aleatorio())
        self.driver.switch_to.default_content()

        # Clica em um elemento específico
        self.driver.find_element(By.XPATH, '//*[@id="cke_145_label"]').click()
        time.sleep(2)

        # Fecha a janela atual e retorna à janela original
        self.driver.close()
        self.driver.switch_to.window(janelas_antes.pop())

class GeraPDFDocumentoSEI:
    def __init__(self, navegador, documento):
        self.driver = navegador
        self.documento = documento

    def gerar_pdf(self):
        wait = WebDriverWait(self.driver, 5)  # Espera até 5 segundos
        DocumentosArvoreSei(self.driver, self.documento).clicar_no_documento()
        IconesBarraProcessoSei(self.driver, "Gerar Arquivo PDF do Documento").clicar_icone_barra()
        IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()
        botao = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@name="btnGerar"]')))
        botao.click()
        IframesSei(self.driver, "Arvore documentos").navegar_iframes_sei()
        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        documentos = DocumentosArvoreSei(self.driver, "Notificação")
        numero = documentos.extrair_numeroSEI_do_ultimo_elemento()
        GerenciadorArquivos("downloads").renomear_arquivo_por_sequencia(numero)
        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano

        # Atualiza o texto parcial antes de clicar no documento
        documentos.texto_parcial = self.documento
        documentos.clicar_no_documento()

        # Verifica se o script está rodando como um executável
        if getattr(sys, 'frozen', False):
            caminho_script_atual = os.path.dirname(sys.executable)
        else:
            caminho_script_atual = os.path.abspath(os.path.dirname(__file__))

        # Concatenar com o subdiretório 'downloads'
        pasta = os.path.join(caminho_script_atual, 'downloads')
        arquivo = f"{numero}.pdf"
        caminho = os.path.join(pasta, arquivo)
        return caminho

class DownloadPDFSEI:
    def __init__(self, navegador, documento, num_sei_doc):
        self.driver = navegador
        self.documento = documento
        self.num_sei_doc = num_sei_doc



    def baixar_pdf_SEI(self):
        wait = WebDriverWait(self.driver, 10)  # Espera até 5 segundos
        # Obtenha o diretório raiz do script
        base_path = os.path.dirname(os.path.abspath(__file__))  # Caminho do arquivo atual
        download_folder = os.path.join(base_path, 'downloads')  # Pasta downloads na raiz do script
        # Garante que a pasta existe
        if not os.path.exists(download_folder):
            os.makedirs(download_folder)

        # Caminho final do arquivo
        arquivo_pdf = os.path.join(download_folder, f'{self.num_sei_doc}.pdf')

        # Atualiza o texto parcial antes de clicar no documento
        documentos = DocumentosArvoreSei(self.driver, self.documento)
        documentos.clicar_no_documento()

        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()
        time.sleep(TempoAleatorio().tempo_aleatorio())  # Simula comportamento humano
        # IframesSei(self.driver, "Exibe documentos").navegar_iframes_sei()
        iframe = self.driver.find_element(By.ID, "ifrArvoreHtml")
        pdf_url = iframe.get_attribute("src")
        print(pdf_url)

        # Obtenha os cookies do Selenium
        cookies = self.driver.get_cookies()
        session = requests.Session()

        for cookie in cookies:
            session.cookies.set(cookie['name'], cookie['value'])

        # Agora faça o download do PDF
        response = session.get(pdf_url)
        if response.status_code == 200:
            with open(arquivo_pdf, "wb") as f:
                f.write(response.content)
            print("PDF baixado com sucesso!")
        else:
            print("Falha ao baixar o PDF, status code:", response.status_code)

        return arquivo_pdf




        # try:
        #     # Localizar o elemento <a> pelo seletor apropriado (classe neste caso)
        #     link_element = WebDriverWait(self.driver, 10).until(
        #         EC.presence_of_element_located((By.CLASS_NAME, "ancoraVisualizacaoArvore"))
        #     )
        #
        #     # Colocar o foco no elemento sem clicar
        #     self.driver.execute_script("arguments[0].focus();", link_element)
        #     print("Foco colocado no elemento com sucesso.")
        #
        #     # Usar ActionChains para enviar TABs
        #     actions = ActionChains(self.driver)
        #
        #     for _ in range(8):  # Enviar 7 TABs
        #         actions.send_keys(Keys.TAB)
        #         actions.perform()
        #         time.sleep(0.5)  # Pequeno intervalo entre TABs para simular comportamento humano
        #
        #     # Enviar ENTER
        #     actions.send_keys(Keys.ENTER).perform()
        #     print("ENTER enviado após os TABs.")
        #     time.sleep(5)
        #
        # except Exception as e:
        #     print(f"Erro ao interagir com o elemento: {e}")
        #
        # try:
        #     app = Application().connect(title_re="Salvar como")
        #     time.sleep(0.5)
        #     dlg = app.window(title_re="Salvar como")
        #     time.sleep(0.5)
        #
        #     # Verifica se o script está rodando como um executável
        #     if getattr(sys, 'frozen', False):
        #         caminho_script_atual = os.path.dirname(sys.executable)
        #     else:
        #         caminho_script_atual = os.path.abspath(os.path.dirname(__file__))
        #
        #     # Concatenar com o subdiretório 'downloads'
        #     pasta = os.path.join(caminho_script_atual, 'downloads')
        #     arquivo = f"{numero_nota_tec}.pdf"
        #     caminho = os.path.join(pasta, arquivo)
        #
        #
        #     dlg.type_keys(caminho)
        #     logging.info(f'Caminho do arquivo inserido na janela de diálogo: {caminho}.')
        #     time.sleep(2)
        #     dlg.type_keys('{ENTER}')
        #     time.sleep(2)
        #     logging.info('Arquivo anexado com sucesso.')
        #     return caminho
        #
        # except Exception as e:
        #     logging.error(f'Erro ao inserir o anexo "{self.arquivo}": {str(e)}')

class EstatisticasSEI:
    def __init__(self, navegador):
        self.driver = navegador

    def acessar_estatisticas(self):

        self.driver.switch_to.default_content()
        elemento = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Estatísticas']")))
        elemento.click()
        time.sleep(0.2)
        self.driver.switch_to.default_content()
        elemento = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@link='gerar_estatisticas_unidade']"))
        )
        elemento.click()

        data_ini = "01/01/2024"
        data_fim = "11/12/2024"

        self.insert_data_and_press_enter('txtPeriodoDe', data_ini, False)
        self.insert_data_and_press_enter('txtPeriodoA', data_fim, True)

    def insert_data_and_press_enter(self, element_id, data, campo2):
        try:
            elemento = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.ID, element_id))
            )
            self.driver.execute_script(f"arguments[0].value = '{data}';", elemento)
            if campo2:
                elemento.send_keys(Keys.ENTER)
        except TimeoutException:
            logging.info(f"O elemento com ID '{element_id}' não foi encontrado no tempo especificado.")

class IniciaProcessos:
    def __init__(self, navegador, especificacao, classificacao, interessado, observacao, tipo="Arrecadação: Cobrança"):
        self.driver = navegador
        self.especificacao = especificacao
        self.classificacao = classificacao
        self.interessado = interessado
        self.observacao = observacao
        self.tipo = tipo

    def iniciar_processo(self):
        wait = WebDriverWait(self.driver, 10)
        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            # Localiza o elemento pelo texto do span
            elemento = self.driver.find_element(By.XPATH, '//span[text()="Iniciar Processo"]')
            elemento.click()
            logging.info('Botão "Iniciar Processo" clicado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao clicar no botão "Iniciar Processo": {str(e)}')
            return

        # Aguarda um tempo aleatório e insere o valor no campo de texto
        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            # Localiza o elemento pelo atributo title
            elemento_img = self.driver.find_element(By.XPATH, '//img[@title="Exibir todos os tipos"]')
            elemento_img.click()
            logging.info('Imagem com título "Exibir todos os tipos" clicada com sucesso.')
        except:
            pass

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            campo_filtro = self.driver.find_element(By.ID, "txtFiltro")  # Localiza o campo pelo ID
            campo_filtro.clear()  # Limpa o campo antes de inserir o valor
            campo_filtro.send_keys(self.tipo)  # Insere o valor de self.tipo no campo
            logging.info(f'Valor "{self.tipo}" inserido no campo de texto com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())
            # Envia TAB e ENTER após a inserção
            campo_filtro.send_keys(Keys.TAB)  # Envia TAB
            logging.info('TAB enviado com sucesso.')
            # Envia ENTER para o elemento que ganhou o foco
            elemento_focado = self.driver.switch_to.active_element
            elemento_focado.send_keys(Keys.ENTER)
            logging.info('ENTER enviado para o elemento focado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir o valor no campo de texto: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            campo_especificacao = self.driver.find_element(By.ID, "txtDescricao")  # Localiza o campo pelo ID
            campo_especificacao.clear()  # Limpa o campo antes de inserir o valor
            campo_especificacao.send_keys(self.especificacao)  # Insere o valor de self.tipo no campo
            logging.info(f'Valor "{self.especificacao}" inserido no campo de texto com sucesso.')

        except Exception as e:
            logging.error(f'Erro ao inserir o valor no campo de texto: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            # Localiza o elemento <option> pelo atributo value ou pelo texto
            elemento_option = self.driver.find_element(
                By.XPATH,
                '//option[text()="ASSUNTO - CLASSIFICAÇÃO PENDENTE DE AVALIAÇÃO"]'
            )

            # Clica no elemento
            elemento_option.click()

            # Loga a mensagem de sucesso
            logging.info('Opção "ASSUNTO - CLASSIFICAÇÃO PENDENTE DE AVALIAÇÃO" clicada com sucesso.')

            remove_assunto = self.driver.find_element(By.XPATH, '//img[@title="Remover Assuntos Selecionados"]')
            remove_assunto.click()

        except Exception as e:
            # Loga a mensagem de erro em caso de falha
            logging.error(f'Erro ao clicar na opção "ASSUNTO - CLASSIFICAÇÃO PENDENTE DE AVALIAÇÃO": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            campo_classificacao = self.driver.find_element(By.ID, "txtAssunto")  # Localiza o campo pelo ID
            campo_classificacao.clear()  # Limpa o campo antes de inserir o valor
            campo_classificacao.send_keys(self.classificacao)  # Insere o valor de self.tipo no campo
            time.sleep(TempoAleatorio().tempo_aleatorio())
            campo_classificacao.send_keys(Keys.ARROW_DOWN)  # Navega para a primeira sugestão
            time.sleep(TempoAleatorio().tempo_aleatorio())
            campo_classificacao.send_keys(Keys.ENTER)

            logging.info(f'Valor "{self.classificacao}" inserido no campo de texto com sucesso.')

        except Exception as e:
            logging.error(f'Erro ao inserir o valor no campo de texto: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            campo_interessado = self.driver.find_element(By.ID, "txtInteressadoProcedimento")  # Localiza o campo pelo ID
            campo_interessado.clear()  # Limpa o campo antes de inserir o valor
            campo_interessado.send_keys(self.interessado)  # Insere o valor de self.tipo no campo
            campo_interessado.send_keys(Keys.ENTER)
            alert = Alert(self.driver)
            alert.accept()

            logging.info(f'Valor "{self.interessado}" inserido no campo de texto com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())
            clique_interessado = self.driver.find_element(By.ID, "selInteressadosProcedimento")
            clique_interessado.click()

        except Exception as e:
            logging.error(f'Erro ao inserir o valor no campo de texto: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        # try:
        #     campo_observacao = self.driver.find_element(By.ID,
        #                                                  "txaObservacoes")  # Localiza o campo pelo ID
        #     campo_observacao.clear()  # Limpa o campo antes de inserir o valor
        #     campo_observacao.send_keys(self.observacao)  # Insere o valor de self.tipo no campo
        #     campo_observacao.send_keys(Keys.ENTER)
        #     time.sleep(0.5)
        #
        #     logging.info(f'Valor "{self.observacao}" inserido no campo de texto com sucesso.')
        #
        #     time.sleep(TempoAleatorio().tempo_aleatorio())
        #     time.sleep(10)
        #
        # except Exception as e:
        #     logging.error(f'Erro ao inserir o valor no campo de texto: {str(e)}')
        #     return

        TipoAcesso(self.driver).escolher_acesso()

        try:
            # Aguarda o botão Salvar estar clicável e clica nele
            btn_salvar = wait.until(EC.element_to_be_clickable((By.ID, "btnSalvar")))
            btn_salvar.click()
        except Exception as e:
            logging.error("Erro ao clicar no botão 'Salvar': %s", e)

class TipoAcesso:
    def __init__(self, navegador):
        self.driver = navegador

    def escolher_acesso(self):
        try:
            # Clica na opção de restrição
            self.driver.find_element(By.XPATH, '//*[@id="divOptRestrito"]/div/label').click()
            logging.info('Opção de restrição selecionada.')

            # Simula comportamento humano com uma espera aleatória
            time.sleep(TempoAleatorio().tempo_aleatorio())

            # Tenta selecionar o dropdown utilizando o método com retry
            self._selecionar_dropdown()
        except Exception as e:
            logging.error(f'Erro ao marcar tipo de acesso: {str(e)}')
            # Aqui você pode tratar a exceção conforme a necessidade
            return

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), reraise=True)
    def _selecionar_dropdown(self):
        """
        Tenta selecionar o dropdown. Caso o elemento não esteja disponível,
        o tenacity realizará até 3 tentativas, esperando 2 segundos entre elas.
        """
        time.sleep(TempoAleatorio().tempo_aleatorio())
        # Tenta encontrar o dropdown
        dropdown_element = self.driver.find_element(By.XPATH, '//*[@id="selHipoteseLegal"]')
        drop = Select(dropdown_element)

        # Seleciona a opção desejada
        drop.select_by_visible_text("Informação Pessoal (Art. 31 da Lei nº 12.527/2011)")
        logging.info('Hipótese legal "Informação Pessoal" selecionada.')

class IncluiNotaPss:
    def __init__(self, navegador, processo_sei, nome_pen, mat_pen, valor):
        self.driver = navegador
        self.processo_sei = processo_sei
        self.nome_pen = nome_pen
        self.mat_pen = mat_pen
        self.valor = float(valor)

    def incluir_nota_tecnica_pss(self):
        logging.info('Iniciando a inclusão da Nota Técnica Pss.')
        wait = WebDriverWait(self.driver, 10)

        # Garante que estamos no conteúdo principal
        self.driver.switch_to.default_content()

        # Aguarda ativamente que o frame 'ifrVisualizacao' esteja disponível e troca para ele
        wait.until(EC.frame_to_be_available_and_switch_to_it("ifrVisualizacao"))

        try:
            # Aguarda até que o ícone esteja clicável e realiza o clique
            elemento = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '/html/body/div[1]/div/div/div[2]/div/a[1]/img')))
            elemento.click()
            logging.info('Clique no ícone para incluir Nota Técnica realizado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao clicar no ícone para incluir Nota Técnica: {str(e)}')
            return

        try:
            # Aguarda que o campo de filtro esteja visível e envia os comandos
            filtro = wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="txtFiltro"]')))
            filtro.send_keys('Nota Técnica', Keys.TAB, Keys.ENTER)
            logging.info('Filtro "Nota Técnica" aplicado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao aplicar filtro "Nota Técnica": {str(e)}')
            return

        try:
            # Clica no label do protocolo e aguarda que o input correspondente esteja visível
            protocolo_label = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="divOptProtocoloDocumentoTextoBase"]/div/label')))
            protocolo_label.click()
            protocolo_input = wait.until(EC.visibility_of_element_located(
                (By.XPATH, '//*[@id="txtProtocoloDocumentoTextoBase"]')))
            protocolo_input.send_keys("47819347")
            logging.info('Protocolo do documento base inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir protocolo do documento base: {str(e)}')
            return

        try:
            # Preenche os demais campos da Nota Técnica
            nome_arvore = wait.until(EC.visibility_of_element_located((By.ID, 'txtNomeArvore')))
            nome_arvore.send_keys(' Passivo tributário PSS')
            restrito_label = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="divOptRestrito"]/div/label')))
            restrito_label.click()
            time.sleep(TempoAleatorio().tempo_aleatorio())
            select_element = wait.until(EC.element_to_be_clickable(
                (By.XPATH, '//*[@id="selHipoteseLegal"]')))
            drop = Select(select_element)
            drop.select_by_visible_text("Informação Pessoal (Art. 31 da Lei nº 12.527/2011)")
            logging.info('Campos da Nota Técnica preenchidos com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao preencher os campos da Nota Técnica: {str(e)}')
            return
        # Armazena os handles existentes antes de acionar a abertura do novo conteúdo
        handles_anteriores = self.driver.window_handles

        try:
            # Aguarda o botão Salvar estar clicável e clica nele
            btn_salvar = wait.until(EC.element_to_be_clickable((By.ID, "btnSalvar")))
            btn_salvar.click()
        except Exception as e:
            logging.error("Erro ao clicar no botão 'Salvar': %s", e)

        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            # Formata o valor e converte para extenso
            locale.setlocale(locale.LC_ALL, 'pt_BR.utf8')
            valor_formatado = locale.currency(self.valor, grouping=True, symbol=True)
            valor_extenso = num2words(self.valor, lang='pt_BR', to='currency')
            logging.info(f'Valores formatados: {valor_formatado}, {valor_extenso}.')
        except Exception as e:
            logging.error(f'Erro ao preparar os dados para inclusão da Nota Técnica: {str(e)}')
            return

        texto_padrao = (
            f"Nos termos do presente expediente e em face do que consta dos autos, autorizo o envio de "
            f"notificação para dar ciência da instauração de processo administrativo para a cobrança de "
            f"passivos no valor de {valor_formatado} ({valor_extenso}), em desfavor do(a) pensionista "
            f"{self.nome_pen}, SIAPE : {self.mat_pen}. Lembrando que a reposição poderá ser realizada de "
            f"forma parcelada (em parcelas não inferiores à 10% de sua remuneração/proventos até a sua "
            f"quitação) em folha de pagamento ou em cota única, mediante quitação através de Guia de "
            f"Recolhimento da União-GRU."
        )

        # Aguarda até que uma nova janela (ou aba) seja aberta
        wait.until(lambda d: len(d.window_handles) > len(handles_anteriores))

        # Armazena a janela original para retornar depois
        janela_original = self.driver.current_window_handle

        # Identifica a nova handle (aquela que não estava presente antes)
        nova_handle = next(handle for handle in self.driver.window_handles if handle not in handles_anteriores)

        # Muda para a nova janela/aba e maximiza
        self.driver.switch_to.window(nova_handle)
        self.driver.maximize_window()

        # Aguarda que os frames com a classe 'cke_wysiwyg_frame' estejam presentes
        frames = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'cke_wysiwyg_frame')))

        # Troca para o frame que contém a Nota Técnica e extrai o número
        self.driver.switch_to.frame(frames[2])
        numero_nota_tecnica_elem = wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//p[contains(text(), 'Nota Técnica SEI nº')]")))
        numero_nota_tecnica = numero_nota_tecnica_elem.text

        # Volta para o conteúdo principal e muda para o frame onde serão preenchidas as informações
        self.driver.switch_to.default_content()
        self.driver.switch_to.frame(frames[7])

        # Preenche os campos utilizando esperas ativas
        cell1 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[1]/tbody/tr[1]/td[2]')))
        cell1.send_keys(self.processo_sei)

        cell2 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[1]/tbody/tr[3]/td[2]')))
        cell2.click()
        cell2.send_keys(self.nome_pen)

        cell3 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[1]/tbody/tr[5]/td[2]')))
        cell3.click()
        cell3.send_keys(self.mat_pen)

        cell4 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[3]/tbody/tr[1]/td[2]')))
        cell4.click()
        cell4.send_keys(f" {valor_formatado} ({valor_extenso})")

        # Atualiza o parágrafo com o texto padrão
        paragraph = wait.until(EC.visibility_of_element_located((By.XPATH, '/html/body/p[10]')))
        self.driver.execute_script('arguments[0].innerText = arguments[1]', paragraph, texto_padrao)

        # Volta para o conteúdo principal e aguarda que o botão de salvar esteja clicável
        self.driver.switch_to.default_content()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        salvar_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="cke_455_label"]')))
        salvar_button.click()
        time.sleep(TempoAleatorio().tempo_aleatorio())

        # Fecha a nova janela/aba
        self.driver.close()

        # Muda o foco de volta para a janela original
        self.driver.switch_to.window(janela_original)

        return numero_nota_tecnica

class NotificacaoNumeradaPss():
    def __init__(self, navegador, tipo_doc, protocolo, nome_arvore, nota_tecnica, processo, nome_pen, mat_pen, cpf_pen, logradouro, bairro, cidade, uf, cep):
        self.driver = navegador
        self.tipo_doc = tipo_doc
        self.protocolo = protocolo
        self.nome_arvore = nome_arvore
        self.nota_tecnica = nota_tecnica
        self.processo = processo
        self.nome_pen = nome_pen
        self.mat_pen = mat_pen
        self.cpf_pen = cpf_pen
        self.logradouro = logradouro
        self.bairro = bairro
        self.cidade = cidade
        self.uf = uf
        self.cep = cep

    def inserir_notificacao_numerada_pss(self):
        # Configurar a localização para português do Brasil
        locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
        logging.info(
            f'Iniciando a inclusão do documento interno: Tipo "{self.tipo_doc}", Protocolo "{self.protocolo}".')

        wait = WebDriverWait(self.driver, 10)
        time.sleep(0.5)
        # Garante que estamos no conteúdo principal
        self.driver.switch_to.default_content()

        # Aguarda ativamente que o frame 'ifrVisualizacao' esteja disponível e troca para ele
        wait.until(EC.frame_to_be_available_and_switch_to_it("ifrVisualizacao"))
        # self.driver.switch_to.frame('ifrArvore')
        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            IconesBarraProcessoSei(self.driver, "Incluir Documento").clicar_icone_barra()
            logging.info('Ícone "Incluir Documento" clicado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao clicar no ícone "Incluir Documento": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.XPATH, '//*[@id="txtFiltro"]').send_keys(self.tipo_doc, Keys.TAB, Keys.ENTER)
            logging.info(f'Documento do tipo "{self.tipo_doc}" filtrado com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao filtrar documento do tipo "{self.tipo_doc}": {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.XPATH, '//*[@id="divOptProtocoloDocumentoTextoBase"]/div/label').click()
            logging.info('Opção de protocolo de documento base selecionada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())
            self.driver.find_element(By.XPATH, '//*[@id="txtProtocoloDocumentoTextoBase"]').send_keys(self.protocolo)
            logging.info(f'Protocolo "{self.protocolo}" inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir protocolo do documento base: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        try:
            self.driver.find_element(By.ID, 'txtNomeArvore').send_keys(self.nome_arvore)
            logging.info(f'Nome da árvore "{self.nome_arvore}" inserido com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao inserir o nome da árvore "{self.nome_arvore}": {str(e)}')
            return

        try:
            self.driver.find_element(By.XPATH, '//*[@id="divOptRestrito"]/div/label').click()
            logging.info('Opção de restrição selecionada com sucesso.')
            time.sleep(TempoAleatorio().tempo_aleatorio())
            drop = Select(self.driver.find_element(By.XPATH, '//*[@id="selHipoteseLegal"]'))
            drop.select_by_visible_text("Informação Pessoal (Art. 31 da Lei nº 12.527/2011)")
            logging.info('Hipótese legal "Informação Pessoal" selecionada com sucesso.')
        except Exception as e:
            logging.error(f'Erro ao selecionar a hipótese legal: {str(e)}')
            return

        time.sleep(TempoAleatorio().tempo_aleatorio())
        # Armazena as janelas abertas antes de clicar no botão "Salvar"
        janelas_antes = set(self.driver.window_handles)

        # Armazena a janela original e os handles existentes antes de acionar a abertura do novo conteúdo
        janela_original = self.driver.current_window_handle
        handles_antes = self.driver.window_handles.copy()

        try:
            # Clica no botão "Salvar"
            self.driver.find_element(By.XPATH, '//*[@id="btnSalvar"]').click()
            logging.info('Botão "Salvar" clicado com sucesso, documento interno incluído.')
        except Exception as e:
            logging.error(f'Erro ao clicar no botão "Salvar": {str(e)}')
            return

        # Aguarda um tempo aleatório para simular o comportamento humano
        time.sleep(TempoAleatorio().tempo_aleatorio())

        # Aguarda até que uma nova janela seja aberta
        WebDriverWait(self.driver, 10).until(
            lambda driver: len(set(driver.window_handles) - set(handles_antes)) == 1
        )

        # Obtém a nova janela que foi aberta
        nova_janela = list(set(self.driver.window_handles) - set(handles_antes))[0]

        # Muda para a nova janela
        self.driver.switch_to.window(nova_janela)
        self.driver.maximize_window()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        self.driver.refresh()
        time.sleep(TempoAleatorio().tempo_aleatorio())

        try:
            # Localiza os frames desejados pela classe 'cke_wysiwyg_frame'
            frames = self.driver.find_elements(By.CLASS_NAME, 'cke_wysiwyg_frame')
            # Verifica se existem frames suficientes
            if len(frames) < 3:
                raise Exception("Não foram encontrados frames suficientes para prosseguir.")
            # Troca para o frame desejado (índice 2)
            self.driver.switch_to.frame(frames[2])
        except Exception as e:
            logging.error(f'Erro durante a manipulação da nova janela: {str(e)}')
            # Caso ocorra um erro, retorna para a janela original e interrompe a execução
            self.driver.switch_to.window(janela_original)
            return

        # Configura o locale para pt_BR (pode variar de sistema para sistema)
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        except locale.Error:
            print("Locale pt_BR.UTF-8 não disponível.")

        hoje = datetime.now()
        # Formata a data: %B para o nome completo do mês, %Y para o ano
        data_formatada = hoje.strftime("%B/%Y").upper()

        # Preenche os campos utilizando esperas ativas

        # Preencher processo SEI
        cell = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[1]/tbody/tr[2]/td[2]')
        ))
        cell.send_keys(self.processo)

        # Preencher data
        cell1 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[1]/tbody/tr[2]/td[3]')
        ))
        cell1.click()
        cell1.send_keys(data_formatada)

        # Preencher Nome
        cell2 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[2]/tbody/tr[2]/td[1]')
        ))
        cell2.click()
        cell2.send_keys(self.nome_pen)

        # Preencher Matrícula
        cell3 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[2]/tbody/tr[2]/td[2]')
        ))
        cell3.click()
        cell3.send_keys(self.mat_pen)

        # Preencher CPF
        cpf_formatado = f"{self.cpf_pen[:3]}.{self.cpf_pen[3:6]}.{self.cpf_pen[6:9]}-{self.cpf_pen[9:]}"
        cell4 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[2]/tbody/tr[2]/td[3]')
        ))
        cell4.click()
        cell4.send_keys(cpf_formatado)

        # Preencher Endereço
        cell5 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[3]/tbody/tr[2]/td[1]')
        ))
        cell5.click()
        cell5.send_keys(f"{self.logradouro}/{self.bairro}")

        cell6 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[3]/tbody/tr[2]/td[2]')
        ))
        cell6.click()
        cell6.send_keys(f"{self.cidade}/{self.uf}")

        cell7 = wait.until(EC.presence_of_element_located(
            (By.XPATH, '/html/body/table[3]/tbody/tr[2]/td[3]')
        ))
        cell7.click()
        cell7.send_keys(self.cep)

        # Novo texto para substituir
        novo_texto1 = (
            f"A fim de esclarecer sobre o objeto da referida instauração, seguem anexos memória de cálculo e "
            f"cópia da <strong>{self.nota_tecnica}</strong>, com manifestação sobre a identificação dos "
            f"indícios de irregularidade e fundamentos jurídicos pertinentes."
        )

        elemento = self.driver.find_element(
            By.XPATH,
            "//span[contains(., 'A fim de esclarecer sobre o objeto da referida instauração')]"
        )

        # Substitui o conteúdo interno (incluindo as tags) utilizando innerHTML
        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", elemento, novo_texto1)

        novo_texto2 = (
            f"Obs: No caso de manifestação sobre a presente Notificação, solicitamos referenciar o 'número do processo "
            f"administrativo' acima destacado juntamente com o nome manifestação <strong>(ex. Manifestação - {self.processo})</strong>."
        )

        elemento2 = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//p[contains(@class, 'Tabela_Texto_Alinhado_Esquerda') and contains(., 'Obs: No caso de manifestação')]")
            )
        )
        self.driver.execute_script("arguments[0].innerHTML = arguments[1];", elemento2, novo_texto2)

        time.sleep(TempoAleatorio().tempo_aleatorio())
        self.driver.switch_to.default_content()

        # Clica em um elemento específico (por exemplo, o botão de confirmação)
        self.driver.find_element(By.XPATH, '//*[@id="cke_145_label"]').click()
        time.sleep(0.5)

        # Fecha a nova janela e retorna para a janela original
        self.driver.close()
        self.driver.switch_to.window(janela_original)

class NumeroProtocolo():
    def __init__(self, navegador, documento):
        self.driver = navegador
        self.documento = documento

    def recuperar_protocolo(self):
        self.driver.switch_to.default_content()
        IframesSei(self.driver, "Arvore documentos").navegar_iframes_sei()

        # Aguarda até que todos os elementos que contenham o texto parcial definido estejam presentes
        protoc_comp = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.PARTIAL_LINK_TEXT, self.documento))
        )

        # Seleciona o último elemento da lista
        ultimo_protocol = protoc_comp[-1]

        # Extrai o texto, removendo espaços em branco extras
        protocol_txt = ultimo_protocol.text.strip()

        return protocol_txt

class AcessoExterno:
    def __init__(self, navegador, email_unidade, nome_bene, email_bene, motivo, validade):
        self.driver = navegador
        self.email_unidade = email_unidade
        self.nome_bene = nome_bene
        self.email_bene = email_bene
        self.motivo = motivo
        self.validade = validade

    def conceder_acesso_externo(self):
        IconesBarraProcessoSei(self.driver, "Gerenciar Disponibilizações de Acesso Externo").clicar_icone_barra()
        IframesSei(self.driver, "Exibe frame documentos").navegar_iframes_sei()

        time.sleep(TempoAleatorio().tempo_aleatorio())
        # Tenta encontrar o dropdown
        try:
            # Aguarda até que o elemento do dropdown esteja visível
            dropdown_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="selEmailUnidade"]'))
            )

            drop = Select(dropdown_element)

            # Seleciona a opção desejada
            drop.select_by_visible_text(self.email_unidade)
            logging.info('Hipótese legal "Informação Pessoal" selecionada.')

        except Exception as e:
            logging.error(f"Erro ao selecionar a hipótese legal: {e}")

        try:
            # Aguarda até que o campo de input esteja visível
            input_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "txtDestinatario"))
            )

            # Limpa o campo antes de inserir o valor
            input_element.clear()

            # Insere o valor da variável self.nome_bene
            input_element.send_keys(self.nome_bene)
            logging.info(f'Nome do beneficiário inserido: {self.nome_bene}')

            # Aguarda a exibição da lista de autocomplete
            auto_complete_list = WebDriverWait(self.driver, 30).until(
                EC.visibility_of_element_located((By.ID, "divInfraAjaxtxtDestinatario"))
            )

            # Aguarda um pequeno intervalo para garantir que a lista seja completamente carregada
            WebDriverWait(self.driver, 2)

            # Pressiona ENTER para confirmar a seleção
            input_element.send_keys(Keys.ENTER)
            logging.info("Tecla Enter pressionada para confirmar a seleção.")

        except Exception as e:
            logging.error(f"Erro ao inserir nome do beneficiário: {e}")

        try:
            # Aguarda até que o campo de input esteja visível
            input_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "txtEmailDestinatario"))
            )

            # Limpa o campo antes de inserir o valor
            input_element.clear()

            # Insere o valor da variável self.email_bene
            input_element.send_keys(self.email_bene)

            logging.info(f'Email do beneficiário inserido: {self.email_bene}')

        except Exception as e:
            logging.error(f"Erro ao inserir email do beneficiário: {e}")

        try:
            # Aguarda até que o campo de textarea esteja visível
            textarea_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "txaMotivo"))
            )

            # Limpa o campo antes de inserir o valor
            textarea_element.clear()

            # Insere o valor da variável self.motivo
            textarea_element.send_keys(self.motivo)

            logging.info(f'Motivo inserido: {self.motivo}')

        except Exception as e:
            logging.error(f"Erro ao inserir motivo: {e}")

        try:
            # Aguarda até que o label esteja visível e clicável
            label_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "lblIntegral"))
            )

            # Clica no label para selecionar o radio button correspondente
            label_element.click()

            logging.info('Opção "Acompanhamento integral do processo" selecionada.')

        except Exception as e:
            logging.error(f"Erro ao selecionar a opção de acompanhamento integral: {e}")

        try:
            # Aguarda até que o campo de input esteja visível
            input_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "txtDias"))
            )

            # Limpa o campo antes de inserir o valor
            input_element.clear()

            # Insere o valor da variável self.validade
            input_element.send_keys(self.validade)

            logging.info(f'Validade inserida: {self.validade} dias')

        except Exception as e:
            logging.error(f"Erro ao inserir validade: {e}")

        senha_acesso = "#Th3l3M4rc0"

        try:
            # Aguarda até que o campo de senha esteja visível
            senha_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.ID, "pwdSenha"))
            )

            # Limpa o campo antes de inserir o valor
            senha_element.clear()

            # Insere o valor da variável self.senha_acesso
            senha_element.send_keys(senha_acesso)

            logging.info('Senha inserida com sucesso.')

        except Exception as e:
            logging.error(f"Erro ao inserir a senha: {e}")

        try:
            # Aguarda até que o botão esteja visível e clicável
            button_element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btnDisponibilizar"))
            )

            # Clica no botão
            button_element.click()

            logging.info('Botão "Disponibilizar" clicado com sucesso.')

        except Exception as e:
            logging.error(f"Erro ao clicar no botão 'Disponibilizar': {e}")

class AcessoAnotacao:
    def __init__(self, navegador):
        self.driver = navegador

    @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
    def acessar_anotacao_com_retry(self):
        IconesBarraProcessoSei(self.driver, "Anotações").clicar_icone_barra()

        texto_cpf = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.ID, "txaDescricao"))
        ).get_attribute('value')

        return texto_cpf

class ApagaDocumentoSEI:
    def __init__(self, navegador, texto_parcial):
        self.driver = navegador
        self.texto_parcial = texto_parcial

    def apagar_documento_sei(self):
        wait = WebDriverWait(self.driver, 10)
        time.sleep(TempoAleatorio().tempo_aleatorio())
        IframesSei(self.driver, "Arvore documentos").navegar_iframes_sei()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        DocumentosArvoreSei(self.driver, self.texto_parcial).clicar_no_documento()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        IconesBarraProcessoSei(self.driver, "Excluir").clicar_icone_barra()
        time.sleep(TempoAleatorio().tempo_aleatorio())
        alert = wait.until(EC.alert_is_present())
        alert.accept()
        time.sleep(TempoAleatorio().tempo_aleatorio())

