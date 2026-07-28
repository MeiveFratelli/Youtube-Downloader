import customtkinter
import threading
import os
import sys
import time
import queue
from tkinter import filedialog, Canvas

try:
    import yt_dlp
except ImportError:
    raise ImportError("Instale com: pip install yt-dlp")

# CONFIG
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")

COR_FUNDO = "#242424"
COR_CARD = "#2f0733"
COR_ACCENT = "#5b8cff"
COR_ACCENT_HOVER = "#4472e6"
COR_TEXTO_SUAVE = "#8a8fa3"
COR_SUCESSO = "#3ddc84"
COR_ERRO = "#ff5c5c"
COR_BADGE_NEUTRO = "#262b3d"
COR_BADGE_INFO = "#1d3a63"
COR_BADGE_SUCESSO = "#164a33"
COR_BADGE_ERRO = "#4a1f24"

# CAMINHOS
if getattr(sys, "frozen", False):
    PASTA_SCRIPT = os.path.dirname(sys.executable)
    PASTA_RECURSOS = getattr(sys, "_MEIPASS", PASTA_SCRIPT)
else:
    PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
    PASTA_RECURSOS = PASTA_SCRIPT

FFMPEG_LOCATION = None
for pasta_candidata in (PASTA_SCRIPT, PASTA_RECURSOS):
    caminho_candidato = os.path.join(pasta_candidata, "ffmpeg.exe")
    if os.path.exists(caminho_candidato):
        FFMPEG_LOCATION = caminho_candidato
        break

# JANELA
janela = customtkinter.CTk()
janela.title("YouTube Downloader")
janela.geometry("620x640")
janela.resizable(False, False)
janela.configure(fg_color=COR_FUNDO)

CAMINHO_ICONE = os.path.join(PASTA_RECURSOS, "icone.ico")
if os.path.exists(CAMINHO_ICONE):
    try:
        janela.iconbitmap(CAMINHO_ICONE)
    except Exception:
        pass

# ESTADO
pasta_destino = os.path.join(os.path.expanduser("~"), "Downloads")
fila_eventos = queue.Queue()
_ultimo_update = {"tempo": 0.0}
_ultimo_arquivo = {"caminho": None}
INTERVALO_MINIMO = 0.15

# FILA
def enfileirar(tipo, *dados):
    fila_eventos.put((tipo, *dados))


def set_status(texto, cor=None, fundo=None):
    enfileirar("status", texto, cor, fundo)


def set_progresso(fracao):
    enfileirar("progresso", fracao)


def set_botao(estado, texto):
    enfileirar("botao", estado, texto)


def processar_fila_eventos():
    try:
        while True:
            evento = fila_eventos.get_nowait()
            tipo = evento[0]

            if tipo == "status":
                _, texto, cor, fundo = evento
                status.configure(
                    text=texto,
                    text_color=cor or "white",
                    fg_color=fundo or COR_BADGE_NEUTRO
                )
            elif tipo == "progresso":
                _, fracao = evento
                barra_progresso.set(fracao)
            elif tipo == "botao":
                _, estado, texto = evento
                botao_download.configure(state=estado, text=texto)
            elif tipo == "popup":
                _, titulo_popup, mensagem, sucesso, cor = evento
                _criar_popup(titulo_popup, mensagem, sucesso, cor)
    except queue.Empty:
        pass
    finally:
        janela.after(100, processar_fila_eventos)

# DOWNLOAD
def hook_progresso(d):
    if d["status"] == "downloading":
        agora = time.time()
        if agora - _ultimo_update["tempo"] < INTERVALO_MINIMO:
            return
        _ultimo_update["tempo"] = agora

        baixado = d.get("downloaded_bytes", 0)
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        percent_str = d.get("_percent_str", "0%").strip()
        if total:
            set_progresso(baixado / total)
        set_status(f"Baixando...  {percent_str}", "white", COR_BADGE_INFO)
    elif d["status"] == "finished":
        _ultimo_arquivo["caminho"] = d.get("filename")
        set_progresso(1.0)
        set_status("Convertendo / finalizando...", "white", COR_BADGE_INFO)


