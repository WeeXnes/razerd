<script setup>
defineProps({
  device: {
    type: Object,
    default: null
  },
  activeProfile: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['open-profiles']);
</script>

<template>
  <div v-if="device" class="hero-stats">
    <div v-if="device.has_dpi" class="hero-stat">
      <div class="hero-stat__val num">{{ device.dpi ? device.dpi[0] : '—' }}</div>
      <div class="micro">Current DPI</div>
    </div>

    <div v-if="device.has_poll_rate" class="hero-stat">
      <div class="hero-stat__val num">{{ device.poll_rate ? `${device.poll_rate} Hz` : '—' }}</div>
      <div class="micro">Polling Rate</div>
    </div>

    <div v-if="device.has_battery" class="hero-stat">
      <div class="hero-stat__val num">
        {{ device.battery !== null ? `${device.battery}%` : 'Wired' }}
      </div>
      <div class="micro">{{ device.is_charging ? 'Charging' : 'Battery' }}</div>
    </div>

    <div v-if="device.has_brightness" class="hero-stat">
      <div class="hero-stat__val num">
        {{ device.brightness !== null ? `${Math.round(device.brightness)}%` : '—' }}
      </div>
      <div class="micro">Brightness</div>
    </div>

    <div v-if="activeProfile" class="hero-stat hero-stat--clickable" @click="emit('open-profiles')" title="Click to switch profiles">
      <div class="hero-stat__val micro-val">{{ activeProfile.name }}</div>
      <div class="micro">Active Profile</div>
    </div>

    <div class="hero-stat">
      <div class="hero-stat__val micro-val num">{{ device.firmware || 'v1.0' }}</div>
      <div class="micro">Firmware</div>
    </div>
  </div>
</template>

<style scoped>
.hero-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 24px;
  border-bottom: 1px solid var(--line);
  padding: 24px 0;
  margin-bottom: 24px;
}

.hero-stat {
  display: flex;
  flex-direction: column;
}

.hero-stat--clickable {
  cursor: pointer;
  transition: opacity 120ms;
}

.hero-stat--clickable:hover {
  opacity: 0.75;
}

.hero-stat__val {
  font-size: 32px;
  font-weight: 500;
  color: var(--text);
  line-height: 1.1;
  margin-bottom: 4px;
}

.micro-val {
  font-size: 20px;
  line-height: 1.7;
}
</style>
