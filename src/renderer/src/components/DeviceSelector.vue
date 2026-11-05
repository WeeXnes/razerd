<script setup>
defineProps({
  devices: {
    type: Array,
    required: true
  },
  selectedSerial: {
    type: String,
    default: ''
  }
});

const emit = defineEmits(['select']);
</script>

<template>
  <div class="device-bar">
    <div
      v-for="dev in devices"
      :key="dev.serial"
      class="device-item"
      :class="{ 'device-item--active': selectedSerial === dev.serial }"
      @click="emit('select', dev.serial)"
    >
      <div class="device-item__header">
        <span class="micro">{{ dev.type }}</span>
        <span v-if="dev.has_battery && dev.battery !== null" class="battery-tag num">
          <span v-if="dev.is_charging" class="charging-icon">⚡</span>
          {{ dev.battery }}%
        </span>
      </div>
      <div class="device-item__name">{{ dev.name }}</div>
      <div class="device-item__meta micro num">{{ dev.serial }}</div>
    </div>
  </div>
</template>

<style scoped>
.device-bar {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.device-item {
  flex: 1;
  min-width: 220px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: background-color 120ms, border-color 120ms;
  position: relative;
}

.device-item:hover {
  background: var(--surface-2);
}

.device-item--active {
  border-color: var(--line-strong);
  background: var(--surface-2);
}

.device-item--active::before {
  content: "";
  position: absolute;
  top: 0;
  left: 16px;
  right: 16px;
  height: 2px;
  background: var(--text);
  border-radius: 2px;
}

.device-item__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.device-item__name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.device-item__meta {
  color: var(--text-3);
  font-size: 11px;
}

.battery-tag {
  font-size: 11px;
  color: var(--text-2);
  display: flex;
  align-items: center;
  gap: 4px;
}

.charging-icon {
  color: var(--warning);
}
</style>
