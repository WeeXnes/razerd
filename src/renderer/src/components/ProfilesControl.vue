<script setup>
import { ref } from 'vue';

const props = defineProps({
  currentDevice: {
    type: Object,
    default: null
  },
  profiles: {
    type: Array,
    required: true
  },
  activeProfileId: {
    type: String,
    required: true
  }
});

const emit = defineEmits([
  'apply-profile',
  'create-profile',
  'delete-profile',
  'reset-profile',
  'import-profiles'
]);

const newProfileName = ref('');
const cloneCurrent = ref(true);
const isCreating = ref(false);

function applyProfile(prof) {
  emit('apply-profile', prof);
}

function createProfile() {
  const name = newProfileName.value.trim();
  if (!name) return;
  emit('create-profile', {
    name,
    cloneCurrent: cloneCurrent.value
  });
  newProfileName.value = '';
  isCreating.value = false;
}

function deleteProfile(id) {
  emit('delete-profile', id);
}

function resetProfile(id) {
  emit('reset-profile', id);
}

function exportProfiles() {
  const data = JSON.stringify(props.profiles, null, 2);
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
      if (Array.isArray(parsed) && parsed.length > 0) {
        emit('import-profiles', parsed);
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
        <p class="section-desc">
          Switch profiles to load saved settings. All changes you make to DPI, polling rate, lighting, buttons, or power are automatically saved to the currently active profile.
        </p>
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
      <div class="create-top">
        <span class="micro">Create New Profile</span>
        <label class="clone-toggle micro">
          <input type="checkbox" v-model="cloneCurrent" />
          <span>Copy current device settings (uncheck for clean 800 DPI default)</span>
        </label>
      </div>
      <div class="create-form">
        <input
          type="text"
          class="input"
          v-model="newProfileName"
          placeholder="Profile Name (e.g. Counter-Strike 2, Desktop)"
          @keydown.enter="createProfile"
        />
        <button class="btn btn--primary btn--small" @click="createProfile">Create & Activate</button>
      </div>
    </div>

    <!-- Profiles List -->
    <div class="profiles-list">
      <div
        v-for="prof in profiles"
        :key="prof.id"
        class="profile-card"
        :class="{ 'profile-card--active': activeProfileId === prof.id }"
        @click="applyProfile(prof)"
      >
        <div class="profile-top">
          <div class="profile-title-row">
            <span class="profile-name">{{ prof.name }}</span>
            <span v-if="activeProfileId === prof.id" class="active-tag micro">Active · Auto-Saving</span>
          </div>
          <div class="profile-btns">
            <button
              v-if="prof.id === 'prof-default'"
              class="btn btn--secondary btn--small"
              title="Reset Default profile back to 800 DPI"
              @click.stop="resetProfile(prof.id)"
            >
              Reset to 800 DPI
            </button>
            <button
              v-if="prof.id !== 'prof-default' && profiles.length > 1"
              class="btn btn--danger btn--small"
              @click.stop="deleteProfile(prof.id)"
            >
              Delete
            </button>
            <button
              class="btn btn--secondary btn--small"
              :class="{ 'btn--primary': activeProfileId === prof.id }"
              @click.stop="applyProfile(prof)"
            >
              {{ activeProfileId === prof.id ? 'Active' : 'Switch' }}
            </button>
          </div>
        </div>

        <p class="profile-desc">{{ prof.desc }}</p>

        <div class="profile-specs micro num">
          <span v-if="prof.dpi">DPI {{ prof.dpi[0] }}{{ prof.dpi[0] !== prof.dpi[1] ? ` × ${prof.dpi[1]}` : '' }}</span>
          <span v-if="prof.poll_rate">POLL {{ prof.poll_rate }}Hz</span>
          <span v-if="prof.effect">EFFECT {{ prof.effect.toUpperCase() }}</span>
          <span v-if="prof.brightness !== undefined">BRIGHT {{ prof.brightness }}%</span>
          <span v-if="Array.isArray(prof.button_mappings) && prof.button_mappings.some((b) => b.action !== 'default')">
            {{ prof.button_mappings.filter((b) => b.action !== 'default').length }} CUSTOM BUTTONS
          </span>
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
  gap: 16px;
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
  flex-shrink: 0;
}

.create-drawer {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.create-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.clone-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--text-2);
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
  cursor: pointer;
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
  flex-wrap: wrap;
  gap: 16px;
  color: var(--text-3);
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
</style>
