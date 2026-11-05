<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  device: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update-brightness', 'update-effect', 'update-channel', 'sync-rgb', 'open-matrix']);

const brightness = ref(
  props.device.brightness !== null && props.device.brightness !== undefined
    ? Math.round(props.device.brightness)
    : 100
);

const lightingState = computed(() => props.device.lighting || {});
const currentEffect = ref(lightingState.value.current_effect || 'static');
const breathMode = ref(lightingState.value.breath_mode || 'single');
const colors = ref(
  lightingState.value.colors && lightingState.value.colors.length
    ? [...lightingState.value.colors]
    : ['#fafafa', '#4ade80']
);
const speed = ref(lightingState.value.speed || 'normal');
const direction = ref(lightingState.value.direction || 'right');
const selectedZone = ref('overall');
const localChannels = ref(
  Array.isArray(props.device.channels) ? props.device.channels.map((c) => ({ ...c })) : []
);

let lastInteractionAt = 0;
const isDragging = ref(false);
function markInteraction() {
  lastInteractionAt = Date.now();
}

const availableEffects = computed(() => {
  return lightingState.value.supported_effects && lightingState.value.supported_effects.length
    ? lightingState.value.supported_effects
    : [];
});

const availableZones = computed(() => {
  return lightingState.value.zones && lightingState.value.zones.length
    ? lightingState.value.zones
    : ['overall'];
});

function syncFromDevice(newDev, force = false) {
  if (!newDev) return;
  if (!force && (isDragging.value || Date.now() - lastInteractionAt < 4000)) return;

  if (newDev.brightness !== null && newDev.brightness !== undefined) {
    brightness.value = Math.round(newDev.brightness);
  }
  if (newDev.lighting) {
    if (newDev.lighting.current_effect) currentEffect.value = newDev.lighting.current_effect;
    if (newDev.lighting.breath_mode) breathMode.value = newDev.lighting.breath_mode;
    if (newDev.lighting.colors && newDev.lighting.colors.length) {
      colors.value = [...newDev.lighting.colors];
    }
    if (newDev.lighting.speed) speed.value = newDev.lighting.speed;
    if (newDev.lighting.direction) direction.value = newDev.lighting.direction;
  }
  if (Array.isArray(newDev.channels)) {
    localChannels.value = newDev.channels.map((c) => ({ ...c }));
  } else {
    localChannels.value = [];
  }
}

watch(
  () => props.device?.serial,
  () => {
    selectedZone.value = 'overall';
    syncFromDevice(props.device, true);
  }
);

watch(
  () => props.device,
  (newDev) => {
    syncFromDevice(newDev, false);
  },
  { deep: true }
);

function onBrightnessChange(val, commit = true) {
  markInteraction();
  const num = Math.min(100, Math.max(0, parseInt(val) || 0));
  brightness.value = num;
  emit('update-brightness', {
    serial: props.device.serial,
    brightness: num,
    zone: selectedZone.value,
    commit
  });
}

function selectEffect(eff) {
  markInteraction();
  currentEffect.value = eff;
  if (brightness.value < 10 && eff !== 'none') {
    brightness.value = 100;
  }
  applyEffect(true);
}

function selectBreathMode(mode) {
  markInteraction();
  breathMode.value = mode;
  applyEffect(true);
}

function setColor(hex, index = 0, commit = true) {
  markInteraction();
  const updated = [...colors.value];
  updated[index] = hex;
  colors.value = updated;
  if (currentEffect.value === 'none' || currentEffect.value === 'spectrum') {
    if (availableEffects.value.includes('static')) {
      currentEffect.value = 'static';
    }
  }
  applyEffect(commit);
}

function setSpeed(val) {
  markInteraction();
  speed.value = val;
  applyEffect(true);
}

function setDirection(val) {
  markInteraction();
  direction.value = val;
  applyEffect(true);
}

function applyEffect(commit = true) {
  emit('update-effect', {
    serial: props.device.serial,
    effect: currentEffect.value,
    breath_mode: breathMode.value,
    colors: colors.value,
    speed: speed.value,
    direction: direction.value,
    zone: selectedZone.value,
    commit
  });
}

