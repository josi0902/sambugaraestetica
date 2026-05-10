import sqlite3
from datetime import datetime

DB_PATH = "clinica.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            telefone TEXT,
            email TEXT,
            data_nascimento TEXT,
            data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
            total_visitas INTEGER DEFAULT 0,
            desconto_atual REAL DEFAULT 0.0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS procedimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            preco REAL NOT NULL,
            duracao_min INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            procedimento_id INTEGER NOT NULL,
            data_hora TEXT NOT NULL,
            status TEXT DEFAULT 'agendado',
            preco_original REAL,
            desconto_aplicado REAL DEFAULT 0.0,
            preco_final REAL,
            observacoes TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (procedimento_id) REFERENCES procedimentos(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS anamnese (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL UNIQUE,
            alergias TEXT,
            medicamentos TEXT,
            doencas TEXT,
            gestante INTEGER DEFAULT 0,
            fumante INTEGER DEFAULT 0,
            problemas_pele TEXT,
            cirurgias TEXT,
            observacoes TEXT,
            data_atualizacao TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS fotos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            agendamento_id INTEGER,
            tipo TEXT DEFAULT 'evolucao',
            descricao TEXT,
            filename TEXT NOT NULL,
            data_upload TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos(id)
        )
    """)

    # Procedimentos de exemplo
    c.execute("SELECT COUNT(*) FROM procedimentos")
    if c.fetchone()[0] == 0:
        procedimentos_exemplo = [
            ("Limpeza de Pele", "Limpeza profunda com extração", 120.00, 60),
            ("Peeling Facial", "Renovação celular com peeling químico", 180.00, 45),
            ("Hidratação Facial", "Hidratação profunda com ativos", 150.00, 60),
            ("Botox", "Injeção de relaxamento muscular", 950.00, 90),
            ("Drenagem Linfática", "Drenagem corporal completa", 220.00, 90),
            ("Preenchimento Labial", "Modelagem e contorno", 650.00, 30),
            ("Micropigmentação", "Procedimento semi-permanente", 450.00, 120),
            ("Radiofrequência", "Tratamento anti-envelhecimento", 280.00, 60),
        ]
        c.executemany(
            "INSERT INTO procedimentos (nome, descricao, preco, duracao_min) VALUES (?,?,?,?)",
            procedimentos_exemplo
        )

    conn.commit()
    conn.close()

def calcular_desconto(total_visitas):
    if total_visitas >= 20:
        return 15.0
    elif total_visitas >= 10:
        return 10.0
    elif total_visitas >= 5:
        return 5.0
    return 0.0

def atualizar_visitas_cliente(cliente_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM agendamentos 
        WHERE cliente_id = ? AND status = 'concluido'
    """, (cliente_id,))
    total = c.fetchone()[0]
    desconto = calcular_desconto(total)
    c.execute("""
        UPDATE clientes SET total_visitas = ?, desconto_atual = ? WHERE id = ?
    """, (total, desconto, cliente_id))
    conn.commit()
    conn.close()
