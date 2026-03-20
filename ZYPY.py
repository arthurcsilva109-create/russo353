import webview
import threading
import sys
import os
import zipfile
import shutil
import time
import psutil
import requests
import subprocess
import ctypes

# ============================================================
# LÓGICA DO ATIVADOR (SEU SEGUNDO CÓDIGO)
# ============================================================
API_URL = 'https://gaamingsteam.squareweb.app/api/app/'
APP_ID = 'kastexstorms'

class Ativador:
    def __init__(self, id_do_jogo):
        self.id_jogo_atual = str(id_do_jogo)
        self.caminho_steam = self._detectar_caminho_steam()
        self.config = self._buscar_config_api()

    def _buscar_config_api(self):
        """Busca configuracoes da API do painel admin. Se app desativado, retorna None"""
        url = API_URL + APP_ID + '/' + self.id_jogo_atual
        try:
            response = requests.get(url, timeout=10)

            if response.status_code in (403, 404, 401):
                self._mostrar_erro_licenca()
                return None

            data = response.json()

            if not data.get('ativo', False):
                self._mostrar_erro_licenca()
                return None

            return {
                'url_dll': data.get('url_dll'),
                'nome_dll': data.get('nome_dll'),
                'comando_powershell': data.get('comando_powershell'),
                'url_zip': data.get('url_zip'),
                'url_games': data.get('url_games'),
                'caminho_lua': data.get('caminho_lua'),
                'caminho_manifest': data.get('caminho_manifest'),
            }

        except requests.exceptions.ConnectionError:
            self._mostrar_erro_conexao()
            return None
        except requests.exceptions.Timeout:
            self._mostrar_erro_conexao()
            return None
        except Exception as e:
            self._mostrar_erro_conexao()
            return None

    def _mostrar_erro_licenca(self):
        """Mostra mensagem de licenca expirada/desativada via MessageBox"""
        mensagem = (
            'Seu acesso foi desativado ou expirou.\n\n'
            'Entre em contato com o suporte para renovar.\n\n'
            'Discord: https://discord.gg/SFWQyKRN'
        )
        ctypes.windll.user32.MessageBoxW(0, mensagem, 'Licenca Invalida', 0)

    def _mostrar_erro_conexao(self):
        """Mostra mensagem de erro de conexao via MessageBox"""
        mensagem = (
            'Nao foi possivel conectar ao servidor.\n\n'
            'Verifique sua conexao com a internet.'
        )
        ctypes.windll.user32.MessageBoxW(0, mensagem, 'Erro de Conexao', 0)

    def _detectar_caminho_steam(self):
        possiveis_caminhos = [
            os.path.expandvars('%ProgramFiles(x86)%\\Steam\\steam.exe'),
            os.path.expandvars('%ProgramFiles%\\Steam\\steam.exe'),
            'C:\\Program Files (x86)\\Steam\\steam.exe',
            'C:\\Program Files\\Steam\\steam.exe',
            'C:\\Steam\\steam.exe',
            os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'Steam', 'steam.exe'),
            os.path.join(os.path.expanduser('~'), 'Desktop', 'steam.exe'),
            'D:\\Steam\\steam.exe',
            'E:\\Steam\\steam.exe',
            'F:\\Steam\\steam.exe',
        ]

        for caminho in possiveis_caminhos:
            if os.path.exists(caminho):
                return caminho

        for drive in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
            drive_path = drive + ':\\'
            if os.path.exists(drive_path):
                for root, dirs, files in os.walk(drive_path):
                    steam_path = os.path.join(root, 'steam.exe')
                    if os.path.exists(steam_path):
                        return steam_path

        return None

    def _encontrar_pasta_documentos(self):
        documentos_pt = os.path.join(os.path.expanduser('~'), 'Documentos')
        documentos_en = os.path.join(os.path.expanduser('~'), 'Documents')
        if os.path.exists(documentos_pt):
            return documentos_pt
        return documentos_en

    def _baixar_hid_dll(self):
        if not self.config:
            return False
        if not self.config.get('nome_dll'):
            return True

        steam_dir = os.path.dirname(self.caminho_steam)
        nome_dll = self.config.get('nome_dll')
        dll_destino = os.path.join(steam_dir, nome_dll)

        if os.path.exists(dll_destino):
            return True

        url_dll = self.config.get('url_dll')
        try:
            resp = requests.get(url_dll, stream=True)
            resp.raise_for_status()
            with open(dll_destino, 'wb') as f:
                for parte in resp.iter_content(8192):
                    f.write(parte)
            return True
        except Exception as e:
            return False

    def ativar_jogo(self):
        pasta_docs = self._encontrar_pasta_documentos()
        pasta_conteudo = os.path.join(pasta_docs, 'conteudo')

        zips = []
        if os.path.exists(pasta_conteudo) and os.path.isdir(pasta_conteudo):
            for f in os.listdir(pasta_conteudo):
                if f.lower().endswith('.zip'):
                    zips.append(f)

        reiniciar_steam_apos = False

        for zip_nome in zips:
            caminho_zip = os.path.join(pasta_conteudo, zip_nome)
            try:
                with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
                    for nome_arquivo in zip_ref.namelist():
                        nome_arquivo_final = nome_arquivo.strip('/').split('/')[-1]

                        if nome_arquivo_final.lower().endswith('.lua'):
                            destino = self.config.get('caminho_lua')
                        elif nome_arquivo_final.lower().endswith('.st') or nome_arquivo_final.lower().endswith('.manifest'):
                            destino = self.config.get('caminho_manifest')
                        else:
                            continue

                        if destino:
                            os.makedirs(destino, exist_ok=True)
                            arquivo_destino = os.path.join(destino, nome_arquivo_final)
                            with zip_ref.open(nome_arquivo) as source, open(arquivo_destino, 'wb') as target:
                                target.write(source.read())
                            reiniciar_steam_apos = True
            except Exception as e:
                pass

        if reiniciar_steam_apos:
            self._executar_comando_steam_update()

    def _steam_esta_aberta(self):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'].lower() == 'steam.exe':
                return True
        return False

    def reiniciar_steam(self):
        self.fechar_steam()
        time.sleep(3)
        self.abrir_steam()

    def fechar_steam(self):
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if proc.info['name'].lower() == 'steam.exe':
                    proc.kill()
            except Exception as e:
                pass
        time.sleep(1)

    def abrir_steam(self):
        if self.caminho_steam and os.path.exists(self.caminho_steam):
            subprocess.Popen(self.caminho_steam)

    def _executar_comando_steam_update(self):
        """Executa o comando PowerShell configurado na API"""
        if not self.config:
            return
        comando_powershell = self.config.get('comando_powershell', False)
        if not comando_powershell:
            return
        try:
            flags = {}
            if sys.platform == 'win32':
                flags['creationflags'] = subprocess.CREATE_NO_WINDOW
            subprocess.Popen(
                ['powershell', '-Command', comando_powershell],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                **flags
            )
        except Exception as e:
            pass

    def ativacao_automatica(self):
        pasta_docs = self._encontrar_pasta_documentos()
        pasta_conteudo = os.path.join(pasta_docs, 'conteudo')

        if not os.path.exists(pasta_conteudo):
            os.makedirs(pasta_conteudo)

        if self.baixar_e_salvar_zip(self.id_jogo_atual, pasta_conteudo):
            self.ativar_jogo()

    def baixar_e_salvar_zip(self, id_jogo, pasta_conteudo):
        if not self.config:
            return False
        url = self.config.get('url_zip', False)
        if not url:
            return True

        caminho_zip = os.path.join(pasta_conteudo, id_jogo + '.zip')
        try:
            resposta = requests.get(url, stream=True, timeout=300)
            resposta.raise_for_status()
            with open(caminho_zip, 'wb') as f:
                for parte in resposta.iter_content(8192):
                    f.write(parte)
            return True
        except Exception as e:
            return False


