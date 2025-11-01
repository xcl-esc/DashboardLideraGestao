import os
import time
import logging
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'painelgestores.settings')

import django
django.setup()
from django.conf import settings
from Automacoes.db_processos import GerenciadorDB
from Automacoes.captura_processos import CapturaProcessos
from Automacoes.passivoteste import AutomacaoPassivo

load_dotenv(override=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def executar_automacoes():
    try:
        USUARIO = os.getenv("USER_EMAIL")
        SENHA = os.getenv("USER_PASSWORD")
        UNIDADE = os.getenv("UNIDADE")
        BASES_DADOS_DIR = settings.BASES_DADOS_DIR 

        logging.info(f"DEBUG: BASES_DADOS_DIR={BASES_DADOS_DIR}")
        logging.info(f"DEBUG: UNIDADE={UNIDADE}")
        
        if not UNIDADE:
            logging.error("ERRO CRÍTICO: Variável UNIDADE não encontrada. Verifique seu arquivo .env.")
            return
        
    
        logging.info("Iniciando automações...")

        db = GerenciadorDB(base_dir=BASES_DADOS_DIR, unidade=UNIDADE)
        automacao = AutomacaoPassivo(usuario=USUARIO, senha=SENHA, unidade=UNIDADE)

        if not automacao._inicializar_navegador():
            logging.error("Erro ao iniciar navegador.")
            return

        if not automacao._realizar_login():
            logging.error("Erro no login.")
            return

        automacao._fechar_tela_aviso()
        automacao._selecionar_unidade_mgi()

        captura = CapturaProcessos(automacao.driver, db)
        captura.capturar_caixa('técnicos')

        logging.info("Automações concluídas com sucesso!")

    except Exception as e:
        logging.exception(f"Erro durante execução das automações: {e}")

    finally:
        try:
            db.fechar()
            automacao.driver.quit()
        except Exception:
            pass

if __name__ == "__main__":
    while True:
        executar_automacoes()
        logging.info("Aguardando 8 horas para próxima execução...")
        time.sleep(8 * 60 * 60)
