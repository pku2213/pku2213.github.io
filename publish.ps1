[CmdletBinding()]
param(
    [string]$Message = "",
    [switch]$SkipTests,
    [ValidateRange(10, 1800)]
    [int]$PublishTimeoutSeconds = 240
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$siteRoot = Join-Path $projectRoot "site"
$qaScript = Join-Path $projectRoot "tools\qa_site.py"
$qaDirectory = Join-Path $projectRoot "_local_docs\qa"
$publicUrl = "https://pku2213.github.io/"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & git @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed: git $($Arguments -join ' ')"
    }
}

function Get-Sha256Hex {
    param([Parameter(Mandatory = $true)][byte[]]$Bytes)

    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        return -join ($sha256.ComputeHash($Bytes) | ForEach-Object { $_.ToString("x2") })
    }
    finally {
        $sha256.Dispose()
    }
}

function Test-LocalAssetReferences {
    param([Parameter(Mandatory = $true)][string]$IndexPath)

    $html = Get-Content -LiteralPath $IndexPath -Raw
    $matches = [regex]::Matches($html, '(?:src|href)=["''](?<path>assets/[^"''?#]+)')
    $missing = New-Object System.Collections.Generic.List[string]

    foreach ($match in $matches) {
        $relativePath = $match.Groups["path"].Value.Replace("/", [IO.Path]::DirectorySeparatorChar)
        $assetPath = Join-Path $siteRoot $relativePath
        if (-not (Test-Path -LiteralPath $assetPath -PathType Leaf)) {
            $missing.Add($match.Groups["path"].Value)
        }
    }

    if ($missing.Count -gt 0) {
        throw "Missing local assets: $($missing -join ', ')"
    }

    Write-Host "Asset check passed ($($matches.Count) local references)." -ForegroundColor Green
}

function Invoke-SiteQa {
    if (-not (Test-Path -LiteralPath $qaScript -PathType Leaf)) {
        throw "QA script not found: $qaScript"
    }
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        throw "Python was not found. Install Python or publish with -SkipTests."
    }

    $previousSiteDirectory = [Environment]::GetEnvironmentVariable("SITE_DIRECTORY", "Process")
    $previousQaDirectory = [Environment]::GetEnvironmentVariable("QA_DIRECTORY", "Process")

    try {
        $env:SITE_DIRECTORY = $siteRoot
        $env:QA_DIRECTORY = $qaDirectory
        & python $qaScript
        if ($LASTEXITCODE -ne 0) {
            throw "Website QA failed. If Playwright is missing, run: pip install playwright; python -m playwright install chromium"
        }
    }
    finally {
        if ($null -eq $previousSiteDirectory) {
            Remove-Item Env:SITE_DIRECTORY -ErrorAction SilentlyContinue
        }
        else {
            $env:SITE_DIRECTORY = $previousSiteDirectory
        }

        if ($null -eq $previousQaDirectory) {
            Remove-Item Env:QA_DIRECTORY -ErrorAction SilentlyContinue
        }
        else {
            $env:QA_DIRECTORY = $previousQaDirectory
        }
    }
}

function Wait-ForPublicSite {
    param(
        [Parameter(Mandatory = $true)][string]$LocalIndexPath,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    Add-Type -AssemblyName System.Net.Http
    $localHash = Get-Sha256Hex -Bytes ([IO.File]::ReadAllBytes($LocalIndexPath))
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $client = New-Object System.Net.Http.HttpClient
    $client.Timeout = [TimeSpan]::FromSeconds(20)

    try {
        while ((Get-Date) -lt $deadline) {
            $cacheBust = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
            $checkUrl = "${publicUrl}index.html?v=${cacheBust}"

            try {
                $response = $client.GetAsync($checkUrl).GetAwaiter().GetResult()
                if ($response.IsSuccessStatusCode) {
                    $remoteBytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
                    $remoteHash = Get-Sha256Hex -Bytes $remoteBytes
                    if ($remoteHash -eq $localHash) {
                        Write-Host "Public site matches the local index." -ForegroundColor Green
                        return
                    }
                }
            }
            catch {
                Write-Host "Deployment check is still waiting: $($_.Exception.Message)" -ForegroundColor DarkYellow
            }

            Write-Host "Waiting for GitHub Pages deployment..."
            Start-Sleep -Seconds 8
        }
    }
    finally {
        $client.Dispose()
    }

    throw "Timed out after $TimeoutSeconds seconds. Check the Actions tab in GitHub, then open $publicUrl"
}

Push-Location $projectRoot
try {
    foreach ($requiredPath in @(
        (Join-Path $projectRoot ".git"),
        (Join-Path $siteRoot "index.html"),
        (Join-Path $siteRoot "assets\site.css"),
        (Join-Path $siteRoot "assets\site.js")
    )) {
        if (-not (Test-Path -LiteralPath $requiredPath)) {
            throw "Required project path not found: $requiredPath"
        }
    }

    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git was not found in PATH."
    }

    $branch = (& git rev-parse --abbrev-ref HEAD | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to read the current Git branch."
    }
    if ($branch -ne "main") {
        throw "Current branch is '$branch'. Switch to main before publishing."
    }

    $conflicts = @(& git diff --name-only --diff-filter=U)
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to check for unresolved Git conflicts."
    }
    if ($conflicts.Count -gt 0) {
        throw "Resolve Git conflicts before publishing: $($conflicts -join ', ')"
    }

    Test-LocalAssetReferences -IndexPath (Join-Path $siteRoot "index.html")

    if ($SkipTests) {
        Write-Host "Browser QA skipped by request." -ForegroundColor DarkYellow
    }
    else {
        Write-Host "Running browser QA..."
        Invoke-SiteQa
        Write-Host "Browser QA passed." -ForegroundColor Green
    }

    Invoke-Git -Arguments @("add", "--", "site")
    & git diff --cached --quiet -- site
    $diffExitCode = $LASTEXITCODE

    if ($diffExitCode -eq 1) {
        if ([string]::IsNullOrWhiteSpace($Message)) {
            $Message = "Update website $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        }

        Invoke-Git -Arguments @("commit", "-m", $Message)
        Invoke-Git -Arguments @("push", "origin", "main")
        Write-Host "Changes pushed to origin/main." -ForegroundColor Green
    }
    elseif ($diffExitCode -eq 0) {
        Write-Host "No website changes to commit. Verifying the current public copy."
    }
    else {
        throw "Unable to inspect staged website changes."
    }

    Wait-ForPublicSite -LocalIndexPath (Join-Path $siteRoot "index.html") -TimeoutSeconds $PublishTimeoutSeconds
    Write-Host "Published successfully: $publicUrl" -ForegroundColor Cyan
}
finally {
    Pop-Location
}
