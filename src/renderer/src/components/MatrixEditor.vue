<script setup>
import { ref, computed } from 'vue';

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
  return [1, 16]; // ARGB controller / accessory
});

const rows = computed(() => dimensions.value[0]);
const cols = computed(() => dimensions.value[1]);

// Initialize grid cells with default color
const grid = ref(createInitialGrid(rows.value, cols.value));

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

function fillAll() {
  for (let i = 0; i < rows.value; i++) {
    for (let j = 0; j < cols.value; j++) {
      grid.value[i][j] = activeBrush.value;
    }
  }
}

function clearAll() {
  for (let i = 0; i < rows.value; i++) {
    for (let j = 0; j < cols.value; j++) {
      grid.value[i][j] = '#141414';
    }
  }
}

function applyMatrix() {
  emit('apply-matrix', {
    serial: props.device.serial,
    grid: grid.value
  });
}

const palette = [
  '#fafafa', '#4ade80', '#00ff00', '#38bdf8', '#3b82f6', '#a855f7', '#fbbf24', '#f87171', '#141414'
];
</script>

<template>
  <div class="matrix-editor" @mouseup="isMouseDown = false" @mouseleave="isMouseDown = false">
    <div class="section-header">
      <div>
        <h2 class="section-title">LED Matrix Editor</h2>
        <p class="section-desc">Design custom per-key and addressable RGB LED layouts.</p>
      </div>
      <div class="matrix-actions">
        <button class="btn btn--secondary btn--small" @click="clearAll">Clear</button>
        <button class="btn btn--secondary btn--small" @click="fillAll">Fill</button>
        <button class="btn btn--primary btn--small" @click="applyMatrix">Apply to Device</button>
      </div>
    </div>

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
          <div
            v-for="(cell, cIdx) in row"
            :key="cIdx"
            class="grid-cell"
            :style="{ backgroundColor: cell }"
            @mousedown="onCellClick(rIdx, cIdx)"
            @mouseenter="onCellEnter(rIdx, cIdx)"
            :title="`Row ${rIdx + 1}, Col ${cIdx + 1}`"
          ></div>
        </div>
      </div>
    </div>
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
  transition: transform 120ms;
}

.palette-btn:hover {
  transform: scale(1.15);
}

.palette-btn--active {
  border-color: var(--text);
  box-shadow: 0 0 0 2px var(--text);
}

.grid-container {
  overflow-x: auto;
  padding: 24px;
  display: flex;
  justify-content: center;
}

.grid-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.grid-row {
  display: flex;
  gap: 4px;
}

.grid-cell {
  width: 26px;
  height: 26px;
  border-radius: 4px;
  border: 1px solid var(--line);
  cursor: pointer;
  transition: background-color 80ms, transform 80ms;
}

.grid-cell:hover {
  transform: scale(1.1);
  border-color: var(--text);
  z-index: 2;
}
</style>
