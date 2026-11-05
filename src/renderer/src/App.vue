<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import AppHeader from './components/AppHeader.vue';
import DeviceSelector from './components/DeviceSelector.vue';
import HeroStats from './components/HeroStats.vue';
import DpiControl from './components/DpiControl.vue';
import PollRateControl from './components/PollRateControl.vue';
import ButtonsControl from './components/ButtonsControl.vue';
import LightingControl from './components/LightingControl.vue';
import MatrixEditor from './components/MatrixEditor.vue';
import PowerControl from './components/PowerControl.vue';
import ProfilesControl from './components/ProfilesControl.vue';
import TroubleshooterControl from './components/TroubleshooterControl.vue';
import SettingsControl from './components/SettingsControl.vue';

const currentSection = ref('overview');
const devices = ref([]);
const selectedSerial = ref('');
const status = ref(null);
const daemonOnline = ref(true);
const mockMode = ref(false);
const notification = ref(null);

const LEGACY_PRESET_IDS = new Set(['prof-comp', 'prof-stealth', 'prof-office', 'prof-chroma']);

function createDefaultProfile() {
  return {
    id: 'prof-default',
    name: 'Default',
    desc: 'Default hardware configuration.',
    dpi: [800, 800],
    dpi_stages: [[400, 400], [800, 800], [1600, 1600], [3200, 3200], [6400, 6400]],
    active_dpi_stage: 2,
    poll_rate: 1000,
    brightness: 100,
    effect: 'static',
    breath_mode: 'single',
    colors: ['#fafafa', '#4ade80'],
    speed: 'normal',
    direction: 'right',
    idle_time: 15,
    low_battery_threshold: 10,
    button_mappings: null
  };
}

const profiles = ref([createDefaultProfile()]);
const activeProfileId = ref('prof-default');

function saveProfilesToStorage() {
  try {
    localStorage.setItem('razerd-profiles-v2', JSON.stringify(profiles.value));
    localStorage.setItem('razerd-active-profile-v2', activeProfileId.value);
  } catch (e) {
    console.warn('Failed to persist profiles:', e);
  }
}

function loadProfilesFromStorage() {
  try {
    const savedV2 = localStorage.getItem('razerd-profiles-v2');
    if (savedV2) {
      const parsed = JSON.parse(savedV2);
      if (Array.isArray(parsed) && parsed.length > 0) {
        profiles.value = parsed;
      }
    } else {
      // Migrate any custom user-created profiles from v1, stripping out the old 4 demo presets
      const savedV1 = localStorage.getItem('razerd-profiles');
      const customFromV1 = [];
      if (savedV1) {
        try {
          const parsedV1 = JSON.parse(savedV1);
          if (Array.isArray(parsedV1)) {
            for (const p of parsedV1) {
              if (p && p.id && !LEGACY_PRESET_IDS.has(p.id)) {
                customFromV1.push(p);
              }
            }
          }
        } catch {}
      }
      profiles.value = [createDefaultProfile(), ...customFromV1];
      localStorage.removeItem('razerd-profiles');
    }

    const savedActive = localStorage.getItem('razerd-active-profile-v2');
    if (savedActive && profiles.value.some((p) => p.id === savedActive)) {
      activeProfileId.value = savedActive;
    } else {
      activeProfileId.value = profiles.value[0].id;
    }
    saveProfilesToStorage();
  } catch {
    profiles.value = [createDefaultProfile()];
    activeProfileId.value = 'prof-default';
  }
}

const activeProfile = computed(() => {
  return profiles.value.find((p) => p.id === activeProfileId.value) || profiles.value[0] || null;
});

function updateActiveProfile(patch) {
  const prof = activeProfile.value;
  if (!prof) return;
  Object.assign(prof, patch);
  saveProfilesToStorage();
}

let unsubscribeUpdates = null;
let browserPollTimer = null;
let lastMutationAt = 0;
let inFlightMutations = 0;
let toastTimer = null;

