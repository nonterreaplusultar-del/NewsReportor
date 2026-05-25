$envFile = Join-Path $PSScriptRoot ".env.local"

if (!(Test-Path $envFile)) {
    Write-Host "没有找到 .env.local，请确认它在项目根目录。" -ForegroundColor Red
    exit 1
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()

    if ($line -eq "" -or $line.StartsWith("#")) {
        return
    }

    if ($line -match '^\s*([^=]+?)\s*=\s*(.*)\s*$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim().Trim('"').Trim("'")
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

Write-Host "已加载 .env.local" -ForegroundColor Green

claude
