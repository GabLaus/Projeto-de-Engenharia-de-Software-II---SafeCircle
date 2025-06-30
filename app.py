from flask import Flask, render_template, request, redirect, session, url_for, flash
import base64
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "seu_segredo"
DB_PATH = "safecircle.db"

##########################################
########### BANCO DE DADOS ###############
##########################################

def criar_banco():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Usuario(
            id_user INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL CHECK(LENGTH(nome) <= 50),
            email TEXT UNIQUE NOT NULL CHECK(LENGTH(email) <= 50),
            senha TEXT NOT NULL CHECK(LENGTH(senha) <= 255),
            dat_nac DATE NOT NULL,
            telefone TEXT UNIQUE NOT NULL CHECK(LENGTH(telefone) = 11),
            cpf TEXT UNIQUE NOT NULL CHECK(LENGTH(cpf) = 11),
            rg TEXT UNIQUE NOT NULL CHECK(LENGTH(rg) <= 14),
            ind_front BLOB,
            ind_back BLOB,
            status TEXT DEFAULT 'Em andamento' CHECK(status IN ('Em andamento', 'aprovado', 'rejeitado'))
        );        
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Ocorrencia(
            id_ocorrencia INTEGER PRIMARY KEY AUTOINCREMENT,
            data_inicio DATETIME NOT NULL,
            data_conclusao DATETIME,
            descricao TEXT CHECK(LENGTH(descricao) <= 80),
            estagio TEXT NOT NULL DEFAULT 'Em andamento' CHECK(LENGTH(estagio) <= 50),
            titulo TEXT,
            local TEXT,
            id_user INTEGER,
            FOREIGN KEY (id_user) REFERENCES Usuario(id_user)
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Admin (
            id_admin INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL CHECK(LENGTH(email) <= 50),
            senha TEXT NOT NULL CHECK(LENGTH(senha) <= 255)
        );        
        """)
        conn.commit()

def inserir_admin_manual():
    email = "admin@safecircle.com"
    senha = generate_password_hash("admin123")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO Admin (email, senha) VALUES (?, ?)", (email, senha))
            conn.commit()
            print("Admin inserido com sucesso!")
        except sqlite3.IntegrityError:
            print("Admin já existe.")

##########################################
############### LOGIN ####################
##########################################

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["emailUsuario"]
        senha = request.form["senhaUsuario"]

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id_admin, senha FROM Admin WHERE email = ?", (email,))
            admin = cursor.fetchone()
            if admin:
                id_admin, senha_hash = admin
                if check_password_hash(senha_hash, senha):
                    session["admin"] = id_admin
                    return redirect("/admin/cadastros")

            cursor.execute("SELECT nome, senha, status FROM Usuario WHERE email = ?", (email,))
            resultado = cursor.fetchone()

            if resultado:
                nome, senha_hash, status = resultado
                if status != "aprovado":
                    flash("Seu cadastro ainda não foi aprovado!", "erro")
                    return redirect("/login")

                if check_password_hash(senha_hash, senha):
                    session["usuario"] = nome
                    return redirect("/telaPrincipal")

            flash("Email ou senha inválidos!", "erro")
            return redirect("/login")

    return render_template("login.html")

##########################################
########### CADASTRO USUÁRIO #############
##########################################

@app.route("/cadastro", methods=["GET"])
def cadastro():
    return render_template("cadastro.html")

@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    nome = request.form["nome"]
    email = request.form["email"]
    senha = generate_password_hash(request.form["senha"])
    nascimento = request.form["nascimento"]
    telefone = request.form["telefone"]
    cpf = request.form["cpf"]
    rg = request.form["rg"]
    ind_front = request.files["ind_front"].read() if "ind_front" in request.files else None
    ind_back = request.files["ind_back"].read() if "ind_back" in request.files else None

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Usuario (
                    nome, email, senha, dat_nac, telefone, cpf, rg, ind_front, ind_back, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)               
            """, (nome, email, senha, nascimento, telefone, cpf, rg, ind_front, ind_back, "Em andamento"))          
            conn.commit()
        return redirect("/login")
    except sqlite3.IntegrityError as e:
        return f"Erro: {str(e)}"

##########################################
########### OCORRÊNCIAS ##################
##########################################

