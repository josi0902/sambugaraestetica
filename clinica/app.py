from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory
from database import get_conn, init_db, calcular_desconto, atualizar_visitas_cliente
from datetime import datetime
import os
import uuid

app = Flask(__name__)
app.secret_key = "clinica_estetica_2024"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

init_db()

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ─── DASHBOARD ────────────────────────────────────────────────
@app.route("/")
def index():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total FROM clientes")
    total_clientes = c.fetchone()["total"]
    c.execute("SELECT COUNT(*) as total FROM agendamentos WHERE status='agendado'")
    agendamentos_pendentes = c.fetchone()["total"]
    c.execute("SELECT COUNT(*) as total FROM agendamentos WHERE status='concluido'")
    atendimentos_feitos = c.fetchone()["total"]
    c.execute("SELECT SUM(preco_final) as receita FROM agendamentos WHERE status='concluido'")
    receita = c.fetchone()["receita"] or 0
    c.execute("""
        SELECT a.id, a.data_hora, a.status, a.preco_final,
               cl.nome as cliente_nome, p.nome as proc_nome
        FROM agendamentos a
        JOIN clientes cl ON a.cliente_id = cl.id
        JOIN procedimentos p ON a.procedimento_id = p.id
        ORDER BY a.data_hora DESC LIMIT 5
    """)
    ultimos = c.fetchall()
    conn.close()
    return render_template("index.html",
        total_clientes=total_clientes,
        agendamentos_pendentes=agendamentos_pendentes,
        atendimentos_feitos=atendimentos_feitos,
        receita=receita,
        ultimos=ultimos
    )

# ─── CLIENTES ─────────────────────────────────────────────────
@app.route("/clientes")
def clientes():
    q = request.args.get("q", "")
    conn = get_conn()
    c = conn.cursor()
    if q:
        c.execute("""
            SELECT * FROM clientes WHERE nome LIKE ? OR telefone LIKE ? OR email LIKE ?
            ORDER BY nome
        """, (f"%{q}%", f"%{q}%", f"%{q}%"))
    else:
        c.execute("SELECT * FROM clientes ORDER BY nome")
    lista = c.fetchall()
    conn.close()
    return render_template("clientes.html", clientes=lista, q=q)

@app.route("/clientes/novo", methods=["GET", "POST"])
def novo_cliente():
    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form.get("telefone", "")
        email = request.form.get("email", "")
        data_nascimento = request.form.get("data_nascimento", "")
        conn = get_conn()
        conn.execute("""
            INSERT INTO clientes (nome, telefone, email, data_nascimento)
            VALUES (?, ?, ?, ?)
        """, (nome, telefone, email, data_nascimento))
        conn.commit()
        conn.close()
        flash("Cliente cadastrado com sucesso!", "success")
        return redirect(url_for("clientes"))
    return render_template("form_cliente.html", cliente=None)

@app.route("/clientes/<int:id>/editar", methods=["GET", "POST"])
def editar_cliente(id):
    conn = get_conn()
    if request.method == "POST":
        nome = request.form["nome"]
        telefone = request.form.get("telefone", "")
        email = request.form.get("email", "")
        data_nascimento = request.form.get("data_nascimento", "")
        conn.execute("""
            UPDATE clientes SET nome=?, telefone=?, email=?, data_nascimento=? WHERE id=?
        """, (nome, telefone, email, data_nascimento, id))
        conn.commit()
        conn.close()
        flash("Cliente atualizado!", "success")
        return redirect(url_for("clientes"))
    cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("form_cliente.html", cliente=cliente)

@app.route("/clientes/<int:id>")
def perfil_cliente(id):
    conn = get_conn()
    cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()
    historico = conn.execute("""
        SELECT a.*, p.nome as proc_nome, p.preco as proc_preco
        FROM agendamentos a
        JOIN procedimentos p ON a.procedimento_id = p.id
        WHERE a.cliente_id = ?
        ORDER BY a.data_hora DESC
    """, (id,)).fetchall()
    anamnese = conn.execute("SELECT * FROM anamnese WHERE cliente_id=?", (id,)).fetchone()
    fotos = conn.execute("""
        SELECT f.*, a.data_hora as ag_data, p.nome as proc_nome
        FROM fotos f
        LEFT JOIN agendamentos a ON f.agendamento_id = a.id
        LEFT JOIN procedimentos p ON a.procedimento_id = p.id
        WHERE f.cliente_id = ?
        ORDER BY f.data_upload DESC
    """, (id,)).fetchall()
    conn.close()
    proximo_nivel = None
    if cliente:
        visitas = cliente["total_visitas"]
        if visitas < 5:
            proximo_nivel = {"visitas_faltam": 5 - visitas, "desconto": 5}
        elif visitas < 10:
            proximo_nivel = {"visitas_faltam": 10 - visitas, "desconto": 10}
        elif visitas < 20:
            proximo_nivel = {"visitas_faltam": 20 - visitas, "desconto": 15}
    return render_template("perfil_cliente.html",
        cliente=cliente, historico=historico,
        proximo_nivel=proximo_nivel, anamnese=anamnese, fotos=fotos)

