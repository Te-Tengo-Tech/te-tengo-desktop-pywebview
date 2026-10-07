# Installation guide (project team)

## Start with the system

The window says «Se inicia con Windows»: the agent must start on its own when the household PC is turned on.

### Windows
Nothing to do. On every start, the packaged agent (`te-tengo-captura.exe`) writes or updates a per-user entry in the registry:

```
HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run
  TeTengoCaptura = "C:\…\te-tengo-captura.exe"
```

To check it: `reg query HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v TeTengoCaptura`. To remove it (uninstall): `reg delete HKCU\Software\Microsoft\Windows\CurrentVersion\Run /v TeTengoCaptura /f`. When run from source (`uv run te-tengo-captura`) nothing is written.

### macOS (LaunchAgent)
Save as `~/Library/LaunchAgents/pe.tetengo.captura.plist`, adjusting the path, and load it with `launchctl load ~/Library/LaunchAgents/pe.tetengo.captura.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>pe.tetengo.captura</string>
  <key>ProgramArguments</key>
  <array><string>/Applications/TeTengoCaptura/te-tengo-captura</string></array>
  <key>RunAtLoad</key><true/>
</dict>
</plist>
```

### Linux (autostart `.desktop`)
Save as `~/.config/autostart/te-tengo-captura.desktop`, adjusting the path:

```ini
[Desktop Entry]
Type=Application
Name=Te Tengo Captura
Exec=/opt/te-tengo-captura/te-tengo-captura
X-GNOME-Autostart-enabled=true
```

## Only one agent

Opening the program again (from the Start menu or a desktop shortcut) does not start a second agent: it shows the window of the one already running. The running agent holds a lock on `instancia.lock` in its data directory.
