#!/usr/bin/env python3
"""
razerd Python Daemon Bridge
Interfaces with openrazer.client and Linux evdev to provide real-time control,
button remapping, monitoring, and diagnostics for Razer hardware.
"""

import sys
import os
import glob
import json
import time
import struct
import select
import fcntl
import atexit
import signal
import math
import colorsys
import threading
import traceback
import subprocess
import configparser

try:
    import openrazer.client
    import dbus
    HAS_OPENRAZER = True
except ImportError:
    HAS_OPENRAZER = False

# Linux input_event constants (64-bit: timeval sec(l), usec(l), type(H), code(H), value(i) = 24 bytes)
EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)
EVIOCGRAB = 0x40044590

EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_MSC = 0x04

SYN_REPORT = 0x00
REL_WHEEL = 0x08
REL_WHEEL_HI_RES = 0x0B

# Mouse button evdev codes
MOUSE_BUTTON_CODES = {
    "btn_left": 272,
    "btn_right": 273,
    "btn_middle": 274,
    "btn_side": 275,
    "btn_extra": 276,
    "btn_forward": 277,
}
CODE_TO_MOUSE_BUTTON = {v: k for k, v in MOUSE_BUTTON_CODES.items()}

# Linux KEY_* table for keyboard/media injection
KEY_CODES = {
    "ESC": 1, "ESCAPE": 1,
    "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
    "MINUS": 12, "EQUAL": 13, "BACKSPACE": 14, "TAB": 15,
    "Q": 16, "W": 17, "E": 18, "R": 19, "T": 20, "Y": 21, "U": 22, "I": 23, "O": 24, "P": 25,
    "LEFTBRACE": 26, "RIGHTBRACE": 27, "ENTER": 28, "LEFTCTRL": 29, "CTRL": 29,
    "A": 30, "S": 31, "D": 32, "F": 33, "G": 34, "H": 35, "J": 36, "K": 37, "L": 38,
    "SEMICOLON": 39, "APOSTROPHE": 40, "GRAVE": 41, "LEFTSHIFT": 42, "SHIFT": 42, "BACKSLASH": 43,
    "Z": 44, "X": 45, "C": 46, "V": 47, "B": 48, "N": 49, "M": 50,
    "COMMA": 51, "DOT": 52, "SLASH": 53, "RIGHTSHIFT": 54, "KPASTERISK": 55,
    "LEFTALT": 56, "ALT": 56, "SPACE": 57, "CAPSLOCK": 58,
    "F1": 59, "F2": 60, "F3": 61, "F4": 62, "F5": 63, "F6": 64, "F7": 65, "F8": 66, "F9": 67, "F10": 68,
    "NUMLOCK": 69, "SCROLLLOCK": 70,
    "F11": 87, "F12": 88,
    "RIGHTCTRL": 97, "RIGHTALT": 100,
    "HOME": 102, "UP": 103, "PAGEUP": 104, "LEFT": 105, "RIGHT": 106, "END": 107, "DOWN": 108, "PAGEDOWN": 109,
    "INSERT": 110, "DELETE": 111,
    "MUTE": 113, "VOLUMEDOWN": 114, "VOLUMEUP": 115,
    "LEFTMETA": 125, "SUPER": 125, "META": 125, "WIN": 125,
    "NEXTSONG": 163, "PLAYPAUSE": 164, "PREVIOUSSONG": 165, "STOPCD": 166,
    "F13": 183, "F14": 184, "F15": 185, "F16": 186, "F17": 187, "F18": 188,
    "F19": 189, "F20": 190, "F21": 191, "F22": 192, "F23": 193, "F24": 194,
}

MEDIA_KEY_MAP = {
    "volume_up": 115,
    "volume_down": 114,
    "mute": 113,
    "play_pause": 164,
    "next_track": 163,
    "prev_track": 165,
}

DEFAULT_MOUSE_BUTTONS = [
    {"id": "btn_left", "label": "Left Click (Button 1)", "action": "default", "value": ""},
    {"id": "btn_right", "label": "Right Click (Button 2)", "action": "default", "value": ""},
    {"id": "btn_middle", "label": "Middle Click (Scroll Press)", "action": "default", "value": ""},
    {"id": "btn_side", "label": "Mouse 4 (Side Back)", "action": "default", "value": ""},
    {"id": "btn_extra", "label": "Mouse 5 (Side Forward)", "action": "default", "value": ""},
    {"id": "scroll_up", "label": "Scroll Wheel Up", "action": "default", "value": ""},
    {"id": "scroll_down", "label": "Scroll Wheel Down", "action": "default", "value": ""},
]

# Fallback / simulated devices for demo and testing without physical hardware
MOCK_DEVICES = [
    {
        "id": "SIM_KEYBOARD_001",
        "name": "Razer Huntsman V3 Pro",
        "serial": "SIM_KEYBOARD_001",
        "type": "keyboard",
        "firmware": "v2.04",
        "driver": "3.12.4",
        "has_battery": False,
        "battery": None,
        "is_charging": None,
        "idle_time": None,
        "low_battery_threshold": None,
        "has_dpi": False,
        "dpi": None,
        "max_dpi": None,
        "dpi_stages": None,
        "active_dpi_stage": None,
        "has_poll_rate": True,
        "poll_rate": 8000,
        "supported_poll_rates": [125, 250, 500, 1000, 2000, 4000, 8000],
        "has_brightness": True,
        "brightness": 100,
        "has_matrix": True,
        "matrix_dimensions": [6, 22],
        "has_lighting": True,
        "has_buttons": False,
        "buttons": [],
        "channels": [],
        "game_mode": True,
        "lighting": {
            "current_effect": "spectrum",
            "breath_mode": "single",
            "colors": ["#fafafa", "#4ade80"],
            "speed": "normal",
            "direction": "left",
            "supported_effects": ["none", "static", "breath", "spectrum", "wave", "reactive", "ripple", "starlight", "matrix"],
            "zones": ["overall"]
        }
    },
    {
        "id": "SIM_FIREFLY_001",
        "name": "Razer Firefly V2 Pro",
        "serial": "SIM_FIREFLY_001",
        "type": "mousemat",
        "firmware": "v1.01",
        "driver": "3.12.4",
        "has_battery": False,
        "battery": None,
        "is_charging": None,
        "idle_time": None,
        "low_battery_threshold": None,
        "has_dpi": False,
        "dpi": None,
        "max_dpi": None,
        "dpi_stages": None,
        "active_dpi_stage": None,
        "has_poll_rate": False,
        "poll_rate": None,
        "supported_poll_rates": [],
        "has_brightness": True,
        "brightness": 85,
        "has_matrix": True,
        "matrix_dimensions": [1, 15],
        "has_lighting": True,
        "has_buttons": False,
        "buttons": [],
        "channels": [],
        "game_mode": False,
        "lighting": {
            "current_effect": "wave",
            "breath_mode": "single",
            "colors": ["#4ade80", "#fafafa"],
            "speed": "normal",
            "direction": "right",
            "supported_effects": ["none", "static", "breath", "spectrum", "wave", "reactive", "matrix"],
            "zones": ["overall"]
        }
    }
]