function onChannelBrightness(ch, val, commit = true) {
  markInteraction();
  const num = Math.min(100, Math.max(0, parseInt(val) || 0));
  ch.brightness = num;
  emit('update-channel', {
    serial: props.device.serial,
    channel: ch.channel,
    brightness: num,
    size: ch.size,
    commit
  });
}

function onChannelSize(ch, val, commit = true) {
  markInteraction();
  const num = Math.min(80, Math.max(1, parseInt(val) || 14));
  ch.size = num;
  emit('update-channel', {
    serial: props.device.serial,
    channel: ch.channel,
    brightness: ch.brightness,
    size: num,
    commit
  });
}

function syncAll() {
  markInteraction();
  emit('sync-rgb', {
    effect: currentEffect.value,
    breath_mode: breathMode.value,
    colors: colors.value,
    speed: speed.value,
    direction: direction.value
  });
}

const colorPresets = [
  { name: 'Monochrome White', hex: '#fafafa' },
  { name: 'Razer Green', hex: '#00ff00' },
  { name: 'Emerald', hex: '#4ade80' },
  { name: 'Cyan', hex: '#00ffff' },
  { name: 'Ice Blue', hex: '#38bdf8' },
  { name: 'Cobalt', hex: '#3b82f6' },
  { name: 'Violet', hex: '#a855f7' },
  { name: 'Amber', hex: '#fbbf24' },
  { name: 'Crimson', hex: '#f87171' }
];
</script>

