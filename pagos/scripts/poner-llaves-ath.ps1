# Pone las llaves de ATH Móvil Business como secretos del Worker en Cloudflare.
# Las llaves se escriben aquí (no se ven en pantalla), van directo a Cloudflare cifradas
# y no quedan en ningún archivo, ni en el historial, ni en git.
#
# Uso (desde la carpeta del sitio, donde está wrangler.jsonc):
#   powershell -ExecutionPolicy Bypass -File scripts\poner-llaves-ath.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\poner-llaves-ath.ps1 -Worker otro-worker
#
# Dónde están las llaves: app ATH Business → Ajustes → Integración (API keys):
#   "Public token" y "Private token".

param([string]$Worker)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

# Un CLOUDFLARE_API_TOKEN viejo o sin permisos de Workers le gana a la sesión de `npx wrangler login`.
# Se ignora solo mientras corre este script (no se toca la variable del sistema).
Remove-Item Env:CLOUDFLARE_API_TOKEN -ErrorAction SilentlyContinue

if (-not $Worker) {
  $cfg = Get-ChildItem -Filter 'wrangler.json*' | Select-Object -First 1
  if ($cfg) {
    $m = Select-String -Path $cfg.FullName -Pattern '"name"\s*:\s*"([^"]+)"' | Select-Object -First 1
    if ($m) { $Worker = $m.Matches[0].Groups[1].Value }
  }
}
if (-not $Worker) {
  Write-Host "No encontré el nombre del Worker. Úselo así: -Worker nombre-del-worker" -ForegroundColor Red
  exit 1
}

function Leer-Secreto([string]$pregunta) {
  $seguro = Read-Host -Prompt $pregunta -AsSecureString
  $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
  try { return ([Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)).Trim() }
  finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

function Poner([string]$nombre, [string]$valor) {
  Write-Host "  Guardando $nombre en Cloudflare..." -ForegroundColor DarkGray
  # wrangler lee el valor por la entrada estándar: no aparece en la línea de comandos
  $valor | npx wrangler secret put $nombre --name $Worker | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "No se pudo guardar $nombre (¿sesión de wrangler activa? pruebe: npx wrangler login)" }
  Write-Host "  $nombre listo." -ForegroundColor Green
}

Write-Host ""
Write-Host "Llaves de ATH Móvil Business para el Worker '$Worker'" -ForegroundColor Yellow
Write-Host "Lo que escriba no se mostrará en pantalla."
Write-Host ""

$publica = Leer-Secreto 'Public token (llave pública)'
$privada = Leer-Secreto 'Private token (llave privada)'

if ($publica.Length -lt 20 -or $privada.Length -lt 20) {
  Write-Host "Las llaves parecen incompletas (muy cortas). No se guardó nada." -ForegroundColor Red
  exit 1
}
if ($publica -eq $privada) {
  Write-Host "La llave pública y la privada son iguales: revise que copió las dos. No se guardó nada." -ForegroundColor Red
  exit 1
}

Poner 'ATHM_PUBLIC_TOKEN' $publica
Poner 'ATHM_PRIVATE_TOKEN' $privada
$publica = $null; $privada = $null

Write-Host ""
Write-Host "Listo. El botón de ATH Móvil se activa solo (sin volver a publicar el sitio)." -ForegroundColor Green
Write-Host "Siguiente: prueba real de `$1.00 desde /pagar/ con un ATH Móvil distinto al del negocio (docs/pruebas.md)."