@app.route("/ocorrencia", methods=["GET", "POST"])
def ocorrencia():
    if "usuario" not in session:
        return redirect("/login")

    if request.method == "POST":
        descricao_completa = request.form["descricao"]
        titulo = request.form["ocorrencia"]
        local = request.form["localizacao"]
        estagio = "Em andamento"
        data_inicio = datetime.now()
        data_conclusao = datetime.now()

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id_user FROM Usuario WHERE nome = ?", (session["usuario"],))
                resultado = cursor.fetchone()
                if not resultado:
                    return "Usuário não encontrado."
                id_user = resultado[0]

                cursor.execute("""
                    INSERT INTO Ocorrencia (data_inicio, data_conclusao, descricao, estagio, titulo, local, id_user)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (data_inicio, data_conclusao, descricao_completa, estagio, titulo, local, id_user))
                conn.commit()

            return redirect("/telaPrincipal")
        except Exception as e:
            return f"Erro ao registrar ocorrência: {str(e)}"

    return render_template("ocorrencia.html")

@app.route("/historicoDeOcorrencias")
def historico_de_ocorrencias():
    if "usuario" not in session:
        return redirect("/login")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id_user FROM Usuario WHERE nome = ?", (session["usuario"],))
        resultado = cursor.fetchone()
        if not resultado:
            return "Usuário não encontrado."
        id_user = resultado[0]

        cursor.execute("""
            SELECT data_inicio, data_conclusao, titulo, descricao, estagio, local
            FROM Ocorrencia
            WHERE id_user = ?
            ORDER BY data_inicio DESC
        """, (id_user,))
        ocorrencias = cursor.fetchall()

    return render_template("historicoDeOcorrencias.html", ocorrencias=ocorrencias)


@app.route("/avaliacoes", methods=["GET", "POST"])
def avaliacoes():
    if "usuario" not in session:
        return redirect("/login")

    if request.method == "POST":
        nome = session["usuario"]
        nota = int(request.form["nota"])
        comentario = request.form["comentario"]
        data = datetime.now()

        if nota < 1 or nota > 5 or not comentario.strip():
            flash("Nota inválida ou comentário em branco.", "erro")
            return redirect("/avaliacoes")

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Avaliacao (nome_usuario, nota, comentario, data_avaliacao)
                    VALUES (?, ?, ?, ?)
                """, (nome, nota, comentario.strip(), data))
                conn.commit()
                flash("Avaliação enviada com sucesso!", "sucesso")
        except Exception as e:
            return f"Erro ao salvar avaliação: {str(e)}"

        return redirect("/avaliacoes")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT nome_usuario, nota, comentario, data_avaliacao
            FROM Avaliacao ORDER BY data_avaliacao DESC
        """)
        avaliacoes = cursor.fetchall()

    return render_template("avaliacoes.html", avaliacoes=avaliacoes)
##########################################
########## PERFIL DO USUÁRIO #############
##########################################

@app.route("/usuario", methods=["GET", "POST"])
def usuario():
    if "usuario" not in session:
        return redirect("/login")

    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = generate_password_hash(request.form["senha"])
        nascimento = request.form["nascimento"]
        telefone = request.form["telefone"]
        cpf = request.form["cpf"]
        rg = request.form["rg"]
        ind_front = request.files["ind_front"].read() if "ind_front" in request.files else None
        ind_back = request.files["ind_back"].read() if "ind_back" in request.files else None

        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE Usuario SET nome=?, email=?, senha=?, dat_nac=?, telefone=?, cpf=?, rg=?, ind_front=?, ind_back=?
                    WHERE nome=?
                """, (nome, email, senha, nascimento, telefone, cpf, rg, ind_front, ind_back, session["usuario"]))
                conn.commit()
                session["usuario"] = nome
        except sqlite3.IntegrityError as e:
            return f"Erro ao atualizar: {str(e)}"

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nome, email, senha, dat_nac, telefone FROM Usuario WHERE nome = ?", (session["usuario"],))
        dados = cursor.fetchone()

    if dados:
        return render_template("usuario.html", usuario=dados)
    return "Usuário não encontrado."

@app.route("/editar", methods=["GET", "POST"])
def editar():
    if "usuario" not in session:
        return redirect("/login")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        if request.method == "POST":
            nome = request.form["nome"]
            email = request.form["email"]
            telefone = request.form["telefone"]
            nascimento = request.form["nascimento"]

            cursor.execute("""
                UPDATE Usuario SET nome=?, email=?, telefone=?, dat_nac=?
                WHERE nome=?
            """, (nome, email, telefone, nascimento, session["usuario"]))
            conn.commit()
            session["usuario"] = nome
            return redirect("/usuario")

        cursor.execute("SELECT nome, email, senha, dat_nac, telefone FROM Usuario WHERE nome = ?", (session["usuario"],))
        usuario = cursor.fetchone()
        if usuario:
            return render_template("editar_perfil.html", usuario=usuario)
        return "Usuário não encontrado."

