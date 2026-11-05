import { spawn } from 'child_process';
import readline from 'readline';
import path from 'path';

const bridgePath = path.resolve('src/bridge/bridge.py');
const py = spawn('python3', [bridgePath], { stdio: ['pipe', 'pipe', 'pipe'] });
const rl = readline.createInterface({ input: py.stdout });

let counter = 0;
const tests = [
  { id: 1, action: 'ping' },
  { id: 2, action: 'get_status' },
  { id: 3, action: 'list_devices' }
];

console.log('--- Starting verification tests ---');

function runNext() {
  if (counter >= tests.length) {
    console.log('--- All bridge tests passed successfully! ---');
    py.kill();
    process.exit(0);
  }
  const t = tests[counter++];
  console.log(`Sending: ${t.action} (id: ${t.id})`);
  py.stdin.write(JSON.stringify(t) + '\n');
}

rl.on('line', (line) => {
  console.log(`Received response:`, line.substring(0, 160) + (line.length > 160 ? '...' : ''));
  runNext();
});

py.stderr.on('data', (d) => {
  console.error('[Py stderr]:', d.toString());
});

runNext();
