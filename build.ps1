# PowerShell Build Script for bn.dict
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Building standalone bn.dict             " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$scriptPath = Join-Path $PSScriptRoot "scripts\build.py"
python $scriptPath $args

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] bn.dict build completed!" -ForegroundColor Green
} else {
    Write-Host "`n[ERROR] Build failed. Check the error log above." -ForegroundColor Red
}

