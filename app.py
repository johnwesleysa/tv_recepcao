from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
import os
import json
from werkzeug.utils import secure_filename
from functools import wraps
import threading
import ffmpeg
import uuid

app = Flask(__name__)
app.secret_key = 'Eleva@2025'

# --- CONFIGURAÇÕES DE PASTA ---
MEDIA_FOLDER = os.path.join(app.root_path, 'midias')
THUMBNAIL_FOLDER = os.path.join(MEDIA_FOLDER, 'thumbnails') 
os.makedirs(MEDIA_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)
app.config['MEDIA_FOLDER'] = MEDIA_FOLDER
OUTPUT_FOLDER = os.path.join(app.root_path, 'static')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
FINAL_VIDEO_FILENAME = 'slideshow_final.mp4'
FINAL_VIDEO_PATH = os.path.join(OUTPUT_FOLDER, FINAL_VIDEO_FILENAME)

# --- CONFIGURAÇÕES DE ARQUIVOS E SENHA ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'mp4', 'mov', 'avi', 'webm'}
CONFIG_FILE = 'config.json'
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "1234")

# --- CONTROLE DE GERAÇÃO DE VÍDEO ---
# Variável global para armazenar o status da tarefa em segundo plano
VIDEO_GENERATION_STATUS = {'status': 'pronto', 'mensagem': 'Nenhuma tarefa em execução.'}


def gerar_thumbnail_video(video_filename):
    """Usa o FFmpeg para extrair o primeiro frame de um vídeo e salvá-lo como JPG."""
    video_path = os.path.join(MEDIA_FOLDER, video_filename)
    thumbnail_path = os.path.join(THUMBNAIL_FOLDER, f"{video_filename}.jpg")

    # Não gera se o thumbnail já existir
    if os.path.exists(thumbnail_path):
        return

    try:
        (
            ffmpeg
            .input(video_path, ss=1) # Pega o frame no segundo 1 (evita frames pretos)
            .output(thumbnail_path, vframes=1) # Extrai apenas 1 frame
            .run(overwrite_output=True, quiet=False)
        )
        print(f"Thumbnail gerado para {video_filename}")
    except ffmpeg.Error as e:
        print(f"Erro ao gerar thumbnail para {video_filename}: {e}")

def carregar_config():
    """Carrega a configuração do arquivo JSON."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"tempo": 7000, "ordem": []}

def salvar_config(config):
    """Salva a configuração no arquivo JSON."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def carregar_ordem():
    config = carregar_config()
    ordem_salva = config.get("ordem", [])
    arquivos, nomes_encontrados = [], set()
    
    def processar_arquivo(nome):
        resource_type = "video" if nome.lower().endswith(('.mp4', '.mov', '.avi', '.webm')) else "image"
        thumbnail_url = None
        if resource_type == 'image':
            thumbnail_url = url_for("midia", filename=nome)
        else:
            thumbnail_filename = f"{nome}.jpg"
            if os.path.exists(os.path.join(THUMBNAIL_FOLDER, thumbnail_filename)):
                thumbnail_url = url_for("midia", filename=f"thumbnails/{thumbnail_filename}")
        return {"url": url_for("midia", filename=nome), "id": nome, "resource_type": resource_type, "thumbnail_url": thumbnail_url}

    for nome in ordem_salva:
        caminho_completo = os.path.join(MEDIA_FOLDER, nome)
        if os.path.isfile(caminho_completo) and allowed_file(nome):
            arquivos.append(processar_arquivo(nome)); nomes_encontrados.add(nome)

    for nome in sorted(os.listdir(MEDIA_FOLDER)):
        caminho_completo = os.path.join(MEDIA_FOLDER, nome)
        # <<< CORREÇÃO 1 ESTÁ AQUI >>>
        # Garante que vamos ignorar subpastas como a 'thumbnails'
        if os.path.isdir(caminho_completo):
            continue

        if nome not in nomes_encontrados and allowed_file(nome):
            arquivos.append(processar_arquivo(nome))
    return arquivos

def salvar_ordem_no_config(lista_ids):
    """Salva a nova ordem dos IDs de mídia no arquivo de configuração."""
    config = carregar_config()
    config["ordem"] = lista_ids
    salvar_config(config)

# ==============================================================================
# FUNÇÃO PRINCIPAL DE GERAÇÃO DE VÍDEO
# ==============================================================================

