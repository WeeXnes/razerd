<script setup>
import { computed } from 'vue';
import ThemeToggle from './ThemeToggle.vue';

const props = defineProps({
  currentSection: {
    type: String,
    required: true
  },
  daemonOnline: {
    type: Boolean,
    default: true
  },
  deviceCount: {
    type: Number,
    default: 0
  },
  device: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['navigate']);

const allSections = [
  { id: 'overview', label: 'Overview' },
  { id: 'performance', label: 'Performance', check: (d) => !d || d.has_dpi || d.has_poll_rate },
  { id: 'buttons', label: 'Buttons', check: (d) => !d || d.has_buttons },
  { id: 'lighting', label: 'Lighting', check: (d) => !d || d.has_lighting },
  { id: 'matrix', label: 'Matrix', check: (d) => !d || d.has_matrix },
  { id: 'power', label: 'Power', check: (d) => !d || d.has_battery },
  { id: 'profiles', label: 'Profiles' },
  { id: 'troubleshooter', label: 'Health' },
  { id: 'settings', label: 'Settings' }
];

const visibleSections = computed(() => {
  return allSections.filter((s) => !s.check || s.check(props.device));
});
</script>

<template>
  <header class="app-header">
    <div class="app-header__left">
      <div class="wordmark-group">
        <span class="app-wordmark">razerd</span>
        <span class="app-slash">/</span>
        <span class="app-section-name">{{ allSections.find(s => s.id === currentSection)?.label || 'Overview' }}</span>
      </div>

      <nav class="app-nav">
        <a
          v-for="sec in visibleSections"
          :key="sec.id"
          class="app-nav__link"
          :class="{ active: currentSection === sec.id }"
          @click.prevent="emit('navigate', sec.id)"
        >
          {{ sec.label }}
        </a>
      </nav>
    </div>

    <div class="app-header__right">
      <div class="daemon-status">
        <span
          class="status-dot"
          :class="daemonOnline ? 'status-dot--success' : 'status-dot--danger'"
        ></span>
        <span class="micro">{{ daemonOnline ? `${deviceCount} Device${deviceCount === 1 ? '' : 's'}` : 'Offline' }}</span>
      </div>
      <ThemeToggle />
    </div>
  </header>
</template>

<style scoped>
.wordmark-group {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 24px;
}

.daemon-status {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
