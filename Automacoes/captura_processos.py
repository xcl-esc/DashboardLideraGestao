import logging
import time
import sqlite3
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .db_processos import GerenciadorDB
from .SEI_Geral import VisualizacaoDetalhada, BotaoProximaPagina, TempoAleatorio, NivelDetalheTecnicos

# Configura o logging para mostrar mensagens no terminal
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class CapturaProcessos:
    def __init__(self, driver, db:GerenciadorDB):
        self.driver = driver
        self.db = db

    def _extrair_processos_da_pagina(self):
        processos = []
        try:
            tabela = self.driver.find_element(By.ID, 'tblProcessosDetalhado')
            linhas = tabela.find_elements(By.XPATH, './tbody/tr')
            
            logging.info(f"Encontradas {len(linhas)} linhas na tabela com ID 'tblProcessosDetalhado'.")

            for i, linha in enumerate(linhas):
                links_na_linha = linha.find_elements(By.TAG_NAME, 'a')
                

                if len(links_na_linha) >= 2:
                    try:
                        tecnico_email = links_na_linha[-1].text.strip()
                        numero_processo = links_na_linha[-2].text.strip()
                        
                        if numero_processo and tecnico_email:
                            logging.info(f"Processo extraído: Número='{numero_processo}', Técnico='{tecnico_email}'")
                            processos.append({
                                "processo_numero": numero_processo,
                                "email": tecnico_email,
                                "tecnico": tecnico_email,
                                "caixa": self.db.unidade,
                                "data": datetime.now().strftime("%Y-%m-%d"),
                                "hora": datetime.now().strftime("%H:%M:%S")
                            })
                        else:
                            logging.warning(f"Dados vazios encontrados na linha {i+1}: Numero='{numero_processo}', Tecnico='{tecnico_email}'")
                    except Exception as e:
                        logging.error(f"Erro ao extrair dados da linha {i+1}: {e}. Pulando.")
                        continue
                else:
                    logging.warning(f"Linha {i+1} com menos de 2 links. Encontrados {len(links_na_linha)} links. Pulando.")
                    continue
        except NoSuchElementException:
            logging.warning("Tabela de processos com ID 'tblProcessosDetalhado' não encontrada.")
        
        logging.info(f"Total de processos para salvar nesta página: {len(processos)}")
        return processos

    def capturar_caixa(self, caixa_nome):
        logging.info(f"Iniciando captura da caixa: {caixa_nome}")
        logging.info(f"URL atual do navegador: {self.driver.current_url}")
        
        # 1. Chamar a visualização detalhada e padronizar o nível de detalhe
        vis_detalhada = VisualizacaoDetalhada(self.driver)
        vis_detalhada.visualizar_detalhado()
        time.sleep(TempoAleatorio().tempo_aleatorio())

        # CHAMA A CLASSE QUE VAI PADRONIZAR A TABELA
        # NivelDetalheTecnicos é o nome da sua classe que faz a padronização
        nivel_detalhe = NivelDetalheTecnicos(self.driver)
        nivel_detalhe.detalhar_nivel_tecnicos() # Chame o método que faz a padronização
        time.sleep(TempoAleatorio().tempo_aleatorio())

        
        # 3. Rolar a página para carregar todos os elementos
        logging.info("Rolando a página para garantir que todos os elementos estejam visíveis.")
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2) 
        
        todos_processos = []

        botao_prox = BotaoProximaPagina(self.driver)

        while True:
            # VOLTAR AO INÍCIO DA PÁGINA ANTES DA EXTRAÇÃO
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            processos = self._extrair_processos_da_pagina()
            todos_processos.extend(processos)
            
            self.db.inserir_ou_atualizar(processos)
            
            # 4. Voltar para o contexto da página principal
            # try:
            #     self.driver.switch_to.default_content()
            #     logging.info("Voltado para o contexto da página principal.")
            # except Exception as e:
            #     logging.error(f"Erro ao tentar voltar para a página principal: {e}")
            #     break

            # ===== LÓGICA DE DETECÇÃO E CLIQUE NO BOTÃO PRÓXIMA PÁGINA (SUPERIOR E INFERIOR) =====
            next_btn = None
            
            try:
                # Tenta encontrar o botão superior
                next_btn = self.driver.find_element(By.XPATH, '//*[@id="lnkInfraProximaPaginaSuperior"]/img')
                logging.info("Botão 'Próxima página' superior encontrado.")
            except NoSuchElementException:
                logging.info("Botão 'Próxima página' superior não encontrado. Tentando o botão inferior...")
                try:
                    # Se o superior não for encontrado, tenta o inferior
                    next_btn = self.driver.find_element(By.ID, 'lnkInfraProximaPaginaInferior')
                    logging.info("Botão 'Próxima página' inferior encontrado.")
                except NoSuchElementException:
                    logging.info("Nenhum botão 'Próxima página' encontrado. Fim da tabela.")
                    break # Sai do loop se nenhum botão for encontrado

            # Se um botão foi encontrado, clica nele
            if next_btn:
                try:
                    next_btn.click()
                    time.sleep(TempoAleatorio().tempo_aleatorio())

                    # 5. Alternar de volta para o iframe após o carregamento da nova página
                    # try:
                    #     self.driver.switch_to.frame("ifrVisualizacaoDetalhada")
                    #     logging.info("Voltado para o iframe 'ifrVisualizacaoDetalhada' após a navegação.")
                    # except Exception as e:
                    #     logging.error(f"Erro ao voltar para o iframe após clicar em 'Próxima Página': {e}")
                    #     break

                except NoSuchElementException:
                    logging.info("Botão 'Próxima página' não encontrado ao tentar clicar.")
                    break
            else:
                logging.info("Botão 'Próxima página' não está presente. Fim da tabela.")
                break
        numeros_atuais = [p["processo_numero"] for p in todos_processos]
        self.db.marcar_concluidos(numeros_atuais)

        logging.info(f"Captura finalizada para a caixa {caixa_nome}. Total extraído: {len(todos_processos)}")

    def fechar(self):
        self.db.fechar()