def gerar_video_slideshow():
    with app.app_context():
        global VIDEO_GENERATION_STATUS
        try:
            VIDEO_GENERATION_STATUS = {'status': 'processando', 'mensagem': 'Iniciando geração...', 'progress': 0}
            config = carregar_config()
            tempo_imagem_s = config.get("tempo", 7000) / 1000.0
            
            ordem_salva = config.get("ordem", [])
            lista_midias_simples, nomes_encontrados = [], set()
            
            for nome in ordem_salva:
                if os.path.isfile(os.path.join(MEDIA_FOLDER, nome)):
                    lista_midias_simples.append({"id": nome, "resource_type": "video" if nome.lower().endswith(('.mp4', '.mov', '.avi', '.webm')) else "image"}); nomes_encontrados.add(nome)
            
            for nome in sorted(os.listdir(MEDIA_FOLDER)):
                caminho_completo = os.path.join(MEDIA_FOLDER, nome)
                if os.path.isdir(caminho_completo):
                    continue
                
                if nome not in nomes_encontrados and allowed_file(nome):
                    lista_midias_simples.append({"id": nome, "resource_type": "video" if nome.lower().endswith(('.mp4', '.mov', '.avi', '.webm')) else "image"})
            
            if not lista_midias_simples:
                VIDEO_GENERATION_STATUS = {'status': 'erro', 'mensagem': 'Nenhuma mídia para processar.', 'progress': 0}
                if os.path.exists(FINAL_VIDEO_PATH): os.remove(FINAL_VIDEO_PATH)
                return

            processed_clips, resolucao = [], "1920x1080"
            total_midias = len(lista_midias_simples)

            for i, midia in enumerate(lista_midias_simples):
                progress = int(((i + 1) / total_midias) * 95)
                VIDEO_GENERATION_STATUS['progress'] = progress
                VIDEO_GENERATION_STATUS['mensagem'] = f"Processando mídia {i+1} de {total_midias}: {midia['id']}"
                
                caminho_midia = os.path.join(MEDIA_FOLDER, midia['id'])
                clip = ffmpeg.input(caminho_midia, loop=1, t=tempo_imagem_s, framerate=25) if midia['resource_type'] == 'image' else ffmpeg.input(caminho_midia)
                clip = clip.filter('scale', resolucao.split('x')[0], resolucao.split('x')[1], force_original_aspect_ratio='decrease').filter('pad', resolucao.split('x')[0], resolucao.split('x')[1], '(ow-iw)/2', '(oh-ih)/2').filter('setsar', 1).filter('format', 'yuv420p')
                processed_clips.append(clip)
            
            VIDEO_GENERATION_STATUS['mensagem'] = f'Finalizando... Concatenando {len(processed_clips)} clipes.'
            VIDEO_GENERATION_STATUS['progress'] = 98

            final_clip = ffmpeg.concat(*processed_clips, v=1, a=0).output(
                FINAL_VIDEO_PATH,
                # <<< PARÂMETROS DE OTIMIZAÇÃO ADICIONADOS AQUI >>>
                vcodec='libx264',      # Codec de vídeo mais compatível (H.264)
                crf=24,                # Fator de compressão (23-28 é um bom balanço. Menor = melhor qualidade)
                preset='medium',       # Balanço entre velocidade de compressão e tamanho do arquivo
                pix_fmt='yuv420p',     # Formato de pixel para máxima compatibilidade
                movflags='+faststart'  # OTIMIZAÇÃO CRÍTICA para streaming na web
            )

            _, stderr = final_clip.run(overwrite_output=True, capture_stderr=True)
            
            VIDEO_GENERATION_STATUS = {'status': 'pronto', 'mensagem': 'Vídeo atualizado com sucesso!', 'progress': 100}

        except ffmpeg.Error as e:
            error_details = e.stderr.decode('utf-8') if e.stderr else 'Unknown FFmpeg error'
            VIDEO_GENERATION_STATUS = {'status': 'erro', 'mensagem': f'Erro no FFmpeg: {error_details}', 'progress': 0}
        except Exception as e:
            VIDEO_GENERATION_STATUS = {'status': 'erro', 'mensagem': f'Erro na geração: {e}', 'progress': 0}


def iniciar_geracao_video():
    """Inicia a função de gerar vídeo em uma thread para não travar a aplicação."""
    if VIDEO_GENERATION_STATUS['status'] == 'processando':
        return
    thread = threading.Thread(target=gerar_video_slideshow)
    thread.daemon = True
    thread.start()

