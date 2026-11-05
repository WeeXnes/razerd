<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  device: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update-brightness', 'update-effect', 'sync-rgb']);

const brightness = ref(
  props.device.brightness !== null && props.device.brightness !== undefined
    ? Math.round(props.device.brightness)
    : 100
);

const lightingState = computed(() => props.device.lighting || {});
const currentEffect = ref(lightingState.value.current_effect || 'static');
const colors = ref(lightingState.value.colors ? [...lightingState.value.colors] : ['#fafafa']);
const speed = ref(lightingState.value.speed || 'normal');
const direction = ref(lightingState.value.direction || 'right');
const selectedZone = ref('overall');

const availableEffects = computed(() => {
  return lightingState.value.supported_effects && lightingState.value.supported_effects.length
    ? lightingState.value.supported_effects
    : ['none', 'static', 'breath', 'spectrum', 'wave'];
});

const availableZones = computed(() => {
  return lightingState.value.zones && lightingState.value.zones.length
    ? lightingState.value.zones
    : ['overall'];
});

watch(
  () => props.device,
  (newDev) => {
    if (newDev) {
      if (newDev.brightness !== null && newDev.brightness !== undefined) {
        brightness.value = Math.round(newDev.brightness);
      }
      if (newDev.lighting) {
        if (newDev.lighting.current_effect) currentEffect.value = newDev.lighting.current_effect;
        if (newDev.lighting.colors) colors.value = [...newDev.lighting.colors];
        if (newDev.lighting.speed) speed.value = newDev.lighting.speed;
        if (newDev.lighting.direction) direction.value = newDev.lighting.direction;
      }
    }
  },
  { deep: true }
);

function onBrightnessChange(val) {
  const num = Math.min(100, Math.max(0, parseInt(val) || 0));
  brightness.value = num;
  emit('update-brightness', {
    serial: props.device.serial,
    brightness: num,
    zone: selectedZone.value
  });
}

function selectEffect(eff) {
  currentEffect.value = eff;
  applyEffect();
}

function setColor(hex, index = 0) {
  const updated = [...colors.value];
  updated[index] = hex;
  colors.value = updated;
  applyEffect();
}

function setSpeed(val) {
  speed.value = val;
  applyEffect();
}

function setDirection(val) {
  direction.value = val;
  applyEffect();
}

function applyEffect() {
  emit('update-effect', {
    serial: props.device.serial,
    effect: currentEffect.value,
    colors: colors.value,
    speed: speed.value,
    direction: direction.value,
    zone: selectedZone.value
  });
}

function syncAll() {
  emit('sync-rgb', {
    effect: currentEffect.value,
    colors: colors.value,
    speed: speed.value,
    direction: direction.value
  });
}

const colorPresets = [
  { name: 'Monochrome White', hex: '#fafafa' },
  { name: 'Razer Green', hex: '#00ff00' },
  { name: 'Emerald', hex: '#4ade80' },
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
      <button class="btn btn--secondary btn--small" @click="syncAll" title="Apply current effect across all connected Razer peripherals">
        Sync RGB to All
      </button>
    </div>

    <!-- Brightness Slider -->
    <div v-if="device.has_brightness" class="box brightness-box">
      <div class="brightness-header">
        <div class="bright-left">
          <span class="micro">Brightness</span>
          <span class="micro num">{{ brightness }}%</span>
        </div>
        <button
          class="btn btn--secondary btn--small"
          @click="onBrightnessChange(brightness === 0 ? 100 : 0)"
        >
          <span class="micro">{{ brightness === 0 ? 'Unmute' : 'Mute' }}</span>
        </button>
      </div>
      <input
        type="range"
        min="0"
        max="100"
        step="1"
        :value="brightness"
        @input="onBrightnessChange($event.target.value)"
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
    <div class="effects-section">
      <div class="effects-header">
        <span class="micro">Lighting Effect</span>
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
            <span v-else-if="eff === 'matrix'">Custom per-LED addressing</span>
            <span v-else>Custom effect</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Effect Parameters & Color Picker -->
    <div v-if="currentEffect !== 'none' && currentEffect !== 'spectrum'" class="box params-box">
      <!-- Color Selection -->
      <div class="color-section">
        <div class="color-header">
          <span class="micro">Color Selection</span>
          <div class="color-inputs">
            <input
              type="color"
              class="color-picker-input"
              :value="colors[0] || '#fafafa'"
              @input="setColor($event.target.value, 0)"
            />
            <input
              type="text"
              class="input input-num color-text-input"
              :value="colors[0] || '#fafafa'"
              @change="setColor($event.target.value, 0)"
            />
          </div>
        </div>

        <!-- Second color for dual breathing/starlight -->
        <div v-if="currentEffect === 'breath' || currentEffect === 'starlight'" class="color-header" style="margin-top: 12px;">
          <span class="micro">Secondary Color</span>
          <div class="color-inputs">
            <input
              type="color"
              class="color-picker-input"
              :value="colors[1] || '#4ade80'"
              @input="setColor($event.target.value, 1)"
            />
            <input
              type="text"
              class="input input-num color-text-input"
              :value="colors[1] || '#4ade80'"
              @change="setColor($event.target.value, 1)"
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
            @click="setColor(swatch.hex, 0)"
          ></button>
        </div>
      </div>

      <!-- Direction & Speed Controls -->
      <div v-if="currentEffect === 'wave'" class="direction-row">
        <span class="micro">Wave Direction:</span>
        <div class="btn-group">
          <button
            class="btn btn--secondary btn--small"
            :class="{ active: direction === 'left' }"
            @click="setDirection('left')"
          >
            <span class="micro">Left</span>
          </button>
          <button
            class="btn btn--secondary btn--small"
            :class="{ active: direction === 'right' }"
            @click="setDirection('right')"
          >
            <span class="micro">Right</span>
          </button>
        </div>
      </div>

      <div v-if="['wave', 'reactive', 'starlight'].includes(currentEffect)" class="speed-row">
        <span class="micro">Animation Speed:</span>
        <div class="btn-group">
          <button
            v-for="spd in ['slow', 'normal', 'fast', 'ultra']"
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
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
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
  transition: transform 120ms;
}

.swatch-btn:hover {
  transform: scale(1.15);
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
</style>