@app.route("/alterar_senha", methods=["GET", "POST"])
def alterar_senha():
    if "usuario" not in session:
        return redirect("/login")

    if request.method == "POST":
        senha_atual = request.form["senha_atual"]
        nova_senha = request.form["nova_senha"]
        confirmar_senha = request.form["confirmar_senha"]

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT senha FROM Usuario WHERE nome = ?", (session["usuario"],))
            resultado = cursor.fetchone()
            if not resultado:
                return "Usuário não encontrado."

            if not check_password_hash(resultado[0], senha_atual):
                return "Senha atual incorreta."
            if nova_senha != confirmar_senha:
                return "As novas senhas não coincidem."

            nova_senha_hash = generate_password_hash(nova_senha)
            cursor.execute("UPDATE Usuario SET senha = ? WHERE nome = ?", (nova_senha_hash, session["usuario"]))
            conn.commit()
            return redirect("/usuario")

    return render_template("alterar_senha.html")

##########################################
################ ADMIN ###################
##########################################

@app.route("/admin/cadastros")
def admin_cadastros():
    if "admin" not in session:
        return redirect("/login")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id_user, nome, email, telefone, cpf, rg, dat_nac, ind_front, ind_back FROM Usuario WHERE status = 'Em andamento'")
        resultados = cursor.fetchall()

        usuarios = []
        for row in resultados:
            usuarios.append({
                "id_user": row[0],
                "nome": row[1],
                "email": row[2],
                "telefone": row[3],
                "cpf": row[4],
                "rg": row[5],
                "dat_nac": row[6],
                "front": base64.b64encode(row[7]).decode('utf-8') if row[7] else '',
                "back": base64.b64encode(row[8]).decode('utf-8') if row[8] else '',
            })

    return render_template("admin_Cadastro.html", usuarios=usuarios)

@app.route("/admin/validar_cadastro", methods=["POST"])
def validar_cadastro():
    if "admin" not in session:
        return redirect("/login")

    id_user = request.form["id_user"]
    status = request.form["status"]
    observacoes = request.form.get("observacoes", "")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Usuario SET status = ? WHERE id_user = ?", (status, id_user))
        conn.commit()

    return redirect("/admin/cadastros")

@app.route("/admin/ocorrencias", methods=["GET"])
def admin_ocorrencias():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id_ocorrencia, titulo, local, descricao FROM Ocorrencia WHERE estagio = 'Em andamento'")
        dados = cursor.fetchall()

        ocorrencias = []
        for row in dados:
            ocorrencias.append({
                'id': row[0],
                'titulo': row[1],
                'local': row[2],
                'descricao': row[3]
            })

    return render_template("admin_Ocorrencia.html", ocorrencias=ocorrencias)

@app.route("/admin/autorizar_ocorrencia", methods=["POST"])
def autorizar_ocorrencia():
    id_ocorrencia = request.form["id_ocorrencia"]
    status = request.form["status"]
    observacoes = request.form.get("observacoes", "")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE Ocorrencia SET estagio = ? WHERE id_ocorrencia = ?", (status, id_ocorrencia))
        conn.commit()

    flash(f"Ocorrência {status} com sucesso!", "sucesso")
    return redirect("/admin/ocorrencias")

##########################################
############### OUTRAS ROTAS #############
##########################################

@app.route("/telaPrincipal")
def tela_principal():
    if "usuario" not in session:
        return redirect("/login")
    return render_template("telaPrincipal.html")

@app.route("/configuracoes")
def configuracoes():
    return render_template("configuracoes.html")

@app.route("/chamadas")
def chamadas():
    return render_template("chamadas.html")

@app.route("/avaliacoes")
def avaliacoes():
    return render_template("avaliacoes.html")

@app.route("/usuario_simples")
def usuario_simples():
    return render_template("usuario.html")

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.clear()
    return redirect("/login")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def index():
    return render_template("login.html")

if __name__ == "__main__":
    criar_banco()
    inserir_admin_manual()
    app.run(debug=True)
