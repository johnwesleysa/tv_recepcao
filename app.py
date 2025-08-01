from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, session

import os, json
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
from functools import wraps
import ast
load_dotenv()

 # Carrega a config no início
app = Flask(__name__)
app.secret_key = 'senha_super_secreta'

# ⚠️ Use variáveis de ambiente no Render ou em um .env local
cloudinary.config(
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key = os.environ.get("CLOUDINARY_API_KEY"),
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
)

ORDEM_FILE = 'ordem.json'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
CONFIG_FILE = 'config.json'
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"tempo": 7000}

def salvar_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def salvar_ordem(lista):
    with open(ORDEM_FILE, 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)

def carregar_ordem():
    if os.path.exists(ORDEM_FILE):
        try:
            with open(ORDEM_FILE, 'r', encoding='utf-8') as f:
                data = f.read().strip()
                lista = json.loads(data) if data else []

                # Corrige entradas que são strings de dicionários
                if lista and isinstance(lista[0], str):
                    lista = [ast.literal_eval(item) for item in lista]

                return lista
        except Exception as e:
            print(f"[AVISO] Erro ao carregar ordem.json: {e}")
            return []
    return []

config = carregar_config() 
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logado'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    imagens = carregar_ordem()
    config = carregar_config()
    return render_template('index.html', imagens=imagens, tempo=config.get("tempo", 7000))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha == ADMIN_PASSWORD:
            session.permanent = False  # <- sessão expira ao fechar a aba
            session['logado'] = True
            return redirect(url_for('dashboard'))
        else:
            flash("Senha incorreta", "error")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logado', None)
    return redirect(url_for('login'))

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if not session.get('logado'):
        return redirect(url_for('login'))
    
    imagens = carregar_ordem()
    tempo = config.get("tempo", 7000)

    if request.method == "POST":
        # Verifica se arquivos foram enviados
        if 'arquivos' in request.files:
            arquivos = request.files.getlist('arquivos')

            for arquivo in arquivos:
                if arquivo and arquivo.filename != '':
                    nome_seguro = secure_filename(arquivo.filename)
                    
                    # Aqui: Envie para Cloudinary ou salve localmente
                    resultado = cloudinary.uploader.upload(arquivo)
                    imagens.append({
                        "url": resultado["secure_url"],
                        "id": resultado["public_id"]
                    })

            salvar_ordem(imagens)
            flash("Imagens enviadas com sucesso!")

        # Atualiza tempo de transição se fornecido
        if 'tempo' in request.form:
            novo_tempo = request.form.get("tempo", type=int)
            config["tempo"] = novo_tempo
            salvar_config()
            flash("Tempo atualizado com sucesso!")

        return redirect(url_for("dashboard"))

    return render_template("dashboard.html", imagens=imagens, tempo=tempo)

@app.route('/deletar/<filename>', methods=['POST'])
def deletar(filename):
    if not session.get('logado'):
        return redirect(url_for('login'))

    ordem = carregar_ordem()
    imagem = next((img for img in ordem if img['id'] == filename), None)

    if imagem:
        try:
            cloudinary.uploader.destroy(imagem['id'])
            ordem = [img for img in ordem if img['id'] != imagem['id']]
            salvar_ordem(ordem)
            flash(f"Imagem {imagem['id']} removida com sucesso!")
        except Exception as e:
            flash(f"Erro ao deletar: {str(e)}")
    else:
        flash("Imagem não encontrada.")

    return redirect(url_for('dashboard'))

@app.route('/deletar-multiplas', methods=['POST'])
@login_required
def deletar_multiplas():
    ids_selecionadas = request.form.getlist('selecionadas')
    ordem = carregar_ordem()
    novas_imagens = []

    for img in ordem:
        if img['id'] in ids_selecionadas:
            try:
                cloudinary.uploader.destroy(img['id'])
            except Exception as e:
                print(f"Erro ao deletar {img['id']}: {e}")
        else:
            novas_imagens.append(img)

    salvar_ordem(novas_imagens)
    flash(f"{len(ids_selecionadas)} imagem(ns) deletada(s) com sucesso.")
    return redirect(url_for('dashboard'))

@app.route('/atualizar-ordem', methods=['POST'])
def atualizar_ordem():
    if not session.get('logado'):
        return redirect(url_for('login'))

    nova_ordem = request.json.get('ordem', [])
    salvar_ordem(nova_ordem)
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