// Coalesce high-frequency slider updates so at most 1 IPC call per key is in flight
const coalescedLocks = new Map();
const coalescedNext = new Map();

async function runCoalesced(key, taskFn) {
  coalescedNext.set(key, taskFn);
  if (coalescedLocks.get(key)) {
    return;
  }
  coalescedLocks.set(key, true);
  try {
    while (coalescedNext.has(key)) {
      const fn = coalescedNext.get(key);
      coalescedNext.delete(key);
      await fn();
    }
  } finally {
    coalescedLocks.set(key, false);
  }
}

// Helper to safely invoke API (native Electron IPC or browser dev API)
async function apiCall(action, params = {}) {
  const isMutation = action !== 'list_devices' && action !== 'get_status';
  if (isMutation) {
    inFlightMutations++;
    lastMutationAt = Date.now();
  }
  try {
    if (window.razerAPI && window.razerAPI.call) {
      return await window.razerAPI.call(action, params);
    } else {
      try {
        const resp = await fetch('/api/bridge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action, params })
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        return data.result;
      } catch (e) {
        console.warn(`[Browser API fallback error]`, e);
        return null;
      }
    }
  } finally {
    if (isMutation) {
      inFlightMutations = Math.max(0, inFlightMutations - 1);
      lastMutationAt = Date.now();
    }
  }
}

function findDeviceRef(serial) {
  return devices.value.find((d) => d.serial === serial) || null;
}

async function refreshDevices(force = false) {
  if (!force && (inFlightMutations > 0 || Date.now() - lastMutationAt < 4000)) {
    return;
  }
  try {
    const list = await apiCall('list_devices');
    if (!force && (inFlightMutations > 0 || Date.now() - lastMutationAt < 4000)) {
      return;
    }
    if (list && Array.isArray(list)) {
      devices.value = list;
      if (!selectedSerial.value && list.length > 0) {
        selectedSerial.value = list[0].serial;
      }
    }
    daemonOnline.value = true;
  } catch (err) {
    console.error('Failed to load devices:', err);
    daemonOnline.value = false;
  }
}

async function refreshStatus() {
  try {
    const res = await apiCall('get_status');
    if (res) {
      status.value = res;
      daemonOnline.value = Boolean(res.daemon_running);
      mockMode.value = Boolean(res.mock_mode);
    }
  } catch (err) {
    console.error('Failed to fetch status:', err);
  }
}

onMounted(async () => {
  loadProfilesFromStorage();
  await refreshStatus();
  await refreshDevices(true);

  if (window.razerAPI && window.razerAPI.onDeviceUpdate) {
    unsubscribeUpdates = window.razerAPI.onDeviceUpdate((updatedList) => {
      if (inFlightMutations > 0 || Date.now() - lastMutationAt < 4000) {
        return;
      }
      if (updatedList && Array.isArray(updatedList)) {
        devices.value = updatedList;
        if (!selectedSerial.value && updatedList.length > 0) {
          selectedSerial.value = updatedList[0].serial;
        }
      }
    });
  } else {
    // When running in browser via Vite, poll every 5s when idle
    browserPollTimer = setInterval(() => refreshDevices(false), 5000);
  }
});

onBeforeUnmount(() => {
  if (unsubscribeUpdates) unsubscribeUpdates();
  if (browserPollTimer) clearInterval(browserPollTimer);
});

const currentDevice = computed(() => {
  return devices.value.find((d) => d.serial === selectedSerial.value) || devices.value[0] || null;
});

// Reset to overview if user switches to a device that lacks the currently viewed tab capability
watch(currentDevice, (dev) => {
  if (!dev) return;
  if (currentSection.value === 'lighting' && !dev.has_lighting) {
    currentSection.value = 'overview';
  } else if (currentSection.value === 'matrix' && !dev.has_matrix) {
    currentSection.value = 'overview';
  } else if (currentSection.value === 'performance' && !dev.has_dpi && !dev.has_poll_rate) {
    currentSection.value = 'overview';
  } else if (currentSection.value === 'buttons' && !dev.has_buttons) {
    currentSection.value = 'overview';
  } else if (currentSection.value === 'power' && !dev.has_battery) {
    currentSection.value = 'overview';
  }
});

function showNotification(msg) {
  notification.value = msg;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    if (notification.value === msg) {
      notification.value = null;
    }
  }, 2600);
}

