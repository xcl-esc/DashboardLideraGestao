import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_file='integra.log', console=True, max_file_size=5 * 1024 * 1024, backup_count=3):
    """
    Configura o sistema de logging da aplicação.

    Args:
        log_file (str): Nome do arquivo de log
        console (bool): Se True, exibe logs no console também
        max_file_size (int): Tamanho máximo do arquivo de log em bytes (padrão: 5MB)
        backup_count (int): Número de arquivos de backup a manter (padrão: 3)
    """
    # Obter nível de log de variável de ambiente ou usar padrão
    log_level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Criar o logger raiz
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Remover handlers existentes para evitar duplicação
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Formato detalhado para os logs
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'
    formatter = logging.Formatter(log_format)

    # Configurar o arquivo de log com rotação
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_file_size, backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    logger.addHandler(file_handler)

    # Adicionar logs no console se solicitado
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)

    # Configurar loggers específicos para reduzir ruído
    noisy_loggers = [
        'selenium', 'urllib3', 'requests', 'connectionpool',
        'filelock', 'PIL', 'chardet', 'certifi'
    ]

    for logger_name in noisy_loggers:
        noisy_logger = logging.getLogger(logger_name)
        # Usar WARNING como nível mínimo para reduzir verbosidade
        noisy_logger.setLevel(logging.WARNING)

    logging.info(f"Sistema de logging configurado. Nível: {log_level_str}")

    return logger