def montar_opcoes(link):
    formato_escolhido = seletor_formato.get()
    qualidade_escolhida = seletor_qualidade.get()
    altura = {"480p": "480", "720p": "720", "1080p": "1080"}[qualidade_escolhida]

    ydl_opts = {
        "outtmpl": os.path.join(pasta_destino, "%(title)s.%(ext)s"),
        "progress_hooks": [hook_progresso],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if FFMPEG_LOCATION:
        ydl_opts["ffmpeg_location"] = FFMPEG_LOCATION

    if formato_escolhido == "MP3":
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })
    else:
        ydl_opts.update({
            "format": f"bestvideo[height<={altura}][ext=mp4]+bestaudio[ext=m4a]/best[height<={altura}]",
            "merge_output_format": "mp4",
        })

    return ydl_opts

# ERROS
def interpretar_erro(mensagem_original):
    msg = mensagem_original.lower()

    if "sign in to confirm your age" in msg or "age" in msg and "restrict" in msg:
        return (
            "Restrição de idade",
            "Esse vídeo tem restrição de idade e o YouTube exige login para "
            "confirmar que você tem idade suficiente.\n\n"
            "Não é possível baixar vídeos com essa restrição sem estar logado "
            "na conta do YouTube, o que este app não faz."
        )
    if "private video" in msg:
        return (
            "Vídeo privado",
            "Esse vídeo é privado e só pode ser acessado por quem tem "
            "permissão direta do dono do canal."
        )
    if "video unavailable" in msg or "this video is unavailable" in msg:
        return (
            "Vídeo indisponível",
            "O YouTube informou que esse vídeo não está mais disponível.\n"
            "Ele pode ter sido removido, ter o link incorreto ou estar bloqueado "
            "na sua região."
        )
    if "sign in to confirm you're not a bot" in msg or "not a bot" in msg:
        return (
            "Bloqueio de segurança do YouTube",
            "O YouTube pediu confirmação de que não é um robô fazendo a "
            "requisição. Isso costuma acontecer quando muitos downloads são "
            "feitos em pouco tempo pelo mesmo IP.\n\n"
            "Tente novamente em alguns minutos."
        )
    if "unable to download webpage" in msg or "urlopen error" in msg or "network" in msg:
        return (
            "Problema de conexão",
            "Não foi possível conectar ao YouTube.\n"
            "Verifique sua internet e tente novamente."
        )
    if "ffmpeg" in msg and ("not found" in msg or "no such file" in msg):
        return (
            "FFmpeg não encontrado",
            "Esse formato/qualidade precisa do ffmpeg para juntar ou converter "
            "os arquivos, mas ele não foi encontrado.\n\n"
            "Coloque o arquivo ffmpeg.exe na mesma pasta deste programa."
        )
    if "unsupported url" in msg:
        return (
            "Link não reconhecido",
            "Esse link não parece ser um link válido do YouTube.\n"
            "Confira se copiou o endereço correto."
        )

    return ("Erro no download", mensagem_original)

