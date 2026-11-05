#!/usr/bin/env python3
"""
razerd Python Daemon Bridge
Interfaces with openrazer.client to provide real-time control, monitoring,
and diagnostics for Razer hardware, exposed to Electron via JSON-RPC over stdin/stdout.
"""

import sys
import os
import json
import traceback
import subprocess

try:
    import openrazer.client
    HAS_OPENRAZER = True
except ImportError:
    HAS_OPENRAZER = False

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
        "game_mode": True,
        "lighting": {
            "current_effect": "spectrum",
            "colors": ["#fafafa"],
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
        "game_mode": False,
        "lighting": {
            "current_effect": "wave",
            "colors": ["#4ade80"],
            "speed": "normal",
            "direction": "right",
            "supported_effects": ["none", "static", "breath", "spectrum", "wave", "reactive", "matrix"],
            "zones": ["overall"]
        }
    }
]


class RazerBridge:
    def __init__(self):
        self.devman = None
        self.mock_mode = False
        self.device_state_cache = {}
        self._init_openrazer()

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

    def get_status(self):
        """Diagnose OpenRazer daemon, kernel modules, and permissions."""
        daemon_version = None
        daemon_running = False
        if self.devman:
            try:
                daemon_version = self.devman.version
                daemon_running = True
            except Exception:
                pass

        # Check kernel modules
        modules = {}
        for mod in ["razerkbd", "razermouse", "razeraccessory", "razerkraken"]:
            try:
                res = subprocess.run(["lsmod"], stdout=subprocess.PIPE, text=True, check=False)
                modules[mod] = mod in res.stdout
            except Exception:
                modules[mod] = False

        # Check plugdev group
        in_plugdev = False
        try:
            groups_res = subprocess.run(["groups"], stdout=subprocess.PIPE, text=True, check=False)
            in_plugdev = "plugdev" in groups_res.stdout
        except Exception:
            pass

        # Check connected Razer USB devices
        usb_devices = []
        try:
            lsusb_res = subprocess.run(["lsusb"], stdout=subprocess.PIPE, text=True, check=False)
            for line in lsusb_res.stdout.splitlines():
                if "1532:" in line:
                    usb_devices.append(line.strip())
        except Exception:
            pass

        return {
            "has_openrazer_lib": HAS_OPENRAZER,
            "daemon_running": daemon_running,
            "daemon_version": daemon_version,
            "kernel_modules": modules,
            "in_plugdev_group": in_plugdev,
            "usb_devices": usb_devices,
            "mock_mode": self.mock_mode
        }

    def _get_supported_effects(self, rdevice):
        caps = rdevice.capabilities
        effects = []
        if caps.get("lighting_none", False):
            effects.append("none")
        if caps.get("lighting_static", False):
            effects.append("static")
        if any([caps.get("lighting_breath_single", False), caps.get("lighting_breath_dual", False), caps.get("lighting_breath_random", False)]):
            effects.append("breath")
        if caps.get("lighting_spectrum", False):
            effects.append("spectrum")
        if caps.get("lighting_wave", False):
            effects.append("wave")
        if caps.get("lighting_reactive", False):
            effects.append("reactive")
        if caps.get("lighting_ripple", False) or caps.get("lighting_ripple_random", False):
            effects.append("ripple")
        if caps.get("lighting_starlight_single", False) or caps.get("lighting_starlight_dual", False):
            effects.append("starlight")
        if caps.get("lighting_wheel", False):
            effects.append("wheel")
        if caps.get("lighting_led_matrix", False):
            effects.append("matrix")
        if not effects and caps.get("lighting", False):
            # Fallback standard set if general lighting supported
            effects = ["none", "static", "spectrum"]
        return effects

    def _get_device_zones(self, rdevice):
        zones = ["overall"]
        caps = rdevice.capabilities
        if caps.get("lighting_logo", False):
            zones.append("logo")
        if caps.get("lighting_scroll", False):
            zones.append("scroll")
        if caps.get("lighting_left", False):
            zones.append("left")
        if caps.get("lighting_right", False):
            zones.append("right")
        if caps.get("lighting_backlight", False):
            zones.append("backlight")
        return zones

    def _serialize_device(self, rdevice):
        serial = rdevice.serial
        cache = self.device_state_cache.get(serial, {})

        # Battery
        has_battery = rdevice.has("battery")
        battery = None
        is_charging = None
        if has_battery:
            try:
                battery = rdevice.battery_level
                is_charging = rdevice.is_charging
            except Exception:
                battery = cache.get("battery", 0)
                is_charging = cache.get("is_charging", False)

        # Idle time & low battery threshold
        idle_time = None
        low_battery_threshold = None
        if rdevice.has("idle_time"):
            try:
                idle_time = rdevice.get_idle_time()
            except Exception:
                idle_time = 15
        if rdevice.has("low_battery_threshold"):
            try:
                low_battery_threshold = rdevice.get_low_battery_threshold()
            except Exception:
                low_battery_threshold = 10

        # DPI
        has_dpi = rdevice.has("dpi")
        dpi = None
        max_dpi = None
        dpi_stages = None
        active_dpi_stage = cache.get("active_dpi_stage", 1)
        if has_dpi:
            try:
                dpi = list(rdevice.dpi)
                max_dpi = int(rdevice.max_dpi)
            except Exception:
                dpi = [1600, 1600]
                max_dpi = 20000

            # Default or cached stages
            if "dpi_stages" in cache:
                dpi_stages = cache["dpi_stages"]
            else:
                base = max_dpi if max_dpi else 16000
                if base >= 30000:
                    dpi_stages = [[400, 400], [800, 800], [1600, 1600], [3200, 3200], [6400, 6400]]
                else:
                    dpi_stages = [[400, 400], [800, 800], [1800, 1800], [4500, 4500], [9000, 9000]]

        # Poll rate
        has_poll_rate = rdevice.has("poll_rate")
        poll_rate = None
        supported_poll_rates = []
        if has_poll_rate:
            try:
                poll_rate = int(rdevice.poll_rate)
            except Exception:
                poll_rate = 1000
            if rdevice.has("supported_poll_rates"):
                try:
                    supported_poll_rates = list(rdevice.supported_poll_rates)
                except Exception:
                    supported_poll_rates = [125, 500, 1000]
            else:
                supported_poll_rates = [125, 500, 1000]

        # Brightness
        has_brightness = rdevice.has("brightness")
        brightness = None
        if has_brightness:
            try:
                brightness = float(rdevice.brightness)
            except Exception:
                brightness = cache.get("brightness", 100.0)

        # Matrix
        has_matrix = rdevice.has("lighting_led_matrix")
        matrix_dims = None
        if has_matrix:
            # Check dimensions if exposed or estimate by type
            fx = getattr(rdevice, "fx", None)
            matrix_dims = [6, 22] if rdevice.type == "keyboard" else [1, 16]

        # Game mode
        game_mode = None
        if rdevice.has("game_mode_led") or rdevice.type == "keyboard":
            game_mode = cache.get("game_mode", False)

        # Lighting effect state
        effects = self._get_supported_effects(rdevice)
        zones = self._get_device_zones(rdevice)
        lighting_state = cache.get("lighting", {
            "current_effect": "static" if "static" in effects else (effects[0] if effects else "none"),
            "colors": ["#fafafa"],
            "speed": "normal",
            "direction": "right",
            "supported_effects": effects,
            "zones": zones
        })
        lighting_state["supported_effects"] = effects
        lighting_state["zones"] = zones

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
            "game_mode": game_mode,
            "lighting": lighting_state
        }

    def list_devices(self):
        devices = []
        if self.devman:
            try:
                for rdev in self.devman.devices:
                    devices.append(self._serialize_device(rdev))
            except Exception as e:
                sys.stderr.write(f"Error listing devices: {e}\n")

        # If mock mode is active, or if 0 devices found, append mock devices
        if self.mock_mode or len(devices) == 0:
            for mock in MOCK_DEVICES:
                devices.append(mock)

        return devices

    def _find_rdevice(self, serial):
        if not self.devman:
            return None
        for d in self.devman.devices:
            if d.serial == serial:
                return d
        return None

    def set_dpi(self, serial, x, y):
        x, y = int(x), int(y)
        rdev = self._find_rdevice(serial)
        if rdev and rdev.has("dpi"):
            rdev.dpi = (x, y)
        if serial not in self.device_state_cache:
            self.device_state_cache[serial] = {}
        self.device_state_cache[serial]["dpi"] = [x, y]
        return {"status": "ok", "dpi": [x, y]}

    def set_dpi_stages(self, serial, active_stage, stages):
        active_stage = int(active_stage)
        rdev = self._find_rdevice(serial)
        if rdev and rdev.has("dpi_stages"):
            try:
                tuple_stages = [(int(s[0]), int(s[1])) for s in stages]
                rdev.dpi_stages = (active_stage, tuple_stages)
            except Exception as e:
                sys.stderr.write(f"Error setting dpi stages: {e}\n")
        if serial not in self.device_state_cache:
            self.device_state_cache[serial] = {}
        self.device_state_cache[serial]["dpi_stages"] = stages
        self.device_state_cache[serial]["active_dpi_stage"] = active_stage
        return {"status": "ok", "active_stage": active_stage, "stages": stages}

    def set_poll_rate(self, serial, rate):
        rate = int(rate)
        rdev = self._find_rdevice(serial)
        if rdev and rdev.has("poll_rate"):
            rdev.poll_rate = rate
        if serial not in self.device_state_cache:
            self.device_state_cache[serial] = {}
        self.device_state_cache[serial]["poll_rate"] = rate
        return {"status": "ok", "poll_rate": rate}

    def set_brightness(self, serial, brightness, zone=None):
        brightness = float(brightness)
        rdev = self._find_rdevice(serial)
        if rdev and rdev.has("brightness"):
            rdev.brightness = brightness
        if serial not in self.device_state_cache:
            self.device_state_cache[serial] = {}
        self.device_state_cache[serial]["brightness"] = brightness
        return {"status": "ok", "brightness": brightness}

    def _hex_to_rgb(self, hex_str):
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 3:
            hex_str = "".join([c * 2 for c in hex_str])
        if len(hex_str) != 6:
            return 255, 255, 255
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

    def set_effect(self, serial, effect, colors=None, speed="normal", direction="right", zone="overall"):
        colors = colors or ["#fafafa"]
        rgb_colors = [self._hex_to_rgb(c) for c in colors]
        rdev = self._find_rdevice(serial)

        if rdev and getattr(rdev, "fx", None):
            fx_target = rdev.fx
            if zone and zone != "overall" and hasattr(rdev.fx, zone):
                fx_target = getattr(rdev.fx, zone)

            try:
                if effect == "none" and hasattr(fx_target, "none"):
                    fx_target.none()
                elif effect == "static" and hasattr(fx_target, "static"):
                    r, g, b = rgb_colors[0]
                    fx_target.static(r, g, b)
                elif effect == "spectrum" and hasattr(fx_target, "spectrum"):
                    fx_target.spectrum()
                elif effect == "wave" and hasattr(fx_target, "wave"):
                    dir_val = 1 if direction == "right" else 2
                    fx_target.wave(dir_val)
                elif effect == "breath":
                    if len(rgb_colors) == 1 and hasattr(fx_target, "breath_single"):
                        r, g, b = rgb_colors[0]
                        fx_target.breath_single(r, g, b)
                    elif len(rgb_colors) >= 2 and hasattr(fx_target, "breath_dual"):
                        r1, g1, b1 = rgb_colors[0]
                        r2, g2, b2 = rgb_colors[1]
                        fx_target.breath_dual(r1, g1, b1, r2, g2, b2)
                    elif hasattr(fx_target, "breath_random"):
                        fx_target.breath_random()
                elif effect == "reactive" and hasattr(fx_target, "reactive"):
                    speed_map = {"slow": 1, "normal": 2, "fast": 3, "ultra": 4}
                    spd = speed_map.get(speed, 2)
                    r, g, b = rgb_colors[0]
                    fx_target.reactive(spd, r, g, b)
                elif effect == "ripple" and hasattr(fx_target, "ripple"):
                    r, g, b = rgb_colors[0]
                    fx_target.ripple(r, g, b)
            except Exception as e:
                sys.stderr.write(f"Error applying effect {effect}: {e}\n")

        if serial not in self.device_state_cache:
            self.device_state_cache[serial] = {}
        self.device_state_cache[serial]["lighting"] = {
            "current_effect": effect,
            "colors": colors,
            "speed": speed,
            "direction": direction,
            "zone": zone
        }
        return {"status": "ok", "effect": effect, "colors": colors}

    def set_power(self, serial, idle_time=None, low_battery_threshold=None):
        rdev = self._find_rdevice(serial)
        if rdev:
            if idle_time is not None and rdev.has("idle_time"):
                try:
                    rdev.set_idle_time(int(idle_time))
                except Exception as e:
                    sys.stderr.write(f"Error setting idle time: {e}\n")
            if low_battery_threshold is not None and rdev.has("low_battery_threshold"):
                try:
                    rdev.set_low_battery_threshold(int(low_battery_threshold))
                except Exception as e:
                    sys.stderr.write(f"Error setting low battery threshold: {e}\n")
        return {"status": "ok", "idle_time": idle_time, "low_battery_threshold": low_battery_threshold}

    def set_game_mode(self, serial, enable):
        enable = bool(enable)
        rdev = self._find_rdevice(serial)
        if rdev and hasattr(rdev, "game_mode_led"):
            try:
                rdev.game_mode_led = enable
            except Exception:
                pass
        if serial not in self.device_state_cache:
            self.device_state_cache[serial] = {}
        self.device_state_cache[serial]["game_mode"] = enable
        return {"status": "ok", "game_mode": enable}

    def sync_rgb(self, effect, colors=None, speed="normal", direction="right"):
        colors = colors or ["#fafafa"]
        devices = self.list_devices()
        results = []
        for dev in devices:
            res = self.set_effect(dev["serial"], effect, colors, speed, direction, "overall")
            results.append({"serial": dev["serial"], "result": res})
        return {"status": "ok", "synced": len(results), "details": results}

    def restart_daemon(self):
        try:
            # Stop daemon via DBus if possible
            if self.devman:
                try:
                    self.devman.stop_daemon()
                except Exception:
                    pass
            # Also try systemctl restart for user service
            subprocess.run(["systemctl", "--user", "restart", "openrazer-daemon.service"], check=False)
            self._init_openrazer()
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
    # Continuous loop reading JSON lines from stdin
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
            elif action == "set_effect":
                result = bridge.set_effect(
                    params.get("serial"),
                    params.get("effect"),
                    params.get("colors"),
                    params.get("speed", "normal"),
                    params.get("direction", "right"),
                    params.get("zone", "overall")
                )
            elif action == "set_power":
                result = bridge.set_power(params.get("serial"), params.get("idle_time"), params.get("low_battery_threshold"))
            elif action == "set_game_mode":
                result = bridge.set_game_mode(params.get("serial"), params.get("enable"))
            elif action == "sync_rgb":
                result = bridge.sync_rgb(
                    params.get("effect"),
                    params.get("colors"),
                    params.get("speed", "normal"),
                    params.get("direction", "right")
                )
            elif action == "restart_daemon":
                result = bridge.restart_daemon()
            elif action == "toggle_mock":
                result = bridge.toggle_mock(params.get("enable"))
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