class EvdevDeviceRemapper:
    """
    Intercepts events from a Razer mouse's primary evdev node (-event-mouse)
    using EVIOCGRAB and forwards unmapped + remapped events into its sibling
    OpenRazer kernel input nodes (-if01-event-mouse and -if02-event-kbd).
    Requires zero root privileges because OpenRazer udev rules grant 0660 root:openrazer.
    """
    def __init__(self, bridge, serial, dev_paths, mappings):
        self.bridge = bridge
        self.serial = serial
        self.dev_paths = dev_paths
        self.mappings = {m["id"]: m for m in mappings if m.get("action", "default") != "default"}
        self.stop_r, self.stop_w = os.pipe()
        self.thread = None
        self.running = False
        self.fd_in = None
        self.fd_out_mouse = None
        self.fd_out_kbd = None

    def start(self):
        if not self.mappings or not self.dev_paths.get("in_mouse") or not self.dev_paths.get("out_mouse"):
            return False
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True, name=f"remapper-{self.serial}")
        self.thread.start()
        return True

    def stop(self):
        self.running = False
        try:
            os.write(self.stop_w, b"x")
        except Exception:
            pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self._cleanup()

    def _cleanup(self):
        if self.fd_in is not None:
            try:
                fcntl.ioctl(self.fd_in, EVIOCGRAB, 0)
            except Exception:
                pass
            try:
                os.close(self.fd_in)
            except Exception:
                pass
            self.fd_in = None
        for attr in ("fd_out_mouse", "fd_out_kbd", "stop_r", "stop_w"):
            fd = getattr(self, attr, None)
            if fd is not None:
                try:
                    os.close(fd)
                except Exception:
                    pass
                setattr(self, attr, None)

    def _emit_event(self, fd, ev_type, ev_code, ev_val, syn=True):
        if fd is None:
            return
        now = time.time()
        sec = int(now)
        usec = int((now - sec) * 1000000)
        pkt = struct.pack(EVENT_FORMAT, sec, usec, ev_type, ev_code, int(ev_val))
        if syn:
            pkt += struct.pack(EVENT_FORMAT, sec, usec, EV_SYN, SYN_REPORT, 0)
        try:
            os.write(fd, pkt)
        except Exception as e:
            sys.stderr.write(f"Evdev write error: {e}\n")

    def _parse_key_combo(self, val_str):
        parts = [p.strip().upper() for p in str(val_str).split("+") if p.strip()]
        codes = []
        for p in parts:
            if p in KEY_CODES:
                codes.append(KEY_CODES[p])
            elif len(p) == 1 and p.isalnum() and p in KEY_CODES:
                codes.append(KEY_CODES[p])
        return codes

    def _trigger_mapping(self, rule, value):
        """
        Handle a remapped event.
        value: 1 (press), 0 (release), 2 (repeat)
        """
        action = rule.get("action", "default")
        target_val = rule.get("value", "")

        if action == "disabled":
            return

        elif action == "mouse":
            target_code = MOUSE_BUTTON_CODES.get(target_val, 272)
            self._emit_event(self.fd_out_mouse, EV_KEY, target_code, value, syn=True)

        elif action == "key":
            codes = self._parse_key_combo(target_val)
            out_fd = self.fd_out_kbd if self.fd_out_kbd is not None else self.fd_out_mouse
            if not codes:
                return
            if value == 1:
                for c in codes:
                    self._emit_event(out_fd, EV_KEY, c, 1, syn=True)
            elif value == 0:
                for c in reversed(codes):
                    self._emit_event(out_fd, EV_KEY, c, 0, syn=True)

        elif action == "media":
            mcode = MEDIA_KEY_MAP.get(target_val)
            if mcode:
                out_fd = self.fd_out_kbd if self.fd_out_kbd is not None else self.fd_out_mouse
                self._emit_event(out_fd, EV_KEY, mcode, value, syn=True)
            if value == 1:
                # Also trigger desktop media/volume helper as reliable fallback
                if target_val == "volume_up":
                    subprocess.Popen(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif target_val == "volume_down":
                    subprocess.Popen(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif target_val == "mute":
                    subprocess.Popen(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif target_val == "play_pause":
                    subprocess.Popen(["playerctl", "play-pause"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif target_val == "next_track":
                    subprocess.Popen(["playerctl", "next"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif target_val == "prev_track":
                    subprocess.Popen(["playerctl", "previous"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        elif action in ("dpi_cycle", "dpi_up", "dpi_down"):
            if value == 1:
                direction = -1 if action == "dpi_down" else 1
                threading.Thread(target=self.bridge.cycle_dpi_stage, args=(self.serial, direction), daemon=True).start()

        elif action == "dpi_sniper":
            sniper_dpi = int(target_val) if str(target_val).isdigit() else 400
            if value == 1:
                self._saved_dpi = self.bridge.get_current_dpi_pair(self.serial)
                threading.Thread(target=self.bridge.set_dpi, args=(self.serial, sniper_dpi, sniper_dpi), daemon=True).start()
            elif value == 0:
                prev = getattr(self, "_saved_dpi", [1600, 1600])
                threading.Thread(target=self.bridge.set_dpi, args=(self.serial, prev[0], prev[1]), daemon=True).start()

        elif action == "poll_cycle":
            if value == 1:
                threading.Thread(target=self.bridge.cycle_poll_rate, args=(self.serial,), daemon=True).start()

        elif action == "command":
            if value == 1 and target_val:
                subprocess.Popen(target_val, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _run(self):
        try:
            self.fd_in = os.open(self.dev_paths["in_mouse"], os.O_RDONLY | os.O_NONBLOCK)
            self.fd_out_mouse = os.open(self.dev_paths["out_mouse"], os.O_WRONLY | os.O_NONBLOCK)
            if self.dev_paths.get("out_kbd"):
                try:
                    self.fd_out_kbd = os.open(self.dev_paths["out_kbd"], os.O_WRONLY | os.O_NONBLOCK)
                except Exception:
                    self.fd_out_kbd = None

            # Wait briefly for any held buttons to release before grabbing
            time.sleep(0.05)
            fcntl.ioctl(self.fd_in, EVIOCGRAB, 1)

            while self.running:
                rlist, _, _ = select.select([self.fd_in, self.stop_r], [], [], 0.5)
                if self.stop_r in rlist:
                    break
                if self.fd_in not in rlist:
                    continue

                try:
                    data = os.read(self.fd_in, EVENT_SIZE * 64)
                except BlockingIOError:
                    continue
                except OSError:
                    break

                if not data:
                    break

                forward_buf = bytearray()
                offset = 0
                n = len(data)
                while offset + EVENT_SIZE <= n:
                    chunk = data[offset:offset + EVENT_SIZE]
                    offset += EVENT_SIZE
                    sec, usec, ev_type, ev_code, ev_val = struct.unpack(EVENT_FORMAT, chunk)

                    if ev_type == EV_KEY and ev_code in CODE_TO_MOUSE_BUTTON:
                        btn_id = CODE_TO_MOUSE_BUTTON[ev_code]
                        if btn_id in self.mappings:
                            self._trigger_mapping(self.mappings[btn_id], ev_val)
                            continue

                    elif ev_type == EV_REL and ev_code in (REL_WHEEL, REL_WHEEL_HI_RES):
                        btn_id = "scroll_up" if ev_val > 0 else "scroll_down"
                        if btn_id in self.mappings:
                            if ev_code == REL_WHEEL:
                                self._trigger_mapping(self.mappings[btn_id], 1)
                                self._trigger_mapping(self.mappings[btn_id], 0)
                            continue

                    forward_buf.extend(chunk)

                if forward_buf:
                    try:
                        os.write(self.fd_out_mouse, forward_buf)
                    except Exception:
                        pass
        except Exception as e:
            sys.stderr.write(f"Remapper thread error for {self.serial}: {e}\n")
        finally:
            self._cleanup()


class ArgbEffectAnimator:
    """
    Software frame animator for the Razer Chroma Addressable RGB Controller (1532:0F1F).
    In OpenRazer's kernel driver (razeraccessory_driver.c), 1532:0F1F is placed into
    Driver Mode (0x03, 0x00) where built-in hardware effect reports (which send ZERO_LED=0x00)
    are ignored by the controller firmware, and the hardware frame buffer blanks if not
    periodically refreshed. This animator continuously streams per-channel ARGB frames
    (one write per row 0..5) so Static, Spectrum, Wave, Breathing, and Matrix Editor
    stay continuously lit across all 6 headers.
    """
    def __init__(self, bridge, serial, effect, rgb_colors, speed="normal", direction="right", breath_mode="single", custom_rows=None):
        self.bridge = bridge
        self.serial = serial
        self.effect = effect
        self.rgb_colors = rgb_colors or [(250, 250, 250), (74, 222, 128)]
        self.speed = speed
        self.direction = direction
        self.breath_mode = breath_mode
        self.custom_rows = custom_rows
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True, name=f"argb-{self.serial}")
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=0.35)

    def _scale_row(self, row_bytes, scale):
        if scale >= 0.995:
            return row_bytes
        if scale <= 0.005:
            return bytes(len(row_bytes))
        return bytes(int(b * scale) for b in row_bytes)

    def _build_frame_rows(self, t, speed_mult, dir_sign):
        cols = 80
        rows = 6
        cache = self.bridge.device_state_cache.get(self.serial, {})
        br_scale = max(0.0, min(1.0, float(cache.get("brightness", 100)) / 100.0))

        if self.effect == "matrix" and self.custom_rows:
            return [self._scale_row(r, br_scale) for r in self.custom_rows]

        if self.effect in ("static", "reactive", "ripple", "starlight", "matrix"):
            base_r, base_g, base_b = self.rgb_colors[0]
            rgb = (
                int(base_r * br_scale),
                int(base_g * br_scale),
                int(base_b * br_scale)
            )
            row_bytes = bytes(rgb) * cols
            return [row_bytes for _ in range(rows)]

        if self.effect == "spectrum":
            hue = (t * 0.12) % 1.0
            r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, 1.0, br_scale)
            rgb = (int(r_f * 255), int(g_f * 255), int(b_f * 255))
            row_bytes = bytes(rgb) * cols
            return [row_bytes for _ in range(rows)]

        if self.effect == "wave":
            row_buf = bytearray(cols * 3)
            for c in range(cols):
                hue = ((c / 20.0) + dir_sign * t * 0.35) % 1.0
                r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, 1.0, br_scale)
                idx = c * 3
                row_buf[idx] = int(r_f * 255)
                row_buf[idx + 1] = int(g_f * 255)
                row_buf[idx + 2] = int(b_f * 255)
            row_bytes = bytes(row_buf)
            return [row_bytes for _ in range(rows)]

        if self.effect == "breath":
            cycle = (t * 0.45)
            phase = cycle % 1.0
            intensity = 0.5 * (1.0 - math.cos(phase * 2.0 * math.pi)) * br_scale
            cycle_idx = int(cycle)

            if self.breath_mode == "random":
                hue = ((cycle_idx * 0.27) % 1.0)
                r_f, g_f, b_f = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                base_rgb = (int(r_f * 255), int(g_f * 255), int(b_f * 255))
            elif self.breath_mode == "dual" and len(self.rgb_colors) >= 2:
                base_rgb = self.rgb_colors[cycle_idx % 2]
            else:
                base_rgb = self.rgb_colors[0]

            rgb = (
                int(base_rgb[0] * intensity),
                int(base_rgb[1] * intensity),
                int(base_rgb[2] * intensity)
            )
            row_bytes = bytes(rgb) * cols
            return [row_bytes for _ in range(rows)]

        return None

    def _run(self):
        speed_mult = {"fast": 2.2, "normal": 1.2, "slow": 0.6, "ultra": 3.0}.get(self.speed, 1.2)
        dir_sign = -1.0 if self.direction in ("right", "up", "clockwise") else 1.0
        t0 = time.time()
        is_static_like = self.effect in ("static", "reactive", "ripple", "starlight", "matrix")
        sleep_ticks = 12 if is_static_like else 3  # ~180ms for static/matrix keepalive, ~45ms for animations

        while self.running:
            t = (time.time() - t0) * speed_mult
            frame_rows = self._build_frame_rows(t, speed_mult, dir_sign)
            if not frame_rows:
                break

            try:
                self.bridge._write_argb_raw_rows(self.serial, frame_rows, latch_custom=False)
            except Exception:
                pass

            for _ in range(sleep_ticks):
                if not self.running:
                    break
                time.sleep(0.015)


class RazerBridge:
    def __init__(self):
        self.devman = None
        self.mock_mode = False
        self._settings_restored = False
        self.device_state_cache = {}
        self.config_dir = os.path.expanduser("~/.config/razerd")
        self.mappings_file = os.path.join(self.config_dir, "button_mappings.json")
        self.lighting_file = os.path.join(self.config_dir, "lighting_state.json")
        self.settings_file = os.path.join(self.config_dir, "device_settings.json")
        self.button_mappings = self._load_button_mappings()
        self._load_lighting_state()
        self._load_device_settings()
        self.active_remappers = {}
        self.argb_animators = {}
        self.argb_write_lock = threading.Lock()
        self._ensure_openrazer_ready()
        atexit.register(self.stop_all_remappers)

    def _init_openrazer(self):
        if not HAS_OPENRAZER:
            return False
        try:
            self.devman = openrazer.client.DeviceManager()
            self.devman.sync_effects = False
            return True
        except Exception as e:
            sys.stderr.write(f"Warning: Could not connect to OpenRazer daemon: {e}\n")
            self.devman = None
            return False

    def _ensure_openrazer_ready(self):
        if not self.devman:
            self._init_openrazer()
        elif not self._settings_restored:
            try:
                if len(self.devman.devices) == 0:
                    self._init_openrazer()
            except Exception:
                self._init_openrazer()

        if self.devman and not self._settings_restored:
            try:
                if len(self.devman.devices) > 0:
                    self._settings_restored = True
                    self._sync_all_remappers()
                    self._restore_all_device_settings()
                    self._restore_argb_controllers()
            except Exception as e:
                sys.stderr.write(f"Warning during initial OpenRazer device restore: {e}\n")

    def _load_openrazer_persistence(self):
        cfg = configparser.ConfigParser()
        p_path = os.path.expanduser("~/.config/openrazer/persistence.conf")
        if os.path.exists(p_path):
            try:
                cfg.read(p_path)
            except Exception:
                pass
        return cfg

    def _load_button_mappings(self):
        if os.path.exists(self.mappings_file):
            try:
                with open(self.mappings_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_button_mappings(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.mappings_file, "w") as f:
                json.dump(self.button_mappings, f, indent=2)
        except Exception as e:
            sys.stderr.write(f"Error saving button mappings: {e}\n")

    def _load_lighting_state(self):
        if os.path.exists(self.lighting_file):
            try:
                with open(self.lighting_file, "r") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    for serial, lstate in saved.items():
                        cache = self.device_state_cache.setdefault(serial, {})
                        cache["user_set_lighting"] = True
                        cache["lighting"] = dict(lstate)
            except Exception:
                pass

    def _save_lighting_state(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            out = {}
            for serial, cache in self.device_state_cache.items():
                if cache.get("user_set_lighting") and "lighting" in cache:
                    out[serial] = cache["lighting"]
            with open(self.lighting_file, "w") as f:
                json.dump(out, f, indent=2)
        except Exception as e:
            sys.stderr.write(f"Error saving lighting state: {e}\n")

    def _load_device_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    saved = json.load(f)
                if isinstance(saved, dict):
                    for serial, dset in saved.items():
                        if not isinstance(dset, dict):
                            continue
                        cache = self.device_state_cache.setdefault(serial, {})
                        for k in ("dpi", "dpi_stages", "active_dpi_stage", "poll_rate", "brightness", "idle_time", "low_battery_threshold"):
                            if k in dset and dset[k] is not None:
                                cache[k] = dset[k]
                        if "lighting" in dset and isinstance(dset["lighting"], dict):
                            cache["user_set_lighting"] = True
                            cache["lighting"] = dict(dset["lighting"])
            except Exception:
                pass

    def _save_device_settings(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            out = {}
            for serial, cache in self.device_state_cache.items():
                dset = {}
                for k in ("dpi", "dpi_stages", "active_dpi_stage", "poll_rate", "brightness", "idle_time", "low_battery_threshold"):
                    if k in cache and cache[k] is not None:
                        dset[k] = cache[k]
                if cache.get("user_set_lighting") and "lighting" in cache:
                    dset["lighting"] = cache["lighting"]
                if dset:
                    out[serial] = dset
            with open(self.settings_file, "w") as f:
                json.dump(out, f, indent=2)
        except Exception as e:
            sys.stderr.write(f"Error saving device settings: {e}\n")

    def _restore_all_device_settings(self):
        if not self.devman:
            return
        try:
            for rdev in self.devman.devices:
                serial = rdev.serial
                cache = self.device_state_cache.get(serial)
                if not cache:
                    continue
                if "dpi_stages" in cache and rdev.has("dpi_stages"):
                    try:
                        active_st = int(cache.get("active_dpi_stage", 1))
                        tuple_stages = [(int(s[0]), int(s[1])) for s in cache["dpi_stages"]]
                        rdev.dpi_stages = (active_st, tuple_stages)
                    except Exception:
                        pass
                if "dpi" in cache and rdev.has("dpi"):
                    try:
                        rdev.dpi = (int(cache["dpi"][0]), int(cache["dpi"][1]))
                    except Exception:
                        pass
                if "poll_rate" in cache and rdev.has("poll_rate"):
                    try:
                        rdev.poll_rate = int(cache["poll_rate"])
                    except Exception:
                        pass
                if "brightness" in cache and rdev.has("brightness"):
                    try:
                        rdev.brightness = float(cache["brightness"])
                    except Exception:
                        pass
                if "idle_time" in cache and (rdev.has("idle_time") or rdev.has("set_idle_time")):
                    try:
                        rdev.set_idle_time(max(1, min(15, int(cache["idle_time"]))) * 60)
                    except Exception:
                        pass
                if "low_battery_threshold" in cache and (rdev.has("low_battery_threshold") or rdev.has("set_low_battery_threshold")):
                    try:
                        rdev.set_low_battery_threshold(max(5, min(100, int(cache["low_battery_threshold"]))))
                    except Exception:
                        pass
                if cache.get("user_set_lighting") and "lighting" in cache and not self._is_argb_controller(rdev):
                    lstate = cache["lighting"]
                    try:
                        self.set_effect(
                            serial,
                            lstate.get("current_effect", "static"),
                            lstate.get("colors", ["#fafafa", "#4ade80"]),
                            lstate.get("speed", "normal"),
                            lstate.get("direction", "right"),
                            lstate.get("zone", "overall"),
                            lstate.get("breath_mode", "single")
                        )
                    except Exception:
                        pass
        except Exception as e:
            sys.stderr.write(f"Warning restoring device settings: {e}\n")

    def stop_all_remappers(self):
        for serial, remapper in list(self.active_remappers.items()):
            try:
                remapper.stop()
            except Exception:
                pass
        self.active_remappers.clear()
        for serial, anim in list(self.argb_animators.items()):
            try:
                anim.stop()
            except Exception:
                pass
        self.argb_animators.clear()

    def _is_argb_controller(self, rdevice):
        if not rdevice:
            return False
        name = getattr(rdevice, "name", "")
        avail = getattr(rdevice, "_available_features", {})
        return "Addressable RGB Controller" in name or "razer.device.lighting.channel" in avail

    def _find_argb_sysfs_dir(self, serial=None):
        try:
            for p in sorted(glob.glob("/sys/bus/hid/drivers/razeraccessory/*/channel1_size")):
                d = os.path.dirname(p)
                if serial:
                    ser_file = os.path.join(d, "device_serial")
                    if os.path.exists(ser_file):
                        try:
                            with open(ser_file, "r") as f:
                                if f.read().strip() == serial:
                                    return d
                        except Exception:
                            pass
                return d
        except Exception:
            pass
        return None

    def _stop_argb_animator(self, serial):
        anim = self.argb_animators.pop(serial, None)
        if anim:
            anim.stop()

    def _get_argb_channel_sizes(self, serial, sysfs_dir=None, force=False):
        cache = self.device_state_cache.setdefault(serial, {})
        if not force and "channel_sizes" in cache:
            return cache["channel_sizes"]
        sizes = [14] * 6
        if not sysfs_dir:
            sysfs_dir = self._find_argb_sysfs_dir(serial)
        if sysfs_dir:
            for ch in range(1, 7):
                sz_file = os.path.join(sysfs_dir, f"channel{ch}_size")
                if os.path.exists(sz_file):
                    try:
                        with open(sz_file, "r") as f:
                            val = int(f.read().strip() or "14")
                        if 1 <= val <= 80:
                            sizes[ch - 1] = val
                    except Exception:
                        pass
        cache["channel_sizes"] = sizes
        return sizes

    def _write_argb_raw_rows(self, serial, row_rgb_buffers, latch_custom=False):
        """
        Writes 6 ARGB channel frames one row at a time to matrix_custom_frame.
        Each write must contain a single row [row_id, 0, stop_col, ...rgb...]
        where stop_col = channel_size - 1.
        IMPORTANT: Do NOT write to matrix_effect_custom (0x0F, 0x02, 0x08) afterwards,
        because on 1532:0F1F that command clears the streamed ARGB buffer to black!
        """
        with self.argb_write_lock:
            cache = self.device_state_cache.setdefault(serial, {})
            cache["last_argb_rows"] = list(row_rgb_buffers)
            sysfs_dir = self._find_argb_sysfs_dir(serial)
            if sysfs_dir:
                ch_sizes = self._get_argb_channel_sizes(serial, sysfs_dir)
                mcf = os.path.join(sysfs_dir, "matrix_custom_frame")
                for row_idx, rgb_bytes in enumerate(row_rgb_buffers):
                    ch_sz = ch_sizes[row_idx] if row_idx < len(ch_sizes) else 14
                    avail_leds = max(1, len(rgb_bytes) // 3)
                    count_leds = max(1, min(ch_sz, avail_leds))
                    payload = bytes([row_idx, 0, count_leds - 1]) + rgb_bytes[:count_leds * 3]
                    with open(mcf, "wb") as f:
                        f.write(payload)
                return True

            # Fallback via OpenRazer DBus setKeyRow one row at a time (without setCustom)
            rdev = self._find_rdevice(serial)
            if rdev and getattr(rdev, "fx", None) and getattr(rdev.fx, "advanced", None):
                ch_sizes = self._get_argb_channel_sizes(serial)
                for row_idx, rgb_bytes in enumerate(row_rgb_buffers):
                    ch_sz = ch_sizes[row_idx] if row_idx < len(ch_sizes) else 14
                    count_leds = max(1, min(ch_sz, len(rgb_bytes) // 3))
                    payload = bytes([row_idx, 0, count_leds - 1]) + rgb_bytes[:count_leds * 3]
                    rdev.fx.advanced._lighting_dbus.setKeyRow(payload)
                return True
        return False

    def _ensure_argb_hw_ready(self, serial):
        cache = self.device_state_cache.setdefault(serial, {})
        if cache.get("argb_hw_init"):
            return
        sysfs_dir = self._find_argb_sysfs_dir(serial)
        if not sysfs_dir:
            return
        try:
            dm = os.path.join(sysfs_dir, "device_mode")
            if os.path.exists(dm):
                with open(dm, "rb") as f:
                    cur_mode = f.read()
                if not cur_mode or cur_mode[0] != 3:
                    with open(dm, "wb") as f:
                        f.write(b"\x03\x00")
        except Exception:
            pass
        try:
            for ch in range(1, 7):
                br_file = os.path.join(sysfs_dir, f"channel{ch}_led_brightness")
                if os.path.exists(br_file):
                    with open(br_file, "r") as f:
                        val = int(f.read().strip() or "0")
                    if val < 15:
                        with open(br_file, "w") as f:
                            f.write("255")
        except Exception:
            pass
        self._get_argb_channel_sizes(serial, sysfs_dir, force=True)
        cache["argb_hw_init"] = True

    def _drive_argb_effect(self, rdev, effect, rgb_colors, speed="normal", direction="right", breath_mode="single", custom_rows=None):
        serial = rdev.serial
        self._stop_argb_animator(serial)

        if effect != "none":
            self._ensure_argb_hw_ready(serial)

        cols = 80
        rows = 6
        if effect == "none":
            off_row = bytes([0, 0, 0]) * cols
            self._write_argb_raw_rows(serial, [off_row for _ in range(rows)])
        else:
            eff_type = "wave" if effect == "wheel" else effect
            anim = ArgbEffectAnimator(self, serial, eff_type, rgb_colors, speed, direction, breath_mode, custom_rows=custom_rows)
            self.argb_animators[serial] = anim
            anim.start()

    def _restore_argb_controllers(self):
        if not self.devman:
            return
        try:
            for rdev in self.devman.devices:
                if self._is_argb_controller(rdev):
                    effects = self._get_supported_effects(rdev)
                    zones = self._get_device_zones(rdev)
                    state = self._read_hardware_lighting_state(rdev, effects, zones)
                    eff = state.get("current_effect", "static")
                    cols_hex = state.get("colors", ["#fafafa", "#4ade80"])
                    rgb_cols = [self._hex_to_rgb(c) for c in cols_hex]
                    self._drive_argb_effect(
                        rdev,
                        eff,
                        rgb_cols,
                        state.get("speed", "normal"),
                        state.get("direction", "right"),
                        state.get("breath_mode", "single")
                    )
        except Exception as e:
            sys.stderr.write(f"Warning restoring ARGB controller: {e}\n")

    def _find_evdev_paths_for_device(self, rdevice_or_name):
        name = rdevice_or_name if isinstance(rdevice_or_name, str) else getattr(rdevice_or_name, "name", "")
        # Strip (Wireless) / (Wired) suffixes to match /dev/input/by-id/usb-Razer_*
        clean = name.replace("(Wireless)", "").replace("(Wired)", "").strip()
        tokens = [t for t in clean.replace("Razer", "").strip().split() if t]
        if not tokens:
            return None

        by_id_files = sorted(glob.glob("/dev/input/by-id/usb-Razer*"))
        matched = [p for p in by_id_files if all(tok.lower() in os.path.basename(p).lower() for tok in tokens)]
        if not matched:
            return None

        in_mouse = None
        out_mouse = None
        out_kbd = None
        for p in matched:
            base = os.path.basename(p)
            if base.endswith("-if01-event-mouse"):
                out_mouse = os.path.realpath(p)
            elif base.endswith("-event-mouse") and "-if" not in base:
                in_mouse = os.path.realpath(p)
            elif base.endswith("-event-kbd"):
                out_kbd = os.path.realpath(p)

        if in_mouse and out_mouse and os.access(in_mouse, os.R_OK) and os.access(out_mouse, os.W_OK):
            return {"in_mouse": in_mouse, "out_mouse": out_mouse, "out_kbd": out_kbd}
        return None

    def _sync_remapper_for_device(self, serial, dev_name):
        if serial in self.active_remappers:
            self.active_remappers[serial].stop()
            del self.active_remappers[serial]

        mappings = self.button_mappings.get(serial, [])
        has_custom = any(m.get("action", "default") != "default" for m in mappings)
        if not has_custom:
            return False

        paths = self._find_evdev_paths_for_device(dev_name)
        if not paths:
            return False

        remapper = EvdevDeviceRemapper(self, serial, paths, mappings)
        if remapper.start():
            self.active_remappers[serial] = remapper
            return True
        return False

    def _sync_all_remappers(self):
        if not self.devman:
            return
        try:
            for rdev in self.devman.devices:
                if rdev.serial in self.button_mappings:
                    self._sync_remapper_for_device(rdev.serial, rdev.name)
        except Exception:
            pass

    def get_status(self):
        """Diagnose OpenRazer daemon, kernel modules, permissions, and USB/HID bus."""
        self._ensure_openrazer_ready()

        daemon_version = None
        daemon_running = False
        if self.devman:
            try:
                daemon_version = self.devman.version
                daemon_running = True
            except Exception:
                pass

        if not daemon_running:
            try:
                res = subprocess.run(
                    ["systemctl", "--user", "is-active", "openrazer-daemon.service"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                if "active" in res.stdout:
                    daemon_running = True
                    daemon_version = daemon_version or "3.12.4"
            except Exception:
                pass

        modules = {}
        try:
            with open("/proc/modules", "r") as f:
                out = f.read()
            for mod in ["razerkbd", "razermouse", "razeraccessory", "razerkraken"]:
                modules[mod] = mod in out
        except Exception:
            modules = {mod: False for mod in ["razerkbd", "razermouse", "razeraccessory", "razerkraken"]}

        groups = []
        try:
            groups_res = subprocess.run(
                ["groups"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            groups = groups_res.stdout.strip().split()
        except Exception:
            pass

        in_group = "openrazer" in groups or "plugdev" in groups
        group_name = "openrazer" if "openrazer" in groups else ("plugdev" if "plugdev" in groups else "openrazer/plugdev")

        # Detect connected Razer USB/HID devices via sysfs (does not require lsusb package)
        usb_devices = []
        seen_vp = set()
        try:
            for p in sorted(glob.glob("/sys/bus/hid/devices/*1532:*")):
                base = os.path.basename(p)
                parts = base.split(".")
                vp = parts[0] if parts else base
                dtype_file = os.path.join(p, "device_type")
                label = vp
                if os.path.exists(dtype_file):
                    try:
                        with open(dtype_file, "r") as f:
                            dtype = f.read().strip()
                        if dtype:
                            label = f"{vp} — {dtype}"
                    except Exception:
                        pass
                if label not in seen_vp and "—" in label:
                    seen_vp.add(label)
                    usb_devices.append(label)
        except Exception:
            pass

        return {
            "has_openrazer_lib": HAS_OPENRAZER,
            "daemon_running": daemon_running,
            "daemon_version": daemon_version,
            "kernel_modules": modules,
            "in_group": in_group,
            "group_name": group_name,
            "user_groups": groups,
            "usb_devices": usb_devices,
            "mock_mode": self.mock_mode,
            "autostart_enabled": self.get_autostart().get("enabled", False)
        }

    def _get_supported_effects(self, rdevice):
        caps = rdevice.capabilities
        effects = []
        if caps.get("lighting_none", False):
            effects.append("none")
        if caps.get("lighting_static", False):
            effects.append("static")
        if any([
            caps.get("lighting_breath_single", False),
            caps.get("lighting_breath_dual", False),
            caps.get("lighting_breath_triple", False),
            caps.get("lighting_breath_random", False)
        ]):
            effects.append("breath")
        if caps.get("lighting_spectrum", False):
            effects.append("spectrum")
        if caps.get("lighting_wave", False):
            effects.append("wave")
        if caps.get("lighting_reactive", False):
            effects.append("reactive")
        if caps.get("lighting_ripple", False) or caps.get("lighting_ripple_random", False):
            effects.append("ripple")
        if any([
            caps.get("lighting_starlight_single", False),
            caps.get("lighting_starlight_dual", False),
            caps.get("lighting_starlight_random", False)
        ]):
            effects.append("starlight")
        if caps.get("lighting_wheel", False):
            effects.append("wheel")
        if caps.get("lighting_led_matrix", False):
            effects.append("matrix")
        # Never add fake lighting effects when hardware has none (e.g. Razer Viper V3 Pro)
        return effects

    def _get_device_zones(self, rdevice):
        zones = ["overall"]
        caps = rdevice.capabilities
        if caps.get("lighting_logo", False) or caps.get("lighting_logo_active", False):
            zones.append("logo")
        if caps.get("lighting_scroll", False) or caps.get("lighting_scroll_active", False):
            zones.append("scroll")
        if caps.get("lighting_left", False):
            zones.append("left")
        if caps.get("lighting_right", False):
            zones.append("right")
        if caps.get("lighting_backlight", False):
            zones.append("backlight")
        return zones

    def _get_argb_channels(self, rdevice, force=False):
        serial = rdevice.serial
        cache = self.device_state_cache.setdefault(serial, {})
        if not force and "channels" in cache:
            return cache["channels"]
        channels = []
        try:
            avail = getattr(rdevice, "_available_features", {})
            if "razer.device.lighting.channel" in avail:
                ch_iface = dbus.Interface(rdevice._dbus, "razer.device.lighting.channel")
                num_ch = int(ch_iface.getNumChannels())
                sizes = []
                for i in range(1, num_ch + 1):
                    sz = int(ch_iface.getChannelSize(i))
                    br = round(float(ch_iface.getChannelBrightness(i)))
                    sizes.append(sz if 1 <= sz <= 80 else 14)
                    channels.append({
                        "channel": i,
                        "name": f"ARGB Header {i}",
                        "size": sz,
                        "brightness": br
                    })
                if len(sizes) == 6:
                    cache["channel_sizes"] = sizes
                cache["channels"] = channels
        except Exception as e:
            sys.stderr.write(f"Error reading ARGB channels: {e}\n")
        return channels

    def _read_hardware_lighting_state(self, rdevice, effects, zones):
        serial = rdevice.serial
        dev_cache = self.device_state_cache.get(serial, {})
        cache = dev_cache.get("lighting", {})
        default_effect = "static" if "static" in effects else (effects[0] if effects else "none")

        current_effect = cache.get("current_effect", default_effect)
        breath_mode = cache.get("breath_mode", "single")
        colors = list(cache.get("colors", ["#fafafa", "#4ade80"]))
        speed = cache.get("speed", "normal")
        direction = cache.get("direction", "right")

        # Once lighting state is cached (or explicitly set by the user), return cached state
        # so periodic list_devices() calls do not re-query D-Bus or overwrite custom ARGB frames.
        if dev_cache.get("user_set_lighting") or "lighting" in dev_cache:
            while len(colors) < 2:
                colors.append("#4ade80")
            return {
                "current_effect": current_effect,
                "breath_mode": breath_mode,
                "colors": colors,
                "speed": speed,
                "direction": direction,
                "supported_effects": effects,
                "zones": zones
            }

        try:
            avail = getattr(rdevice, "_available_features", {})
            chroma_methods = avail.get("razer.device.lighting.chroma", [])
            if "getEffect" in chroma_methods and getattr(rdevice, "fx", None):
                hw_eff = str(rdevice.fx.effect)
                if hw_eff:
                    if hw_eff.startswith("breath"):
                        current_effect = "breath"
                        sub = hw_eff.replace("breath", "").lower()
                        if sub in ("single", "dual", "triple", "random"):
                            breath_mode = sub
                    elif hw_eff.startswith("starlight"):
                        current_effect = "starlight"
                    elif hw_eff.startswith("ripple"):
                        current_effect = "ripple"
                    elif hw_eff == "custom":
                        current_effect = "matrix"
                    elif hw_eff in effects:
                        current_effect = hw_eff

                if "getEffectColors" in chroma_methods:
                    raw_hex = rdevice.fx.colors.hex()
                    parsed_colors = []
                    if len(raw_hex) >= 6:
                        parsed_colors.append("#" + raw_hex[0:6])
                    if len(raw_hex) >= 12:
                        parsed_colors.append("#" + raw_hex[6:12])
                    if len(raw_hex) >= 18:
                        parsed_colors.append("#" + raw_hex[12:18])
                    if parsed_colors and any(c.lower() != "#000000" for c in parsed_colors):
                        colors = parsed_colors

                if "getWaveDir" in chroma_methods:
                    wdir = int(rdevice.fx.wave_dir)
                    direction = "right" if wdir == 1 else "left"

                if "getEffectSpeed" in chroma_methods:
                    spd_int = int(rdevice.fx.speed)
                    inv_speed = {1: "fast", 2: "normal", 3: "slow", 4: "ultra"}
                    speed = inv_speed.get(spd_int, speed)
        except Exception:
            pass

        while len(colors) < 2:
            colors.append("#4ade80")

        return {
            "current_effect": current_effect,
            "breath_mode": breath_mode,
            "colors": colors,
            "speed": speed,
            "direction": direction,
            "supported_effects": effects,
            "zones": zones
        }

    def _serialize_device(self, rdevice):
        serial = rdevice.serial
        cache = self.device_state_cache.setdefault(serial, {})
        persistence_cfg = self._load_openrazer_persistence()
        p_sec = persistence_cfg[serial] if serial in persistence_cfg else {}
        now = time.time()

        # Battery (throttled to once every 30s per device so sleeping wireless mice don't stall USB)
        has_battery = rdevice.has("battery")
        battery = None
        is_charging = None
        if has_battery:
            if "battery" in cache and (now - cache.get("last_battery_poll", 0)) < 30.0:
                battery = cache["battery"]
                is_charging = cache.get("is_charging", False)
            else:
                cache["last_battery_poll"] = now
                try:
                    hw_bat = int(rdevice.battery_level)
                    hw_chg = bool(rdevice.is_charging)
                    if hw_bat > 0 or hw_chg:
                        battery = hw_bat
                        is_charging = hw_chg
                        cache["battery"] = battery
                        cache["is_charging"] = is_charging
                    else:
                        battery = cache.get("battery", 0)
                        is_charging = cache.get("is_charging", False)
                        cache["battery"] = battery
                        cache["is_charging"] = is_charging
                except Exception:
                    battery = cache.get("battery", 0)
                    is_charging = cache.get("is_charging", False)
                    cache["battery"] = battery
                    cache["is_charging"] = is_charging

        # Idle time (OpenRazer returns seconds 60..900; UI presents minutes 1..15)
        idle_time = None
        low_battery_threshold = None
        if rdevice.has("idle_time") or rdevice.has("get_idle_time"):
            if "idle_time" in cache:
                idle_time = cache["idle_time"]
            else:
                try:
                    raw_idle = int(rdevice.get_idle_time())
                    if raw_idle > 0:
                        idle_time = max(1, min(15, round(raw_idle / 60))) if raw_idle > 15 else raw_idle
                    else:
                        idle_time = 5
                except Exception:
                    idle_time = 5
                cache["idle_time"] = idle_time

        if rdevice.has("low_battery_threshold") or rdevice.has("get_low_battery_threshold"):
            if "low_battery_threshold" in cache:
                low_battery_threshold = cache["low_battery_threshold"]
            else:
                try:
                    raw_thresh = int(rdevice.get_low_battery_threshold())
                    if raw_thresh > 0:
                        low_battery_threshold = raw_thresh
                    else:
                        low_battery_threshold = 15
                except Exception:
                    low_battery_threshold = 15
                cache["low_battery_threshold"] = low_battery_threshold

        # DPI
        has_dpi = rdevice.has("dpi")
        dpi = None
        max_dpi = None
        dpi_stages = None
        active_dpi_stage = cache.get("active_dpi_stage", 1)
        if has_dpi:
            if "max_dpi" in cache:
                max_dpi = cache["max_dpi"]
            else:
                try:
                    max_dpi = int(rdevice.max_dpi)
                except Exception:
                    max_dpi = 30000
                cache["max_dpi"] = max_dpi

            if "dpi" in cache:
                dpi = cache["dpi"]
            else:
                try:
                    hw_dpi = list(rdevice.dpi)
                    if hw_dpi and hw_dpi[0] > 0:
                        dpi = [int(hw_dpi[0]), int(hw_dpi[1])]
                    elif "dpi_x" in p_sec and int(p_sec.get("dpi_x", 0)) > 0:
                        dpi = [int(p_sec.get("dpi_x", 800)), int(p_sec.get("dpi_y", 800))]
                    else:
                        dpi = [800, 800]
                except Exception:
                    dpi = [800, 800]
                cache["dpi"] = dpi

            if "dpi_stages" in cache:
                dpi_stages = cache["dpi_stages"]
                active_dpi_stage = cache.get("active_dpi_stage", 1)
            elif rdevice.has("dpi_stages"):
                try:
                    st_active, st_list = rdevice.dpi_stages
                    valid_stages = [[int(x), int(y)] for (x, y) in st_list if int(x) > 0]
                    if valid_stages:
                        dpi_stages = valid_stages
                        active_dpi_stage = int(st_active) if int(st_active) > 0 else 1
                except Exception:
                    pass

            if not dpi_stages:
                dpi_stages = [[400, 400], [800, 800], [1600, 1600], [3200, 3200], [6400, 6400]]
                for idx, st in enumerate(dpi_stages):
                    if dpi and st[0] == dpi[0]:
                        active_dpi_stage = idx + 1
            cache["dpi_stages"] = dpi_stages
            cache["active_dpi_stage"] = active_dpi_stage

        # Poll rate
        has_poll_rate = rdevice.has("poll_rate")
        poll_rate = None
        supported_poll_rates = []
        if has_poll_rate:
            if "poll_rate" in cache:
                poll_rate = cache["poll_rate"]
            else:
                try:
                    hw_rate = int(rdevice.poll_rate)
                    if hw_rate > 0:
                        poll_rate = hw_rate
                    elif "poll_rate" in p_sec and int(p_sec["poll_rate"]) > 0:
                        poll_rate = int(p_sec["poll_rate"])
                    else:
                        poll_rate = 1000
                except Exception:
                    poll_rate = 1000
                cache["poll_rate"] = poll_rate

            if "supported_poll_rates" in cache:
                supported_poll_rates = cache["supported_poll_rates"]
            elif rdevice.has("supported_poll_rates"):
                try:
                    supported_poll_rates = [int(r) for r in rdevice.supported_poll_rates]
                except Exception:
                    supported_poll_rates = [125, 500, 1000]
                cache["supported_poll_rates"] = supported_poll_rates
            else:
                supported_poll_rates = [125, 500, 1000]
                cache["supported_poll_rates"] = supported_poll_rates

        # Brightness
        has_brightness = rdevice.has("brightness")
        brightness = None
        if has_brightness:
            if "brightness" in cache:
                brightness = cache["brightness"]
            else:
                try:
                    brightness = round(float(rdevice.brightness))
                    if brightness <= 0:
                        brightness = 100
                except Exception:
                    brightness = 100
                cache["brightness"] = brightness

        # Matrix
        has_matrix = rdevice.has("lighting_led_matrix")
        matrix_dims = None
        if has_matrix:
            try:
                rows = int(rdevice.fx.advanced.rows)
                cols = int(rdevice.fx.advanced.cols)
                # For 80-col ARGB controllers, cap visual editor columns to the max active channel size (or 20)
                channels_preview = self._get_argb_channels(rdevice)
                if channels_preview:
                    max_ch_size = max([c["size"] for c in channels_preview] + [14])
                    cols = min(cols, max(14, max_ch_size))
                matrix_dims = [rows, cols]
            except Exception:
                matrix_dims = [6, 22] if rdevice.type == "keyboard" else [6, 16]

        # Channels (for Razer Chroma Addressable RGB Controller)
        channels = self._get_argb_channels(rdevice)

        # Lighting effect state
        effects = self._get_supported_effects(rdevice)
        zones = self._get_device_zones(rdevice)
        has_lighting = bool(len(effects) > 0 or has_brightness or has_matrix)
        lighting_state = self._read_hardware_lighting_state(rdevice, effects, zones) if has_lighting else {
            "current_effect": "none",
            "breath_mode": "single",
            "colors": [],
            "speed": "normal",
            "direction": "right",
            "supported_effects": [],
            "zones": []
        }
        cache["lighting"] = lighting_state
        if has_lighting and "user_set_lighting" not in cache:
            cache["user_set_lighting"] = True

        # Ensure ARGB controller animator is running if device has active lighting
        if self._is_argb_controller(rdevice) and serial not in self.argb_animators:
            eff = lighting_state.get("current_effect", "static")
            if eff != "none":
                cols_hex = lighting_state.get("colors", ["#fafafa", "#4ade80"])
                rgb_cols = [self._hex_to_rgb(c) for c in cols_hex]
                self._drive_argb_effect(
                    rdevice,
                    eff,
                    rgb_cols,
                    lighting_state.get("speed", "normal"),
                    lighting_state.get("direction", "right"),
                    lighting_state.get("breath_mode", "single")
                )

        # Button Remapping support (for Razer mice)
        evdev_paths = self._find_evdev_paths_for_device(rdevice.name)
        has_buttons = bool(rdevice.type == "mouse" and evdev_paths is not None)
        buttons = []
        if has_buttons:
            saved_map = {m["id"]: m for m in self.button_mappings.get(serial, [])}
            for btn_def in DEFAULT_MOUSE_BUTTONS:
                bid = btn_def["id"]
                if bid in saved_map:
                    buttons.append({
                        "id": bid,
                        "label": btn_def["label"],
                        "action": saved_map[bid].get("action", "default"),
                        "value": saved_map[bid].get("value", "")
                    })
                else:
                    buttons.append(dict(btn_def))

        # Game mode
        game_mode = None
        if rdevice.has("game_mode_led"):
            try:
                game_mode = bool(rdevice.game_mode_led)
            except Exception:
                game_mode = cache.get("game_mode", False)

        return {
            "id": serial,
            "name": rdevice.name,
            "serial": serial,
            "type": rdevice.type,
            "firmware": getattr(rdevice, "firmware_version", "v1.0"),
            "driver": getattr(rdevice, "driver_version", "3.12.4"),
            "has_battery": has_battery,
            "battery": battery,
            "is_charging": is_charging,
            "idle_time": idle_time,
            "low_battery_threshold": low_battery_threshold,
            "has_dpi": has_dpi,
            "dpi": dpi,
            "max_dpi": max_dpi,
            "dpi_stages": dpi_stages,
            "active_dpi_stage": active_dpi_stage,
            "has_poll_rate": has_poll_rate,
            "poll_rate": poll_rate,
            "supported_poll_rates": supported_poll_rates,
            "has_brightness": has_brightness,
            "brightness": brightness,
            "has_matrix": has_matrix,
            "matrix_dimensions": matrix_dims,
            "has_lighting": has_lighting,
            "has_buttons": has_buttons,
            "buttons": buttons,
            "remapper_active": serial in self.active_remappers,
            "channels": channels,
            "game_mode": game_mode,
            "lighting": lighting_state
        }

    def list_devices(self):
        devices = []
        self._ensure_openrazer_ready()

        if self.devman:
            try:
                for rdev in self.devman.devices:
                    devices.append(self._serialize_device(rdev))
                if devices and not os.path.exists(self.settings_file):
                    self._save_device_settings()
                    self._save_lighting_state()
            except Exception as e:
                sys.stderr.write(f"Error listing devices: {e}\n")

        if self.mock_mode or len(devices) == 0:
            for mock in MOCK_DEVICES:
                devices.append(mock)

        return devices

    def _find_rdevice(self, serial):
        self._ensure_openrazer_ready()
        if not self.devman:
            return None
        for d in self.devman.devices:
            if d.serial == serial:
                return d
        return None

    def get_current_dpi_pair(self, serial):
        cache = self.device_state_cache.get(serial, {})
        return cache.get("dpi", [1600, 1600])

    def set_dpi(self, serial, x, y):
        x, y = int(x), int(y)
        rdev = self._find_rdevice(serial)
        if rdev and rdev.has("dpi"):
            try:
                rdev.dpi = (x, y)
            except Exception as e:
                sys.stderr.write(f"Error setting DPI on {serial}: {e}\n")
        cache = self.device_state_cache.setdefault(serial, {})
        cache["dpi"] = [x, y]
        cache["last_dpi_write"] = time.time()
        # Keep active stage in cache consistent with new DPI if stages are cached
        if "dpi_stages" in cache and cache["dpi_stages"]:
            matched_stage = None
            for idx, st in enumerate(cache["dpi_stages"]):
                if st[0] == x and st[1] == y:
                    matched_stage = idx + 1
                    break
            if matched_stage is not None:
                cache["active_dpi_stage"] = matched_stage
        self._save_device_settings()
        return {"status": "ok", "dpi": [x, y]}

    def set_dpi_stages(self, serial, active_stage, stages):
        active_stage = int(active_stage)
        clean_stages = [[int(s[0]), int(s[1])] for s in stages]
        rdev = self._find_rdevice(serial)
        if rdev and rdev.has("dpi_stages"):
            try:
                tuple_stages = [(s[0], s[1]) for s in clean_stages]
                rdev.dpi_stages = (active_stage, tuple_stages)
            except Exception as e:
                sys.stderr.write(f"Error setting dpi stages: {e}\n")
        cache = self.device_state_cache.setdefault(serial, {})
        cache["dpi_stages"] = clean_stages
        cache["active_dpi_stage"] = active_stage
        cache["last_dpi_write"] = time.time()
        if 1 <= active_stage <= len(clean_stages):
            cache["dpi"] = clean_stages[active_stage - 1]
        self._save_device_settings()
        return {"status": "ok", "active_stage": active_stage, "stages": clean_stages}

    def cycle_dpi_stage(self, serial, direction=1):
        cache = self.device_state_cache.setdefault(serial, {})
        stages = cache.get("dpi_stages", [[400, 400], [800, 800], [1600, 1600], [3200, 3200], [6400, 6400]])
        active = int(cache.get("active_dpi_stage", 1))
        next_idx = (active - 1 + direction) % len(stages)
        next_stage = next_idx + 1
        target_dpi = stages[next_idx]
        self.set_dpi(serial, target_dpi[0], target_dpi[1])
        self.set_dpi_stages(serial, next_stage, stages)
        return {"status": "ok", "active_stage": next_stage, "dpi": target_dpi}

    def set_poll_rate(self, serial, rate):
        rate = int(rate)
        rdev = self._find_rdevice(serial)
        if rdev and rdev.has("poll_rate"):
            try:
                rdev.poll_rate = rate
            except Exception as e:
                sys.stderr.write(f"Error setting poll rate: {e}\n")
        self.device_state_cache.setdefault(serial, {})["poll_rate"] = rate
        self._save_device_settings()
        return {"status": "ok", "poll_rate": rate}

    def cycle_poll_rate(self, serial):
        rdev = self._find_rdevice(serial)
        rates = [125, 500, 1000]
        if rdev and rdev.has("supported_poll_rates"):
            try:
                rates = [int(r) for r in rdev.supported_poll_rates]
            except Exception:
                pass
        cache = self.device_state_cache.setdefault(serial, {})
        cur = cache.get("poll_rate", 1000)
        idx = rates.index(cur) if cur in rates else 0
        nxt = rates[(idx + 1) % len(rates)]
        return self.set_poll_rate(serial, nxt)

    def _resolve_fx_zone(self, rdev, zone):
        if not rdev or not getattr(rdev, "fx", None):
            return None
        if not zone or zone in ("overall", "main"):
            return rdev.fx
        misc = getattr(rdev.fx, "misc", None)
        if misc:
            zone_map = {
                "logo": getattr(misc, "logo", None),
                "scroll": getattr(misc, "scroll_wheel", None),
                "left": getattr(misc, "left", None),
                "right": getattr(misc, "right", None),
                "backlight": getattr(misc, "backlight", None),
                "charging": getattr(misc, "charging", None),
            }
            if zone in zone_map and zone_map[zone] is not None:
                return zone_map[zone]
        return rdev.fx

    def set_brightness(self, serial, brightness, zone=None):
        brightness = max(0.0, min(100.0, float(brightness)))
        rdev = self._find_rdevice(serial)
        self.device_state_cache.setdefault(serial, {})["brightness"] = round(brightness)
        if rdev:
            try:
                if not self._is_argb_controller(rdev):
                    if zone and zone not in ("overall", "main"):
                        ztarget = self._resolve_fx_zone(rdev, zone)
                        if ztarget and hasattr(ztarget, "brightness"):
                            ztarget.brightness = brightness
                    elif rdev.has("brightness"):
                        rdev.brightness = brightness
            except Exception as e:
                sys.stderr.write(f"Error setting brightness: {e}\n")
        self._save_device_settings()
        return {"status": "ok", "brightness": round(brightness)}

    def set_channel(self, serial, channel, brightness=None, size=None):
        channel = int(channel)
        rdev = self._find_rdevice(serial)
        cache = self.device_state_cache.setdefault(serial, {})
        if rdev:
            try:
                avail = getattr(rdev, "_available_features", {})
                if "razer.device.lighting.channel" in avail:
                    ch_iface = dbus.Interface(rdev._dbus, "razer.device.lighting.channel")
                    if brightness is not None:
                        ch_iface.setChannelBrightness(channel, float(brightness))
                        if "channels" in cache and 1 <= channel <= len(cache["channels"]):
                            cache["channels"][channel - 1]["brightness"] = round(float(brightness))
                    if size is not None:
                        sz_val = max(1, min(80, int(size)))
                        ch_iface.setChannelSize(channel, sz_val)
                        if "channel_sizes" in cache and 1 <= channel <= len(cache["channel_sizes"]):
                            cache["channel_sizes"][channel - 1] = sz_val
                        if "channels" in cache and 1 <= channel <= len(cache["channels"]):
                            cache["channels"][channel - 1]["size"] = sz_val
            except Exception as e:
                sys.stderr.write(f"Error configuring ARGB channel {channel}: {e}\n")
                return {"status": "error", "message": str(e)}
        return {"status": "ok", "channel": channel, "brightness": brightness, "size": size}

    def _hex_to_rgb(self, hex_str):
        hex_str = str(hex_str).lstrip("#")
        if len(hex_str) == 3:
            hex_str = "".join([c * 2 for c in hex_str])
        if len(hex_str) != 6:
            return 255, 255, 255
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

    def set_effect(self, serial, effect, colors=None, speed="normal", direction="right", zone="overall", breath_mode="single"):
        colors = [str(c) for c in (colors or ["#fafafa", "#4ade80"])]
        while len(colors) < 2:
            colors.append("#4ade80")
        rgb_colors = [self._hex_to_rgb(c) for c in colors]
        rdev = self._find_rdevice(serial)
        cache = self.device_state_cache.setdefault(serial, {})

        if rdev and getattr(rdev, "fx", None):
            # For the Razer Chroma Addressable RGB Controller (1532:0F1F), drive all 6 ARGB channels directly
            # via per-channel custom frames / software animator to bypass the kernel driver's ZERO_LED and single-row bugs.
            if self._is_argb_controller(rdev):
                if effect != "none" and cache.get("brightness", 100) < 10:
                    cache["brightness"] = 100
                try:
                    self._drive_argb_effect(rdev, effect, rgb_colors, speed, direction, breath_mode)
                except Exception as e:
                    sys.stderr.write(f"Error driving ARGB controller {serial}: {e}\n")
            else:
                # Always ensure hardware brightness is written when turning on an effect
                # (on wireless mice like Pro Click V2 Vertical, openrazer's get_brightness returns cached persistence
                # even if hardware LED brightness register was dimmed or zeroed).
                if effect != "none" and rdev.has("brightness"):
                    try:
                        target_br = float(cache.get("brightness", 100))
                        if target_br < 10.0:
                            target_br = 100.0
                            cache["brightness"] = 100
                        rdev.brightness = target_br
                    except Exception:
                        pass

                fx_target = self._resolve_fx_zone(rdev, zone)
                speed_map = {"fast": 1, "normal": 2, "slow": 3, "ultra": 4}
                spd = speed_map.get(speed, 2)

                try:
                    if effect == "none" and hasattr(fx_target, "none"):
                        fx_target.none()
                    elif effect == "static" and hasattr(fx_target, "static"):
                        r, g, b = rgb_colors[0]
                        fx_target.static(r, g, b)
                    elif effect == "spectrum" and hasattr(fx_target, "spectrum"):
                        fx_target.spectrum()
                    elif effect == "wave" and hasattr(fx_target, "wave"):
                        dir_val = 1 if direction in ("right", "up", "clockwise") else 2
                        fx_target.wave(dir_val)
                    elif effect == "wheel" and hasattr(fx_target, "wheel"):
                        dir_val = 1 if direction in ("right", "clockwise") else 2
                        fx_target.wheel(dir_val)
                    elif effect == "breath":
                        if breath_mode == "random" and hasattr(fx_target, "breath_random"):
                            fx_target.breath_random()
                        elif breath_mode == "dual" and hasattr(fx_target, "breath_dual"):
                            r1, g1, b1 = rgb_colors[0]
                            r2, g2, b2 = rgb_colors[1]
                            fx_target.breath_dual(r1, g1, b1, r2, g2, b2)
                        elif hasattr(fx_target, "breath_single"):
                            r, g, b = rgb_colors[0]
                            fx_target.breath_single(r, g, b)
                        elif hasattr(fx_target, "breath_random"):
                            fx_target.breath_random()
                    elif effect == "reactive" and hasattr(fx_target, "reactive"):
                        r, g, b = rgb_colors[0]
                        fx_target.reactive(r, g, b, spd)
                    elif effect == "ripple":
                        if breath_mode == "random" and hasattr(fx_target, "ripple_random"):
                            fx_target.ripple_random()
                        elif hasattr(fx_target, "ripple"):
                            r, g, b = rgb_colors[0]
                            fx_target.ripple(r, g, b)
                    elif effect == "starlight":
                        st_spd = min(3, max(1, spd))
                        if breath_mode == "random" and hasattr(fx_target, "starlight_random"):
                            fx_target.starlight_random(st_spd)
                        elif breath_mode == "dual" and hasattr(fx_target, "starlight_dual"):
                            r1, g1, b1 = rgb_colors[0]
                            r2, g2, b2 = rgb_colors[1]
                            fx_target.starlight_dual(r1, g1, b1, r2, g2, b2, st_spd)
                        elif hasattr(fx_target, "starlight_single"):
                            r, g, b = rgb_colors[0]
                            fx_target.starlight_single(r, g, b, st_spd)
                    elif effect == "matrix" and rdev.has("lighting_led_matrix"):
                        r, g, b = rgb_colors[0]
                        rows = int(rdev.fx.advanced.rows)
                        cols = int(rdev.fx.advanced.cols)
                        for row_idx in range(rows):
                            for col_idx in range(cols):
                                rdev.fx.advanced.matrix[row_idx, col_idx] = (r, g, b)
                        rdev.fx.advanced.draw()
                except Exception as e:
                    sys.stderr.write(f"Error applying effect {effect} on {serial}: {e}\n")

        cache["user_set_lighting"] = True
        lighting_cache = cache.setdefault("lighting", {})
        lighting_cache.update({
            "current_effect": effect,
            "breath_mode": breath_mode,
            "colors": colors,
            "speed": speed,
            "direction": direction,
            "zone": zone
        })
        self._save_lighting_state()
        self._save_device_settings()
        return {"status": "ok", "effect": effect, "colors": colors, "breath_mode": breath_mode}

    def set_matrix(self, serial, grid):
        rdev = self._find_rdevice(serial)
        if not rdev or not rdev.has("lighting_led_matrix"):
            return {"status": "error", "message": "Device does not support addressable LED matrix"}

        try:
            self._stop_argb_animator(serial)
            cache = self.device_state_cache.setdefault(serial, {})
            if cache.get("brightness", 100) < 10:
                cache["brightness"] = 100

            hw_rows = int(rdev.fx.advanced.rows)
            hw_cols = int(rdev.fx.advanced.cols)

            if self._is_argb_controller(rdev):
                raw_rows = []
                for r_idx in range(hw_rows):
                    row_cells = grid[r_idx] if r_idx < len(grid) and grid[r_idx] else []
                    row_rgb_list = []
                    for c_idx in range(len(row_cells)):
                        hex_col = row_cells[c_idx]
                        if str(hex_col).lower() in ("#141414", "#000000", "#0a0a0a"):
                            row_rgb_list.append((0, 0, 0))
                        else:
                            row_rgb_list.append(self._hex_to_rgb(hex_col))
                    if not row_rgb_list:
                        row_rgb_list = [(0, 0, 0)]
                    # Tile/extend painted pattern across all 80 addressable LEDs of the channel
                    full_row = bytearray()
                    for c_idx in range(hw_cols):
                        rgb = row_rgb_list[c_idx] if c_idx < len(row_rgb_list) else row_rgb_list[-1]
                        full_row.extend(rgb)
                    raw_rows.append(bytes(full_row))
                self._drive_argb_effect(rdev, "matrix", [(250, 250, 250)], custom_rows=raw_rows)
            else:
                if rdev.has("brightness"):
                    try:
                        rdev.brightness = float(cache.get("brightness", 100))
                    except Exception:
                        pass
                rdev.fx.advanced.matrix.reset()
                for r_idx in range(min(hw_rows, len(grid))):
                    row_cells = grid[r_idx]
                    if not row_cells:
                        continue
                    for c_idx in range(min(hw_cols, len(row_cells))):
                        hex_col = row_cells[c_idx]
                        if str(hex_col).lower() in ("#141414", "#000000", "#0a0a0a"):
                            rgb = (0, 0, 0)
                        else:
                            rgb = self._hex_to_rgb(hex_col)
                        rdev.fx.advanced.matrix[r_idx, c_idx] = rgb
                rdev.fx.advanced.draw()

            cache["user_set_lighting"] = True
            cache.setdefault("lighting", {})["current_effect"] = "matrix"
            self._save_lighting_state()
            self._save_device_settings()
            return {"status": "ok", "rows": hw_rows, "cols": hw_cols}
        except Exception as e:
            sys.stderr.write(f"Error applying custom matrix on {serial}: {e}\n")
            return {"status": "error", "message": str(e)}

    def set_button_mappings(self, serial, mappings):
        clean_mappings = []
        left_Default = False
        for m in mappings:
            bid = m.get("id")
            action = m.get("action", "default")
            val = m.get("value", "")
            if bid == "btn_left" and (action == "default" or (action == "mouse" and val == "btn_left")):
                left_Default = True
            clean_mappings.append({
                "id": bid,
                "label": m.get("label", bid),
                "action": action,
                "value": val
            })

        # Safety check: ensure Left Click isn't remapped unless another button is mapped to Left Click
        has_any_left = left_Default or any(
            m["action"] == "mouse" and m["value"] == "btn_left" for m in clean_mappings
        )
        if not has_any_left:
            for m in clean_mappings:
                if m["id"] == "btn_left":
                    m["action"] = "default"
                    m["value"] = ""

        self.button_mappings[serial] = clean_mappings
        self._save_button_mappings()

        rdev = self._find_rdevice(serial)
        dev_name = rdev.name if rdev else ""
        active = self._sync_remapper_for_device(serial, dev_name) if dev_name else False
        return {"status": "ok", "serial": serial, "remapper_active": active, "buttons": clean_mappings}

    def set_power(self, serial, idle_time=None, low_battery_threshold=None):
        rdev = self._find_rdevice(serial)
        cache = self.device_state_cache.setdefault(serial, {})
        if rdev:
            if idle_time is not None and (rdev.has("idle_time") or rdev.has("set_idle_time")):
                try:
                    mins = max(1, min(15, int(idle_time)))
                    rdev.set_idle_time(mins * 60)
                    cache["idle_time"] = mins
                except Exception as e:
                    sys.stderr.write(f"Error setting idle time: {e}\n")
            if low_battery_threshold is not None and (rdev.has("low_battery_threshold") or rdev.has("set_low_battery_threshold")):
                try:
                    thresh = max(5, min(100, int(low_battery_threshold)))
                    rdev.set_low_battery_threshold(thresh)
                    cache["low_battery_threshold"] = thresh
                except Exception as e:
                    sys.stderr.write(f"Error setting low battery threshold: {e}\n")
        self._save_device_settings()
        return {"status": "ok", "idle_time": idle_time, "low_battery_threshold": low_battery_threshold}

    def get_autostart(self):
        autostart_desktop = os.path.expanduser("~/.config/autostart/razerd.desktop")
        systemd_service = os.path.expanduser("~/.config/systemd/user/razerd.service")
        enabled = os.path.exists(systemd_service) or os.path.exists(autostart_desktop)
        return {"status": "ok", "enabled": enabled}

    def set_autostart(self, enabled=True, start_minimized=True):
        enabled = bool(enabled)
        autostart_dir = os.path.expanduser("~/.config/autostart")
        systemd_dir = os.path.expanduser("~/.config/systemd/user")
        autostart_desktop = os.path.join(autostart_dir, "razerd.desktop")
        systemd_service = os.path.join(systemd_dir, "razerd.service")
        launcher_bin = os.path.expanduser("~/.local/bin/razerd")
        flag = " --minimized" if start_minimized else ""

        # Always ensure Polychromatic autostart stays disabled so it doesn't conflict
        try:
            os.makedirs(autostart_dir, exist_ok=True)
            poly_desktop = os.path.join(autostart_dir, "polychromatic-autostart.desktop")
            with open(poly_desktop, "w") as f:
                f.write("[Desktop Entry]\nType=Application\nName=Polychromatic Autostart\nExec=polychromatic-helper --autostart\nHidden=true\nX-GNOME-Autostart-enabled=false\n")
            subprocess.run(["systemctl", "--user", "disable", "--now", "polychromatic.service"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except Exception:
            pass

        if enabled:
            try:
                # Remove duplicate XDG autostart desktop file so systemd user service is the single clean launcher
                if os.path.exists(autostart_desktop):
                    try:
                        os.remove(autostart_desktop)
                    except Exception:
                        pass

                os.makedirs(systemd_dir, exist_ok=True)
                service_content = (
                    "[Unit]\n"
                    "Description=RazerD Background Hardware Controller & Tray Applet\n"
                    "PartOf=graphical-session.target\n"
                    "After=graphical-session.target openrazer-daemon.service waybar.service\n"
                    "Wants=openrazer-daemon.service\n\n"
                    "[Service]\n"
                    "Type=simple\n"
                    "ExecStartPre=/bin/sh -c 'for i in $(seq 1 30); do busctl --user list 2>/dev/null | grep -q \"StatusNotifierWatcher\" && busctl --user list 2>/dev/null | grep -q \"org.razer\" && break; sleep 0.5; done'\n"
                    f"ExecStart={launcher_bin}{flag}\n"
                    "Restart=on-failure\n"
                    "RestartSec=3\n\n"
                    "[Install]\n"
                    "WantedBy=graphical-session.target\n"
                )
                with open(systemd_service, "w") as f:
                    f.write(service_content)
                subprocess.run(["systemctl", "--user", "daemon-reload"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                subprocess.run(["systemctl", "--user", "enable", "razerd.service"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except Exception as e:
                sys.stderr.write(f"Error enabling autostart: {e}\n")
                return {"status": "error", "message": str(e)}
        else:
            try:
                if os.path.exists(autostart_desktop):
                    os.remove(autostart_desktop)
                subprocess.run(["systemctl", "--user", "disable", "razerd.service"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                if os.path.exists(systemd_service):
                    os.remove(systemd_service)
                subprocess.run(["systemctl", "--user", "daemon-reload"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except Exception as e:
                sys.stderr.write(f"Error disabling autostart: {e}\n")

        return {"status": "ok", "enabled": enabled}

    def set_game_mode(self, serial, enable):
        enable = bool(enable)
        rdev = self._find_rdevice(serial)
        if rdev and hasattr(rdev, "game_mode_led"):
            try:
                rdev.game_mode_led = enable
            except Exception:
                pass
        self.device_state_cache.setdefault(serial, {})["game_mode"] = enable
        return {"status": "ok", "game_mode": enable}

    def sync_rgb(self, effect, colors=None, speed="normal", direction="right", breath_mode="single"):
        colors = colors or ["#fafafa", "#4ade80"]
        devices = self.list_devices()
        results = []
        for dev in devices:
            if dev.get("has_lighting"):
                res = self.set_effect(dev["serial"], effect, colors, speed, direction, "overall", breath_mode)
                results.append({"serial": dev["serial"], "result": res})
        return {"status": "ok", "synced": len(results), "details": results}

    def restart_daemon(self):
        try:
            if self.devman:
                try:
                    self.devman.stop_daemon()
                except Exception:
                    pass
            subprocess.run(["systemctl", "--user", "restart", "openrazer-daemon.service"], check=False)
            time.sleep(1.0)
            self._settings_restored = False
            self._ensure_openrazer_ready()
            return {"status": "ok", "restarted": True}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def toggle_mock(self, enable=None):
        if enable is None:
            self.mock_mode = not self.mock_mode
        else:
            self.mock_mode = bool(enable)
        return {"status": "ok", "mock_mode": self.mock_mode}


def main():
    bridge = RazerBridge()

    def _sig_handler(signum, frame):
        bridge.stop_all_remappers()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _sig_handler)
    signal.signal(signal.SIGINT, _sig_handler)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            action = req.get("action")
            params = req.get("params", {})

            result = None
            error = None

            if action == "ping":
                result = "pong"
            elif action == "get_status":
                result = bridge.get_status()
            elif action == "list_devices":
                result = bridge.list_devices()
            elif action == "set_dpi":
                result = bridge.set_dpi(params.get("serial"), params.get("x"), params.get("y"))
            elif action == "set_dpi_stages":
                result = bridge.set_dpi_stages(params.get("serial"), params.get("active", 1), params.get("stages", []))
            elif action == "set_poll_rate":
                result = bridge.set_poll_rate(params.get("serial"), params.get("rate"))
            elif action == "set_brightness":
                result = bridge.set_brightness(params.get("serial"), params.get("brightness"), params.get("zone"))
            elif action == "set_channel":
                result = bridge.set_channel(
                    params.get("serial"),
                    params.get("channel"),
                    params.get("brightness"),
                    params.get("size")
                )
            elif action == "set_effect":
                result = bridge.set_effect(
                    params.get("serial"),
                    params.get("effect"),
                    params.get("colors"),
                    params.get("speed", "normal"),
                    params.get("direction", "right"),
                    params.get("zone", "overall"),
                    params.get("breath_mode", "single")
                )
            elif action == "set_matrix":
                result = bridge.set_matrix(params.get("serial"), params.get("grid", []))
            elif action == "set_button_mappings":
                result = bridge.set_button_mappings(params.get("serial"), params.get("buttons", []))
            elif action == "set_power":
                result = bridge.set_power(params.get("serial"), params.get("idle_time"), params.get("low_battery_threshold"))
            elif action == "set_game_mode":
                result = bridge.set_game_mode(params.get("serial"), params.get("enable"))
            elif action == "sync_rgb":
                result = bridge.sync_rgb(
                    params.get("effect"),
                    params.get("colors"),
                    params.get("speed", "normal"),
                    params.get("direction", "right"),
                    params.get("breath_mode", "single")
                )
            elif action == "restart_daemon":
                result = bridge.restart_daemon()
            elif action == "toggle_mock":
                result = bridge.toggle_mock(params.get("enable"))
            elif action == "get_autostart":
                result = bridge.get_autostart()
            elif action == "set_autostart":
                result = bridge.set_autostart(params.get("enabled", True), params.get("start_minimized", True))
            else:
                error = f"Unknown action: {action}"

            resp = {"id": req_id}
            if error:
                resp["error"] = error
            else:
                resp["result"] = result

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Exception processing request: {traceback.format_exc()}\n")
            sys.stdout.write(json.dumps({"id": req.get("id") if 'req' in locals() else None, "error": str(e)}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
