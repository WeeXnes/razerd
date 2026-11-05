# razerd

A modern, high-precision Linux native peripheral management suite for Razer hardware, built on top of [OpenRazer](https://openrazer.github.io).

Re-engineered from [Polychromatic](https://polychromatic.app) into a native Electron desktop application, following the monochrome, typography-led design system defined in `DESIGN.md` (OpenProStreet design principles).

---

## Design Principles

RazerD replaces the legacy Qt-based widget layout with an intentional, monochrome interface inspired by Coder and Ollama:

1. **Black first:** True black (`#000000`) canvas. Depth emerges from subtle hairlines (`#1f1f1f`) and near-black surfaces (`#0a0a0a`), never drop shadows or colored ambient glows.
2. **Colour is information:** The UI itself is strictly monochrome. Color appears solely for status badges (green/amber/red) or when directly manipulating RGB Chroma values.
3. **Type does the work:** Built with Geist Variable and Geist Mono Variable. Hierarchy is established through size and contrast. Hero metrics (DPI, Polling Rate, Battery) are presented in clean tabular numerals.
4. **Fewer boxes:** Clean whitespace and hairline dividers instead of nested card clutter.
5. **Quiet precision:** Everything aligns to a 4px grid with 120ms transitions on color and opacity only.

---

## Features

- **Peripheral Auto-Detection & Management:**
  - Real-time enumeration of all attached Razer peripherals via the OpenRazer D-Bus daemon.
  - Full support for mice (e.g. Viper V3 Pro, Pro Click V2), keyboards (Huntsman, BlackWidow), addressable ARGB controllers, mousemats, and keypads.
  - Live battery percentage and charging state indicators.
  - Firmware, driver version, and hardware serial tracking.

- **Sensitivity & DPI Configuration:**
  - Dynamic X and Y axis sensitivity adjustment (linked or independent).
  - 5 configurable hardware DPI stages with active stage selection.
  - One-click quick presets (400, 800, 1600, 3200, 6400, Max DPI).

- **HyperPolling & Refresh Rates:**
  - Complete support for 125 Hz, 500 Hz, 1000 Hz, 2000 Hz, 4000 Hz, and 8000 Hz HyperPolling.
  - Real-time latency calculations (e.g., 0.125ms at 8000 Hz).

- **Chroma Lighting & Effects:**
  - Full hardware brightness slider (0% to 100%) with instant mute toggle.
  - Effect modes: Static, Breathing (Single, Dual, Random), Spectrum Cycling, Wave (Directional), Reactive, Ripple, Starlight, and Off.
  - Multi-zone addressing: Overall, Logo, Scroll Wheel, Side Strips, and Backlight.
  - "Sync RGB to All": One-click synchronization across all connected peripherals.

- **Interactive LED Matrix Editor:**
  - Custom per-LED matrix drawing canvas for keyboards and ARGB controllers.
  - Active color brush, palette swatches, fill all, and clear tools.

- **Power Management:**
  - Low battery alert threshold slider (5% to 30%).
  - Standby sleep inactivity timeout slider (1 to 15 minutes).
  - Displays energy capacity bar and charging status.

- **Profile Presets:**
  - Save, activate, export, and import custom hardware profiles in JSON format.
  - Preloaded with Competitive FPS, Stealth Night, Studio Work, and Chroma Neon profiles.

- **System Health & Troubleshooter:**
  - Real-time diagnostic verification of OpenRazer D-Bus service, Python client libraries, kernel DKMS modules (`razerkbd`, `razermouse`, `razeraccessory`), and user `plugdev` group membership.
  - In-app OpenRazer daemon restart button.

- **Hardware Simulator Mode:**
  - Built-in simulation toggle allows full feature exploration and UI testing even without physical hardware connected.

---

## Architecture

- **Frontend:** Vue 3 (Composition API) + Vite with bundled `@fontsource-variable/geist` and `@fontsource-variable/geist-mono` for zero external network calls.
- **Backend Bridge:** Lightweight Python daemon bridge (`src/bridge/bridge.py`) interfacing with `openrazer.client.DeviceManager()`, communicating with Electron over bidirectional JSON-RPC.
- **Desktop Runtime:** Electron 44 with secure context isolation and typed IPC channels.

---

## Development & Usage

### Prerequisites

- Node.js >= 22
- Python 3 with `openrazer` library installed
- OpenRazer daemon running (`systemctl --user status openrazer-daemon.service`)

### Quick Start

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

### Running with Dev Server

```bash
# Terminal 1: Start Vite dev server
npm run dev

# Terminal 2: Launch Electron pointing to dev server
VITE_DEV_SERVER_URL=http://localhost:5173 electron .
```

---

## License

GPL-3.0-or-later. Derived and re-architected from Polychromatic.