# POPUP
def _criar_popup(titulo, mensagem, sucesso, cor):
    popup = customtkinter.CTkToplevel(janela)
    popup.title(titulo)
    popup.geometry("440x270")
    popup.resizable(False, False)
    popup.configure(fg_color=COR_CARD)
    popup.transient(janela)

    canvas_icone = Canvas(
        popup, width=70, height=70, bg=COR_CARD, highlightthickness=0
    )
    canvas_icone.pack(pady=(22, 8))
    canvas_icone.create_oval(4, 4, 66, 66, fill=cor, outline="")
    if sucesso:
        canvas_icone.create_line(
            20, 36, 31, 47, 50, 23,
            fill="white", width=6, capstyle="round", joinstyle="round"
        )
    else:
        canvas_icone.create_line(23, 23, 47, 47, fill="white", width=6, capstyle="round")
        canvas_icone.create_line(47, 23, 23, 47, fill="white", width=6, capstyle="round")

    titulo_label = customtkinter.CTkLabel(
        popup, text=titulo, font=("Segoe UI", 16, "bold"),
        text_color="white"
    )
    titulo_label.pack(pady=(0, 10))

    texto_label = customtkinter.CTkLabel(
        popup, text=mensagem, font=("Segoe UI", 12),
        text_color=COR_TEXTO_SUAVE, wraplength=380, justify="left"
    )
    texto_label.pack(padx=20, pady=(0, 15))

    botao_ok = customtkinter.CTkButton(
        popup, text="Entendi", width=120, height=36,
        corner_radius=8, fg_color=COR_ACCENT, hover_color=COR_ACCENT_HOVER,
        command=popup.destroy
    )
    botao_ok.pack(pady=(0, 15))

    popup.update_idletasks()
    x = janela.winfo_x() + (janela.winfo_width() // 2) - (popup.winfo_width() // 2)
    y = janela.winfo_y() + (janela.winfo_height() // 2) - (popup.winfo_height() // 2)
    popup.geometry(f"+{x}+{y}")

    popup.grab_set()
    popup.lift()
    popup.focus_force()


def mostrar_popup_erro(titulo_erro, explicacao):
    enfileirar("popup", titulo_erro, explicacao, False, COR_ERRO)


def mostrar_popup_sucesso(caminho_arquivo):
    nome_arquivo = os.path.basename(caminho_arquivo) if caminho_arquivo else None
    mensagem = "O arquivo foi baixado e salvo com sucesso."
    if nome_arquivo:
        mensagem += f"\n\nArquivo: {nome_arquivo}"
    enfileirar("popup", "Download concluído!", mensagem, True, COR_SUCESSO)

# ACOES
def baixar_video(link):
    _ultimo_arquivo["caminho"] = None
    set_status("Iniciando download...", "white", COR_BADGE_INFO)

    try:
        ydl_opts = montar_opcoes(link)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
        set_progresso(1.0)
        set_status("Download concluído com sucesso!", COR_SUCESSO, COR_BADGE_SUCESSO)
        mostrar_popup_sucesso(_ultimo_arquivo["caminho"])
    except Exception as e:
        import traceback
        caminho_log = os.path.join(PASTA_SCRIPT, "erro.log")
        with open(caminho_log, "a", encoding="utf-8") as f:
            f.write(f"\n--- {time.ctime()} ---\n")
            f.write(traceback.format_exc())

        titulo_erro, explicacao = interpretar_erro(str(e))
        set_progresso(0)
        set_status(f"Erro: {titulo_erro}", COR_ERRO, COR_BADGE_ERRO)
        mostrar_popup_erro(titulo_erro, explicacao)
    finally:
        set_botao("normal", "Baixar")


def iniciar_download_thread():
    link = entrada_link.get().strip()

    if not link or link.startswith("Cole"):
        set_status("Cole um link válido!", "white", COR_BADGE_ERRO)
        return

    botao_download.configure(state="disabled", text="Baixando...")
    barra_progresso.set(0)

    thread = threading.Thread(target=baixar_video, args=(link,), daemon=True)
    thread.start()


def escolher_pasta():
    global pasta_destino
    caminho = filedialog.askdirectory()
    if caminho:
        pasta_destino = caminho
        label_pasta.configure(text=pasta_destino)


def alternar_qualidade(valor):
    if valor == "MP3":
        seletor_qualidade.configure(state="disabled")
    else:
        seletor_qualidade.configure(state="normal")

# HEADER
frame_header = customtkinter.CTkFrame(janela, fg_color="transparent")
frame_header.pack(pady=(30, 10), padx=30, fill="x")

titulo = customtkinter.CTkLabel(
    frame_header,
    text="YouTube Downloader",
    font=("Segoe UI", 30, "bold"),
    text_color="white"
)
titulo.pack(anchor="w")

subtitulo = customtkinter.CTkLabel(
    frame_header,
    text="Baixe vídeos e áudios em segundos",
    font=("Segoe UI", 13),
    text_color=COR_TEXTO_SUAVE
)
subtitulo.pack(anchor="w", pady=(2, 0))

# CARD
card = customtkinter.CTkFrame(janela, fg_color=COR_CARD, corner_radius=16)
card.pack(padx=30, pady=10, fill="both", expand=True)

# LINK
label_link = customtkinter.CTkLabel(
    card, text="Link do vídeo", font=("Segoe UI", 13, "bold"),
    text_color="white", anchor="w"
)
label_link.pack(anchor="w", padx=25, pady=(25, 5))

entrada_link = customtkinter.CTkEntry(
    card,
    height=42,
    corner_radius=10,
    placeholder_text="https://www.youtube.com/watch?v=...",
    font=("Segoe UI", 13),
    fg_color="#262b3d",
    border_color="#343a52",
    border_width=1
)
entrada_link.pack(padx=25, fill="x")

# FORMATO
label_formato = customtkinter.CTkLabel(
    card, text="Formato", font=("Segoe UI", 13, "bold"),
    text_color="white", anchor="w"
)
label_formato.pack(anchor="w", padx=25, pady=(22, 5))

seletor_formato = customtkinter.CTkSegmentedButton(
    card,
    values=["MP4", "MP3"],
    font=("Segoe UI", 13),
    height=38,
    corner_radius=10,
    selected_color=COR_ACCENT,
    selected_hover_color=COR_ACCENT_HOVER,
    unselected_color="#262b3d",
    command=alternar_qualidade
)
seletor_formato.set("MP4")
seletor_formato.pack(padx=25, fill="x")

# QUALIDADE
label_qualidade = customtkinter.CTkLabel(
    card, text="Qualidade (somente vídeo)", font=("Segoe UI", 13, "bold"),
    text_color="white", anchor="w"
)
label_qualidade.pack(anchor="w", padx=25, pady=(22, 5))

seletor_qualidade = customtkinter.CTkSegmentedButton(
    card,
    values=["480p", "720p", "1080p"],
    font=("Segoe UI", 13),
    height=38,
    corner_radius=10,
    selected_color=COR_ACCENT,
    selected_hover_color=COR_ACCENT_HOVER,
    unselected_color="#262b3d",
)
seletor_qualidade.set("720p")
seletor_qualidade.pack(padx=25, fill="x")

# PASTA
label_pasta_titulo = customtkinter.CTkLabel(
    card, text="Salvar em", font=("Segoe UI", 13, "bold"),
    text_color="white", anchor="w"
)
label_pasta_titulo.pack(anchor="w", padx=25, pady=(22, 5))

frame_pasta = customtkinter.CTkFrame(card, fg_color="transparent")
frame_pasta.pack(padx=25, fill="x")

label_pasta = customtkinter.CTkLabel(
    frame_pasta,
    text=pasta_destino,
    font=("Segoe UI", 12),
    text_color=COR_TEXTO_SUAVE,
    anchor="w"
)
label_pasta.pack(side="left", fill="x", expand=True)

botao_pasta = customtkinter.CTkButton(
    frame_pasta,
    text="Alterar",
    width=90,
    height=32,
    corner_radius=8,
    font=("Segoe UI", 12),
    fg_color="#343a52",
    hover_color="#3d4460",
    command=escolher_pasta
)
botao_pasta.pack(side="right")

# BOTAO
botao_download = customtkinter.CTkButton(
    card,
    text="Baixar",
    height=46,
    corner_radius=10,
    font=("Segoe UI", 15, "bold"),
    fg_color=COR_ACCENT,
    hover_color=COR_ACCENT_HOVER,
    command=iniciar_download_thread
)
botao_download.pack(padx=25, pady=(28, 15), fill="x")

# PROGRESSO
barra_progresso = customtkinter.CTkProgressBar(
    card,
    height=14,
    corner_radius=8,
    progress_color=COR_ACCENT,
    fg_color="#262b3d"
)
barra_progresso.set(0)
barra_progresso.pack(padx=25, fill="x")

# STATUS
status = customtkinter.CTkLabel(
    card,
    text="Aguardando...",
    font=("Segoe UI", 13, "bold"),
    text_color=COR_TEXTO_SUAVE,
    fg_color="#262b3d",
    corner_radius=10,
    height=42
)
status.pack(padx=25, pady=(12, 25), fill="x")

# LOOP
processar_fila_eventos()
janela.mainloop()