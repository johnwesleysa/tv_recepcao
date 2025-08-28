from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import os, json
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.secret_key = 'senha_super_secreta'

# Pasta de mídias
MEDIA_FOLDER = os.path.join(app.root_path, 'midias')
os.makedirs(MEDIA_FOLDER, exist_ok=True)
app.config['MEDIA_FOLDER'] = MEDIA_FOLDER

# Arquivos e configs
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'mp4', 'mov', 'avi', 'webm'}
CONFIG_FILE = 'config.json'
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")  # senha default se não tiver .env


def carregar_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"tempo": 7000, "ordem": []}


def salvar_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def carregar_ordem():
    config = carregar_config()
    ordem_salva = config.get("ordem", [])

    # Lista arquivos existentes
    arquivos = []
    for nome in os.listdir(MEDIA_FOLDER):
        caminho = os.path.join(MEDIA_FOLDER, nome)
        if os.path.isfile(caminho) and allowed_file(nome):
            arquivos.append({
                "url": url_for("midia", filename=nome),
                "id": nome,
                "ordem": ordem_salva.index(nome) if nome in ordem_salva else 9999,
                "resource_type": "video" if nome.lower().endswith(('.mp4', '.mov', '.avi', '.webm')) else "image"
            })

    # Ordena
    arquivos.sort(key=lambda x: x['ordem'])
    return arquivos


def salvar_ordem(lista):
    config = carregar_config()
    config["ordem"] = [item['id'] for item in lista]
    salvar_config(config)


# Rota para servir arquivos da pasta midias
@app.route('/midias/<path:filename>')
def midia(filename):
    return send_from_directory(MEDIA_FOLDER, filename)


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
    imagens = carregar_ordem()
    tempo = config.get("tempo", 7000)

    if request.method == "POST":
        # Upload de mídias
        if 'arquivos' in request.files:
            arquivos = request.files.getlist('arquivos')
            for arquivo in arquivos:
                if arquivo and allowed_file(arquivo.filename):
                    nome_seguro = secure_filename(arquivo.filename)
                    caminho = os.path.join(MEDIA_FOLDER, nome_seguro)
                    arquivo.save(caminho)
            flash("Mídias enviadas com sucesso!")

        # Atualização do tempo
        if 'tempo' in request.form:
            novo_tempo = request.form.get("tempo", type=int)
            config["tempo"] = novo_tempo
            salvar_config(config)
            flash("Tempo atualizado com sucesso!")

        return redirect(url_for("dashboard"))

    return render_template("dashboard.html", imagens=imagens, tempo=tempo)


@app.route('/deletar/<filename>', methods=['POST'])
@login_required
def deletar(filename):
    caminho = os.path.join(MEDIA_FOLDER, filename)
    if os.path.exists(caminho):
        os.remove(caminho)
        flash(f"Arquivo {filename} removido com sucesso!")
    else:
        flash(f"Arquivo {filename} não encontrado!")
    return redirect(url_for('dashboard'))


@app.route('/deletar-multiplas', methods=['POST'])
@login_required
def deletar_multiplas():
    ids_selecionadas = request.form.getlist('selecionadas')

    for nome in ids_selecionadas:
        caminho = os.path.join(MEDIA_FOLDER, nome)
        if os.path.exists(caminho):
            os.remove(caminho)

    flash(f"{len(ids_selecionadas)} arquivo(s) deletado(s) com sucesso.")
    return redirect(url_for('dashboard'))


@app.route('/atualizar-ordem', methods=['POST'])
@login_required
def atualizar_ordem():
    nova_ordem = request.json.get('ordem', [])
    salvar_ordem(nova_ordem)
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
