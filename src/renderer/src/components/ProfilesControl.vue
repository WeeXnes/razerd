<script setup>
import { ref, onMounted } from 'vue';

const props = defineProps({
  currentDevice: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['apply-profile']);

const DEFAULT_PROFILES = [
  {
    id: 'prof-comp',
    name: 'Competitive FPS',
    desc: 'High refresh rate, 800/1600 DPI stage, zero latency, static monochrome lighting.',
    dpi: [1600, 1600],
    poll_rate: 8000,
    brightness: 80,
    effect: 'static',
    colors: ['#fafafa'],
    idle_time: 15
  },
  {
    id: 'prof-stealth',
    name: 'Stealth Night',
    desc: 'Low power, minimal distraction, illumination turned off, extended standby timeout.',
    dpi: [1200, 1200],
    poll_rate: 1000,
    brightness: 0,
    effect: 'none',
    colors: ['#000000'],
    idle_time: 5
  },
  {
    id: 'prof-office',
    name: 'Work & Studio',
    desc: 'Balanced 1600 DPI, 1000 Hz reporting rate, clean white subtle breathing glow.',
    dpi: [1600, 1600],
    poll_rate: 1000,
    brightness: 50,
    effect: 'breath',
    colors: ['#fafafa'],
    idle_time: 10
  },
  {
    id: 'prof-chroma',
    name: 'Chroma Neon',
    desc: 'Dynamic spectrum cycling effect at 100% brightness with full RGB expression.',
    dpi: [1600, 1600],
    poll_rate: 1000,
    brightness: 100,
    effect: 'spectrum',
    colors: ['#4ade80'],
    idle_time: 15
  }
];

const profiles = ref([]);
const activeProfileId = ref('prof-comp');
const newProfileName = ref('');
const isCreating = ref(false);

onMounted(() => {
  const saved = localStorage.getItem('razerd-profiles');
  if (saved) {
    try {
      profiles.value = JSON.parse(saved);
    } catch {
      profiles.value = [...DEFAULT_PROFILES];
    }
  } else {
    profiles.value = [...DEFAULT_PROFILES];
    saveToStorage();
  }
});

function saveToStorage() {
  localStorage.setItem('razerd-profiles', JSON.stringify(profiles.value));
}

function applyProfile(prof) {
  activeProfileId.value = prof.id;
  emit('apply-profile', prof);
}

function createProfile() {
  const name = newProfileName.value.trim();
  if (!name) return;

  const newProf = {
    id: `prof-${Date.now()}`,
    name,
    desc: 'Custom user-saved peripheral profile.',
    dpi: props.currentDevice?.dpi ? [...props.currentDevice.dpi] : [1600, 1600],
    poll_rate: props.currentDevice?.poll_rate || 1000,
    brightness: props.currentDevice?.brightness || 100,
    effect: props.currentDevice?.lighting?.current_effect || 'static',
    colors: props.currentDevice?.lighting?.colors || ['#fafafa'],
    idle_time: props.currentDevice?.idle_time || 15
  };

  profiles.value.unshift(newProf);
  saveToStorage();
  newProfileName.value = '';
  isCreating.value = false;
  applyProfile(newProf);
}

function deleteProfile(id) {
  profiles.value = profiles.value.filter(p => p.id !== id);
  saveToStorage();
}

function exportProfiles() {
  const data = JSON.stringify(profiles.value, null, 2);
  const blob = new Blob([data], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'razerd-profiles.json';
  a.click();
  URL.revokeObjectURL(url);
}

function importProfiles(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (event) => {
    try {
      const parsed = JSON.parse(event.target.result);
      if (Array.isArray(parsed)) {
        profiles.value = parsed;
        saveToStorage();
      }
    } catch (err) {
      alert('Failed to parse profiles JSON: ' + err.message);
    }
  };
  reader.readAsText(file);
}
</script>

<template>
  <div class="profiles-control">
    <div class="section-header">
      <div>
        <h2 class="section-title">Hardware Profiles</h2>
        <p class="section-desc">Save and activate hardware performance and Chroma lighting presets.</p>
      </div>
      <div class="profile-actions">
        <label class="btn btn--secondary btn--small" title="Import JSON profiles">
          <input type="file" accept=".json" @change="importProfiles" style="display: none;" />
          Import
        </label>
        <button class="btn btn--secondary btn--small" @click="exportProfiles">Export</button>
        <button class="btn btn--primary btn--small" @click="isCreating = !isCreating">
          {{ isCreating ? 'Cancel' : 'New Profile' }}
        </button>
      </div>
    </div>

    <!-- Create Profile Drawer -->
    <div v-if="isCreating" class="box create-drawer">
      <span class="micro">Capture Current Configuration</span>
      <div class="create-form">
        <input
          type="text"
          class="input"
          v-model="newProfileName"
          placeholder="Profile Name (e.g. Counter-Strike 2, Lightroom)"
          @keydown.enter="createProfile"
        />
        <button class="btn btn--primary btn--small" @click="createProfile">Save</button>
      </div>
    </div>

    <!-- Profiles List -->
    <div class="profiles-list">
      <div
        v-for="prof in profiles"
        :key="prof.id"
        class="profile-card"
        :class="{ 'profile-card--active': activeProfileId === prof.id }"
      >
        <div class="profile-top">
          <div class="profile-title-row">
            <span class="profile-name">{{ prof.name }}</span>
            <span v-if="activeProfileId === prof.id" class="active-tag micro">Active</span>
          </div>
          <div class="profile-btns">
            <button
              v-if="!prof.id.startsWith('prof-comp') && !prof.id.startsWith('prof-stealth')"
              class="btn btn--danger btn--small"
              @click.stop="deleteProfile(prof.id)"
            >
              Delete
            </button>
            <button
              class="btn btn--secondary btn--small"
              :class="{ 'btn--primary': activeProfileId === prof.id }"
              @click="applyProfile(prof)"
            >
              {{ activeProfileId === prof.id ? 'Applied' : 'Apply' }}
            </button>
          </div>
        </div>

        <p class="profile-desc">{{ prof.desc }}</p>

        <div class="profile-specs micro num">
          <span v-if="prof.dpi">DPI {{ prof.dpi[0] }}</span>
          <span v-if="prof.poll_rate">POLL {{ prof.poll_rate }}Hz</span>
          <span v-if="prof.effect">EFFECT {{ prof.effect.toUpperCase() }}</span>
          <span v-if="prof.brightness !== undefined">BRIGHT {{ prof.brightness }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profiles-control {
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

.profile-actions {
  display: flex;
  gap: 8px;
}

.create-drawer {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.create-form {
  display: flex;
  gap: 12px;
}

.profiles-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 20px;
  transition: background-color 120ms, border-color 120ms;
}

.profile-card:hover {
  background: var(--surface-2);
}

.profile-card--active {
  border-color: var(--line-strong);
  background: var(--surface-2);
}

.profile-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.profile-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.profile-name {
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
}

.active-tag {
  color: var(--success);
  border: 1px solid var(--success);
  padding: 1px 6px;
  border-radius: 6px;
}

.profile-btns {
  display: flex;
  gap: 8px;
}

.profile-desc {
  font-size: 14px;
  color: var(--text-2);
  margin-bottom: 12px;
}

.profile-specs {
  display: flex;
  gap: 16px;
  color: var(--text-3);
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
</style>
