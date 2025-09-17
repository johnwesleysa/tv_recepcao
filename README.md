# tv_recepcao
# instalar o requiriments
# instalar o ffmpeg, caso seja ubuntu basta usar sudo apt install ffmpeg, caso seja windows seguir o tutorial
Passo a Passo para Instalar o FFmpeg no Windows 11:

    Baixe o FFmpeg:

        Vá para o site: https://www.gyan.dev/ffmpeg/builds/

        Procure pela seção "release builds" e baixe o arquivo que termina em ...-full_build.zip.

    Extraia e Mova os Arquivos:

        Descompacte o arquivo ZIP que você baixou.

        Você terá uma pasta com um nome como ffmpeg-6.1.1-full_build. Renomeie essa pasta para algo simples, como ffmpeg.

        Mova essa pasta ffmpeg para a raiz do seu disco C:. O caminho final deve ser C:\ffmpeg.

    Adicione o FFmpeg ao PATH do Windows (Passo Crucial):

        Clique no menu Iniciar e digite "variáveis de ambiente". Selecione a opção "Editar as variáveis de ambiente do sistema".

        Na janela que abrir, clique no botão "Variáveis de Ambiente...".

        Na seção de baixo ("Variáveis do sistema"), encontre e selecione a variável chamada Path e clique em "Editar...".

        Clique em "Novo" e cole o caminho para a pasta bin de dentro da sua pasta ffmpeg. O caminho será: C:\ffmpeg\bin

        Clique em "OK" em todas as janelas para salvar.

    Verifique a Instalação:

        Feche todos os terminais/prompt de comando que estiverem abertos.

        Abra um novo Prompt de Comando (CMD) ou PowerShell e digite:
        Bash

ffmpeg -version

Se aparecer a versão do FFmpeg, a instalação foi um sucesso! Se der "comando não encontrado", reinicie o computador e tente novamente.