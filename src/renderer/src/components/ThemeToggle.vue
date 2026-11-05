<script setup>
import { ref, onMounted } from 'vue';

const theme = ref('dark');

onMounted(() => {
  const saved = localStorage.getItem('razerd-theme') || 'dark';
  setTheme(saved);
});

function setTheme(val) {
  theme.value = val;
  localStorage.setItem('razerd-theme', val);
  if (val === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
}

function toggle() {
  setTheme(theme.value === 'dark' ? 'light' : 'dark');
}
</script>

<template>
  <button
    class="theme-toggle btn btn--secondary btn--small"
    @click="toggle"
    :title="theme === 'dark' ? 'Switch to Light theme' : 'Switch to Dark theme'"
  >
    <span class="micro">{{ theme === 'dark' ? 'Dark' : 'Light' }}</span>
  </button>
</template>

<style scoped>
.theme-toggle {
  min-width: 64px;
}
</style>
