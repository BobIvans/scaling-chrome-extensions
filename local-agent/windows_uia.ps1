param(
  [Parameter(Mandatory=$true)][ValidateSet('Inventory','Act')][string]$Mode,
  [Parameter(Mandatory=$true)][string]$RequestJson
)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class AgentOSUser32 {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
"@
function Out-Json($value){ $value | ConvertTo-Json -Depth 12 -Compress }
function Runtime-Key($el){
  try { return (($el.GetRuntimeId() | ForEach-Object { [string]$_ }) -join '.') } catch { return '' }
}
function Window-Element($req){
  $hwnd=[IntPtr]::Zero
  if($req.hwnd){$hwnd=[IntPtr][int64]$req.hwnd}else{$hwnd=[AgentOSUser32]::GetForegroundWindow()}
  if($hwnd -eq [IntPtr]::Zero){throw 'WINDOWS_UI_NO_FOREGROUND'}
  $el=[System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
  if($null -eq $el){throw 'WINDOWS_UI_WINDOW_UNAVAILABLE'}
  return @{Hwnd=$hwnd;Element=$el}
}
function Pattern-Flags($el){
  $names=New-Object System.Collections.Generic.List[string]
  $p=$null
  if($el.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$p)){$names.Add('Invoke')}
  if($el.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$p)){$names.Add('Value')}
  if($el.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$p)){$names.Add('ExpandCollapse')}
  if($el.TryGetCurrentPattern([System.Windows.Automation.ScrollItemPattern]::Pattern,[ref]$p)){$names.Add('ScrollItem')}
  if($el.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern,[ref]$p)){$names.Add('Toggle')}
  if($el.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern,[ref]$p)){$names.Add('SelectionItem')}
  if($el.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern,[ref]$p)){$names.Add('Text')}
  return @($names)
}
function Element-Row($el,$hwnd){
  $c=$el.Current
  $r=$c.BoundingRectangle
  $value=''
  $text=''
  $p=$null
  try{
    if($el.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$p)){
      $value=[string]([System.Windows.Automation.ValuePattern]$p).Current.Value
      if($value.Length -gt 2000){$value=$value.Substring(0,2000)}
    }
  }catch{}
  try{
    if($el.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern,[ref]$p)){
      $text=[string]([System.Windows.Automation.TextPattern]$p).DocumentRange.GetText(4000)
      if($text.Length -gt 4000){$text=$text.Substring(0,4000)}
    }
  }catch{}
  return [ordered]@{
    runtime_id=(Runtime-Key $el)
    hwnd=[int64]$hwnd
    process_id=[int]$c.ProcessId
    control_type=[string]$c.ControlType.ProgrammaticName
    name=[string]$c.Name
    automation_id=[string]$c.AutomationId
    class_name=[string]$c.ClassName
    enabled=[bool]$c.IsEnabled
    offscreen=[bool]$c.IsOffscreen
    is_password=[bool]$c.IsPassword
    rect=@{x=[double]$r.X;y=[double]$r.Y;width=[double]$r.Width;height=[double]$r.Height}
    patterns=(Pattern-Flags $el)
    value=$value
    text=$text
  }
}
function Find-Runtime($root,$key){
  if((Runtime-Key $root) -eq $key){return $root}
  $all=$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
  $limit=[Math]::Min($all.Count,5000)
  for($i=0;$i -lt $limit;$i++){if((Runtime-Key $all.Item($i)) -eq $key){return $all.Item($i)}}
  return $null
}
try{
  $req=$RequestJson | ConvertFrom-Json
  $w=Window-Element $req
  $root=$w.Element;$hwnd=$w.Hwnd
  if($Mode -eq 'Inventory'){
    $rows=New-Object System.Collections.Generic.List[object]
    $rows.Add((Element-Row $root $hwnd))
    $all=$root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
    $requested=1200;if($null -ne $req.max_elements){$requested=[int]$req.max_elements};$limit=[Math]::Min($all.Count,[Math]::Min(3000,$requested))
    for($i=0;$i -lt $limit;$i++){
      $el=$all.Item($i);$row=Element-Row $el $hwnd
      if(-not $row.offscreen -and ($row.name -or $row.value -or $row.text -or $row.patterns.Count -gt 0)){$rows.Add($row)}
    }
    Out-Json ([ordered]@{ok=$true;hwnd=[int64]$hwnd;window=(Element-Row $root $hwnd);elements=@($rows)})
    exit 0
  }
  $key=[string]$req.runtime_id
  if(-not $key){throw 'WINDOWS_UI_RUNTIME_ID_REQUIRED'}
  $el=Find-Runtime $root $key
  if($null -eq $el){throw 'WINDOWS_UI_ELEMENT_STALE'}
  $row=Element-Row $el $hwnd
  foreach($field in @('process_id','control_type','automation_id','class_name','name')){
    if($req.expected.$field -ne $null -and [string]$req.expected.$field -ne [string]$row.$field){throw 'WINDOWS_UI_ELEMENT_DRIFT'}
  }
  if(-not $row.enabled -or $row.offscreen){throw 'WINDOWS_UI_ELEMENT_UNAVAILABLE'}
  if($req.action -eq 'invoke'){
    $p=$null
    if(-not $el.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern,[ref]$p)){throw 'WINDOWS_UI_INVOKE_UNSUPPORTED'}
    ([System.Windows.Automation.InvokePattern]$p).Invoke()
    Out-Json ([ordered]@{ok=$true;state='WINDOWS_UI_INVOKE_INVOKED';before=$row;desired_outcome_verified=$false})
    exit 0
  }
  if($req.action -eq 'expand'){
    $p=$null
    if(-not $el.TryGetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern,[ref]$p)){throw 'WINDOWS_UI_EXPAND_UNSUPPORTED'}
    ([System.Windows.Automation.ExpandCollapsePattern]$p).Expand()
    Out-Json ([ordered]@{ok=$true;state='WINDOWS_UI_EXPANDED';before=$row;desired_outcome_verified=$false})
    exit 0
  }
  if($req.action -eq 'scroll_into_view'){
    $p=$null
    if(-not $el.TryGetCurrentPattern([System.Windows.Automation.ScrollItemPattern]::Pattern,[ref]$p)){throw 'WINDOWS_UI_SCROLL_UNSUPPORTED'}
    ([System.Windows.Automation.ScrollItemPattern]$p).ScrollIntoView()
    Out-Json ([ordered]@{ok=$true;state='WINDOWS_UI_SCROLLED';before=$row;desired_outcome_verified=$false})
    exit 0
  }
  if($req.action -eq 'set_value'){
    if($row.is_password){throw 'WINDOWS_UI_PASSWORD_BLOCKED'}
    $value=[string]$req.value
    if($value.Length -gt 100000){throw 'WINDOWS_UI_VALUE_LIMIT'}
    $p=$null
    if(-not $el.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern,[ref]$p)){throw 'WINDOWS_UI_VALUE_UNSUPPORTED'}
    ([System.Windows.Automation.ValuePattern]$p).SetValue($value)
    $after=Element-Row $el $hwnd
    if([string]$after.value -ne $value){throw 'WINDOWS_UI_VALUE_READBACK_MISMATCH'}
    Out-Json ([ordered]@{ok=$true;state='WINDOWS_UI_VALUE_VERIFIED';before=$row;after=$after;desired_outcome_verified=$false})
    exit 0
  }
  throw 'WINDOWS_UI_ACTION_UNSUPPORTED'
}catch{
  Out-Json ([ordered]@{ok=$false;error=[string]$_.Exception.Message})
  exit 2
}
