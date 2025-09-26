
import time
import logging
from num2words import num2words
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .SEI_Geral import LoginSei, TelaAviso, SelecaoUnidade, StatusLogin, PaginaMovimentacoes

import os

class AutomacaoPassivo:
    """
    Classe principal para automação do processo passivo no SEI
    """
    
    def __init__(self, usuario, senha, unidade):
        """
        Inicializa a automação
        
        Args:
            usuario: Nome de usuário do SEI
            senha: Senha do usuário
            unidade: Nome da unidade a ser selecionada
        """
        self.usuario = usuario
        self.senha = senha
        self.unidade = unidade
        self.driver = None
        self.login_sei = None
        self.tela_aviso = None
        self.selecao_unidade = None
        
        # Configurar logging
        self._configurar_logging()
    
    def _configurar_logging(self):
        """Configura o sistema de logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('automacao_mgi_passivo.log'),
                logging.StreamHandler()
            ]
        )
    
    def _inicializar_navegador(self):
        """Inicializa o navegador Chrome"""
        try:
            chrome_options = Options()
            # Comentado para mostrar a janela do navegador
            # chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.maximize_window()
            
            logging.info('Navegador inicializado com sucesso.')
            return True
        except Exception as e:
            logging.error(f'Erro ao inicializar navegador: {e}')
            return False
    
    def _realizar_login(self):
        """
        Realiza o login no SEI usando a classe LoginSei
        
        Returns:
            bool: True se login foi bem-sucedido, False caso contrário
        """
        try:
            # Instancia a classe de login
            self.login_sei = LoginSei(self.driver, self.usuario, self.senha)
            
            # Executa o login
            status_login = self.login_sei.logar_sei()
            
            # Verifica o resultado
            if status_login == StatusLogin.SUCESSO:
                # Verifica novamente se o login foi realmente bem-sucedido
                if self.login_sei.verificar_login_bem_sucedido():
                    logging.info('Login realizado com sucesso!')
                    return True
                else:
                    logging.error('Falha na verificação do login.')
                    return False
            elif status_login == StatusLogin.CREDENCIAIS_INVALIDAS:
                logging.error('Credenciais inválidas!')
                return False
            else:
                logging.error('Erro durante o processo de login.')
                return False
                
        except Exception as e:
            logging.error(f'Erro durante o login: {e}')
            return False
    
    def _fechar_tela_aviso(self):
        """Remove a tela de aviso após o login"""
        try:
            self.tela_aviso = TelaAviso(self.driver)
            self.tela_aviso.fechar_tela_aviso_sei()
            time.sleep(2)  # Aguarda um pouco após fechar o aviso
            logging.info('Tela de aviso fechada com sucesso.')
        except Exception as e:
            logging.warning(f'Erro ao fechar tela de aviso (pode não ter aparecido): {e}')
    
    def _selecionar_unidade_mgi(self):
        """
        Seleciona especificamente a unidade MGI-SGP-DECIPEX-CGPAG-ANIST
        
        Returns:
            bool: True se unidade foi selecionada com sucesso, False caso contrário
        """
        try:
            logging.info(f'Iniciando seleção da unidade MGI: {self.unidade}')
            
            # Instancia a classe de seleção de unidade
            self.selecao_unidade = SelecaoUnidade(None, self.driver, self.unidade)
            
            # Executa a seleção da unidade MGI
            self.selecao_unidade.selecionar_unidade_sei()
            
            logging.info('Unidade MGI-SGP-DECIPEX-CGPAG-ANIST selecionada com sucesso!')
            time.sleep(3)  # Aguarda um pouco após selecionar a unidade
            return True
            
        except Exception as e:
            logging.error(f'Erro durante seleção da unidade MGI: {e}')
            return False