// Action Handlers
async function handleUpdateDpi({ serial, x, y, commit = true }) {
  const dev = findDeviceRef(serial);
  const patch = { dpi: [x, y] };
  if (dev) {
    dev.dpi = [x, y];
    if (Array.isArray(dev.dpi_stages) && dev.active_dpi_stage >= 1 && dev.active_dpi_stage <= dev.dpi_stages.length) {
      dev.dpi_stages[dev.active_dpi_stage - 1] = [x, y];
      patch.dpi_stages = dev.dpi_stages.map((st) => [st[0], st[1]]);
      patch.active_dpi_stage = dev.active_dpi_stage;
    }
  }
  updateActiveProfile(patch);
  if (commit) {
    showNotification(`DPI set to ${x} × ${y} (${activeProfile.value?.name || 'Profile'})`);
  }
  await runCoalesced(`dpi:${serial}`, async () => {
    try {
      await apiCall('set_dpi', { serial, x, y });
    } catch (err) {
      console.error('Failed to set DPI:', err);
    }
  });
}

async function handleUpdateStages({ serial, active, stages, commit = true }) {
  const dev = findDeviceRef(serial);
  const clonedStages = stages.map((st) => [st[0], st[1]]);
  const activeDpi = active >= 1 && active <= clonedStages.length
    ? [clonedStages[active - 1][0], clonedStages[active - 1][1]]
    : [800, 800];
  if (dev) {
    dev.active_dpi_stage = active;
    dev.dpi_stages = clonedStages;
    dev.dpi = [...activeDpi];
  }
  updateActiveProfile({
    active_dpi_stage: active,
    dpi_stages: clonedStages,
    dpi: [...activeDpi]
  });
  if (commit) {
    showNotification(`DPI Stage ${active} active (${activeDpi[0]} DPI)`);
  }
  await runCoalesced(`stages:${serial}`, async () => {
    try {
      await apiCall('set_dpi_stages', { serial, active, stages: clonedStages });
    } catch (err) {
      console.error('Failed to save DPI stages:', err);
    }
  });
}

async function handleUpdatePollRate({ serial, rate }) {
  const dev = findDeviceRef(serial);
  if (dev) {
    dev.poll_rate = rate;
  }
  updateActiveProfile({ poll_rate: rate });
  showNotification(`Polling rate switched to ${rate} Hz`);
  await runCoalesced(`poll:${serial}`, async () => {
    try {
      await apiCall('set_poll_rate', { serial, rate });
    } catch (err) {
      console.error('Failed to update polling rate:', err);
    }
  });
}

async function handleUpdateBrightness({ serial, brightness, zone, commit = true }) {
  const dev = findDeviceRef(serial);
  if (dev) {
    dev.brightness = brightness;
  }
  updateActiveProfile({ brightness });
  if (commit) {
    showNotification(`Brightness set to ${brightness}%`);
  }
  await runCoalesced(`brightness:${serial}`, async () => {
    try {
      await apiCall('set_brightness', { serial, brightness, zone });
    } catch (err) {
      console.error(err);
    }
  });
}

async function handleUpdateChannel({ serial, channel, brightness, size, commit = true }) {
  const dev = findDeviceRef(serial);
  if (dev && Array.isArray(dev.channels)) {
    const ch = dev.channels.find((c) => c.channel === channel);
    if (ch) {
      if (brightness !== undefined) ch.brightness = brightness;
      if (size !== undefined) ch.size = size;
    }
    updateActiveProfile({
      channels: dev.channels.map((c) => ({ ...c }))
    });
  }
  if (commit) {
    showNotification(`ARGB Header ${channel} updated (${size} LEDs @ ${brightness}%)`);
  }
  await runCoalesced(`channel:${serial}:${channel}`, async () => {
    try {
      await apiCall('set_channel', { serial, channel, brightness, size });
    } catch (err) {
      console.error(err);
    }
  });
}

