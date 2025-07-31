from flask import Flask, render_template_string, send_from_directory
import os

app = Flask(__name__)
IMAGES_DIR = 'pictures'

@app.route('/')
def index():
    imagens = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    imagens.sort()
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
      <meta charset="UTF-8">
      <title>Slideshow Automático</title>
      <style>
        body { margin:0; background:black; display:flex; justify-content:center; align-items:center; height:100vh; }
        img { max-width:100%; max-height:100vh; object-fit:contain; }
      </style>
    </head>
    <body>
      <img id="slideshow" src="/pictures/{{ imagens[0] }}" alt="Slideshow">
      <script>
        const imagens = {{ imagens|tojson }};
        let index = 0;
        const tempo = 7000;
        function trocarImagem() {
          index = (index + 1) % imagens.length;
          document.getElementById('slideshow').src = "/pictures/" + imagens[index];
        }
        setInterval(trocarImagem, tempo);
      </script>
    </body>
    </html>
    """, imagens=imagens)

@app.route('/pictures/<path:filename>')
def imagens(filename):
    return send_from_directory(IMAGES_DIR, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
