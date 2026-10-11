$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$script = Join-Path $PSScriptRoot 'update_daily_digest.py'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Set-Location $projectRoot
uv run python $script --root (Join-Path $projectRoot 'llm_agent_news')
uv run python (Join-Path $projectRoot 'llm_agent_news\scripts\build_knowledge_graph.py') --root (Join-Path $projectRoot 'llm_agent_news')
uv run python (Join-Path $projectRoot 'llm_agent_news\scripts\cleanup_archive.py') --root (Join-Path $projectRoot 'llm_agent_news') --limit-gib 1 --apply