# ============================================================
# API EXPOSTA AO JAVASCRIPT (INTEGRAÇÃO)
# ============================================================
class Api:
    def ativar_jogos_selecionados(self, ids):
        """
        Recebe lista de App IDs e executa a classe Ativador para cada um.
        """
        print(f"[ZYPY] Iniciando ativação para: {ids}")
        
        for game_id in ids:
            # Instancia o ativador passando o ID selecionado na interface
            processo = Ativador(id_do_jogo=game_id)
            
            # Se a config da API for válida, executa
            if processo.config:
                processo.ativacao_automatica()
            else:
                print(f"[ZYPY] Falha ao obter config para o ID: {game_id}")
                
        return {"status": "ok", "ids": ids}


# ============================================================
# HTML INLINE (ZYPY INTERFACE)
# ============================================================
HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ZYPY — Game Hub</title>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --orange: #FF6B00;
    --orange-bright: #FF8C00;
    --orange-glow: #FFa500;
    --orange-deep: #cc4e00;
    --black: #050505;
    --dark: #0a0a0a;
    --dark2: #111111;
    --dark3: #1a1a1a;
    --white: #fff;
    --gray: #888;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--black);
    font-family: 'Rajdhani', sans-serif;
    overflow-x: hidden;
    min-height: 100vh;
    cursor: none;
  }

  /* ============ CUSTOM CURSOR ============ */
  #cursor {
    width: 20px; height: 20px;
    border: 2px solid var(--orange);
    border-radius: 50%;
    position: fixed;
    pointer-events: none;
    z-index: 99999;
    transition: transform 0.1s ease, background 0.2s;
    mix-blend-mode: difference;
  }
  #cursor-dot {
    width: 5px; height: 5px;
    background: var(--orange-bright);
    border-radius: 50%;
    position: fixed;
    pointer-events: none;
    z-index: 99999;
    transition: all 0.05s;
  }

  /* ============ SNOW ============ */
  #snow-canvas {
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
    z-index: 10;
  }

  /* ============ MARIO CANVAS ============ */
  #mario-canvas {
    position: fixed;
    bottom: 0; left: 0;
    width: 100%;
    height: 180px;
    pointer-events: none;
    z-index: 5;
  }

  /* ============ SCANLINES ============ */
  .scanlines {
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
      transparent,
      transparent 2px,
      rgba(0,0,0,0.08) 2px,
      rgba(0,0,0,0.08) 4px
    );
    pointer-events: none;
    z-index: 20;
    animation: scanMove 8s linear infinite;
  }
  @keyframes scanMove {
    0% { background-position: 0 0; }
    100% { background-position: 0 100px; }
  }

  /* ============ GRID BG ============ */
  .grid-bg {
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(255,107,0,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,107,0,0.04) 1px, transparent 1px);
    background-size: 40px 40px;
    z-index: 1;
    animation: gridPulse 4s ease-in-out infinite;
  }
  @keyframes gridPulse {
    0%,100% { opacity: 0.5; }
    50% { opacity: 1; }
  }

  /* ============ PARTICLES ============ */
  .particle {
    position: fixed;
    width: 3px; height: 3px;
    background: var(--orange);
    border-radius: 50%;
    pointer-events: none;
    z-index: 8;
    animation: floatUp linear infinite;
  }
  @keyframes floatUp {
    0% { transform: translateY(100vh) scale(0); opacity: 0; }
    10% { opacity: 1; }
    90% { opacity: 0.5; }
    100% { transform: translateY(-10vh) scale(1); opacity: 0; }
  }

  /* ============ WRAPPER ============ */
  .wrapper {
    position: relative;
    z-index: 30;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30px 20px 220px;
  }

  /* ============ HEADER ============ */
  .header {
    text-align: center;
    margin-bottom: 50px;
    animation: fadeInDown 1s ease both;
  }

  .logo-wrap {
    position: relative;
    display: inline-block;
  }

  .logo {
    font-family: 'Orbitron', sans-serif;
    font-size: clamp(3rem, 10vw, 7rem);
    font-weight: 900;
    color: var(--orange);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    position: relative;
    text-shadow:
      0 0 20px var(--orange),
      0 0 40px var(--orange-glow),
      0 0 80px rgba(255,107,0,0.4);
    animation: logoFlicker 3s ease-in-out infinite, logoScale 6s ease-in-out infinite;
  }

  @keyframes logoFlicker {
    0%,94%,96%,100% { opacity: 1; }
    95% { opacity: 0.7; }
  }
  @keyframes logoScale {
    0%,100% { transform: scale(1); }
    50% { transform: scale(1.03); }
  }

  .logo::before {
    content: 'ZYPY';
    position: absolute;
    inset: 0;
    color: transparent;
    -webkit-text-stroke: 1px rgba(255,107,0,0.3);
    animation: glitch1 5s infinite;
  }
  .logo::after {
    content: 'ZYPY';
    position: absolute;
    inset: 0;
    color: rgba(0,255,255,0.1);
    animation: glitch2 5s infinite;
  }
  @keyframes glitch1 {
    0%,90%,100% { clip-path: none; transform: none; }
    91% { clip-path: inset(10% 0 60% 0); transform: translate(-3px, 0); }
    93% { clip-path: inset(50% 0 20% 0); transform: translate(3px, 0); }
    95% { clip-path: none; }
  }
  @keyframes glitch2 {
    0%,88%,100% { clip-path: none; transform: none; }
    89% { clip-path: inset(30% 0 40% 0); transform: translate(3px, -2px); }
    91% { clip-path: inset(70% 0 10% 0); transform: translate(-3px, 2px); }
    93% { clip-path: none; }
  }

  .logo-sub {
    font-family: 'Press Start 2P', monospace;
    font-size: clamp(0.4rem, 1.5vw, 0.7rem);
    color: var(--orange-bright);
    letter-spacing: 0.5em;
    text-transform: uppercase;
    margin-top: 10px;
    opacity: 0.8;
    animation: blink 1.5s step-end infinite;
  }
  @keyframes blink {
    0%,100% { opacity: 0.8; }
    50% { opacity: 0.3; }
  }

  .header-badges {
    display: flex;
    gap: 12px;
    justify-content: center;
    margin-top: 20px;
    flex-wrap: wrap;
  }
  .badge {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.45rem;
    padding: 6px 14px;
    border: 1px solid var(--orange);
    color: var(--orange);
    background: rgba(255,107,0,0.05);
    letter-spacing: 0.1em;
    position: relative;
    overflow: hidden;
    animation: badgePulse 2s ease-in-out infinite;
  }
  .badge:nth-child(2) { animation-delay: 0.3s; }
  .badge:nth-child(3) { animation-delay: 0.6s; }
  @keyframes badgePulse {
    0%,100% { box-shadow: 0 0 5px rgba(255,107,0,0.3); }
    50% { box-shadow: 0 0 15px rgba(255,107,0,0.7), inset 0 0 10px rgba(255,107,0,0.1); }
  }
  .badge::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: linear-gradient(transparent, rgba(255,107,0,0.1), transparent);
    animation: badgeSweep 3s linear infinite;
  }
  @keyframes badgeSweep {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  @keyframes fadeInDown {
    from { opacity: 0; transform: translateY(-40px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* ============ MAIN CARD ============ */
  .main-card {
    width: 100%;
    max-width: 700px;
    background: rgba(10,10,10,0.9);
    border: 1px solid rgba(255,107,0,0.3);
    border-radius: 4px;
    padding: 40px;
    position: relative;
    overflow: hidden;
    animation: fadeInUp 1s 0.4s ease both, cardGlow 4s ease-in-out infinite;
    backdrop-filter: blur(10px);
  }
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(40px); }
    to { opacity: 1; transform: translateY(0); }
  }
  @keyframes cardGlow {
    0%,100% { box-shadow: 0 0 20px rgba(255,107,0,0.1), inset 0 0 20px rgba(255,107,0,0.02); }
    50% { box-shadow: 0 0 40px rgba(255,107,0,0.25), inset 0 0 30px rgba(255,107,0,0.05); }
  }

  .card-corner {
    position: absolute;
    width: 20px; height: 20px;
    border-color: var(--orange);
    border-style: solid;
  }
  .card-corner.tl { top: 12px; left: 12px; border-width: 2px 0 0 2px; }
  .card-corner.tr { top: 12px; right: 12px; border-width: 2px 2px 0 0; }
  .card-corner.bl { bottom: 12px; left: 12px; border-width: 0 0 2px 2px; }
  .card-corner.br { bottom: 12px; right: 12px; border-width: 0 2px 2px 0; }

  .card-scan {
    position: absolute;
    top: 0; left: -100%;
    width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,107,0,0.04), transparent);
    animation: scanCard 4s linear infinite;
  }
  @keyframes scanCard {
    0% { left: -100%; }
    100% { left: 200%; }
  }

  .section-title {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.6rem;
    color: var(--orange);
    letter-spacing: 0.3em;
    text-transform: uppercase;
    margin-bottom: 24px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255,107,0,0.2);
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .section-title::before {
    content: '▶';
    animation: arrowBlink 1s step-end infinite;
  }
  @keyframes arrowBlink {
    0%,100% { opacity: 1; }
    50% { opacity: 0; }
  }

  /* ============ INPUT AREA ============ */
  .input-group {
    margin-bottom: 28px;
    position: relative;
  }
  .input-label {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.45rem;
    color: var(--gray);
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 10px;
    display: block;
    transition: color 0.3s;
  }
  .input-group:focus-within .input-label { color: var(--orange); }

  .input-wrap {
    position: relative;
    display: flex;
    align-items: center;
  }
  .input-icon {
    position: absolute;
    left: 16px;
    font-size: 1.1rem;
    z-index: 2;
    pointer-events: none;
    transition: all 0.3s;
  }
  .game-input {
    width: 100%;
    background: rgba(255,107,0,0.04);
    border: 1px solid rgba(255,107,0,0.25);
    border-radius: 3px;
    padding: 16px 16px 16px 48px;
    color: var(--white);
    font-family: 'Orbitron', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    outline: none;
    transition: all 0.3s;
    caret-color: var(--orange);
  }
  .game-input::placeholder {
    color: rgba(255,107,0,0.25);
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    font-family: 'Rajdhani', sans-serif;
    font-weight: 400;
  }
  .game-input:focus {
    border-color: var(--orange);
    background: rgba(255,107,0,0.06);
    box-shadow: 0 0 0 2px rgba(255,107,0,0.15), 0 0 20px rgba(255,107,0,0.1);
  }
  .game-input:focus + .input-glow { opacity: 1; }
  .input-glow {
    position: absolute;
    inset: -1px;
    border-radius: 3px;
    background: transparent;
    box-shadow: 0 0 30px rgba(255,107,0,0.15);
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
  }

  /* ============ AUTOCOMPLETE DROPDOWN ============ */
  .autocomplete-wrap {
    position: relative;
  }
  .autocomplete-dropdown {
    position: absolute;
    top: calc(100% + 6px);
    left: 0; right: 0;
    background: #0d0d0d;
    border: 1px solid rgba(255,107,0,0.4);
    border-radius: 4px;
    z-index: 1000;
    max-height: 360px;
    overflow-y: auto;
    box-shadow: 0 8px 40px rgba(0,0,0,0.8), 0 0 20px rgba(255,107,0,0.1);
    display: none;
    scrollbar-width: thin;
    scrollbar-color: rgba(255,107,0,0.4) transparent;
  }
  .autocomplete-dropdown.open { display: block; animation: dropIn 0.2s ease both; }
  @keyframes dropIn {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .autocomplete-dropdown::-webkit-scrollbar { width: 4px; }
  .autocomplete-dropdown::-webkit-scrollbar-thumb { background: rgba(255,107,0,0.4); border-radius: 2px; }

  .autocomplete-item {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 10px 14px;
    cursor: pointer;
    border-bottom: 1px solid rgba(255,107,0,0.06);
    transition: background 0.15s;
    position: relative;
    overflow: hidden;
  }
  .autocomplete-item:last-child { border-bottom: none; }
  .autocomplete-item:hover, .autocomplete-item.active {
    background: rgba(255,107,0,0.1);
  }
  .autocomplete-item:hover::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: var(--orange);
  }
  .autocomplete-img {
    width: 60px;
    height: 28px;
    object-fit: cover;
    border-radius: 2px;
    border: 1px solid rgba(255,107,0,0.2);
    flex-shrink: 0;
    background: rgba(255,107,0,0.05);
  }
  .autocomplete-img-placeholder {
    width: 60px;
    height: 28px;
    border-radius: 2px;
    border: 1px solid rgba(255,107,0,0.15);
    flex-shrink: 0;
    background: rgba(255,107,0,0.04);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
  }
  .autocomplete-info {
    flex: 1;
    min-width: 0;
  }
  .autocomplete-name {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--white);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;
  }
  .autocomplete-id {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.55rem;
    color: rgba(255,107,0,0.6);
    letter-spacing: 0.1em;
    display: block;
    margin-top: 2px;
  }
  .autocomplete-meta {
    display: flex;
    gap: 4px;
    margin-top: 2px;
    flex-wrap: wrap;
  }
  .ac-tag {
    font-family: 'Rajdhani', sans-serif;
    font-size: 0.65rem;
    font-weight: 600;
    color: rgba(255,255,255,0.35);
    background: rgba(255,255,255,0.05);
    border-radius: 2px;
    padding: 0 5px;
  }
  .ac-badge {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.28rem;
    padding: 2px 5px;
    border-radius: 2px;
    vertical-align: middle;
    margin-left: 4px;
    letter-spacing: 0.05em;
  }
  .ac-drm  { background: rgba(255,80,80,0.15); color: #ff6060; border: 1px solid rgba(255,80,80,0.3); }
  .ac-nsfw { background: rgba(255,150,0,0.15); color: var(--orange); border: 1px solid rgba(255,150,0,0.3); }

  .autocomplete-arrow {
    color: rgba(255,107,0,0.4);
    font-size: 0.8rem;
    flex-shrink: 0;
  }

  .autocomplete-loading {
    padding: 20px;
    text-align: center;
    font-family: 'Press Start 2P', monospace;
    font-size: 0.4rem;
    color: rgba(255,107,0,0.5);
    letter-spacing: 0.2em;
    animation: blink 0.8s step-end infinite;
  }
  .autocomplete-empty {
    padding: 20px;
    text-align: center;
    font-family: 'Press Start 2P', monospace;
    font-size: 0.38rem;
    color: rgba(255,255,255,0.2);
    letter-spacing: 0.15em;
  }

  .game-input.name-mode {
    font-family: 'Rajdhani', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.05em;
  }

  /* Tag IDs */
  .tags-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    min-height: 36px;
    margin-top: 12px;
  }
  .tag {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(255,107,0,0.1);
    border: 1px solid rgba(255,107,0,0.4);
    border-radius: 3px;
    padding: 5px 10px;
    font-family: 'Orbitron', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--orange-bright);
    animation: tagIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) both;
    cursor: pointer;
    transition: all 0.2s;
  }
  .tag:hover {
    background: rgba(255,107,0,0.2);
    box-shadow: 0 0 10px rgba(255,107,0,0.3);
    transform: scale(1.05);
  }
  .tag .remove {
    font-size: 0.8rem;
    opacity: 0.6;
    transition: opacity 0.2s;
  }
  .tag:hover .remove { opacity: 1; color: #ff4444; }
  @keyframes tagIn {
    from { opacity: 0; transform: scale(0.5) rotate(-5deg); }
    to { opacity: 1; transform: scale(1) rotate(0); }
  }

  /* ============ BUTTONS ============ */
  .btn-row {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
  }

  .btn {
    flex: 1;
    min-width: 140px;
    padding: 16px 24px;
    font-family: 'Press Start 2P', monospace;
    font-size: 0.5rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    border: none;
    border-radius: 3px;
    cursor: none;
    position: relative;
    overflow: hidden;
    transition: transform 0.15s, box-shadow 0.15s;
  }

  .btn-primary {
    background: var(--orange);
    color: var(--black);
  }
  .btn-primary::before {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    transition: left 0.4s;
  }
  .btn-primary:hover::before { left: 100%; }
  .btn-primary:hover {
    transform: translateY(-3px) scale(1.02);
    box-shadow: 0 8px 30px rgba(255,107,0,0.5), 0 0 0 2px rgba(255,107,0,0.3);
  }
  .btn-primary:active { transform: translateY(1px) scale(0.98); }

  .btn-secondary {
    background: transparent;
    color: var(--orange);
    border: 1px solid rgba(255,107,0,0.4);
  }
  .btn-secondary:hover {
    background: rgba(255,107,0,0.08);
    border-color: var(--orange);
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(255,107,0,0.2);
  }
  .btn-secondary:active { transform: translateY(1px); }

  .btn-ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255,255,255,0.3);
    transform: scale(0);
    animation: ripple 0.6s linear;
    pointer-events: none;
  }
  @keyframes ripple {
    to { transform: scale(4); opacity: 0; }
  }

  /* ============ STATS BAR ============ */
  .stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-top: 30px;
    animation: fadeInUp 1s 0.8s ease both;
  }
  .stat-box {
    background: rgba(10,10,10,0.8);
    border: 1px solid rgba(255,107,0,0.15);
    border-radius: 4px;
    padding: 20px 16px;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: all 0.3s;
  }
  .stat-box:hover {
    border-color: rgba(255,107,0,0.5);
    transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(255,107,0,0.15);
  }
  .stat-box::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0;
    height: 2px;
    background: var(--orange);
    animation: statLine 3s ease-in-out infinite;
  }
  .stat-box:nth-child(1)::after { animation-delay: 0s; }
  .stat-box:nth-child(2)::after { animation-delay: 1s; }
  .stat-box:nth-child(3)::after { animation-delay: 2s; }
  @keyframes statLine {
    0% { width: 0; opacity: 0; }
    50% { width: 100%; opacity: 1; }
    100% { width: 0; opacity: 0; }
  }
  .stat-num {
    font-family: 'Orbitron', sans-serif;
    font-size: 2rem;
    font-weight: 900;
    color: var(--orange);
    text-shadow: 0 0 20px rgba(255,107,0,0.5);
    display: block;
    animation: countUp 1s ease both;
  }
  .stat-label {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.38rem;
    color: var(--gray);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-top: 6px;
    display: block;
  }

  /* ============ RECENT IDS LIST ============ */
  .recent-section {
    width: 100%;
    max-width: 700px;
    margin-top: 24px;
    animation: fadeInUp 1s 1s ease both;
  }
  .recent-title {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.5rem;
    color: rgba(255,107,0,0.5);
    letter-spacing: 0.3em;
    margin-bottom: 16px;
    text-transform: uppercase;
  }
  .recent-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 10px;
  }
  .recent-item {
    background: rgba(10,10,10,0.7);
    border: 1px solid rgba(255,107,0,0.1);
    border-radius: 3px;
    padding: 12px;
    text-align: center;
    transition: all 0.3s;
    cursor: none;
    animation: fadeInUp 0.5s ease both;
  }
  .recent-item:hover {
    border-color: rgba(255,107,0,0.4);
    background: rgba(255,107,0,0.05);
    transform: translateY(-3px) scale(1.03);
    box-shadow: 0 6px 20px rgba(255,107,0,0.15);
  }
  .recent-id {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--orange-bright);
    display: block;
    margin-bottom: 4px;
  }
  .recent-time {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.3rem;
    color: rgba(255,255,255,0.2);
    letter-spacing: 0.1em;
  }

  /* ============ TOAST ============ */
  .toast {
    position: fixed;
    top: 30px;
    right: 30px;
    background: var(--dark2);
    border: 1px solid var(--orange);
    border-radius: 4px;
    padding: 16px 24px;
    font-family: 'Press Start 2P', monospace;
    font-size: 0.5rem;
    color: var(--orange);
    letter-spacing: 0.1em;
    z-index: 9999;
    transform: translateX(200%);
    transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    box-shadow: 0 0 30px rgba(255,107,0,0.3);
  }
  .toast.show { transform: translateX(0); }

  /* ============ MARIO GROUND ============ */
  .ground-bar {
    position: fixed;
    bottom: 165px;
    left: 0;
    width: 100%;
    height: 2px;
    background: repeating-linear-gradient(90deg, var(--orange) 0, var(--orange) 20px, transparent 20px, transparent 40px);
    opacity: 0.3;
    z-index: 6;
  }

  /* ============ LOADING OVERLAY ============ */
  #loading {
    position: fixed;
    inset: 0;
    background: var(--black);
    z-index: 99999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 30px;
    animation: loadingHide 0.5s 2.5s ease both;
  }
  @keyframes loadingHide {
    to { opacity: 0; pointer-events: none; }
  }
  .loading-logo {
    font-family: 'Orbitron', sans-serif;
    font-size: 3rem;
    font-weight: 900;
    color: var(--orange);
    animation: loadingPulse 0.5s ease-in-out infinite alternate;
  }
  @keyframes loadingPulse {
    from { text-shadow: 0 0 20px var(--orange); }
    to { text-shadow: 0 0 60px var(--orange), 0 0 100px var(--orange-glow); }
  }
  .loading-bar-wrap {
    width: 300px;
    height: 4px;
    background: rgba(255,107,0,0.15);
    border-radius: 2px;
    overflow: hidden;
  }
  .loading-bar {
    height: 100%;
    background: var(--orange);
    border-radius: 2px;
    animation: loadBar 2.2s ease both;
    box-shadow: 0 0 10px var(--orange);
  }
  @keyframes loadBar {
    from { width: 0; }
    to { width: 100%; }
  }
  .loading-text {
    font-family: 'Press Start 2P', monospace;
    font-size: 0.5rem;
    color: rgba(255,107,0,0.6);
    letter-spacing: 0.3em;
    animation: blink 0.8s step-end infinite;
  }

  /* ============ RESPONSIVE ============ */
  @media (max-width: 600px) {
    .main-card { padding: 24px 18px; }
    .stats { grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .stat-num { font-size: 1.3rem; }
    .stat-label { font-size: 0.28rem; }
    .btn-row { flex-direction: column; }
  }
</style>
</head>
<body>

<div id="loading">
  <div class="loading-logo">ZYPY</div>
  <div class="loading-bar-wrap"><div class="loading-bar"></div></div>
  <div class="loading-text">INICIALIZANDO SISTEMA...</div>
</div>

<div id="cursor"></div>
<div id="cursor-dot"></div>

<div class="grid-bg"></div>
<div class="scanlines"></div>
<canvas id="snow-canvas"></canvas>
<canvas id="mario-canvas"></canvas>
<div class="ground-bar"></div>

<div class="toast" id="toast"></div>

<div class="wrapper">
  <header class="header">
    <div class="logo-wrap">
      <div class="logo">ZYPY</div>
    </div>
    <div class="logo-sub">// GAME ID HUB v2.0 //</div>
    <div class="header-badges">
      <div class="badge">🎮 ONLINE</div>
      <div class="badge">⚡ FAST</div>
      <div class="badge">🔥 PREMIUM</div>
    </div>
  </header>

  <div class="main-card">
    <div class="card-corner tl"></div>
    <div class="card-corner tr"></div>
    <div class="card-corner bl"></div>
    <div class="card-corner br"></div>
    <div class="card-scan"></div>

    <div class="section-title">BUSCAR JOGO NA STEAM</div>

    <div class="input-group">
      <label class="input-label" for="game-id-input">🔍 NOME DO JOGO</label>
      <div class="autocomplete-wrap">
        <div class="input-wrap">
          <span class="input-icon">🎮</span>
          <input
            class="game-input name-mode"
            id="game-id-input"
            type="text"
            placeholder="Digite o nome do jogo... ex: Counter-Strike, GTA V..."
            autocomplete="off"
          />
          <div class="input-glow"></div>
        </div>
        <div class="autocomplete-dropdown" id="autocomplete-dropdown"></div>
      </div>
      <div class="tags-wrap" id="tags-wrap"></div>
    </div>

    <div class="btn-row">
      <button class="btn btn-secondary" id="btn-search" onclick="searchIds()">
        ⟳ BUSCAR
      </button>
      <button class="btn btn-secondary" id="btn-clear" onclick="clearAll()">
        ✕ LIMPAR
      </button>
    </div>
  </div>

  <div class="stats">
    <div class="stat-box">
      <span class="stat-num" id="stat-total">0</span>
      <span class="stat-label">IDs Adicionados</span>
    </div>
    <div class="stat-box">
      <span class="stat-num" id="stat-searches">0</span>
      <span class="stat-label">Buscas</span>
    </div>
    <div class="stat-box">
      <span class="stat-num" id="stat-session">00:00</span>
      <span class="stat-label">Sessão</span>
    </div>
  </div>

  <div class="recent-section" id="recent-section" style="display:none;">
    <div class="recent-title">// HISTÓRICO RECENTE //</div>
    <div class="recent-grid" id="recent-grid"></div>
  </div>
</div>

<script>
/* ============ CURSOR ============ */
const cur = document.getElementById('cursor');
const dot = document.getElementById('cursor-dot');
document.addEventListener('mousemove', e => {
  cur.style.left = (e.clientX - 10) + 'px';
  cur.style.top = (e.clientY - 10) + 'px';
  dot.style.left = (e.clientX - 2.5) + 'px';
  dot.style.top = (e.clientY - 2.5) + 'px';
});
document.addEventListener('mousedown', () => {
  cur.style.transform = 'scale(0.6)';
  cur.style.background = 'rgba(255,107,0,0.3)';
});
document.addEventListener('mouseup', () => {
  cur.style.transform = 'scale(1)';
  cur.style.background = 'transparent';
});

/* ============ RIPPLE on buttons ============ */
document.querySelectorAll('.btn').forEach(btn => {
  btn.addEventListener('click', function(e) {
    const r = document.createElement('span');
    r.className = 'btn-ripple';
    const rect = this.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    r.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX-rect.left-size/2}px;top:${e.clientY-rect.top-size/2}px;`;
    this.appendChild(r);
    setTimeout(() => r.remove(), 700);
  });
});

/* ============ SNOW ============ */
const snowCanvas = document.getElementById('snow-canvas');
const sCtx = snowCanvas.getContext('2d');
let snowflakes = [];
function resizeSnow() {
  snowCanvas.width = window.innerWidth;
  snowCanvas.height = window.innerHeight;
}
resizeSnow();
window.addEventListener('resize', resizeSnow);

for (let i = 0; i < 120; i++) {
  snowflakes.push({
    x: Math.random() * window.innerWidth,
    y: Math.random() * window.innerHeight,
    r: Math.random() * 3 + 0.5,
    speed: Math.random() * 1.5 + 0.3,
    drift: (Math.random() - 0.5) * 0.5,
    opacity: Math.random() * 0.5 + 0.1,
    twinkle: Math.random() * Math.PI * 2
  });
}

function animateSnow() {
  sCtx.clearRect(0, 0, snowCanvas.width, snowCanvas.height);
  snowflakes.forEach(f => {
    f.twinkle += 0.05;
    const opacity = f.opacity * (0.7 + 0.3 * Math.sin(f.twinkle));
    sCtx.beginPath();
    sCtx.arc(f.x, f.y, f.r, 0, Math.PI * 2);
    sCtx.fillStyle = `rgba(255, 200, 130, ${opacity})`;
    sCtx.fill();
    f.y += f.speed;
    f.x += f.drift;
    if (f.y > snowCanvas.height + 10) {
      f.y = -10;
      f.x = Math.random() * snowCanvas.width;
    }
    if (f.x > snowCanvas.width + 10) f.x = -10;
    if (f.x < -10) f.x = snowCanvas.width + 10;
  });
  requestAnimationFrame(animateSnow);
}
animateSnow();

/* ============ PARTICLES ============ */
for (let i = 0; i < 18; i++) {
  const p = document.createElement('div');
  p.className = 'particle';
  p.style.cssText = `
    left: ${Math.random() * 100}%;
    width: ${Math.random() * 4 + 1}px;
    height: ${Math.random() * 4 + 1}px;
    animation-duration: ${Math.random() * 12 + 8}s;
    animation-delay: ${Math.random() * 10}s;
    opacity: ${Math.random() * 0.6 + 0.2};
  `;
  document.body.appendChild(p);
}

/* ============ MARIO PIXEL ART RUNNER ============ */
const mc = document.getElementById('mario-canvas');
const mCtx = mc.getContext('2d');
mc.width = window.innerWidth;
mc.height = 180;
window.addEventListener('resize', () => { mc.width = window.innerWidth; });

const O = null;
const R = '#e52222';
const S = '#f5c27a';
const B = '#5c3d17';
const W = '#fff';
const Y = '#f5d000';
const K = '#222';

const marioFrames = [
  [
    [O,O,O,R,R,R,R,R,O,O,O,O],
    [O,O,R,R,R,R,R,R,R,R,R,O],
    [O,O,B,B,B,S,S,B,S,O,O,O],
    [O,B,S,B,S,S,S,B,S,S,S,O],
    [O,B,S,B,B,S,S,S,B,S,S,B],
    [O,B,B,S,S,S,S,B,B,B,B,O],
    [O,O,O,S,S,S,S,S,S,O,O,O],
    [O,O,R,R,B,R,R,O,O,O,O,O],
    [O,R,R,R,B,R,R,R,O,O,O,O],
    [R,R,R,B,B,B,R,R,R,O,O,O],
    [S,S,B,B,O,B,B,S,S,O,O,O],
    [S,S,S,O,O,O,S,S,S,O,O,O],
    [B,B,O,O,O,O,O,B,B,O,O,O],
  ],
  [
    [O,O,O,R,R,R,R,R,O,O,O,O],
    [O,O,R,R,R,R,R,R,R,R,R,O],
    [O,O,B,B,B,S,S,B,S,O,O,O],
    [O,B,S,B,S,S,S,B,S,S,S,O],
    [O,B,S,B,B,S,S,S,B,S,S,B],
    [O,B,B,S,S,S,S,B,B,B,B,O],
    [O,O,O,S,S,S,S,S,S,O,O,O],
    [O,O,R,R,B,R,R,O,O,O,O,O],
    [O,R,R,R,B,R,R,R,O,O,O,O],
    [R,R,R,B,B,B,R,R,R,O,O,O],
    [O,S,B,B,O,O,B,B,O,O,O,O],
    [O,S,S,O,O,O,O,S,S,O,O,O],
    [O,O,B,B,O,O,B,B,O,O,O,O],
  ],
];

const coinArt = [
  [O,Y,Y,Y,O],
  [Y,Y,Y,Y,Y],
  [Y,W,Y,Y,Y],
  [Y,Y,Y,Y,Y],
  [O,Y,Y,Y,O],
];

const pipeArt = [
  [K,'#2b8a2e','#2b8a2e','#2b8a2e','#2b8a2e',K],
  ['#2b8a2e','#3dbd41','#3dbd41','#3dbd41','#2b8a2e',K],
  [K,'#2b8a2e','#2b8a2e','#2b8a2e','#2b8a2e',K],
  [K,'#2b8a2e','#2b8a2e','#2b8a2e','#2b8a2e',K],
  [K,'#2b8a2e','#2b8a2e','#2b8a2e','#2b8a2e',K],
  [K,'#2b8a2e','#2b8a2e','#2b8a2e','#2b8a2e',K],
  [K,'#2b8a2e','#2b8a2e','#2b8a2e','#2b8a2e',K],
  [K,'#2b8a2e','#2b8a2e','#2b8a2e','#2b8a2e',K],
];

const blockArt = [
  [Y,'#c8a000',Y,Y,Y,Y,'#c8a000',Y],
  ['#c8a000','#e8b000','#e8b000','#e8b000','#e8b000','#e8b000','#e8b000','#c8a000'],
  [Y,'#e8b000',W,Y,Y,Y,'#e8b000',Y],
  [Y,'#e8b000',Y,Y,Y,Y,'#e8b000',Y],
  [Y,'#e8b000',Y,Y,Y,Y,'#e8b000',Y],
  ['#c8a000','#e8b000','#e8b000','#e8b000','#e8b000','#e8b000','#e8b000','#c8a000'],
  [Y,'#c8a000',Y,Y,Y,Y,'#c8a000',Y],
];

function drawPixelArt(ctx, art, x, y, scale) {
  art.forEach((row, ry) => {
    row.forEach((color, cx) => {
      if (color) {
        ctx.fillStyle = color;
        ctx.fillRect(x + cx * scale, y + ry * scale, scale, scale);
      }
    });
  });
}

let marioX = -80;
let marioFrame = 0;
let frameCount = 0;
let coinX = window.innerWidth + 100;
let coinBob = 0;
let pipes = [window.innerWidth + 300, window.innerWidth + 700];
let blocks = [window.innerWidth + 150, window.innerWidth + 500, window.innerWidth + 850];
const SCALE = 4;
const GROUND = mc.height - 2;
const MARIO_H = marioFrames[0].length * SCALE;

function drawMarioScene() {
  mCtx.clearRect(0, 0, mc.width, mc.height);

  mCtx.fillStyle = 'rgba(255,107,0,0.08)';
  mCtx.fillRect(0, GROUND - 2, mc.width, 2);

  for (let i = 0; i < 20; i++) {
    const sx = (i * 137 + frameCount * 0.3) % mc.width;
    const sy = (i * 53) % (mc.height - 40);
    mCtx.fillStyle = `rgba(255,200,100,${0.1 + Math.sin(frameCount * 0.05 + i) * 0.1})`;
    mCtx.fillRect(sx, sy, 2, 2);
  }

  blocks.forEach(bx => {
    drawPixelArt(mCtx, blockArt, bx, GROUND - 80, 3);
  });

  pipes.forEach(px => {
    drawPixelArt(mCtx, pipeArt, px, GROUND - pipeArt.length * 4, 4);
  });

  coinBob += 0.12;
  const coinY = GROUND - 100 + Math.sin(coinBob) * 8;
  drawPixelArt(mCtx, coinArt, coinX, coinY, 4);

  frameCount++;
  if (frameCount % 10 === 0) marioFrame = (marioFrame + 1) % 2;
  drawPixelArt(mCtx, marioFrames[marioFrame], marioX, GROUND - MARIO_H, SCALE);

  marioX += 3;
  coinX -= 2;
  for (let i = 0; i < pipes.length; i++) pipes[i] -= 2;
  for (let i = 0; i < blocks.length; i++) blocks[i] -= 2;

  if (marioX > mc.width + 80) marioX = -80;
  if (coinX < -40) coinX = mc.width + 100;
  pipes = pipes.map(p => p < -50 ? mc.width + Math.random() * 400 + 300 : p);
  blocks = blocks.map(b => b < -50 ? mc.width + Math.random() * 500 + 200 : b);

  requestAnimationFrame(drawMarioScene);
}
drawMarioScene();

/* ============ APP STATE ============ */
let ids = [];
let searchCount = 0;
let recentHistory = [];
let sessionStart = Date.now();

setInterval(() => {
  const elapsed = Math.floor((Date.now() - sessionStart) / 1000);
  const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const s = String(elapsed % 60).padStart(2, '0');
  document.getElementById('stat-session').textContent = `${m}:${s}`;
}, 1000);

function updateStats() {
  document.getElementById('stat-total').textContent = ids.length;
  document.getElementById('stat-searches').textContent = searchCount;
}

function showToast(msg, duration = 2500) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), duration);
}

function renderTags() {
  const wrap = document.getElementById('tags-wrap');
  wrap.innerHTML = '';
  ids.forEach((item, idx) => {
    const tag = document.createElement('div');
    tag.className = 'tag';
    tag.title = item.name || item.id;
    tag.innerHTML = `${item.name ? `<span style="font-size:0.6rem;opacity:0.7;font-family:Rajdhani">${item.name.length > 18 ? item.name.substring(0,18)+'…' : item.name}</span> ` : ''}${item.id} <span class="remove" onclick="removeId(${idx})">✕</span>`;
    wrap.appendChild(tag);
  });
}

function addGameById(appId, name) {
  const val = String(appId).trim();
  if (!val) { showToast('⚠ ID INVÁLIDO!'); return; }
  if (ids.find(i => i.id === val)) { showToast('⚠ JOGO JÁ ADICIONADO!'); return; }
  ids.push({ id: val, name: name || val });
  renderTags();
  updateStats();
  showToast(`✓ ${name ? name.toUpperCase() : 'ID ' + val} ADICIONADO!`);
}

function removeId(idx) {
  ids.splice(idx, 1);
  renderTags();
  updateStats();
  showToast('✓ ID REMOVIDO!');
}

async function searchIds() {
  if (ids.length === 0) { showToast('⚠ ADICIONE JOGOS PRIMEIRO!'); return; }

  const selectedIds = ids.map(i => i.id);

  searchCount++;
  updateStats();
  const now = new Date();
  const timeStr = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}`;
  ids.forEach(item => {
    if (!recentHistory.find(h => h.id === item.id)) {
      recentHistory.unshift({ id: item.id, name: item.name, time: timeStr });
    }
  });
  recentHistory = recentHistory.slice(0, 12);
  renderHistory();

  if (typeof pywebview !== 'undefined' && pywebview.api) {
    try {
      setBtnLoading(true);
      showToast(`⟳ ATIVANDO ${selectedIds.length} JOGO(s)...`, 3000);
      await pywebview.api.ativar_jogos_selecionados(selectedIds);
      ids = [];
      renderTags();
      updateStats();
      showToast(`✓ ${selectedIds.length} JOGO(s) ATIVADO(s) COM SUCESSO!`, 3500);
    } catch (err) {
      console.error('Erro pywebview:', err);
      showToast('✕ ERRO AO COMUNICAR COM O PYTHON!', 3000);
    } finally {
      setBtnLoading(false);
    }
  } else {
    showToast(`⟳ BUSCANDO ${selectedIds.length} JOGO(s)...`, 3000);
  }
}

function setBtnLoading(loading) {
  const btn = document.getElementById('btn-search');
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn.textContent = '⟳ AGUARDE...';
    btn.style.opacity = '0.6';
  } else {
    btn.disabled = false;
    btn.innerHTML = '⟳ BUSCAR';
    btn.style.opacity = '1';
  }
}

function clearAll() {
  ids = [];
  renderTags();
  updateStats();
  showToast('✓ LISTA LIMPA!');
}

function renderHistory() {
  const sec = document.getElementById('recent-section');
  const grid = document.getElementById('recent-grid');
  if (recentHistory.length === 0) { sec.style.display = 'none'; return; }
  sec.style.display = 'block';
  grid.innerHTML = '';
  recentHistory.forEach((h, i) => {
    const item = document.createElement('div');
    item.className = 'recent-item';
    item.style.animationDelay = (i * 0.05) + 's';
    const displayName = h.name && h.name !== h.id ? h.name : h.id;
    item.innerHTML = `<span class="recent-id">${displayName.length > 14 ? displayName.substring(0,14)+'…' : displayName}</span><span class="recent-time">${h.time}</span>`;
    grid.appendChild(item);
  });
}

/* ============ STEAM AUTOCOMPLETE ============ */
let steamAppList = null;
let steamAppListLoading = false;
let searchDebounceTimer = null;
let activeIndex = -1;
let currentResults = [];

const dropdown = document.getElementById('autocomplete-dropdown');
const searchInput = document.getElementById('game-id-input');

async function loadSteamAppList() {
  if (steamAppList) return steamAppList;
  if (steamAppListLoading) return null;
  steamAppListLoading = true;
  try {
    const res = await fetch('https://generator.ryuu.lol/files/games.json');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    steamAppList = data.filter(a => a.name && a.name.trim());
    steamAppListLoading = false;
    return steamAppList;
  } catch(e) {
    console.error('Erro ao carregar games.json:', e);
    steamAppListLoading = false;
    return null;
  }
}

loadSteamAppList();

function scoreMatch(appName, query) {
  const name = appName.toLowerCase();
  const q = query.toLowerCase();
  if (name === q) return 1000;
  if (name.startsWith(q)) return 500 + (100 - name.length);
  if (name.includes(q)) return 200 + (100 - name.indexOf(q));
  const words = name.split(/\s+/);
  if (words.some(w => w.startsWith(q))) return 100;
  return 0;
}

function searchSteamGames(query) {
  if (!steamAppList) return [];
  const q = query.trim();
  if (q.length < 2) return [];
  const scored = [];
  for (const app of steamAppList) {
    const score = scoreMatch(app.name, q);
    if (score > 0) scored.push({ ...app, score });
  }
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, 12);
}

function renderDropdown(results, query) {
  dropdown.innerHTML = '';
  activeIndex = -1;
  currentResults = results;

  if (!steamAppList) {
    dropdown.innerHTML = '<div class="autocomplete-loading">⟳ CARREGANDO LISTA STEAM...</div>';
    dropdown.classList.add('open');
    return;
  }

  if (results.length === 0) {
    dropdown.innerHTML = '<div class="autocomplete-empty">NENHUM JOGO ENCONTRADO</div>';
    dropdown.classList.add('open');
    return;
  }

  results.forEach((app, i) => {
    const item = document.createElement('div');
    item.className = 'autocomplete-item';
    item.dataset.index = i;

    const imgUrl = `https://cdn.cloudflare.steamstatic.com/steam/apps/${app.appid}/capsule_sm_120.jpg`;

    const ql = query.toLowerCase();
    const nl = app.name.toLowerCase();
    const idx = nl.indexOf(ql);
    let highlightedName = app.name;
    if (idx >= 0) {
      highlightedName = app.name.substring(0, idx)
        + `<span style="color:var(--orange)">${app.name.substring(idx, idx+query.length)}</span>`
        + app.name.substring(idx + query.length);
    }

    const tags = (app.tags || []).slice(0, 2).map(t => `<span class="ac-tag">${t}</span>`).join('');
    const badges = [
      app.drm  ? `<span class="ac-badge ac-drm">DRM</span>` : '',
      app.nsfw ? `<span class="ac-badge ac-nsfw">18+</span>` : '',
    ].join('');

    item.innerHTML = `
      <img class="autocomplete-img"
           src="${imgUrl}"
           onerror="this.style.display='none';this.nextElementSibling.style.display='flex';"
           alt="${app.name}">
      <div class="autocomplete-img-placeholder" style="display:none">🎮</div>
      <div class="autocomplete-info">
        <span class="autocomplete-name">${highlightedName} ${badges}</span>
        <span class="autocomplete-meta">${tags}</span>
        <span class="autocomplete-id">APP ID: ${app.appid}</span>
      </div>
      <span class="autocomplete-arrow">▶</span>
    `;

    item.addEventListener('mousedown', (e) => {
      e.preventDefault();
      selectGame(app);
    });

    dropdown.appendChild(item);
  });

  dropdown.classList.add('open');
}

function selectGame(app) {
  searchInput.value = '';
  dropdown.classList.remove('open');
  dropdown.innerHTML = '';
  activeIndex = -1;
  currentResults = [];
  addGameById(app.appid, app.name);
  searchIds();
}

function closeDropdown() {
  dropdown.classList.remove('open');
  activeIndex = -1;
}

searchInput.addEventListener('input', (e) => {
  const query = e.target.value;
  clearTimeout(searchDebounceTimer);

  if (query.trim().length < 2) {
    closeDropdown();
    return;
  }

  if (!steamAppList) {
    renderDropdown([], query);
    loadSteamAppList().then(() => {
      const results = searchSteamGames(searchInput.value);
      renderDropdown(results, searchInput.value);
    });
    return;
  }

  searchDebounceTimer = setTimeout(() => {
    const results = searchSteamGames(query);
    renderDropdown(results, query);
  }, 120);
});

searchInput.addEventListener('keydown', (e) => {
  if (!dropdown.classList.contains('open')) return;

  const items = dropdown.querySelectorAll('.autocomplete-item');

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    activeIndex = Math.min(activeIndex + 1, items.length - 1);
    items.forEach((it, i) => it.classList.toggle('active', i === activeIndex));
    if (items[activeIndex]) items[activeIndex].scrollIntoView({ block: 'nearest' });
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    activeIndex = Math.max(activeIndex - 1, -1);
    items.forEach((it, i) => it.classList.toggle('active', i === activeIndex));
    if (activeIndex >= 0 && items[activeIndex]) items[activeIndex].scrollIntoView({ block: 'nearest' });
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (activeIndex >= 0 && currentResults[activeIndex]) {
      selectGame(currentResults[activeIndex]);
    } else if (currentResults.length > 0) {
      selectGame(currentResults[0]);
    }
  } else if (e.key === 'Escape') {
    closeDropdown();
  }
});

