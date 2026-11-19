<div align="center">
  <img src="assets/razerd.png" width="96" alt="" />
  <h1>razerd</h1>
  <p>Native Linux control suite for Razer peripherals, built on <a href="https://openrazer.github.io">OpenRazer</a>.</p>
  <p>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0--or--later-000000?style=flat-square&labelColor=1f1f1f" alt="License" /></a>
    <a href="#requirements"><img src="https://img.shields.io/badge/platform-Linux-000000?style=flat-square&labelColor=1f1f1f" alt="Platform" /></a>
    <a href="#architecture"><img src="https://img.shields.io/badge/stack-Electron%20%C2%B7%20Vue-000000?style=flat-square&labelColor=1f1f1f" alt="Stack" /></a>
  </p>
</div>

---

A high-precision, native Electron desktop application with a monochrome, typography-led interface.

## Features

- **Peripheral auto-detection and management:**
  - Real-time enumeration of all attached Razer peripherals via the OpenRazer D-Bus daemon.
  - Support for mice (e.g. Viper V3 Pro, Pro Click V2), keyboards (Huntsman, BlackWidow), addressable ARGB controllers, mousemats, and keypads.
  - Live battery percentage and charging state indicators.
  - Firmware, driver version, and hardware serial tracking.
- **Sensitivity and DPI:**
  - X and Y axis sensitivity adjustment (linked or independent).
  - 5 configurable hardware DPI stages with active stage selection.
  - One-click quick presets (400, 800, 1600, 3200, 6400, Max DPI).
- **HyperPolling and refresh rates:**
  - 125 Hz, 500 Hz, 1000 Hz, 2000 Hz, 4000 Hz, and 8000 Hz HyperPolling.
  - Real-time latency calculations (e.g. 0.125 ms at 8000 Hz).
- **Chroma lighting and effects:**
  - Hardware brightness slider (0% to 100%) with an instant mute toggle.
  - Effect modes: Static, Breathing (Single, Dual, Random), Spectrum Cycling, Wave (Directional), Reactive, Ripple, Starlight, and Off.
  - Multi-zone addressing: Overall, Logo, Scroll Wheel, Side Strips, and Backlight.
  - "Sync RGB to All": one-click synchronization across all connected peripherals.
- **Interactive LED matrix editor:**
  - Custom per-LED matrix drawing canvas for keyboards and ARGB controllers.
  - Active color brush, palette swatches, fill all, and clear tools.
- **Power management:**
  - Low battery alert threshold slider (5% to 30%).
  - Standby sleep inactivity timeout slider (1 to 15 minutes).
  - Energy capacity bar and charging status.
- **Profile presets:**
  - Save, activate, export, and import hardware profiles in JSON format.
  - Preloaded with Competitive FPS, Stealth Night, Studio Work, and Chroma Neon profiles.
- **System health and troubleshooter:**
  - Real-time checks of the OpenRazer D-Bus service, Python client libraries, kernel DKMS modules (`razerkbd`, `razermouse`, `razeraccessory`), and user `plugdev` group membership.
  - In-app OpenRazer daemon restart button.
- **Hardware simulator mode:** a simulation toggle for exploring every feature and testing the UI without physical hardware connected.

## Design principles

razerd replaces the legacy Qt-based widget layout with an intentional, monochrome interface inspired by Coder and Ollama:

1. **Black first:** true black (`#000000`) canvas. Depth comes from subtle hairlines (`#1f1f1f`) and near-black surfaces (`#0a0a0a`), never drop shadows or colored ambient glows.
2. **Colour is information:** the UI itself is strictly monochrome. Color appears only in status badges (green/amber/red) or when directly manipulating RGB Chroma values.
3. **Type does the work:** built with Geist Variable and Geist Mono Variable. Hierarchy comes from size and contrast. Hero metrics (DPI, polling rate, battery) use tabular numerals.
4. **Fewer boxes:** whitespace and hairline dividers instead of nested cards.
5. **Quiet precision:** everything aligns to a 4 px grid, with 120 ms transitions on color and opacity only.

## Requirements

- Node.js >= 22
- Python 3 with the `openrazer` library installed
- OpenRazer daemon running (`systemctl --user status openrazer-daemon.service`)

## Usage

```bash
# Install dependencies
npm install
# Run backend verification test
npm test
# Build production bundle
npm run build
# Start the desktop application
npm start
```

## Build from source

### Running with the dev server

```bash
# Terminal 1: start the Vite dev server
npm run dev

# Terminal 2: launch Electron pointing to the dev server
VITE_DEV_SERVER_URL=http://localhost:5173 electron .
```

### Architecture

- **Frontend:** Vue 3 (Composition API) + Vite, with bundled `@fontsource-variable/geist` and `@fontsource-variable/geist-mono` for zero external network calls.
- **Backend bridge:** a lightweight Python daemon bridge (`src/bridge/bridge.py`) interfacing with `openrazer.client.DeviceManager()`, communicating with Electron over bidirectional JSON-RPC.
- **Desktop runtime:** Electron 44 with context isolation and typed IPC channels.

## License

GPL-3.0-or-later, see [LICENSE](LICENSE). Based in part on Polychromatic (GPL-3.0-or-later).
