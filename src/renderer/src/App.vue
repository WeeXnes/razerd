<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import AppHeader from './components/AppHeader.vue';
import DeviceSelector from './components/DeviceSelector.vue';
import HeroStats from './components/HeroStats.vue';
import DpiControl from './components/DpiControl.vue';
import PollRateControl from './components/PollRateControl.vue';
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

let unsubscribeUpdates = null;
let browserPollTimer = null;

// Helper to safely invoke API (native Electron IPC or browser dev API)
async function apiCall(action, params = {}) {
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
}

async function refreshDevices() {
  try {
    const list = await apiCall('list_devices');
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
  await refreshStatus();
  await refreshDevices();

  if (window.razerAPI && window.razerAPI.onDeviceUpdate) {
    unsubscribeUpdates = window.razerAPI.onDeviceUpdate((updatedList) => {
      if (updatedList && Array.isArray(updatedList)) {
        devices.value = updatedList;
        if (!selectedSerial.value && updatedList.length > 0) {
          selectedSerial.value = updatedList[0].serial;
        }
      }
    });
  } else {
    // When running in browser via Vite, poll every 3.5s
    browserPollTimer = setInterval(refreshDevices, 3500);
  }
});

onBeforeUnmount(() => {
  if (unsubscribeUpdates) unsubscribeUpdates();
  if (browserPollTimer) clearInterval(browserPollTimer);
});

const currentDevice = computed(() => {
  return devices.value.find((d) => d.serial === selectedSerial.value) || devices.value[0] || null;
});

function showNotification(msg) {
  notification.value = msg;
  setTimeout(() => {
    if (notification.value === msg) {
      notification.value = null;
    }
  }, 3000);
}

// Action Handlers
async function handleUpdateDpi({ serial, x, y }) {
  try {
    await apiCall('set_dpi', { serial, x, y });
    showNotification(`DPI set to ${x} × ${y}`);
  } catch (err) {
    alert(`Failed to set DPI: ${err.message}`);
  }
}

async function handleUpdateStages({ serial, active, stages }) {
  try {
    await apiCall('set_dpi_stages', { serial, active, stages });
    showNotification(`DPI Stages saved (Active: Stage ${active})`);
  } catch (err) {
    alert(`Failed to save DPI stages: ${err.message}`);
  }
}

async function handleUpdatePollRate({ serial, rate }) {
  try {
    await apiCall('set_poll_rate', { serial, rate });
    showNotification(`Polling rate switched to ${rate} Hz`);
  } catch (err) {
    alert(`Failed to update polling rate: ${err.message}`);
  }
}

async function handleUpdateBrightness({ serial, brightness, zone }) {
  try {
    await apiCall('set_brightness', { serial, brightness, zone });
  } catch (err) {
    console.error(err);
  }
}

async function handleUpdateEffect({ serial, effect, colors, speed, direction, zone }) {
  try {
    await apiCall('set_effect', { serial, effect, colors, speed, direction, zone });
    showNotification(`Applied ${effect.toUpperCase()} lighting`);
  } catch (err) {
    alert(`Failed to apply effect: ${err.message}`);
  }
}

async function handleSyncRgb({ effect, colors, speed, direction }) {
  try {
    const res = await apiCall('sync_rgb', { effect, colors, speed, direction });
    showNotification(`Synchronised RGB effect across ${res?.synced || devices.value.length} devices`);
  } catch (err) {
    alert(`Sync failed: ${err.message}`);
  }
}

async function handleUpdatePower({ serial, idle_time, low_battery_threshold }) {
  try {
    await apiCall('set_power', { serial, idle_time, low_battery_threshold });
    showNotification('Power management settings saved');
  } catch (err) {
    console.error(err);
  }
}

async function handleApplyProfile(profile) {
  if (!currentDevice.value) return;
  const serial = currentDevice.value.serial;
  try {
    if (profile.dpi && currentDevice.value.has_dpi) {
      await apiCall('set_dpi', { serial, x: profile.dpi[0], y: profile.dpi[1] });
    }
    if (profile.poll_rate && currentDevice.value.has_poll_rate) {
      await apiCall('set_poll_rate', { serial, rate: profile.poll_rate });
    }
    if (profile.brightness !== undefined && currentDevice.value.has_brightness) {
      await apiCall('set_brightness', { serial, brightness: profile.brightness });
    }
    if (profile.effect) {
      await apiCall('set_effect', {
        serial,
        effect: profile.effect,
        colors: profile.colors || ['#fafafa']
      });
    }
    if (profile.idle_time && currentDevice.value.has_battery) {
      await apiCall('set_power', { serial, idle_time: profile.idle_time });
    }
    await refreshDevices();
    showNotification(`Profile "${profile.name}" applied`);
  } catch (err) {
    alert(`Failed to apply profile: ${err.message}`);
  }
}

async function handleToggleMock() {
  try {
    const res = await apiCall('toggle_mock');
    mockMode.value = res.mock_mode;
    await refreshDevices();
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
    await refreshDevices();
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
        <HeroStats :device="currentDevice" />

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

            <div class="grid-col grid-col--full">
              <LightingControl
                v-if="currentDevice"
                :device="currentDevice"
                @update-brightness="handleUpdateBrightness"
                @update-effect="handleUpdateEffect"
                @sync-rgb="handleSyncRgb"
              />
            </div>
          </div>

          <!-- Dedicated Lighting View -->
          <LightingControl
            v-else-if="currentSection === 'lighting' && currentDevice"
            :device="currentDevice"
            @update-brightness="handleUpdateBrightness"
            @update-effect="handleUpdateEffect"
            @sync-rgb="handleSyncRgb"
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

          <!-- LED Matrix View -->
          <MatrixEditor
            v-else-if="currentSection === 'matrix' && currentDevice"
            :device="currentDevice"
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
            @apply-profile="handleApplyProfile"
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
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
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