# ==============================================================================
# ROTAS FLASK
# ==============================================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logado'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/midias/<path:filename>')
def midia(filename):
    return send_from_directory(MEDIA_FOLDER, filename)

@app.route('/')
def index():
    """Página principal que exibe o vídeo final para as TVs."""
    return render_template('slideshow_video.html', video_file=url_for('static', filename=FINAL_VIDEO_FILENAME))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form.get('senha')
        if senha == ADMIN_PASSWORD:
            session['logado'] = True
            # Gera o vídeo no primeiro login se ele não existir e houver mídias
            if not os.path.exists(FINAL_VIDEO_PATH) and len(os.listdir(MEDIA_FOLDER)) > 0:
                iniciar_geracao_video()
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
    config = carregar_config()
    # A lógica de POST agora só trata do formulário de tempo
    if request.method == "POST":
        if 'tempo' in request.form:
            novo_tempo = request.form.get("tempo", type=int)
            if config["tempo"] != novo_tempo:
                config["tempo"] = novo_tempo; salvar_config(config)
                flash("Tempo atualizado com sucesso!")
                # Dispara a geração de vídeo se o tempo mudar
                iniciar_geracao_video()
        return redirect(url_for("dashboard"))
    
    return render_template("dashboard.html", imagens=carregar_ordem(), tempo=config.get("tempo", 7000), status_video=VIDEO_GENERATION_STATUS)

# <<< ROTA NOVA PARA RECEBER ARQUIVOS INDIVIDUALMENTE >>>
@app.route('/upload-media', methods=['POST'])
@login_required
def upload_media():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['file']
        if arquivo and allowed_file(arquivo.filename):
            nome_seguro = secure_filename(arquivo.filename)
            arquivo.save(os.path.join(MEDIA_FOLDER, nome_seguro))
            if nome_seguro.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                gerar_thumbnail_video(nome_seguro)
            return jsonify({'status': 'success', 'filename': nome_seguro})
        else:
            return jsonify({'status': 'error', 'message': 'Tipo de arquivo não permitido'}), 400
    except Exception as e:
        # Se a geração do thumbnail falhar, reporta o erro
        return jsonify({'status': 'error', 'message': str(e)}), 500

# <<< ROTA NOVA PARA INICIAR A GERAÇÃO APÓS O UPLOAD >>>
@app.route('/start-generation', methods=['POST'])
@login_required
def start_generation():
    iniciar_geracao_video()
    return jsonify({'status': 'ok', 'message': 'Geração de vídeo iniciada.'})

@app.route('/deletar-multiplas', methods=['POST'])
@login_required
def deletar_multiplas():
    ids_selecionadas = request.form.getlist('selecionadas')
    ordem_atual = carregar_ordem()
    for nome in ids_selecionadas:
        caminho = os.path.join(MEDIA_FOLDER, nome)
        if os.path.exists(caminho):
            os.remove(caminho)
    nova_ordem_ids = [item['id'] for item in ordem_atual if item['id'] not in ids_selecionadas]
    salvar_ordem_no_config(nova_ordem_ids)
    flash(f"{len(ids_selecionadas)} arquivo(s) deletado(s) com sucesso.")
    iniciar_geracao_video()
    return redirect(url_for('dashboard'))

@app.route('/atualizar-ordem', methods=['POST'])
@login_required
def atualizar_ordem():
    nova_ordem = request.json.get('ordem', [])
    nova_ordem_ids = [item['id'] for item in nova_ordem]
    salvar_ordem_no_config(nova_ordem_ids)
    iniciar_geracao_video()
    return jsonify({'status': 'ok'})

@app.route('/regenerate-thumbnails', methods=['POST'])
@login_required
def regenerate_thumbnails():
    try:
        arquivos_na_pasta = os.listdir(MEDIA_FOLDER)
        videos_processados = 0
        for nome_arquivo in arquivos_na_pasta:
            if nome_arquivo.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                gerar_thumbnail_video(nome_arquivo)
                videos_processados += 1
        flash(f'Verificação concluída! Miniaturas para {videos_processados} vídeos foram criadas ou atualizadas.')
    except Exception as e:
        flash(f"Erro ao recriar miniaturas: {e}", "error")
    return redirect(url_for('dashboard'))

@app.route('/generation-status')
@login_required
def generation_status():
    """Rota para o frontend consultar o status da geração do vídeo."""
    return jsonify(VIDEO_GENERATION_STATUS)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    app.run(host='0.0.0.0', port=port)