<template>
  <div class="lighting-control">
    <div class="section-header">
      <div>
        <h2 class="section-title">Chroma Lighting</h2>
        <p class="section-desc">Manage RGB effects, brightness, color palettes, and device synchronisation.</p>
      </div>
      <button
        v-if="device.has_lighting"
        class="btn btn--secondary btn--small"
        @click="syncAll"
        title="Apply current effect across all lighting-capable Razer peripherals"
      >
        Sync RGB to All
      </button>
    </div>

    <div v-if="!device.has_lighting" class="box no-lighting-box">
      <span class="micro">This device ({{ device.name }}) has no onboard LED lighting zones.</span>
    </div>

    <template v-else>
      <!-- Master Brightness Slider -->
      <div v-if="device.has_brightness" class="box brightness-box">
        <div class="brightness-header">
          <div class="bright-left">
            <span class="micro">Master Brightness</span>
            <span class="micro num">{{ brightness }}%</span>
          </div>
          <div class="bright-actions">
            <button
              v-if="brightness < 100"
              class="btn btn--secondary btn--small"
              @click="onBrightnessChange(100)"
            >
              <span class="micro">100%</span>
            </button>
            <button
              class="btn btn--secondary btn--small"
              @click="onBrightnessChange(brightness === 0 ? 100 : 0)"
            >
              <span class="micro">{{ brightness === 0 ? 'Unmute' : 'Off' }}</span>
            </button>
          </div>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          step="1"
          :value="brightness"
          @pointerdown="isDragging = true"
          @pointerup="isDragging = false"
          @input="onBrightnessChange($event.target.value, false)"
          @change="onBrightnessChange($event.target.value, true)"
        />
      </div>

      <!-- Zones Selector (if multiple) -->
      <div v-if="availableZones.length > 1" class="zones-bar">
        <span class="micro">Lighting Zone:</span>
        <div class="zones-pills">
          <button
            v-for="zone in availableZones"
            :key="zone"
            class="btn btn--secondary btn--small"
            :class="{ active: selectedZone === zone }"
            @click="selectedZone = zone"
          >
            <span class="micro">{{ zone }}</span>
          </button>
        </div>
      </div>

      <!-- Effect Modes Grid -->
      <div v-if="availableEffects.length > 0" class="effects-section">
        <div class="effects-header">
          <span class="micro">Lighting Effect</span>
          <button
            v-if="device.has_matrix"
            class="btn btn--secondary btn--small"
            @click="emit('open-matrix')"
          >
            <span class="micro">Open LED Matrix Editor</span>
          </button>
        </div>

        <div class="effects-grid">
          <div
            v-for="eff in availableEffects"
            :key="eff"
            class="effect-card"
            :class="{ 'effect-card--active': currentEffect === eff }"
            @click="selectEffect(eff)"
          >
            <div class="effect-top">
              <span class="effect-name">{{ eff.toUpperCase() }}</span>
              <div class="select-dot" :class="{ 'select-dot--active': currentEffect === eff }"></div>
            </div>
            <div class="effect-desc micro">
              <span v-if="eff === 'none'">Turn illumination off</span>
              <span v-else-if="eff === 'static'">Constant single hue</span>
              <span v-else-if="eff === 'breath'">Pulsing breathing cycle</span>
              <span v-else-if="eff === 'spectrum'">Full 16.8M spectrum cycle</span>
              <span v-else-if="eff === 'wave'">Continuous directional wave</span>
              <span v-else-if="eff === 'reactive'">Lights upon actuation</span>
              <span v-else-if="eff === 'ripple'">Expanding circular ripple</span>
              <span v-else-if="eff === 'starlight'">Twinkling celestial stars</span>
              <span v-else-if="eff === 'matrix'">Custom addressable frame</span>
              <span v-else>Hardware effect</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Effect Parameters & Color Picker -->
      <div v-if="currentEffect !== 'none' && currentEffect !== 'spectrum'" class="box params-box">
        <!-- Sub-mode for Breath / Starlight / Ripple -->
        <div v-if="['breath', 'starlight', 'ripple'].includes(currentEffect)" class="mode-row">
          <span class="micro">Color Mode:</span>
          <div class="btn-group">
            <button
              class="btn btn--secondary btn--small"
              :class="{ active: breathMode === 'single' }"
              @click="selectBreathMode('single')"
            >
              <span class="micro">Single</span>
            </button>
            <button
              v-if="currentEffect !== 'ripple'"
              class="btn btn--secondary btn--small"
              :class="{ active: breathMode === 'dual' }"
              @click="selectBreathMode('dual')"
            >
              <span class="micro">Dual</span>
            </button>
            <button
              class="btn btn--secondary btn--small"
              :class="{ active: breathMode === 'random' }"
              @click="selectBreathMode('random')"
            >
              <span class="micro">Random</span>
            </button>
          </div>
        </div>

        <!-- Color Selection (hidden if Wave/Wheel or Random mode) -->
        <div
          v-if="!['wave', 'wheel'].includes(currentEffect) && !(['breath', 'starlight', 'ripple'].includes(currentEffect) && breathMode === 'random')"
          class="color-section"
        >
          <div class="color-header">
            <span class="micro">Primary Color</span>
            <div class="color-inputs">
              <input
                type="color"
                class="color-picker-input"
                :value="colors[0] || '#fafafa'"
                @input="setColor($event.target.value, 0, false)"
                @change="setColor($event.target.value, 0, true)"
              />
              <input
                type="text"
                class="input input-num color-text-input"
                :value="colors[0] || '#fafafa'"
                @change="setColor($event.target.value, 0, true)"
              />
            </div>
          </div>

          <!-- Second color for dual breathing/starlight -->
          <div
            v-if="(['breath', 'starlight'].includes(currentEffect) && breathMode === 'dual')"
            class="color-header"
            style="margin-top: 12px;"
          >
            <span class="micro">Secondary Color</span>
            <div class="color-inputs">
              <input
                type="color"
                class="color-picker-input"
                :value="colors[1] || '#4ade80'"
                @input="setColor($event.target.value, 1, false)"
                @change="setColor($event.target.value, 1, true)"
              />
              <input
                type="text"
                class="input input-num color-text-input"
                :value="colors[1] || '#4ade80'"
                @change="setColor($event.target.value, 1, true)"
              />
            </div>
          </div>

          <!-- Color Swatches -->
          <div class="swatches-row">
            <button
              v-for="swatch in colorPresets"
              :key="swatch.hex"
              class="swatch-btn"
              :style="{ backgroundColor: swatch.hex }"
              :title="swatch.name"
              @click="setColor(swatch.hex, 0, true)"
            ></button>
          </div>
        </div>

        <!-- Direction & Speed Controls -->
        <div v-if="currentEffect === 'wave' || currentEffect === 'wheel'" class="direction-row">
          <span class="micro">Wave Direction:</span>
          <div class="btn-group">
            <button
              class="btn btn--secondary btn--small"
              :class="{ active: direction === 'left' }"
              @click="setDirection('left')"
            >
              <span class="micro">{{ device.type === 'mouse' ? 'Down' : 'Left' }}</span>
            </button>
            <button
              class="btn btn--secondary btn--small"
              :class="{ active: direction === 'right' }"
              @click="setDirection('right')"
            >
              <span class="micro">{{ device.type === 'mouse' ? 'Up' : 'Right' }}</span>
            </button>
          </div>
        </div>

        <div v-if="['reactive', 'starlight'].includes(currentEffect)" class="speed-row">
          <span class="micro">Animation Speed:</span>
          <div class="btn-group">
            <button
              v-for="spd in ['fast', 'normal', 'slow']"
              :key="spd"
              class="btn btn--secondary btn--small"
              :class="{ active: speed === spd }"
              @click="setSpeed(spd)"
            >
              <span class="micro">{{ spd }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Addressable ARGB Channels (for Razer Chroma Addressable RGB Controller) -->
      <div v-if="localChannels.length > 0" class="box channels-box">
        <div class="channels-header">
          <span class="micro">Addressable ARGB Headers ({{ localChannels.length }} Channels)</span>
          <span class="micro num">Per-Port LED Count & Brightness</span>
        </div>

        <div class="channels-grid">
          <div v-for="ch in localChannels" :key="ch.channel" class="channel-card">
            <div class="channel-top">
              <span class="channel-name">{{ ch.name }}</span>
              <span class="micro num">{{ ch.brightness }}%</span>
            </div>

            <input
              type="range"
              min="0"
              max="100"
              step="1"
              :value="ch.brightness"
              @pointerdown="isDragging = true"
              @pointerup="isDragging = false"
              @input="onChannelBrightness(ch, $event.target.value, false)"
              @change="onChannelBrightness(ch, $event.target.value, true)"
            />

            <div class="channel-size-row">
              <span class="micro">LED Count:</span>
              <input
                type="number"
                min="1"
                max="80"
                class="input input-num channel-size-input"
                :value="ch.size"
                @change="onChannelSize(ch, $event.target.value, true)"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.lighting-control {
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

.no-lighting-box {
  padding: 24px;
  text-align: center;
}

.brightness-box {
  display: flex;
  flex-direction: column;
}

.brightness-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.bright-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bright-actions {
  display: flex;
  gap: 8px;
}

.zones-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.zones-pills {
  display: flex;
  gap: 8px;
}

.effects-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.effects-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.effects-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
}

.effect-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: background-color 120ms, border-color 120ms;
}

