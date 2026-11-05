<script setup>
import { ref, onMounted } from 'vue';

const props = defineProps({
  status: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['restart-daemon', 'refresh-status']);

const restarting = ref(false);

onMounted(() => {
  emit('refresh-status');
});

async function onRestart() {
  restarting.value = true;
  emit('restart-daemon');
  setTimeout(() => {
    restarting.value = false;
    emit('refresh-status');
  }, 2000);
}
</script>

<template>
  <div class="troubleshooter-control">
    <div class="section-header">
      <div>
        <h2 class="section-title">System Health & Diagnostics</h2>
        <p class="section-desc">Verify OpenRazer kernel drivers, daemon D-Bus services, and hardware permissions.</p>
      </div>
      <button
        class="btn btn--secondary btn--small"
        :disabled="restarting"
        @click="onRestart"
      >
        {{ restarting ? 'Restarting...' : 'Restart OpenRazer Daemon' }}
      </button>
    </div>

    <!-- Diagnostic Cards Table -->
    <div class="diag-table box">
      <!-- Daemon Service -->
      <div class="diag-row">
        <div class="diag-left">
          <span
            class="status-dot"
            :class="status?.daemon_running ? 'status-dot--success' : (status ? 'status-dot--danger' : '')"
          ></span>
          <div>
            <div class="diag-name">OpenRazer Daemon</div>
            <div class="diag-desc">D-Bus Session Service (org.razer)</div>
          </div>
        </div>
        <div class="diag-right micro num">
          <span v-if="status?.daemon_running">v{{ status?.daemon_version || '3.x' }} (Active)</span>
          <span v-else-if="status">Inactive / Stopped</span>
          <span v-else>Connecting...</span>
        </div>
      </div>

      <div class="row-divider"></div>

      <!-- Python Client Library -->
      <div class="diag-row">
        <div class="diag-left">
          <span
            class="status-dot"
            :class="status?.has_openrazer_lib ? 'status-dot--success' : (status ? 'status-dot--danger' : '')"
          ></span>
          <div>
            <div class="diag-name">OpenRazer Python Library</div>
            <div class="diag-desc">openrazer.client bindings</div>
          </div>
        </div>
        <div class="diag-right micro num">
          <span v-if="status?.has_openrazer_lib">Installed</span>
          <span v-else-if="status">Missing</span>
          <span v-else>Connecting...</span>
        </div>
      </div>

      <div class="row-divider"></div>

      <!-- Kernel Modules -->
      <div class="diag-row" v-for="(loaded, mod) in (status?.kernel_modules || {})" :key="mod">
        <div class="diag-left">
          <span
            class="status-dot"
            :class="loaded ? 'status-dot--success' : ''"
          ></span>
          <div>
            <div class="diag-name">Kernel Module: {{ mod }}</div>
            <div class="diag-desc">
              {{ mod === 'razermouse' ? 'Mouse device driver' :
                 mod === 'razeraccessory' ? 'Addressable RGB Controller / Accessory driver' :
                 mod === 'razerkbd' ? 'Keyboard device driver' : 'Audio headset driver' }}
            </div>
          </div>
        </div>
        <div class="diag-right micro num">
          {{ loaded ? 'Loaded in Kernel' : 'Dormant (Hardware not attached)' }}
        </div>
      </div>

      <div class="row-divider"></div>

      <!-- User Group Membership -->
      <div class="diag-row">
        <div class="diag-left">
          <span
            class="status-dot"
            :class="status?.in_group ? 'status-dot--success' : (status ? 'status-dot--warning' : '')"
          ></span>
          <div>
            <div class="diag-name">User Group: {{ status?.group_name || 'openrazer / plugdev' }}</div>
            <div class="diag-desc">Hardware device permissions (udev)</div>
          </div>
        </div>
        <div class="diag-right micro num">
          <span v-if="status?.in_group">Member ({{ status?.group_name }})</span>
          <span v-else-if="status">Not Member (Add user to {{ status?.group_name || 'openrazer' }})</span>
          <span v-else>Connecting...</span>
        </div>
      </div>
    </div>

    <!-- Troubleshooting Tips -->
    <div class="box tips-box">
      <div class="micro">Troubleshooting Guide</div>
      <p class="tip-text">
        Linux udev permissions for Razer devices are managed by the <code>openrazer</code> group on Arch Linux, Fedora, and openSUSE, and <code>plugdev</code> on Debian and Ubuntu.
        Your user is currently verified in the <code>{{ status?.group_name || 'openrazer' }}</code> group. Kernel modules load dynamically on-demand when matching USB hardware is plugged in.
      </p>
    </div>
  </div>
</template>

<style scoped>
.troubleshooter-control {
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

.diag-table {
  display: flex;
  flex-direction: column;
}

.diag-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0;
}

.diag-row:first-child {
  padding-top: 0;
}
.diag-row:last-child {
  padding-bottom: 0;
}

.diag-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.diag-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.diag-desc {
  font-size: 12px;
  color: var(--text-3);
}

.diag-right {
  color: var(--text-2);
}

.row-divider {
  height: 1px;
  background: var(--line);
}

.tips-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tip-text {
  font-size: 13px;
  color: var(--text-2);
  line-height: 1.6;
}

.tip-text code {
  color: var(--text);
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--line);
}
</style>
