<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  device: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['apply-matrix']);

const activeBrush = ref('#4ade80');
const isMouseDown = ref(false);

const dimensions = computed(() => {
  if (props.device.matrix_dimensions && props.device.matrix_dimensions.length === 2) {
    return props.device.matrix_dimensions;
  }
  if (props.device.type === 'keyboard') return [6, 22];
  if (props.device.type === 'mousemat') return [1, 15];
  return [6, 14];
});

const rows = computed(() => dimensions.value[0]);
const cols = computed(() => dimensions.value[1]);

const grid = ref(createInitialGrid(rows.value, cols.value));

watch(
  () => [props.device?.serial, rows.value, cols.value],
  ([, r, c]) => {
    grid.value = createInitialGrid(r, c);
  }
);

function createInitialGrid(r, c) {
  const arr = [];
  for (let i = 0; i < r; i++) {
    const row = [];
    for (let j = 0; j < c; j++) {
      row.push('#141414');
    }
    arr.push(row);
  }
  return arr;
}

function onCellClick(r, c) {
  grid.value[r][c] = activeBrush.value;
}

function onCellEnter(r, c) {
  if (isMouseDown.value) {
    grid.value[r][c] = activeBrush.value;
  }
}

function fillRow(rIdx) {
  for (let j = 0; j < cols.value; j++) {
    grid.value[rIdx][j] = activeBrush.value;
  }
}

function fillAll() {
  for (let i = 0; i < rows.value; i++) {
    for (let j = 0; j < cols.value; j++) {
      grid.value[i][j] = activeBrush.value;
    }
  }
  applyMatrix();
}

function clearAll() {
  for (let i = 0; i < rows.value; i++) {
    for (let j = 0; j < cols.value; j++) {
      grid.value[i][j] = '#141414';
    }
  }
  applyMatrix();
}

function applyMatrix() {
  emit('apply-matrix', {
    serial: props.device.serial,
    grid: grid.value
  });
}

const palette = [
  '#fafafa', '#4ade80', '#00ff00', '#00ffff', '#38bdf8', '#3b82f6', '#a855f7', '#fbbf24', '#f87171', '#141414'
];
</script>

<template>
  <div class="matrix-editor" @mouseup="isMouseDown = false" @mouseleave="isMouseDown = false">
    <div class="section-header">
      <div>
        <h2 class="section-title">LED Matrix Editor</h2>
        <p class="section-desc">
          Design custom per-key and per-channel addressable RGB LED layouts ({{ rows }} × {{ cols }} matrix).
        </p>
      </div>
      <div v-if="device.has_matrix" class="matrix-actions">
        <button class="btn btn--secondary btn--small" @click="clearAll">Clear</button>
        <button class="btn btn--secondary btn--small" @click="fillAll">Fill All</button>
        <button class="btn btn--primary btn--small" @click="applyMatrix">Apply to Hardware</button>
      </div>
    </div>

    <div v-if="!device.has_matrix" class="box empty-matrix-box">
      <span class="micro">This device ({{ device.name }}) does not have an individually addressable LED matrix.</span>
    </div>

    <template v-else>
      <!-- Brush Selector -->
      <div class="brush-bar box">
        <div class="brush-left">
          <span class="micro">Active Brush:</span>
          <input type="color" class="brush-color-picker" v-model="activeBrush" />
          <span class="micro num">{{ activeBrush }}</span>
        </div>
        <div class="palette-swatches">
          <button
            v-for="color in palette"
            :key="color"
            class="palette-btn"
            :style="{ backgroundColor: color }"
            :class="{ 'palette-btn--active': activeBrush === color }"
            @click="activeBrush = color"
          ></button>
        </div>
      </div>

      <!-- Interactive Grid -->
      <div class="grid-container box" @mousedown="isMouseDown = true">
        <div class="grid-wrap">
          <div v-for="(row, rIdx) in grid" :key="rIdx" class="grid-row">
            <button
              class="row-label micro num"
              @click.stop="fillRow(rIdx)"
              :title="`Click to fill Row/Channel ${rIdx + 1}`"
            >
              {{ device.channels && device.channels.length ? `CH ${rIdx + 1}` : `R${rIdx + 1}` }}
            </button>
            <div
              v-for="(cell, cIdx) in row"
              :key="cIdx"
              class="grid-cell"
              :style="{ backgroundColor: cell }"
              @mousedown="onCellClick(rIdx, cIdx)"
              @mouseenter="onCellEnter(rIdx, cIdx)"
              :title="`Row ${rIdx + 1}, LED ${cIdx + 1}`"
            ></div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.matrix-editor {
  display: flex;
  flex-direction: column;
  gap: 20px;
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

.empty-matrix-box {
  padding: 24px;
  text-align: center;
}

.matrix-actions {
  display: flex;
  gap: 8px;
}

.brush-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.brush-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brush-color-picker {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--line-strong);
  cursor: pointer;
  background: transparent;
  padding: 0;
}

.palette-swatches {
  display: flex;
  gap: 8px;
}

.palette-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 1px solid var(--line-strong);
  cursor: pointer;
  transition: opacity 120ms;
}

.palette-btn:hover {
  opacity: 0.85;
}

.palette-btn--active {
  border-color: var(--text);
  box-shadow: 0 0 0 2px var(--text);
}

.grid-container {
  overflow-x: auto;
  padding: 24px;
  display: flex;
  justify-content: flex-start;
}

.grid-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.grid-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.row-label {
  min-width: 48px;
  height: 26px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 4px;
  color: var(--text-2);
  cursor: pointer;
  margin-right: 6px;
  transition: border-color 120ms, color 120ms;
}

.row-label:hover {
  border-color: var(--line-strong);
  color: var(--text);
}

.grid-cell {
  width: 26px;
  height: 26px;
  border-radius: 4px;
  border: 1px solid var(--line);
  cursor: pointer;
  transition: background-color 80ms, border-color 80ms;
}

.grid-cell:hover {
  border-color: var(--text);
}
</style>