async function handleUpdateEffect({ serial, effect, breath_mode, colors, speed, direction, zone, commit = true }) {
  const dev = findDeviceRef(serial);
  if (dev && dev.lighting) {
    dev.lighting.current_effect = effect;
    if (breath_mode) dev.lighting.breath_mode = breath_mode;
    if (colors && colors.length) dev.lighting.colors = [...colors];
    if (speed) dev.lighting.speed = speed;
    if (direction) dev.lighting.direction = direction;
    if (effect !== 'none' && (dev.brightness === 0 || dev.brightness === null)) {
      dev.brightness = 100;
    }
  }
  const profPatch = { effect };
  if (breath_mode) profPatch.breath_mode = breath_mode;
  if (colors && colors.length) profPatch.colors = [...colors];
  if (speed) profPatch.speed = speed;
  if (direction) profPatch.direction = direction;
  updateActiveProfile(profPatch);
  if (commit) {
    showNotification(`Applied ${effect.toUpperCase()} lighting`);
  }
  await runCoalesced(`effect:${serial}`, async () => {
    try {
      await apiCall('set_effect', { serial, effect, breath_mode, colors, speed, direction, zone });
    } catch (err) {
      console.error('Failed to apply effect:', err);
    }
  });
}

async function handleApplyMatrix({ serial, grid }) {
  try {
    const res = await apiCall('set_matrix', { serial, grid });
    if (res && res.status === 'error') {
      throw new Error(res.message);
    }
    const dev = findDeviceRef(serial);
    if (dev && dev.lighting) {
      dev.lighting.current_effect = 'matrix';
    }
    showNotification('Custom LED matrix frame applied to hardware');
  } catch (err) {
    alert(`Failed to apply LED matrix: ${err.message}`);
  }
}

async function handleUpdateButtons({ serial, buttons }) {
  try {
    const res = await apiCall('set_button_mappings', { serial, buttons });
    const dev = findDeviceRef(serial);
    const clonedButtons = buttons.map((b) => ({ ...b }));
    if (dev) {
      dev.button_mappings = clonedButtons;
    }
    updateActiveProfile({ button_mappings: clonedButtons });
    const activeCount = buttons.filter((b) => b.action !== 'default').length;
    showNotification(
      activeCount > 0
        ? `Button mappings active (${activeCount} custom binding${activeCount === 1 ? '' : 's'})`
        : 'Buttons restored to native hardware passthrough'
    );
    return res;
  } catch (err) {
    alert(`Failed to update button mappings: ${err.message}`);
  }
}

async function handleSyncRgb({ effect, breath_mode, colors, speed, direction }) {
  try {
    updateActiveProfile({
      effect,
      breath_mode,
      colors: colors ? [...colors] : ['#fafafa'],
      speed,
      direction
    });
    const res = await apiCall('sync_rgb', { effect, breath_mode, colors, speed, direction });
    await refreshDevices(true);
    showNotification(`Synchronised RGB effect across ${res?.synced || 0} lighting-capable devices`);
  } catch (err) {
    alert(`Sync failed: ${err.message}`);
  }
}

async function handleUpdatePower({ serial, idle_time, low_battery_threshold, commit = true }) {
  const dev = findDeviceRef(serial);
  if (dev) {
    if (idle_time !== undefined) dev.idle_time = idle_time;
    if (low_battery_threshold !== undefined) dev.low_battery_threshold = low_battery_threshold;
  }
  const patch = {};
  if (idle_time !== undefined) patch.idle_time = idle_time;
  if (low_battery_threshold !== undefined) patch.low_battery_threshold = low_battery_threshold;
  updateActiveProfile(patch);
  if (commit) {
    showNotification('Power management settings saved');
  }
  await runCoalesced(`power:${serial}`, async () => {
    try {
      await apiCall('set_power', { serial, idle_time, low_battery_threshold });
    } catch (err) {
      console.error(err);
    }
  });
}

