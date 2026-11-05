<script setup>
import { computed } from 'vue';

const props = defineProps({
  device: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update-poll-rate']);

const currentRate = computed(() => props.device.poll_rate || 1000);
const supportedRates = computed(() => {
  if (props.device.supported_poll_rates && props.device.supported_poll_rates.length) {
    return props.device.supported_poll_rates;
  }
  return [125, 500, 1000];
});

function getLatency(rate) {
  const ms = 1000 / rate;
  return ms < 1 ? `${ms.toFixed(3)} ms` : `${ms.toFixed(1)} ms`;
}

function selectRate(rate) {
  emit('update-poll-rate', {
    serial: props.device.serial,
    rate: parseInt(rate)
  });
}
</script>

<template>
  <div class="poll-rate-control">
    <div class="section-header">
      <div>
        <h2 class="section-title">Polling Rate</h2>
        <p class="section-desc">Report rate frequency communicated between peripheral and host system.</p>
      </div>
      <div class="current-meta micro num">
        {{ currentRate }} Hz ({{ getLatency(currentRate) }})
      </div>
    </div>

    <div class="rates-list">
      <div
        v-for="rate in supportedRates"
        :key="rate"
        class="rate-row"
        :class="{ 'rate-row--active': currentRate === rate }"
        @click="selectRate(rate)"
      >
        <div class="rate-left">
          <span class="rate-name num">{{ rate }} Hz</span>
          <span v-if="rate >= 4000" class="hyper-tag micro">HyperPolling</span>
        </div>
        <div class="rate-right">
          <span class="rate-latency micro num">{{ getLatency(rate) }}</span>
          <div class="select-dot" :class="{ 'select-dot--active': currentRate === rate }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.poll-rate-control {
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

.current-meta {
  color: var(--text);
}

.rates-list {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}

.rate-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
  cursor: pointer;
  transition: background-color 120ms;
}

.rate-row:last-child {
  border-bottom: none;
}

.rate-row:hover {
  background: var(--surface-2);
}

.rate-row--active {
  background: var(--surface-2);
}

.rate-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rate-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text);
}

.hyper-tag {
  color: var(--success);
  border: 1px solid var(--success);
  border-radius: 6px;
  padding: 2px 6px;
  font-size: 10px;
}

.rate-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.rate-latency {
  color: var(--text-3);
}

.select-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 1px solid var(--line-strong);
  background: transparent;
  transition: all 120ms;
}

.select-dot--active {
  border-color: var(--text);
  background: var(--text);
  box-shadow: inset 0 0 0 3px var(--bg);
}
</style>
