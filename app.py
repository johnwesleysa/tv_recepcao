from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os, json
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = 'senha_super_secreta'

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET")
)

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


def carregar_ordem():
    resources = cloudinary.api.resources(type='upload', prefix='', context=True, max_results=100)
    imagens = []
    for r in resources['resources']:
        ordem = int(r['context']['custom'].get('ordem', 9999)) if 'context' in r and 'custom' in r['context'] else 9999
        imagens.append({
            "url": r['secure_url'],
            "id": r['public_id'],
            "ordem": ordem
        })
    imagens.sort(key=lambda x: x['ordem'])
    return imagens


def salvar_ordem(lista):
    for i, img in enumerate(lista):
        cloudinary.uploader.add_context(f"ordem={i}", public_ids=[img['id']])


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
            session.permanent = False
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
        if 'arquivos' in request.files:
            arquivos = request.files.getlist('arquivos')

            for arquivo in arquivos:
                if arquivo and arquivo.filename != '':
                    nome_seguro = secure_filename(arquivo.filename)
                    resultado = cloudinary.uploader.upload(arquivo)
                    cloudinary.uploader.add_context("ordem=9999", public_ids=[resultado["public_id"]])

            flash("Imagens enviadas com sucesso!")

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
    try:
        cloudinary.uploader.destroy(filename)
        flash(f"Imagem {filename} removida com sucesso!")
    except Exception as e:
        flash(f"Erro ao deletar: {str(e)}")

    return redirect(url_for('dashboard'))


@app.route('/deletar-multiplas', methods=['POST'])
@login_required
def deletar_multiplas():
    ids_selecionadas = request.form.getlist('selecionadas')

    for img_id in ids_selecionadas:
        try:
            cloudinary.uploader.destroy(img_id)
        except Exception as e:
            print(f"Erro ao deletar {img_id}: {e}")

    flash(f"{len(ids_selecionadas)} imagem(ns) deletada(s) com sucesso.")
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
