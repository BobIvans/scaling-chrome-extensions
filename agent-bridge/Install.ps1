param(
 [Parameter(Mandatory=$true)][ValidatePattern('^[a-p]{32}$')][string]$ExtensionId,
 [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$PackageTreeSha256,
 [Parameter(Mandatory=$true)][ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?$')][string]$ExtensionVersion,
 [string]$Destination=(Join-Path $env:LOCALAPPDATA 'OneClickContextAgent'),
 [switch]$Register
)
$ErrorActionPreference='Stop'
$occNode=(Get-Command node.exe -ErrorAction Stop).Source
$occCodex=(Get-Command codex.exe -ErrorAction Stop).Source
$occCompiler=Join-Path $env:WINDIR 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
if(!(Test-Path -LiteralPath $occCompiler)){throw 'C# compiler unavailable. Native host was not registered.'}
$occDestination=[IO.Path]::GetFullPath($Destination)
if(Test-Path -LiteralPath $occDestination){throw 'Destination already exists. Use another explicit directory; existing installs are never overwritten.'}
New-Item -ItemType Directory -Path $occDestination | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'host.mjs') -Destination $occDestination
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'durable.mjs') -Destination $occDestination
# Preserve the adapter's sibling layout. Durable access remains opt-in in host-config.json.
$occContentDestination=Join-Path $occDestination 'content-lab'
New-Item -ItemType Directory -Path $occContentDestination | Out-Null
foreach($occFile in @('native_adapter.py','automation_core.py','content_lab.py')){
 Copy-Item -LiteralPath (Join-Path (Join-Path $PSScriptRoot '../content-lab') $occFile) -Destination $occContentDestination
}
& $occCompiler /nologo /target:exe /reference:System.Web.Extensions.dll "/out:$occDestination/occ-native-host.exe" (Join-Path $PSScriptRoot 'NativeHost.cs')
if($LASTEXITCODE -ne 0){throw 'Compilation failed; registry unchanged.'}
$occConfig=@{extensionId=$ExtensionId;extensionVersion=$ExtensionVersion;packageTreeSha256=$PackageTreeSha256;nodePath=$occNode;codexPath=$occCodex;dataRoot=(Join-Path $occDestination 'jobs')}
[IO.File]::WriteAllText((Join-Path $occDestination 'host-config.json'),($occConfig|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
$occManifest=@{name='com.one_click_context.codex';description='Explicit One Click Context jobs through the local Codex CLI';path=(Join-Path $occDestination 'occ-native-host.exe');type='stdio';allowed_origins=@("chrome-extension://$ExtensionId/")}
$occManifestPath=Join-Path $occDestination 'native-host.json'
[IO.File]::WriteAllText($occManifestPath,($occManifest|ConvertTo-Json),[Text.UTF8Encoding]::new($false))
if($Register){
 $occRegistry='HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.one_click_context.codex'
 if(Test-Path -LiteralPath $occRegistry){throw 'A native host is already registered. Existing registration was not changed.'}
 New-Item -Path $occRegistry -Force | Out-Null
 Set-Item -LiteralPath $occRegistry -Value $occManifestPath
 Write-Output 'Registered for the single supplied extension ID in this Windows user account.'
}else{Write-Output 'Prepared only. Chrome registration was not changed. Review native-host.json before explicitly registering.'}
Write-Output $occDestination
