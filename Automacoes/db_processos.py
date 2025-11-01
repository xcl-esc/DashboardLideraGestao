import sqlite3
import os
from datetime import datetime

class GerenciadorDB:
    def __init__(self, base_dir, unidade):
        self.unidade = unidade
        
        # monta o caminho da pasta e do arquivo .db
        pasta = os.path.join(base_dir, unidade)
        os.makedirs(pasta, exist_ok=True)  # cria a pasta se não existir
        
        self.db_path = os.path.join(pasta, f"{unidade}.db")  
        
        # conecta ao banco
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # Agora sim cria a tabela
        self._criar_tabela()

    def _criar_tabela(self):
        """Cria a tabela se não existir ainda"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    processo_numero TEXT UNIQUE,
                    email TEXT,
                    data TEXT,
                    hora TEXT,
                    caixa TEXT,
                    tecnico TEXT,
                    concluido INTEGER DEFAULT 0,
                    data_conclusao TEXT
                )
            """)

            try:
                cursor.execute("ALTER TABLE processos ADD COLUMN data_conclusao TEXT;")
                print("Coluna 'data_conclusao' adicionada com sucesso.")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    pass 
                else:
                    raise e
            conn.commit()

    def inserir_ou_atualizar(self, processos):
        """
        Insere ou atualiza processos na tabela.
        processos deve ser uma lista de dicionários:
        {
            "processo_numero": str,
            "email": str,
            "data": str,
            "hora": str,
            "caixa": str,
            "tecnico": str
        }
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for proc in processos:
                cursor.execute("""
                    INSERT INTO processos (processo_numero, email, data, hora, caixa, tecnico)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(processo_numero) DO UPDATE SET
                        email=excluded.email,
                        data=excluded.data,
                        hora=excluded.hora,
                        caixa=excluded.caixa,
                        tecnico=excluded.tecnico
                """, (
                    proc["processo_numero"],
                    proc.get("email"),
                    proc.get("data"),
                    proc.get("hora"),
                    proc.get("caixa"),
                    proc.get("tecnico")
                ))
            conn.commit()

    def marcar_concluidos(self, processos_atuais):
        """
        Marca como concluídos os processos que estão no banco
        mas não apareceram na coleta atual.
        processos_atuais deve ser uma lista de números de processo (strings).
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Pega todos os processos ainda não concluídos
            cursor.execute("SELECT processo_numero FROM processos WHERE data_conclusao is NULL")
            processos_no_banco = {row[0] for row in cursor.fetchall()}

            # Processos que sumiram
            processos_para_concluir = processos_no_banco - set(processos_atuais)

            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for proc in processos_para_concluir:
                cursor.execute("""
                    UPDATE processos
                    SET concluido = 1,
                    data_conclusao = ?
                    WHERE processo_numero = ?
                """, (agora, proc,))

            conn.commit()
            print(f"Número de processos marcados como concluídos: {len(processos_para_concluir)}")

    def fechar(self):
        if self.conn:
            self.conn.commit()
            self.conn.close()