.effect-card:hover {
  background: var(--surface-2);
}

.effect-card--active {
  border-color: var(--line-strong);
  background: var(--surface-2);
}

.effect-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.effect-name {
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: var(--text);
}

.effect-desc {
  color: var(--text-3);
  font-size: 11px;
}

.select-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid var(--line-strong);
  background: transparent;
}

.select-dot--active {
  border-color: var(--text);
  background: var(--text);
  box-shadow: inset 0 0 0 2px var(--bg);
}

.params-box {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.mode-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}

.color-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.color-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-picker-input {
  width: 32px;
  height: 32px;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  padding: 0;
}

.color-text-input {
  width: 100px;
  height: 32px;
  font-size: 12px;
  text-align: center;
}

.swatches-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.swatch-btn {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1px solid var(--line-strong);
  cursor: pointer;
  transition: opacity 120ms;
}

.swatch-btn:hover {
  opacity: 0.85;
}

.direction-row, .speed-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.btn-group {
  display: flex;
  gap: 8px;
}

.channels-box {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.channels-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.channels-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.channel-card {
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.channel-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.channel-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
}

.channel-size-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 6px;
  border-top: 1px solid var(--line);
}

.channel-size-input {
  width: 68px;
  height: 28px;
  font-size: 12px;
  text-align: center;
}
</style>
