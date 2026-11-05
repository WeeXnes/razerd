<script setup>
import ThemeToggle from './ThemeToggle.vue';

defineProps({
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
  }
});

const emit = defineEmits(['navigate']);

const sections = [
  { id: 'overview', label: 'Overview' },
  { id: 'lighting', label: 'Lighting' },
  { id: 'performance', label: 'Performance' },
  { id: 'matrix', label: 'Matrix' },
  { id: 'power', label: 'Power' },
  { id: 'profiles', label: 'Profiles' },
  { id: 'troubleshooter', label: 'Health' },
  { id: 'settings', label: 'Settings' }
];
</script>

<template>
  <header class="app-header">
    <div class="app-header__left">
      <div class="wordmark-group">
        <span class="app-wordmark">razerd</span>
        <span class="app-slash">/</span>
        <span class="app-section-name">{{ sections.find(s => s.id === currentSection)?.label || 'Overview' }}</span>
      </div>

      <nav class="app-nav">
        <a
          v-for="sec in sections"
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
