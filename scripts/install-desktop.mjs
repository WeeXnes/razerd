#!/usr/bin/env node
import fs from 'fs';
import os from 'os';
import path from 'path';
import { execSync } from 'child_process';

const projectDir = path.resolve(import.meta.dirname, '..');
const homeDir = os.homedir();

const xdgDataHome = process.env.XDG_DATA_HOME || path.join(homeDir, '.local', 'share');
const xdgConfigHome = process.env.XDG_CONFIG_HOME || path.join(homeDir, '.config');
const localBinDir = path.join(homeDir, '.local', 'bin');
const applicationsDir = path.join(xdgDataHome, 'applications');
const autostartDir = path.join(xdgConfigHome, 'autostart');
const systemdUserDir = path.join(xdgConfigHome, 'systemd', 'user');
const hicolorScalableDir = path.join(xdgDataHome, 'icons', 'hicolor', 'scalable', 'apps');
const flatIconsDir = path.join(xdgDataHome, 'icons');

const launcherPath = path.join(localBinDir, 'razerd');
const desktopEntryPath = path.join(applicationsDir, 'razerd.desktop');
const autostartEntryPath = path.join(autostartDir, 'razerd.desktop');
const polyAutostartPath = path.join(autostartDir, 'polychromatic-autostart.desktop');
const systemdServicePath = path.join(systemdUserDir, 'razerd.service');
const iconDestPath = path.join(hicolorScalableDir, 'razerd.svg');
const flatIconDestPath = path.join(flatIconsDir, 'razerd.svg');
const iconSrcPath = path.join(projectDir, 'assets', 'razerd.svg');
const runElectronScript = path.join(projectDir, 'scripts', 'run-electron.sh');

const isUninstall = process.argv.includes('--uninstall') || process.argv.includes('-u');

function safeUnlink(targetPath) {
  if (fs.existsSync(targetPath)) {
    fs.unlinkSync(targetPath);
    console.log(`Removed: ${targetPath}`);
  }
}

function refreshDesktopDatabase() {
  try {
    execSync(`update-desktop-database "${applicationsDir}"`, { stdio: 'ignore' });
  } catch {
    // update-desktop-database is optional
  }
}

if (isUninstall) {
  console.log('Uninstalling razerd desktop entry, autostart & launcher...');
  safeUnlink(launcherPath);
  safeUnlink(desktopEntryPath);
  safeUnlink(autostartEntryPath);
  try {
    execSync('systemctl --user disable razerd.service', { stdio: 'ignore' });
  } catch {}
  safeUnlink(systemdServicePath);
  safeUnlink(iconDestPath);
  safeUnlink(flatIconDestPath);
  refreshDesktopDatabase();
  console.log('✓ Uninstalled razerd desktop shortcut and autostart.');
  process.exit(0);
}

console.log('=== Installing razerd Desktop & Rofi Menu Entry ===');

// 1. Ensure scripts/run-electron.sh is executable
if (fs.existsSync(runElectronScript)) {
  fs.chmodSync(runElectronScript, 0o755);
}

// 2. Build production frontend bundle so standalone desktop launch works immediately
console.log('Building production UI bundle (dist/)...');
execSync('npm run build', { cwd: projectDir, stdio: 'inherit' });

// 3. Install ~/.local/bin/razerd CLI wrapper
fs.mkdirSync(localBinDir, { recursive: true });
const wrapperContent = `#!/usr/bin/env bash
exec "${runElectronScript}" "$@"
`;
fs.writeFileSync(launcherPath, wrapperContent, { mode: 0o755 });
fs.chmodSync(launcherPath, 0o755);
console.log(`✓ Installed CLI launcher:      ${launcherPath}`);

// 4. Install SVG application icon into XDG hicolor & flat icon paths
if (fs.existsSync(iconSrcPath)) {
  fs.mkdirSync(hicolorScalableDir, { recursive: true });
  fs.mkdirSync(flatIconsDir, { recursive: true });
  fs.copyFileSync(iconSrcPath, iconDestPath);
  fs.copyFileSync(iconSrcPath, flatIconDestPath);
  console.log(`✓ Installed application icon:  ${iconDestPath}`);
}

// 5. Create ~/.local/share/applications/razerd.desktop for Rofi / Wofi / Linux application menus
fs.mkdirSync(applicationsDir, { recursive: true });
const desktopEntryContent = `[Desktop Entry]
Version=1.0
Type=Application
Name=RazerD
GenericName=Razer Hardware & RGB Control
Comment=Modern Linux native peripheral control suite for Razer hardware (OpenRazer)
Exec=${launcherPath} %U
TryExec=${launcherPath}
Path=${projectDir}
Icon=${iconDestPath}
Terminal=false
Categories=Settings;HardwareSettings;Utility;System;
Keywords=razer;razerd;openrazer;rgb;chroma;dpi;mouse;keyboard;led;
StartupWMClass=razerd
StartupNotify=true
`;

fs.writeFileSync(desktopEntryPath, desktopEntryContent, { mode: 0o755 });
fs.chmodSync(desktopEntryPath, 0o755);
console.log(`✓ Installed desktop shortcut:  ${desktopEntryPath}`);

// 6. Disable Polychromatic autostart and enable RazerD minimized tray autostart
fs.mkdirSync(autostartDir, { recursive: true });
fs.writeFileSync(
  polyAutostartPath,
  `[Desktop Entry]\nType=Application\nName=Polychromatic Autostart\nExec=polychromatic-helper --autostart\nHidden=true\nX-GNOME-Autostart-enabled=false\n`
);
try {
  execSync('systemctl --user disable --now polychromatic.service', { stdio: 'ignore' });
} catch {}

// Remove duplicate XDG autostart entry so systemd user service is the single clean launcher
safeUnlink(autostartEntryPath);

fs.mkdirSync(systemdUserDir, { recursive: true });
const systemdContent = `[Unit]
Description=RazerD Background Hardware Controller & Tray Applet
PartOf=graphical-session.target
After=graphical-session.target openrazer-daemon.service waybar.service
Wants=openrazer-daemon.service

[Service]
Type=simple
ExecStartPre=/bin/sh -c 'for i in $(seq 1 30); do busctl --user list 2>/dev/null | grep -q "StatusNotifierWatcher" && busctl --user list 2>/dev/null | grep -q "org.razer" && break; sleep 0.5; done'
ExecStart=${launcherPath} --minimized
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical-session.target
`;
fs.writeFileSync(systemdServicePath, systemdContent);
try {
  execSync('systemctl --user daemon-reload && systemctl --user enable razerd.service', { stdio: 'ignore' });
  console.log(`✓ Enabled systemd autostart:   ${systemdServicePath}`);
} catch {}

// 7. Refresh desktop database for application launchers (Rofi, Wofi, Fuzzel, KDE, GNOME)
refreshDesktopDatabase();

console.log('\n✓ RazerD is now installed in your Linux application menu & configured to autostart minimized in the system tray!');
console.log('  • Search for "RazerD" or "razer" in Rofi (rofi -show drun)');
console.log(`  • Or launch directly from terminal via: ${launcherPath}`);
