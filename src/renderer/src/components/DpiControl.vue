<script setup>
import { ref, watch, computed, onBeforeUnmount } from 'vue';

const props = defineProps({
  device: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update-dpi', 'update-stages']);

const linkXY = ref(true);
const currentX = ref(props.device.dpi ? props.device.dpi[0] : 1600);
const currentY = ref(props.device.dpi ? props.device.dpi[1] : 1600);
const maxDpi = computed(() => props.device.max_dpi || 30000);

const activeStage = ref(props.device.active_dpi_stage || 1);
const stages = ref(
  props.device.dpi_stages && props.device.dpi_stages.length
    ? JSON.parse(JSON.stringify(props.device.dpi_stages))
    : [[400, 400], [800, 800], [1600, 1600], [3200, 3200], [6400, 6400]]
);

const isDragging = ref(false);
let lastInteractionAt = 0;
let dpiThrottleTimer = null;
let lastDpiSentAt = 0;
let stageThrottleTimer = null;
let lastStageSentAt = 0;

function markInteraction() {
  lastInteractionAt = Date.now();
}

function syncFromDevice(newDev, force = false) {
  if (!newDev) return;
  if (!force && (isDragging.value || Date.now() - lastInteractionAt < 4000)) {
    return;
  }
  if (newDev.dpi) {
    currentX.value = newDev.dpi[0] || 1600;
    currentY.value = newDev.dpi[1] || 1600;
    if (newDev.dpi[0] === newDev.dpi[1]) {
      linkXY.value = true;
    }
  }
  if (newDev.dpi_stages && newDev.dpi_stages.length) {
    stages.value = JSON.parse(JSON.stringify(newDev.dpi_stages));
  }
  if (newDev.active_dpi_stage) {
    activeStage.value = newDev.active_dpi_stage;
  }
}

watch(
  () => props.device?.serial,
  () => {
    isDragging.value = false;
    lastInteractionAt = 0;
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

onBeforeUnmount(() => {
  if (dpiThrottleTimer) clearTimeout(dpiThrottleTimer);
  if (stageThrottleTimer) clearTimeout(stageThrottleTimer);
});

function syncActiveStageSlot() {
  const idx = activeStage.value - 1;
  if (idx >= 0 && idx < stages.value.length) {
    stages.value[idx] = [currentX.value, currentY.value];
  }
}

function emitDpiThrottled(commit = false) {
  if (commit) {
    if (dpiThrottleTimer) {
      clearTimeout(dpiThrottleTimer);
      dpiThrottleTimer = null;
    }
    lastDpiSentAt = Date.now();
    emit('update-dpi', {
      serial: props.device.serial,
      x: currentX.value,
      y: currentY.value,
      commit: true
    });
    return;
  }

  const now = Date.now();
  const elapsed = now - lastDpiSentAt;
  if (elapsed >= 90) {
    lastDpiSentAt = now;
    emit('update-dpi', {
      serial: props.device.serial,
      x: currentX.value,
      y: currentY.value,
      commit: false
    });
  } else if (!dpiThrottleTimer) {
    dpiThrottleTimer = setTimeout(() => {
      dpiThrottleTimer = null;
      lastDpiSentAt = Date.now();
      emit('update-dpi', {
        serial: props.device.serial,
        x: currentX.value,
        y: currentY.value,
        commit: false
      });
    }, 90 - elapsed);
  }
}

function emitStagesThrottled(commit = false) {
  if (commit) {
    if (stageThrottleTimer) {
      clearTimeout(stageThrottleTimer);
      stageThrottleTimer = null;
    }
    lastStageSentAt = Date.now();
    emit('update-stages', {
      serial: props.device.serial,
      active: activeStage.value,
      stages: stages.value.map((s) => [s[0], s[1]]),
      commit: true
    });
    return;
  }

  const now = Date.now();
  const elapsed = now - lastStageSentAt;
  if (elapsed >= 110) {
    lastStageSentAt = now;
    emit('update-stages', {
      serial: props.device.serial,
      active: activeStage.value,
      stages: stages.value.map((s) => [s[0], s[1]]),
      commit: false
    });
  } else if (!stageThrottleTimer) {
    stageThrottleTimer = setTimeout(() => {
      stageThrottleTimer = null;
      lastStageSentAt = Date.now();
      emit('update-stages', {
        serial: props.device.serial,
        active: activeStage.value,
        stages: stages.value.map((s) => [s[0], s[1]]),
        commit: false
      });
    }, 110 - elapsed);
  }
}

function onXInput(val) {
  isDragging.value = true;
  markInteraction();
  const num = Math.min(maxDpi.value, Math.max(100, parseInt(val) || 100));
  currentX.value = num;
  if (linkXY.value) {
    currentY.value = num;
  }
  syncActiveStageSlot();
  emitDpiThrottled(false);
}

function onXCommit(val) {
  isDragging.value = false;
  markInteraction();
  const num = Math.min(maxDpi.value, Math.max(100, parseInt(val) || 100));
  currentX.value = num;
  if (linkXY.value) {
    currentY.value = num;
  }
  syncActiveStageSlot();
  emitDpiThrottled(true);
}

function onYInput(val) {
  isDragging.value = true;
  markInteraction();
  const num = Math.min(maxDpi.value, Math.max(100, parseInt(val) || 100));
  currentY.value = num;
  if (linkXY.value) {
    currentX.value = num;
  }
  syncActiveStageSlot();
  emitDpiThrottled(false);
}

function onYCommit(val) {
  isDragging.value = false;
  markInteraction();
  const num = Math.min(maxDpi.value, Math.max(100, parseInt(val) || 100));
  currentY.value = num;
  if (linkXY.value) {
    currentX.value = num;
  }
  syncActiveStageSlot();
  emitDpiThrottled(true);
}

function setQuickPreset(val) {
  markInteraction();
  currentX.value = val;
  currentY.value = val;
  syncActiveStageSlot();
  emitDpiThrottled(true);
}

function selectStage(index) {
  markInteraction();
  activeStage.value = index + 1;
  const stageVal = stages.value[index];
  if (stageVal) {
    currentX.value = stageVal[0];
    currentY.value = stageVal[1];
  }
  emitStagesThrottled(true);
}

function onStageInput(index, val) {
  isDragging.value = true;
  markInteraction();
  const num = Math.min(maxDpi.value, Math.max(100, parseInt(val) || 100));
  stages.value[index] = [num, num];
  if (activeStage.value === index + 1) {
    currentX.value = num;
    currentY.value = num;
  }
  emitStagesThrottled(false);
}

function onStageCommit(index, val) {
  isDragging.value = false;
  markInteraction();
  const num = Math.min(maxDpi.value, Math.max(100, parseInt(val) || 100));
  stages.value[index] = [num, num];
  if (activeStage.value === index + 1) {
    currentX.value = num;
    currentY.value = num;
  }
  emitStagesThrottled(true);
}
</script>

<template>
  <div class="dpi-control">
    <div class="section-header">
      <div>
        <h2 class="section-title">Sensitivity (DPI)</h2>
        <p class="section-desc">Configure optical sensor resolution and switch hardware DPI stages.</p>
      </div>
      <div class="link-toggle">
        <label class="toggle-label">
          <input type="checkbox" v-model="linkXY" />
          <span class="micro">Link X & Y</span>
        </label>
      </div>
    </div>

    <!-- Active DPI Sliders -->
    <div class="dpi-main box">
      <div class="axis-row">
        <div class="axis-label">
          <span class="micro">X Axis</span>
          <span class="axis-value num">{{ currentX }} DPI</span>
        </div>
        <input
          type="range"
          min="100"
          :max="maxDpi"
          step="50"
          :value="currentX"
          @pointerdown="isDragging = true"
          @pointerup="isDragging = false"
          @input="onXInput($event.target.value)"
          @change="onXCommit($event.target.value)"
        />
      </div>

      <div v-if="!linkXY" class="axis-row">
        <div class="axis-label">
          <span class="micro">Y Axis</span>
          <span class="axis-value num">{{ currentY }} DPI</span>
        </div>
        <input
          type="range"
          min="100"
          :max="maxDpi"
          step="50"
          :value="currentY"
          @pointerdown="isDragging = true"
          @pointerup="isDragging = false"
          @input="onYInput($event.target.value)"
          @change="onYCommit($event.target.value)"
        />
      </div>

      <!-- Quick Presets -->
      <div class="quick-presets">
        <span class="micro">Presets:</span>
        <div class="presets-row">
          <button
            v-for="preset in [400, 800, 1600, 3200, 6400]"
            :key="preset"
            class="btn btn--secondary btn--small num"
            :class="{ active: currentX === preset && currentY === preset }"
            @click="setQuickPreset(preset)"
          >
            {{ preset }}
          </button>
        </div>
      </div>
    </div>

    <!-- DPI Stages Editor -->
    <div class="stages-section">
      <div class="stages-header">
        <span class="micro">DPI Stages</span>
        <span class="micro num">Max {{ maxDpi }} DPI</span>
      </div>

      <div class="stages-grid">
        <div
          v-for="(st, idx) in stages"
          :key="idx"
          class="stage-card"
          :class="{ 'stage-card--active': activeStage === idx + 1 }"
          @click="selectStage(idx)"
        >
          <div class="stage-top">
            <span class="micro">Stage {{ idx + 1 }}</span>
            <span v-if="activeStage === idx + 1" class="active-badge micro">Active</span>
          </div>
          <div class="stage-val num">{{ st[0] }}</div>
          <input
            type="range"
            min="100"
            :max="maxDpi"
            step="50"
            :value="st[0]"
            @click.stop
            @pointerdown.stop="isDragging = true"
            @pointerup.stop="isDragging = false"
            @input.stop="onStageInput(idx, $event.target.value)"
            @change.stop="onStageCommit(idx, $event.target.value)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dpi-control {
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

.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.axis-row {
  margin-bottom: 16px;
}

.axis-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.axis-value {
  font-size: 16px;
  color: var(--text);
}

.quick-presets {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}

.presets-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stages-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stages-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.stage-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: background-color 120ms, border-color 120ms;
}

.stage-card:hover {
  background: var(--surface-2);
}

.stage-card--active {
  border-color: var(--line-strong);
  background: var(--surface-2);
}

.stage-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.active-badge {
  color: var(--text);
}

.stage-val {
  font-size: 20px;
  font-weight: 500;
  color: var(--text);
  margin-bottom: 8px;
}
</style>
