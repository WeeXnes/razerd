#!/usr/bin/env node
import fs from 'fs';
import os from 'os';
import path from 'path';
import { execSync } from 'child_process';

const projectDir = path.resolve(import.meta.dirname, '..');
const homeDir = os.homedir();

const xdgDataHome = process.env.XDG_DATA_HOME || path.join(homeDir, '.local', 'share');
const localBinDir = path.join(homeDir, '.local', 'bin');
const applicationsDir = path.join(xdgDataHome, 'applications');
const hicolorScalableDir = path.join(xdgDataHome, 'icons', 'hicolor', 'scalable', 'apps');
const flatIconsDir = path.join(xdgDataHome, 'icons');

const launcherPath = path.join(localBinDir, 'razerd');
const desktopEntryPath = path.join(applicationsDir, 'razerd.desktop');
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
  console.log('Uninstalling razerd desktop entry & launcher...');
  safeUnlink(launcherPath);
  safeUnlink(desktopEntryPath);
  safeUnlink(iconDestPath);
  safeUnlink(flatIconDestPath);
  refreshDesktopDatabase();
  console.log('✓ Uninstalled razerd desktop shortcut.');
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
Keywords=razer;razerd;openrazer;rgb;chroma;dpi;mouse;keyboard;polychromatic;led;
StartupWMClass=razerd
StartupNotify=true
`;

fs.writeFileSync(desktopEntryPath, desktopEntryContent, { mode: 0o755 });
fs.chmodSync(desktopEntryPath, 0o755);
console.log(`✓ Installed desktop shortcut:  ${desktopEntryPath}`);

// 6. Refresh desktop database for application launchers (Rofi, Wofi, Fuzzel, KDE, GNOME)
refreshDesktopDatabase();

console.log('\n✓ RazerD is now installed in your Linux application menu (Rofi / Wofi / Desktop)!');
console.log('  • Search for "RazerD" or "razer" in Rofi (rofi -show drun)');
console.log(`  • Or launch directly from terminal via: ${launcherPath}`);