@app.route("/clientes/<int:id>/excluir", methods=["POST"])
def excluir_cliente(id):
    conn = get_conn()
    conn.execute("DELETE FROM fotos WHERE cliente_id=?", (id,))
    conn.execute("DELETE FROM anamnese WHERE cliente_id=?", (id,))
    conn.execute("DELETE FROM agendamentos WHERE cliente_id=?", (id,))
    conn.execute("DELETE FROM clientes WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Cliente removido.", "info")
    return redirect(url_for("clientes"))

# ─── ANAMNESE ─────────────────────────────────────────────────
@app.route("/clientes/<int:id>/anamnese", methods=["GET", "POST"])
def anamnese_cliente(id):
    conn = get_conn()
    cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()
    if request.method == "POST":
        dados = {
            "alergias": request.form.get("alergias", ""),
            "medicamentos": request.form.get("medicamentos", ""),
            "doencas": request.form.get("doencas", ""),
            "gestante": 1 if request.form.get("gestante") else 0,
            "fumante": 1 if request.form.get("fumante") else 0,
            "problemas_pele": request.form.get("problemas_pele", ""),
            "cirurgias": request.form.get("cirurgias", ""),
            "observacoes": request.form.get("observacoes", ""),
            "data_atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        existente = conn.execute("SELECT id FROM anamnese WHERE cliente_id=?", (id,)).fetchone()
        if existente:
            conn.execute("""
                UPDATE anamnese SET alergias=?, medicamentos=?, doencas=?, gestante=?,
                fumante=?, problemas_pele=?, cirurgias=?, observacoes=?, data_atualizacao=?
                WHERE cliente_id=?
            """, (*dados.values(), id))
        else:
            conn.execute("""
                INSERT INTO anamnese (cliente_id, alergias, medicamentos, doencas, gestante,
                fumante, problemas_pele, cirurgias, observacoes, data_atualizacao)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (id, *dados.values()))
        conn.commit()
        conn.close()
        flash("Anamnese salva com sucesso!", "success")
        return redirect(url_for("perfil_cliente", id=id))
    anamnese = conn.execute("SELECT * FROM anamnese WHERE cliente_id=?", (id,)).fetchone()
    conn.close()
    return render_template("anamnese.html", cliente=cliente, anamnese=anamnese)

# ─── FOTOS ────────────────────────────────────────────────────
@app.route("/clientes/<int:id>/fotos/upload", methods=["POST"])
def upload_foto(id):
    file = request.files.get("foto")
    descricao = request.form.get("descricao", "")
    agendamento_id = request.form.get("agendamento_id") or None
    tipo = request.form.get("tipo", "evolucao")
    if not file or not allowed_file(file.filename):
        flash("Arquivo inválido. Use JPG, PNG ou WEBP.", "error")
        return redirect(url_for("perfil_cliente", id=id))
    ext = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    conn = get_conn()
    conn.execute("""
        INSERT INTO fotos (cliente_id, agendamento_id, tipo, descricao, filename)
        VALUES (?, ?, ?, ?, ?)
    """, (id, agendamento_id, tipo, descricao, filename))
    conn.commit()
    conn.close()
    flash("Foto adicionada!", "success")
    return redirect(url_for("perfil_cliente", id=id))

@app.route("/fotos/<int:foto_id>/excluir", methods=["POST"])
def excluir_foto(foto_id):
    conn = get_conn()
    foto = conn.execute("SELECT * FROM fotos WHERE id=?", (foto_id,)).fetchone()
    if foto:
        filepath = os.path.join(UPLOAD_FOLDER, foto["filename"])
        if os.path.exists(filepath):
            os.remove(filepath)
        conn.execute("DELETE FROM fotos WHERE id=?", (foto_id,))
        conn.commit()
        cliente_id = foto["cliente_id"]
    conn.close()
    flash("Foto removida.", "info")
    return redirect(url_for("perfil_cliente", id=cliente_id))

# ─── AGENDAMENTOS ─────────────────────────────────────────────
@app.route("/agendamentos")
def agendamentos():
    conn = get_conn()
    lista = conn.execute("""
        SELECT a.*, cl.nome as cliente_nome, cl.desconto_atual,
               p.nome as proc_nome, p.preco as proc_preco
        FROM agendamentos a
        JOIN clientes cl ON a.cliente_id = cl.id
        JOIN procedimentos p ON a.procedimento_id = p.id
        ORDER BY a.data_hora DESC
    """).fetchall()
    conn.close()
    return render_template("agendamentos.html", agendamentos=lista)

@app.route("/agendamentos/novo", methods=["GET", "POST"])
def novo_agendamento():
    conn = get_conn()
    if request.method == "POST":
        cliente_id = int(request.form["cliente_id"])
        procedimento_id = int(request.form["procedimento_id"])
        data_hora = request.form["data_hora"]
        observacoes = request.form.get("observacoes", "")
        cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
        proc = conn.execute("SELECT * FROM procedimentos WHERE id=?", (procedimento_id,)).fetchone()
        desconto = cliente["desconto_atual"]
        preco_original = proc["preco"]
        preco_final = preco_original * (1 - desconto / 100)
        conn.execute("""
            INSERT INTO agendamentos (cliente_id, procedimento_id, data_hora, observacoes,
                                      preco_original, desconto_aplicado, preco_final)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (cliente_id, procedimento_id, data_hora, observacoes,
              preco_original, desconto, preco_final))
        conn.commit()
        conn.close()
        flash("Agendamento criado com sucesso!", "success")
        return redirect(url_for("agendamentos"))
    clientes = conn.execute("SELECT id, nome, desconto_atual FROM clientes ORDER BY nome").fetchall()
    procedimentos = conn.execute("SELECT * FROM procedimentos ORDER BY nome").fetchall()
    conn.close()
    return render_template("form_agendamento.html", clientes=clientes, procedimentos=procedimentos)

@app.route("/agendamentos/<int:id>/concluir", methods=["GET", "POST"])
def concluir_agendamento(id):
    conn = get_conn()
    ag = conn.execute("SELECT * FROM agendamentos WHERE id=?", (id,)).fetchone()
    if request.method == "POST":
        conn.execute("UPDATE agendamentos SET status='concluido' WHERE id=?", (id,))
        conn.commit()
        # handle optional photo upload
        file = request.files.get("foto")
        if file and allowed_file(file.filename):
            ext = file.filename.rsplit(".", 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            descricao = request.form.get("descricao", "")
            conn2 = get_conn()
            conn2.execute("""
                INSERT INTO fotos (cliente_id, agendamento_id, tipo, descricao, filename)
                VALUES (?, ?, 'procedimento', ?, ?)
            """, (ag["cliente_id"], id, descricao, filename))
            conn2.commit()
            conn2.close()
        conn.close()
        atualizar_visitas_cliente(ag["cliente_id"])
        flash("Atendimento concluído! Fidelidade atualizada.", "success")
        return redirect(url_for("agendamentos"))
    cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (ag["cliente_id"],)).fetchone()
    proc = conn.execute("SELECT * FROM procedimentos WHERE id=?", (ag["procedimento_id"],)).fetchone()
    conn.close()
    return render_template("concluir_agendamento.html", ag=ag, cliente=cliente, proc=proc)

@app.route("/agendamentos/<int:id>/cancelar", methods=["POST"])
def cancelar_agendamento(id):
    conn = get_conn()
    conn.execute("UPDATE agendamentos SET status='cancelado' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Agendamento cancelado.", "info")
    return redirect(url_for("agendamentos"))

# ─── API AJAX ─────────────────────────────────────────────────
@app.route("/api/preco_preview")
def preco_preview():
    cliente_id = request.args.get("cliente_id", type=int)
    proc_id = request.args.get("proc_id", type=int)
    if not cliente_id or not proc_id:
        return jsonify({})
    conn = get_conn()
    cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (cliente_id,)).fetchone()
    proc = conn.execute("SELECT * FROM procedimentos WHERE id=?", (proc_id,)).fetchone()
    conn.close()
    if not cliente or not proc:
        return jsonify({})
    desconto = cliente["desconto_atual"]
    preco_final = proc["preco"] * (1 - desconto / 100)
    return jsonify({
        "preco_original": proc["preco"],
        "desconto": desconto,
        "preco_final": round(preco_final, 2),
        "cliente_visitas": cliente["total_visitas"]
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
