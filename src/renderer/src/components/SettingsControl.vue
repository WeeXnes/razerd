<script setup>
import { ref, onMounted } from 'vue';

const props = defineProps({
  mockMode: {
    type: Boolean,
    default: false
  },
  autostartEnabled: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['toggle-mock', 'toggle-screensaver', 'toggle-autostart']);

const screensaverOff = ref(true);

onMounted(() => {
  const saved = localStorage.getItem('razerd-screensaver-off');
  if (saved !== null) {
    screensaverOff.value = saved === 'true';
  }
});

function onScreensaverToggle() {
  screensaverOff.value = !screensaverOff.value;
  localStorage.setItem('razerd-screensaver-off', screensaverOff.value.toString());
  emit('toggle-screensaver', screensaverOff.value);
}
</script>

<template>
  <div class="settings-control">
    <div class="section-header">
      <div>
        <h2 class="section-title">Application Settings</h2>
        <p class="section-desc">Manage runtime parameters, background daemons, and hardware simulation.</p>
      </div>
    </div>

    <div class="box settings-box">
      <!-- Autostart Minimized in System Tray -->
      <div class="setting-row">
        <div class="setting-info">
          <span class="setting-title">Autostart Minimized in System Tray</span>
          <span class="setting-hint">Launch RazerD silently in the system tray at desktop login, disable Polychromatic autostart, and automatically restore your saved hardware profile & lighting.</span>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="autostartEnabled"
            @change="emit('toggle-autostart', $event.target.checked)"
          />
          <span class="switch__slider"></span>
        </label>
      </div>

      <div class="row-divider"></div>

      <!-- Hardware Simulator -->
      <div class="setting-row">
        <div class="setting-info">
          <span class="setting-title">Hardware Simulator</span>
          <span class="setting-hint">Inject simulated Razer peripherals (Huntsman V3 Pro keyboard, Firefly mousemat) for testing without physical units.</span>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="mockMode"
            @change="emit('toggle-mock')"
          />
          <span class="switch__slider"></span>
        </label>
      </div>

      <div class="row-divider"></div>

      <!-- Screensaver Energy Saver -->
      <div class="setting-row">
        <div class="setting-info">
          <span class="setting-title">Screensaver Energy Saver</span>
          <span class="setting-hint">Automatically extinguish peripheral Chroma lighting when display enters power standby.</span>
        </div>
        <label class="switch">
          <input
            type="checkbox"
            :checked="screensaverOff"
            @change="onScreensaverToggle"
          />
          <span class="switch__slider"></span>
        </label>
      </div>
    </div>

    <!-- About RazerD Box -->
    <div class="box about-box">
      <div class="about-header">
        <span class="about-brand">razerd</span>
        <span class="micro num">Version 1.0.0</span>
      </div>
      <p class="about-desc">
        Modern Linux native peripheral control suite for Razer hardware.
        Reworked from the Polychromatic project on top of the OpenRazer driver stack,
        crafted with high-precision monochrome ergonomics following the OpenProStreet design philosophy.
      </p>
      <div class="about-meta micro">
        <span>Framework: Electron 44 + Vue 3</span>
        <span>•</span>
        <span>Driver: OpenRazer 3.12.4</span>
        <span>•</span>
        <span>License: GPLv3</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-control {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 500;
  letter-spacing: -0.01em;
  color: var(--text);
  margin-bottom: 4px;
}

.section-desc {
  font-size: 14px;
  color: var(--text-2);
}

.settings-box {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setting-info {
  display: flex;
  flex-direction: column;
  padding-right: 24px;
}

.setting-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  margin-bottom: 2px;
}

.setting-hint {
  font-size: 13px;
  color: var(--text-3);
}

.row-divider {
  height: 1px;
  background: var(--line);
}

.about-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.about-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.about-brand {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.01em;
}

.about-desc {
  font-size: 14px;
  color: var(--text-2);
  line-height: 1.6;
}

.about-meta {
  display: flex;
  gap: 8px;
  color: var(--text-3);
}
</style>
