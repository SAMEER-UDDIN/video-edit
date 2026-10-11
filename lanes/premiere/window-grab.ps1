# window-grab.ps1 — Windows counterpart of workflows/window-grab.sh: screenshot an app's main window
# WITHOUT fronting it. PrintWindow flag 2 (PW_RENDERFULLCONTENT) includes GPU-drawn panels such as
# Premiere's Program monitor.
#   powershell -ExecutionPolicy Bypass -File lanes/premiere/window-grab.ps1 -Out C:\path\premiere.png [-Process "Adobe Premiere Pro*"]
param([Parameter(Mandatory = $true)][string]$Out, [string]$Process = "Adobe Premiere Pro*")
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WGrab {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
"@
$p = Get-Process | Where-Object { $_.ProcessName -like $Process -and $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { Write-Error "no window for $Process"; exit 1 }
$r = New-Object WGrab+RECT
[void][WGrab]::GetWindowRect($p.MainWindowHandle, [ref]$r)
$bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$dc = $g.GetHdc()
$ok = [WGrab]::PrintWindow($p.MainWindowHandle, $dc, 2)
$g.ReleaseHdc($dc); $g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
"$($p.ProcessName) $($r.R - $r.L)x$($r.B - $r.T) PrintWindow=$ok -> $Out"
