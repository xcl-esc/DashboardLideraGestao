from .log_config import setup_logging
import logging
from selenium import webdriver
import chromedriver_autoinstaller
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_exception_type
from typing import Dict, Any, Optional, List, Tuple
import os
import glob
import json
import re
import subprocess
import sys
import platform
import requests
from contextlib import contextmanager
import importlib.util

# Caminho absoluto para o arquivo log_config.py
current_dir = os.path.dirname(os.path.abspath(__file__))
log_config_path = os.path.join(current_dir, "log_config.py")

# Importa o módulo a partir do caminho absoluto
if os.path.exists(log_config_path):
    spec = importlib.util.spec_from_file_location("log_config", log_config_path)
    log_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(log_config)
    setup_logging = log_config.setup_logging
else:
    # Tenta importar normalmente como fallback
    from .log_config import setup_logging


class SeleniumSetup:
    """
    Classe responsável por configurar e gerenciar o ambiente Selenium para automação web.

    Esta classe configura o Chrome WebDriver com opções personalizáveis, gerencia a pasta
    de downloads e implementa funcionalidades como atualização automática do chromedriver
    e limpeza de arquivos temporários.
    """

    def __init__(self, download_folder: Optional[str] = None):
        """
        Inicializa a configuração do Selenium.

        Args:
            download_folder: Caminho personalizado para a pasta de downloads.
                            Se não for fornecido, será criada uma pasta 'downloads' no diretório base.
        """
        # Configuração de logging
        self.logger = logging.getLogger(__name__)
        setup_logging()

        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.download_folder = download_folder or os.path.join(self.base_path, 'downloads')

        # Criar o diretório 'downloads' se não existir
        try:
            if not os.path.exists(self.download_folder):
                os.makedirs(self.download_folder)
                self.logger.info(f"Pasta de downloads criada: {self.download_folder}")

            # Limpar a pasta de downloads
            self.limpar_downloads()
        except Exception as e:
            self.logger.error(f"Erro ao configurar pasta de downloads: {str(e)}")
            raise

    @property
    def get_download_folder(self) -> str:
        """
        Retorna o caminho da pasta de downloads.

        Returns:
            str: Caminho completo para a pasta de downloads.
        """
        return self.download_folder

    def limpar_downloads(self, padroes: List[str] = None) -> None:
        """
        Remove arquivos com padrões específicos da pasta de downloads.

        Args:
            padroes: Lista de padrões de arquivos a serem removidos.
                    Se não fornecido, usa o padrão 'hodcivws*.jsp' por padrão.
        """
        if padroes is None:
            padroes = ['hodcivws*.jsp']

        self.logger.info(f"Limpando pasta de downloads: {self.download_folder}")
        try:
            for padrao in padroes:
                arquivos = glob.glob(os.path.join(self.download_folder, padrao))
                for arquivo in arquivos:
                    os.remove(arquivo)
                    self.logger.debug(f"Arquivo removido: {arquivo}")

            self.logger.info(f"Pasta de downloads limpa com sucesso")
        except Exception as e:
            self.logger.error(f"Erro ao limpar downloads: {str(e)}")
            raise

    def get_chrome_version(self) -> str:
        """
        Obtém a versão atual do Google Chrome instalado no sistema.

        Returns:
            str: A versão do Chrome (ex: "91.0.4472.124")

        Raises:
            Exception: Se não for possível detectar a versão do Chrome
        """
        self.logger.info("Detectando versão do Chrome instalado")
        try:
            system = platform.system()
            chrome_version = ""

            if system == "Windows":
                # Procura nos locais comuns de instalação do Chrome no Windows
                locations = [
                    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                    os.path.expanduser(r'~\AppData\Local\Google\Chrome\Application\chrome.exe')
                ]

                for location in locations:
                    if os.path.exists(location):
                        # Usa wmic para obter a versão
                        result = subprocess.run(
                            ['wmic', 'datafile', 'where', f'name="{location.replace("\\", "\\\\")}"', 'get', 'Version',
                             '/value'],
                            capture_output=True, text=True
                        )
                        match = re.search(r'Version=(.+)', result.stdout)
                        if match:
                            chrome_version = match.group(1)
                            break

                # Se não encontrou com wmic, tenta com o próprio Chrome
                if not chrome_version:
                    for location in locations:
                        if os.path.exists(location):
                            result = subprocess.run([location, '--version'], capture_output=True, text=True)
                            match = re.search(r'Chrome\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
                            if match:
                                chrome_version = match.group(1)
                                break

            elif system == "Darwin":  # macOS
                try:
                    result = subprocess.run(
                        ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
                        capture_output=True, text=True
                    )
                    match = re.search(r'Chrome\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        chrome_version = match.group(1)
                except Exception:
                    pass

            elif system == "Linux":
                try:
                    result = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
                    match = re.search(r'Chrome\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
                    if match:
                        chrome_version = match.group(1)
                except Exception:
                    try:
                        result = subprocess.run(['google-chrome-stable', '--version'], capture_output=True, text=True)
                        match = re.search(r'Chrome\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
                        if match:
                            chrome_version = match.group(1)
                    except Exception:
                        pass

            if not chrome_version:
                raise Exception("Não foi possível detectar a versão do Chrome")

            self.logger.info(f"Versão do Chrome detectada: {chrome_version}")
            return chrome_version

        except Exception as e:
            self.logger.error(f"Erro ao detectar versão do Chrome: {str(e)}")
            raise

    def get_compatible_chromedriver_version(self, chrome_version: str) -> str:
        """
        Determina qual versão do ChromeDriver é compatível com a versão do Chrome.

        Args:
            chrome_version: A versão do Chrome (ex: "91.0.4472.124")

        Returns:
            str: A versão principal do ChromeDriver compatível (ex: "91.0.4472")
        """
        # Extrai a versão principal (ex: de "91.0.4472.124" para "91")
        major_version = chrome_version.split('.')[0]
        self.logger.info(f"Buscando versão do ChromeDriver compatível com Chrome {major_version}")

        try:
            # Consulta a API de versões do ChromeDriver para encontrar a versão mais compatível
            response = requests.get('https://chromedriver.storage.googleapis.com/LATEST_RELEASE_' + major_version)
            if response.status_code == 200:
                compatible_version = response.text.strip()
                self.logger.info(f"Versão compatível do ChromeDriver encontrada: {compatible_version}")
                return compatible_version
            else:
                self.logger.warning(f"Não foi possível encontrar versão específica. Tentando versão genérica.")
                # Tenta obter a última versão disponível
                response = requests.get('https://chromedriver.storage.googleapis.com/LATEST_RELEASE')
                if response.status_code == 200:
                    latest_version = response.text.strip()
                    self.logger.warning(f"Usando última versão disponível do ChromeDriver: {latest_version}")
                    return latest_version
                raise Exception(f"Falha ao obter versão compatível do ChromeDriver. Status: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Erro ao determinar versão compatível do ChromeDriver: {str(e)}")
            raise

    def download_chromedriver(self, version: str) -> str:
        """
        Baixa e instala uma versão específica do ChromeDriver.

        Args:
            version: A versão do ChromeDriver para baixar

        Returns:
            str: O caminho para o executável do ChromeDriver
        """
        # Usaremos o chromedriver_autoinstaller com a versão específica
        self.logger.info(f"Baixando ChromeDriver versão {version}")
        try:
            path = chromedriver_autoinstaller.install(version=version)
            self.logger.info(f"ChromeDriver instalado em: {path}")
            return path
        except Exception as e:
            self.logger.error(f"Erro ao baixar ChromeDriver {version}: {str(e)}")
            raise

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def install_chromedriver(self) -> str:
        """
        Instala ou atualiza o chromedriver de forma automática,
        garantindo compatibilidade com a versão do Chrome instalada.

        Faz até 5 tentativas em caso de falha, com intervalo de 2 segundos entre cada tentativa.

        Returns:
            str: O caminho para o executável do ChromeDriver
        """
        self.logger.info("Instalando/atualizando chromedriver compatível")
        try:
            # 1. Detectar versão do Chrome
            chrome_version = self.get_chrome_version()

            # 2. Obter versão compatível do ChromeDriver
            chromedriver_version = self.get_compatible_chromedriver_version(chrome_version)

            # 3. Baixar e instalar o ChromeDriver específico
            chromedriver_path = self.download_chromedriver(chromedriver_version)

            self.logger.info(f"ChromeDriver {chromedriver_version} instalado com sucesso para Chrome {chrome_version}")
            return chromedriver_path
        except Exception as e:
            self.logger.error(f"Erro ao instalar chromedriver compatível: {str(e)}")
            self.logger.warning("Tentando instalar última versão disponível do ChromeDriver")

            # Fallback para o método padrão
            try:
                path = chromedriver_autoinstaller.install()
                self.logger.info(f"ChromeDriver instalado usando método padrão: {path}")
                return path
            except Exception as fallback_error:
                self.logger.error(f"Erro no fallback de instalação: {str(fallback_error)}")
                raise

    def setup_driver(self, opcoes_extras: Dict[str, Any] = None) -> webdriver.Chrome:
        """
        Configura e inicia o Chrome WebDriver com as opções especificadas,
        garantindo compatibilidade entre o ChromeDriver e o Chrome.

        Args:
            opcoes_extras: Dicionário com opções adicionais para o Chrome.
                        Cada chave deve ser o nome do método a ser chamado,
                        e o valor os argumentos para esse método.

        Returns:
            webdriver.Chrome: Instância configurada do Chrome WebDriver.
        """
        self.logger.info("Configurando Chrome WebDriver")

        options = Options()

        # Configurações para impressão automática em PDF
        settings = {
            "recentDestinations": [{
                "id": "Save as PDF",
                "origin": "local",
                "account": ""
            }],
            "selectedDestinationId": "Save as PDF",
            "version": 2
        }

        prefs = {
            "download.default_directory": self.download_folder,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "credentials_enable_service": False,
            "password_manager_enabled": False,
            # Adiciona a configuração de impressão
            "printing.print_preview_sticky_settings.appState": json.dumps(settings),
            # Desabilitar webRTC para evitar vazamento de IP real
            "webrtc.ip_handling_policy": "disable_non_proxied_udp",
            # Evitar detecção do modo headless
            "profile.default_content_setting_values.notifications": 2
        }

        # Opções padrão
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument('--kiosk-printing')  # Ativa a impressão em quiosque
        options.add_argument('disable-infobars')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--allow-insecure-localhost')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument("window-size=1366,768")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument('--headless')
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")

        # User agent mais natural
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                             "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        # Adiciona opções extras, se fornecidas
        if opcoes_extras:
            for metodo, args in opcoes_extras.items():
                if isinstance(args, list):
                    # Se for uma lista, desempacota os argumentos
                    getattr(options, metodo)(*args)
                else:
                    # Se não for uma lista, passa como um único argumento
                    getattr(options, metodo)(args)

        # Instala o chromedriver compatível e configura o serviço
        try:
            chromedriver_path = self.install_chromedriver()
            service = Service(executable_path=chromedriver_path)

            self.logger.info("Chrome WebDriver iniciando com driver compatível")
            navegador = webdriver.Chrome(service=service, options=options)

            # Executar comandos JavaScript para ocultar a automação
            navegador.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            navegador.execute_script("window.navigator.chrome = { runtime: {} };")
            navegador.execute_script(
                "Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR', 'pt', 'en-US', 'en'] });")
            navegador.execute_script("Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });")

            navegador.maximize_window()
            self.logger.info("Chrome WebDriver iniciado com sucesso")
            return navegador
        except Exception as e:
            self.logger.error(f"Falha ao iniciar Chrome WebDriver: {str(e)}")

            # Tenta novamente com o método padrão como fallback final
            try:
                self.logger.warning("Tentando iniciar o driver com o método padrão como fallback")
                navegador = webdriver.Chrome(options=options)
                navegador.maximize_window()
                self.logger.info("Chrome WebDriver iniciado com método fallback")
                return navegador
            except Exception as fallback_error:
                self.logger.error(f"Falha total ao iniciar Chrome WebDriver: {str(fallback_error)}")
                raise

    @contextmanager
    def get_driver(self, opcoes_extras: Dict[str, Any] = None):
        """
        Context manager para criar e gerenciar o driver de forma segura.

        Exemplo de uso:
            with selenium_setup.get_driver() as driver:
                driver.get("https://www.exemplo.com")

        Args:
            opcoes_extras: Opções adicionais para o Chrome WebDriver.

        Yields:
            webdriver.Chrome: Instância configurada do Chrome WebDriver.
        """
        driver = None
        try:
            driver = self.setup_driver(opcoes_extras)
            self.logger.info("Driver criado e pronto para uso")
            yield driver
        finally:
            if driver:
                self.logger.info("Encerrando driver")
                driver.quit()