async function handleApplyProfile(profile) {
  if (!profile) return;
  activeProfileId.value = profile.id;
  saveProfilesToStorage();

  // Apply profile across connected devices according to their capabilities
  try {
    for (const dev of devices.value) {
      const serial = dev.serial;
      if (profile.dpi && dev.has_dpi) {
        dev.dpi = [...profile.dpi];
        if (Array.isArray(profile.dpi_stages) && profile.dpi_stages.length) {
          dev.dpi_stages = profile.dpi_stages.map((s) => [s[0], s[1]]);
          dev.active_dpi_stage = profile.active_dpi_stage || 1;
          await apiCall('set_dpi_stages', {
            serial,
            active: dev.active_dpi_stage,
            stages: dev.dpi_stages
          });
        }
        await apiCall('set_dpi', { serial, x: profile.dpi[0], y: profile.dpi[1] });
      }
      if (profile.poll_rate && dev.has_poll_rate) {
        dev.poll_rate = profile.poll_rate;
        await apiCall('set_poll_rate', { serial, rate: profile.poll_rate });
      }
      if (profile.brightness !== undefined && dev.has_brightness) {
        dev.brightness = profile.brightness;
        await apiCall('set_brightness', { serial, brightness: profile.brightness });
      }
      if (profile.effect && dev.has_lighting) {
        if (dev.lighting) {
          dev.lighting.current_effect = profile.effect;
          if (profile.breath_mode) dev.lighting.breath_mode = profile.breath_mode;
          if (profile.colors) dev.lighting.colors = [...profile.colors];
          if (profile.speed) dev.lighting.speed = profile.speed;
          if (profile.direction) dev.lighting.direction = profile.direction;
        }
        await apiCall('set_effect', {
          serial,
          effect: profile.effect,
          breath_mode: profile.breath_mode || 'single',
          colors: profile.colors || ['#fafafa'],
          speed: profile.speed || 'normal',
          direction: profile.direction || 'right'
        });
      }
      if (profile.idle_time && dev.has_battery) {
        dev.idle_time = profile.idle_time;
        if (profile.low_battery_threshold !== undefined) {
          dev.low_battery_threshold = profile.low_battery_threshold;
        }
        await apiCall('set_power', {
          serial,
          idle_time: profile.idle_time,
          low_battery_threshold: profile.low_battery_threshold
        });
      }
      if (Array.isArray(profile.button_mappings) && dev.has_buttons) {
        dev.button_mappings = profile.button_mappings.map((b) => ({ ...b }));
        await apiCall('set_button_mappings', {
          serial,
          buttons: dev.button_mappings
        });
      }
    }
    showNotification(`Switched to profile "${profile.name}"`);
  } catch (err) {
    console.error('Failed to apply profile:', err);
  }
}

