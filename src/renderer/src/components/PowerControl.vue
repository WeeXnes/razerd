<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  device: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update-power']);

const idleTime = ref(props.device.idle_time || 15);
const lowBattery = ref(props.device.low_battery_threshold || 10);

watch(
  () => props.device,
  (newDev) => {
    if (newDev) {
      if (newDev.idle_time !== null && newDev.idle_time !== undefined) {
        idleTime.value = newDev.idle_time;
      }
      if (newDev.low_battery_threshold !== null && newDev.low_battery_threshold !== undefined) {
        lowBattery.value = newDev.low_battery_threshold;
      }
    }
  },
  { deep: true }
);

function onIdleChange(val) {
  const num = parseInt(val) || 15;
  idleTime.value = num;
  applyPower();
}

function onThresholdChange(val) {
  const num = parseInt(val) || 10;
  lowBattery.value = num;
  applyPower();
}

function applyPower() {
  emit('update-power', {
    serial: props.device.serial,
    idle_time: idleTime.value,
    low_battery_threshold: lowBattery.value
  });
}
</script>

<template>
  <div class="power-control">
    <div class="section-header">
      <div>
        <h2 class="section-title">Power & Battery</h2>
        <p class="section-desc">Manage wireless energy consumption, standby timers, and low battery thresholds.</p>
      </div>
      <div v-if="device.has_battery" class="battery-status">
        <span class="status-dot" :class="device.is_charging ? 'status-dot--warning' : (device.battery > 20 ? 'status-dot--success' : 'status-dot--danger')"></span>
        <span class="micro num">{{ device.battery !== null ? `${device.battery}%` : 'Unknown' }} {{ device.is_charging ? '(Charging)' : '' }}</span>
      </div>
    </div>

    <!-- Battery Overview -->
    <div v-if="device.has_battery" class="box battery-summary">
      <div class="summary-top">
        <span class="micro">Energy Level</span>
        <span class="battery-val num">{{ device.battery !== null ? `${device.battery}%` : '—' }}</span>
      </div>
      <div class="battery-meter-bar">
        <div
          class="battery-fill"
          :style="{
            width: `${device.battery || 0}%`,
            backgroundColor: device.battery > 20 ? 'var(--text)' : 'var(--danger)'
          }"
        ></div>
      </div>
    </div>

    <!-- Power Options -->
    <div class="box power-options">
      <!-- Idle Sleep Timeout -->
      <div class="option-row">
        <div class="option-header">
          <div class="option-info">
            <span class="option-title">Sleep Inactivity Timeout</span>
            <span class="option-hint">Enter low-power standby mode after uninterrupted inactivity.</span>
          </div>
          <span class="option-val num">{{ idleTime }} min</span>
        </div>
        <input
          type="range"
          min="1"
          max="15"
          step="1"
          :value="idleTime"
          @input="onIdleChange($event.target.value)"
        />
      </div>

      <div class="row-divider"></div>

      <!-- Low Battery Threshold -->
      <div class="option-row">
        <div class="option-header">
          <div class="option-info">
            <span class="option-title">Low Power Warning Threshold</span>
            <span class="option-hint">Activate low battery warning blinking when capacity drops below this percentage.</span>
          </div>
          <span class="option-val num">{{ lowBattery }}%</span>
        </div>
        <input
          type="range"
          min="5"
          max="30"
          step="1"
          :value="lowBattery"
          @input="onThresholdChange($event.target.value)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.power-control {
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

.battery-status {
  display: flex;
  align-items: center;
  gap: 6px;
}

.battery-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.battery-val {
  font-size: 24px;
  font-weight: 500;
  color: var(--text);
}

.battery-meter-bar {
  width: 100%;
  height: 6px;
  background: var(--surface-2);
  border-radius: 3px;
  overflow: hidden;
  border: 1px solid var(--line);
}

.battery-fill {
  height: 100%;
  transition: width 200ms ease-out;
}

.power-options {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.option-row {
  display: flex;
  flex-direction: column;
}

.option-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.option-info {
  display: flex;
  flex-direction: column;
}

.option-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  margin-bottom: 2px;
}

.option-hint {
  font-size: 13px;
  color: var(--text-3);
}

.option-val {
  font-size: 15px;
  color: var(--text);
}

.row-divider {
  height: 1px;
  background: var(--line);
}
</style>
