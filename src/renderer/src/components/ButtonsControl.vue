<script setup>
import { ref, watch, computed, onBeforeUnmount } from 'vue';

const props = defineProps({
  device: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update-buttons']);

const localButtons = ref([]);
const recordingButtonId = ref(null);

function syncFromProps(dev) {
  if (dev && Array.isArray(dev.buttons) && dev.buttons.length > 0) {
    localButtons.value = dev.buttons.map((b) => ({
      id: b.id,
      label: b.label,
      action: b.action || 'default',
      value: b.value || ''
    }));
  } else {
    localButtons.value = [
      { id: 'btn_left', label: 'Left Click (Button 1)', action: 'default', value: '' },
      { id: 'btn_right', label: 'Right Click (Button 2)', action: 'default', value: '' },
      { id: 'btn_middle', label: 'Middle Click (Scroll Press)', action: 'default', value: '' },
      { id: 'btn_side', label: 'Mouse 4 (Side Back)', action: 'default', value: '' },
      { id: 'btn_extra', label: 'Mouse 5 (Side Forward)', action: 'default', value: '' },
      { id: 'scroll_up', label: 'Scroll Wheel Up', action: 'default', value: '' },
      { id: 'scroll_down', label: 'Scroll Wheel Down', action: 'default', value: '' }
    ];
  }
}

syncFromProps(props.device);

watch(
  () => props.device?.serial,
  () => {
    stopRecording();
    syncFromProps(props.device);
  }
);

const customCount = computed(() => {
  return localButtons.value.filter((b) => b.action !== 'default').length;
});

const actionTypes = [
  { id: 'default', label: 'Default' },
  { id: 'key', label: 'Key / Shortcut' },
  { id: 'mouse', label: 'Mouse Button' },
  { id: 'dpi_cycle', label: 'DPI Cycle' },
  { id: 'dpi_up', label: 'DPI Stage +' },
  { id: 'dpi_down', label: 'DPI Stage −' },
  { id: 'dpi_sniper', label: 'Sniper Hold (DPI)' },
  { id: 'poll_cycle', label: 'Polling Cycle' },
  { id: 'media', label: 'Media / Volume' },
  { id: 'command', label: 'Command / Hyprctl' },
  { id: 'disabled', label: 'Disabled' }
];

const mouseTargets = [
  { id: 'btn_left', label: 'Left Click' },
  { id: 'btn_right', label: 'Right Click' },
  { id: 'btn_middle', label: 'Middle Click' },
  { id: 'btn_side', label: 'Mouse 4 (Back)' },
  { id: 'btn_extra', label: 'Mouse 5 (Forward)' }
];

const mediaTargets = [
  { id: 'volume_up', label: 'Volume Up (+5%)' },
  { id: 'volume_down', label: 'Volume Down (-5%)' },
  { id: 'mute', label: 'Mute / Unmute Audio' },
  { id: 'play_pause', label: 'Play / Pause Media' },
  { id: 'next_track', label: 'Next Track' },
  { id: 'prev_track', label: 'Previous Track' }
];

const keyPresets = [
  'ESC', 'ENTER', 'SPACE', 'TAB', 'BACKSPACE', 'DELETE',
  'LEFTCTRL+C', 'LEFTCTRL+V', 'LEFTCTRL+Z', 'LEFTALT+TAB', 'SUPER', 'F13'
];

const commandPresets = [
  { label: 'Workspace +1', cmd: 'hyprctl dispatch workspace e+1' },
  { label: 'Workspace -1', cmd: 'hyprctl dispatch workspace e-1' },
  { label: 'Fullscreen', cmd: 'hyprctl dispatch fullscreen 0' },
  { label: 'Float Window', cmd: 'hyprctl dispatch togglefloating' }
];

function onActionChange(btn, newAction) {
  btn.action = newAction;
  if (newAction === 'default' || newAction === 'disabled' || newAction === 'dpi_cycle' || newAction === 'dpi_up' || newAction === 'dpi_down' || newAction === 'poll_cycle') {
    btn.value = '';
  } else if (newAction === 'mouse') {
    btn.value = 'btn_middle';
  } else if (newAction === 'media') {
    btn.value = 'play_pause';
  } else if (newAction === 'dpi_sniper') {
    btn.value = '400';
  } else if (newAction === 'key' && !btn.value) {
    btn.value = 'F13';
  } else if (newAction === 'command' && !btn.value) {
    btn.value = 'hyprctl dispatch workspace e+1';
  }
  saveMappings();
}

function onValueChange(btn, val) {
  btn.value = val;
  saveMappings();
}

function resetAll() {
  stopRecording();
  localButtons.value.forEach((b) => {
    b.action = 'default';
    b.value = '';
  });
  saveMappings();
}

function saveMappings() {
  emit('update-buttons', {
    serial: props.device.serial,
    buttons: localButtons.value.map((b) => ({ ...b }))
  });
}

// Key recording support
function normalizeBrowserKey(e) {
  const parts = [];
  if (e.ctrlKey) parts.push('LEFTCTRL');
  if (e.altKey) parts.push('LEFTALT');
  if (e.shiftKey) parts.push('LEFTSHIFT');
  if (e.metaKey) parts.push('SUPER');

  const k = e.key.toUpperCase();
  const code = e.code;

  let mainKey = '';
  if (['CONTROL', 'SHIFT', 'ALT', 'META'].includes(k)) {
    mainKey = '';
  } else if (code.startsWith('Key')) {
    mainKey = code.replace('Key', '').toUpperCase();
  } else if (code.startsWith('Digit')) {
    mainKey = code.replace('Digit', '');
  } else if (k === 'ESCAPE') {
    mainKey = 'ESC';
  } else if (k === ' ') {
    mainKey = 'SPACE';
  } else if (k === 'ARROWUP') {
    mainKey = 'UP';
  } else if (k === 'ARROWDOWN') {
    mainKey = 'DOWN';
  } else if (k === 'ARROWLEFT') {
    mainKey = 'LEFT';
  } else if (k === 'ARROWRIGHT') {
    mainKey = 'RIGHT';
  } else if (/^F\d+$/.test(k)) {
    mainKey = k;
  } else if (['ENTER', 'TAB', 'BACKSPACE', 'DELETE', 'HOME', 'END', 'PAGEUP', 'PAGEDOWN', 'INSERT'].includes(k)) {
    mainKey = k;
  }

  if (mainKey && !parts.includes(mainKey)) {
    parts.push(mainKey);
  }
  return parts.join('+');
}

function handleKeydown(e) {
  if (!recordingButtonId.value) return;
  e.preventDefault();
  e.stopPropagation();

  // Wait if user only pressed a modifier so far
  if (['Control', 'Shift', 'Alt', 'Meta'].includes(e.key)) {
    return;
  }

  const combo = normalizeBrowserKey(e);
  const target = localButtons.value.find((b) => b.id === recordingButtonId.value);
  if (target && combo) {
    target.value = combo;
    saveMappings();
  }
  stopRecording();
}

function startRecording(btnId) {
  if (recordingButtonId.value === btnId) {
    stopRecording();
    return;
  }
  recordingButtonId.value = btnId;
  window.addEventListener('keydown', handleKeydown, true);
}

function stopRecording() {
  recordingButtonId.value = null;
  window.removeEventListener('keydown', handleKeydown, true);
}

onBeforeUnmount(() => {
  stopRecording();
});
</script>

<template>
  <div class="buttons-control">
    <div class="section-header">
      <div>
        <h2 class="section-title">Button Mapping</h2>
        <p class="section-desc">
          Remap hardware mouse buttons and scroll wheel actions via kernel evdev interception.
        </p>
      </div>
      <div class="header-actions">
        <div class="remapper-status">
          <span
            class="status-dot"
            :class="customCount > 0 ? 'status-dot--success' : ''"
          ></span>
          <span class="micro num">
            {{ customCount > 0 ? `${customCount} Active Remap${customCount === 1 ? '' : 's'}` : 'Native Passthrough' }}
          </span>
        </div>
        <button
          v-if="customCount > 0"
          class="btn btn--secondary btn--small"
          @click="resetAll"
        >
          <span class="micro">Reset All</span>
        </button>
      </div>
    </div>

    <div v-if="!device.has_buttons" class="box empty-box">
      <span class="micro">No programmable mouse buttons detected on this device.</span>
    </div>

    <div v-else class="buttons-list">
      <div
        v-for="btn in localButtons"
        :key="btn.id"
        class="box button-row"
        :class="{ 'button-row--custom': btn.action !== 'default' }"
      >
        <div class="button-row__top">
          <div class="button-info">
            <span class="button-label">{{ btn.label }}</span>
            <span class="micro num button-code">{{ btn.id.toUpperCase() }}</span>
          </div>

          <div class="action-selector">
            <select
              class="input action-select"
              :value="btn.action"
              @change="onActionChange(btn, $event.target.value)"
            >
              <option
                v-for="act in actionTypes"
                :key="act.id"
                :value="act.id"
                :disabled="btn.id === 'btn_left' && act.id !== 'default' && !localButtons.some(o => o.id !== 'btn_left' && o.action === 'mouse' && o.value === 'btn_left')"
              >
                {{ act.label }}
              </option>
            </select>
          </div>
        </div>

        <!-- Secondary Configuration for Key / Shortcut -->
        <div v-if="btn.action === 'key'" class="button-row__config">
          <div class="config-line">
            <input
              type="text"
              class="input input-num key-input"
              :value="btn.value"
              placeholder="e.g. F13 or LEFTCTRL+C"
              @change="onValueChange(btn, $event.target.value.toUpperCase())"
            />
            <button
              class="btn btn--small"
              :class="recordingButtonId === btn.id ? 'btn--primary' : 'btn--secondary'"
              @click="startRecording(btn.id)"
            >
              <span class="micro">
                {{ recordingButtonId === btn.id ? 'Press Any Key...' : 'Record Key' }}
              </span>
            </button>
          </div>
          <div class="preset-pills">
            <button
              v-for="kp in keyPresets"
              :key="kp"
              class="btn btn--secondary btn--small"
              :class="{ active: btn.value === kp }"
              @click="onValueChange(btn, kp)"
            >
              <span class="micro num">{{ kp }}</span>
            </button>
          </div>
        </div>

        <!-- Secondary Configuration for Mouse Button target -->
        <div v-else-if="btn.action === 'mouse'" class="button-row__config">
          <div class="preset-pills">
            <button
              v-for="mt in mouseTargets"
              :key="mt.id"
              class="btn btn--secondary btn--small"
              :class="{ active: btn.value === mt.id }"
              @click="onValueChange(btn, mt.id)"
            >
              <span class="micro">{{ mt.label }}</span>
            </button>
          </div>
        </div>

        <!-- Secondary Configuration for Media / Volume -->
        <div v-else-if="btn.action === 'media'" class="button-row__config">
          <div class="preset-pills">
            <button
              v-for="med in mediaTargets"
              :key="med.id"
              class="btn btn--secondary btn--small"
              :class="{ active: btn.value === med.id }"
              @click="onValueChange(btn, med.id)"
            >
              <span class="micro">{{ med.label }}</span>
            </button>
          </div>
        </div>

        <!-- Secondary Configuration for Sniper DPI Hold -->
        <div v-else-if="btn.action === 'dpi_sniper'" class="button-row__config">
          <div class="config-line">
            <span class="micro">Hold Target DPI:</span>
            <div class="preset-pills">
              <button
                v-for="sDpi in ['200', '400', '600', '800']"
                :key="sDpi"
                class="btn btn--secondary btn--small num"
                :class="{ active: String(btn.value) === sDpi }"
                @click="onValueChange(btn, sDpi)"
              >
                <span class="micro num">{{ sDpi }} DPI</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Secondary Configuration for Shell / Hyprctl Command -->
        <div v-else-if="btn.action === 'command'" class="button-row__config">
          <div class="config-line">
            <input
              type="text"
              class="input input-num cmd-input"
              :value="btn.value"
              placeholder="e.g. hyprctl dispatch workspace e+1"
              @change="onValueChange(btn, $event.target.value)"
            />
          </div>
          <div class="preset-pills">
            <button
              v-for="cp in commandPresets"
              :key="cp.cmd"
              class="btn btn--secondary btn--small"
              :class="{ active: btn.value === cp.cmd }"
              @click="onValueChange(btn, cp.cmd)"
            >
              <span class="micro">{{ cp.label }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.buttons-control {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.remapper-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: 9999px;
  background: var(--surface);
}

.empty-box {
  padding: 24px;
  text-align: center;
}

.buttons-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.button-row {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 20px;
  transition: border-color 120ms, background-color 120ms;
}

.button-row--custom {
  border-color: var(--line-strong);
  background: var(--surface-2);
}

.button-row__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.button-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.button-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.button-code {
  font-size: 11px;
  color: var(--text-3);
}

.action-select {
  min-width: 190px;
  height: 34px;
  font-size: 13px;
  background: var(--bg);
  color: var(--text);
  cursor: pointer;
}

.button-row__config {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}

.config-line {
  display: flex;
  align-items: center;
  gap: 10px;
}

.key-input {
  width: 220px;
  height: 32px;
  font-size: 12px;
}

.cmd-input {
  flex: 1;
  height: 32px;
  font-size: 12px;
}

.preset-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