function handleCreateProfile({ name, cloneCurrent = true }) {
  const trimmed = (name || '').trim();
  if (!trimmed) return;
  const dev = currentDevice.value;
  const base = createDefaultProfile();
  const newProf = {
    ...base,
    id: `prof-${Date.now()}`,
    name: trimmed,
    desc: 'Custom hardware profile — changes auto-save while active.',
    dpi: cloneCurrent && dev?.dpi ? [...dev.dpi] : [800, 800],
    dpi_stages:
      cloneCurrent && Array.isArray(dev?.dpi_stages) && dev.dpi_stages.length
        ? dev.dpi_stages.map((s) => [s[0], s[1]])
        : base.dpi_stages,
    active_dpi_stage: cloneCurrent && dev?.active_dpi_stage ? dev.active_dpi_stage : 2,
    poll_rate: cloneCurrent && dev?.poll_rate ? dev.poll_rate : 1000,
    brightness: cloneCurrent && dev?.brightness !== null && dev?.brightness !== undefined ? Math.round(dev.brightness) : 100,
    effect: cloneCurrent && dev?.lighting?.current_effect ? dev.lighting.current_effect : 'static',
    breath_mode: cloneCurrent && dev?.lighting?.breath_mode ? dev.lighting.breath_mode : 'single',
    colors: cloneCurrent && dev?.lighting?.colors?.length ? [...dev.lighting.colors] : ['#fafafa', '#4ade80'],
    speed: cloneCurrent && dev?.lighting?.speed ? dev.lighting.speed : 'normal',
    direction: cloneCurrent && dev?.lighting?.direction ? dev.lighting.direction : 'right',
    idle_time: cloneCurrent && dev?.idle_time ? dev.idle_time : 15,
    low_battery_threshold: cloneCurrent && dev?.low_battery_threshold ? dev.low_battery_threshold : 10,
    button_mappings:
      cloneCurrent && Array.isArray(dev?.button_mappings)
        ? dev.button_mappings.map((b) => ({ ...b }))
        : null
  };
  profiles.value.push(newProf);
  activeProfileId.value = newProf.id;
  saveProfilesToStorage();
  handleApplyProfile(newProf);
}

function handleDeleteProfile(id) {
  if (profiles.value.length <= 1) return;
  profiles.value = profiles.value.filter((p) => p.id !== id);
  if (activeProfileId.value === id) {
    const nextProf = profiles.value[0];
    activeProfileId.value = nextProf.id;
    handleApplyProfile(nextProf);
  } else {
    saveProfilesToStorage();
  }
}

function handleResetDefaultProfile(id) {
  const idx = profiles.value.findIndex((p) => p.id === id);
  if (idx === -1) return;
  const fresh = createDefaultProfile();
  fresh.id = profiles.value[idx].id;
  fresh.name = profiles.value[idx].name;
  profiles.value[idx] = fresh;
  saveProfilesToStorage();
  if (activeProfileId.value === id) {
    handleApplyProfile(fresh);
  }
}

function handleImportProfiles(importedList) {
  if (!Array.isArray(importedList) || importedList.length === 0) return;
  profiles.value = importedList;
  activeProfileId.value = importedList[0].id;
  saveProfilesToStorage();
  handleApplyProfile(importedList[0]);
}

async function handleToggleMock() {
  try {
    const res = await apiCall('toggle_mock');
    mockMode.value = res.mock_mode;
    await refreshDevices(true);
    showNotification(mockMode.value ? 'Hardware simulator enabled' : 'Hardware simulator disabled');
  } catch (err) {
    console.error(err);
  }
}

async function handleRestartDaemon() {
  try {
    await apiCall('restart_daemon');
    showNotification('OpenRazer daemon restarted');
    await refreshStatus();
    await refreshDevices(true);
  } catch (err) {
    alert(`Daemon restart failed: ${err.message}`);
  }
}
</script>

