# Configurações do Jogo
$ID_JOGO = "2322010"
$URL = "https://gaamingsteam.squareweb.app/api/app/kastexstorms/$ID_JOGO"

try {
    # Consulta a API de forma silenciosa
    $resp = Invoke-RestMethod -Uri $URL -Method Get -ErrorAction Stop
    
    if ($resp.ativo -eq $true) {
        # Janela de Sucesso (Estilo nativo Windows)
        $wshell = New-Object -ComObject WScript.Shell
        $wshell.Popup("O jogo $ID_JOGO foi ativado com sucesso!", 0, "Sucesso", 64)
        
        # --- INSIRA AQUI SUA LÓGICA DE ATIVAÇÃO EXTRA SE NECESSÁRIO ---
    } else {
        $wshell = New-Object -ComObject WScript.Shell
        $wshell.Popup("Acesso negado. Este jogo não está liberado no servidor.", 0, "Erro de Autenticação", 16)
    }
} catch {
    Write-Host "Erro: Não foi possível conectar ao servidor de ativação." -ForegroundColor Red
}
