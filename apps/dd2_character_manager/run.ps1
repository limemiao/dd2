$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "app.py"
python $script