<template>
  <div class="app-layout">
    <AppHeader
      :current-section="currentSection"
      :daemon-online="daemonOnline"
      :device-count="devices.length"
      :device="currentDevice"
      @navigate="currentSection = $event"
    />

    <main class="main-content">
      <div class="content-container">
        <!-- Toast Notification -->
        <transition name="fade">
          <div v-if="notification" class="toast-notification micro">
            {{ notification }}
          </div>
        </transition>

        <!-- Device Selector -->
        <section class="device-section">
          <DeviceSelector
            :devices="devices"
            :selected-serial="selectedSerial"
            @select="selectedSerial = $event"
          />
        </section>

        <!-- Hero Stats for selected device -->
        <HeroStats
          :device="currentDevice"
          :active-profile="activeProfile"
          @open-profiles="currentSection = 'profiles'"
        />

        <!-- Views -->
        <div class="view-container">
          <!-- Overview -->
          <div v-if="currentSection === 'overview'" class="view-grid">
            <div class="grid-col" v-if="currentDevice?.has_dpi">
              <DpiControl
                :device="currentDevice"
                @update-dpi="handleUpdateDpi"
                @update-stages="handleUpdateStages"
              />
            </div>

            <div class="grid-col" v-if="currentDevice?.has_poll_rate">
              <PollRateControl
                :device="currentDevice"
                @update-poll-rate="handleUpdatePollRate"
              />
            </div>

            <div class="grid-col grid-col--full" v-if="currentDevice?.has_buttons">
              <ButtonsControl
                :device="currentDevice"
                @update-buttons="handleUpdateButtons"
              />
            </div>

            <div class="grid-col grid-col--full" v-if="currentDevice?.has_lighting">
              <LightingControl
                :device="currentDevice"
                @update-brightness="handleUpdateBrightness"
                @update-channel="handleUpdateChannel"
                @update-effect="handleUpdateEffect"
                @sync-rgb="handleSyncRgb"
                @open-matrix="currentSection = 'matrix'"
              />
            </div>
          </div>

          <!-- Dedicated Lighting View -->
          <LightingControl
            v-else-if="currentSection === 'lighting' && currentDevice"
            :device="currentDevice"
            @update-brightness="handleUpdateBrightness"
            @update-channel="handleUpdateChannel"
            @update-effect="handleUpdateEffect"
            @sync-rgb="handleSyncRgb"
            @open-matrix="currentSection = 'matrix'"
          />

          <!-- Dedicated Performance View -->
          <div v-else-if="currentSection === 'performance' && currentDevice" class="perf-view">
            <DpiControl
              v-if="currentDevice.has_dpi"
              :device="currentDevice"
              @update-dpi="handleUpdateDpi"
              @update-stages="handleUpdateStages"
            />
            <PollRateControl
              v-if="currentDevice.has_poll_rate"
              :device="currentDevice"
              @update-poll-rate="handleUpdatePollRate"
            />
          </div>

          <!-- Dedicated Buttons View -->
          <ButtonsControl
            v-else-if="currentSection === 'buttons' && currentDevice"
            :device="currentDevice"
            @update-buttons="handleUpdateButtons"
          />

          <!-- LED Matrix View -->
          <MatrixEditor
            v-else-if="currentSection === 'matrix' && currentDevice"
            :device="currentDevice"
            @apply-matrix="handleApplyMatrix"
          />

          <!-- Power View -->
          <PowerControl
            v-else-if="currentSection === 'power' && currentDevice"
            :device="currentDevice"
            @update-power="handleUpdatePower"
          />

          <!-- Profiles View -->
          <ProfilesControl
            v-else-if="currentSection === 'profiles'"
            :current-device="currentDevice"
            :profiles="profiles"
            :active-profile-id="activeProfileId"
            @apply-profile="handleApplyProfile"
            @create-profile="handleCreateProfile"
            @delete-profile="handleDeleteProfile"
            @reset-profile="handleResetDefaultProfile"
            @import-profiles="handleImportProfiles"
          />

          <!-- Troubleshooter / Health View -->
          <TroubleshooterControl
            v-else-if="currentSection === 'troubleshooter'"
            :status="status"
            @restart-daemon="handleRestartDaemon"
            @refresh-status="refreshStatus"
          />

          <!-- Settings View -->
          <SettingsControl
            v-else-if="currentSection === 'settings'"
            :mock-mode="mockMode"
            @toggle-mock="handleToggleMock"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg);
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 0 64px 0;
}

.content-container {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 24px;
  position: relative;
}

.toast-notification {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: var(--invert);
  color: var(--on-invert);
  padding: 10px 18px;
  border-radius: 9999px;
  font-weight: 500;
  z-index: 1000;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 120ms;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.device-section {
  margin-bottom: 8px;
}

.view-container {
  margin-top: 24px;
}

.view-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.grid-col--full {
  grid-column: 1 / -1;
}

.perf-view {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

@media (max-width: 800px) {
  .view-grid {
    grid-template-columns: 1fr;
  }
}
</style>