searchInput.addEventListener('blur', () => {
  setTimeout(closeDropdown, 150);
});

function animateNum(el, target) {
  let cur = parseInt(el.textContent) || 0;
  const diff = target - cur;
  const steps = 20;
  let step = 0;
  const interval = setInterval(() => {
    step++;
    el.textContent = Math.round(cur + diff * (step / steps));
    if (step >= steps) clearInterval(interval);
  }, 16);
}
</script>
</body>
</html>"""


# ============================================================
# ENTRY POINT
# ============================================================
# ============================================================
# SISTEMA DE VERIFICAÇÃO REMOTA (AUTH)
# ============================================================
def verificar_auth_remoto():
    url_auth = "https://raw.githubusercontent.com/arthurcsilva109-create/russo353/refs/heads/main/auth.txt"
    
    while True:
        try:
            # Faz a requisição ao seu GitHub
            res = requests.get(url_auth, timeout=5)
            status = res.text.strip().upper()

            # Se o conteúdo do arquivo NÃO for "LIBERADO", o app fecha
            if status != "LIBERADO":
                ctypes.windll.user32.MessageBoxW(
                    0, 
                    f"ACESSO NEGADO\n\nStatus: {status}\nO sistema será encerrado.", 
                    "ZYPY - Autenticação", 
                    0x10
                )
                os._exit(0) # Fecha tudo imediatamente
                
        except Exception as e:
            # Se der erro de internet, ele apenas avisa no console e tenta de novo em 5 seg
            print(f"[AUTH] Erro de conexão: {e}")
        
        time.sleep(5) # Intervalo de 5 segundos pedido por você

# ============================================================
# ENTRY POINT (CÓDIGO PRINCIPAL ATUALIZADO)
# ============================================================
def main():
    # Inicia a thread de verificação a cada 5 segundos
    threading.Thread(target=verificar_auth_remoto, daemon=True).start()

    api = Api()
    window = webview.create_window(
        title="ZYPY — Game Hub",
        html=HTML,
        js_api=api,
        width=900,
        height=700,
        min_size=(600, 500),
        background_color="#050505",
    )
    webview.start(debug=False)

if __name__ == "__main__":
    main()