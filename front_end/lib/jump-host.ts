import { Client } from 'ssh2';
import type { TaskExecParam } from '@/lib/types';

const JUMP_HOST = 'jump.zs.shaipower.online';
const JUMP_PORT = 22;
const JUMP_USER = 'liujiarui';
const JUMP_PASSWORD = 'jF1TskjAY2wO';

let sharedConn: Client | null = null;
let connectPromise: Promise<Client> | null = null;

function shEscape(v: string): string {
  return `'${v.replace(/'/g, `'"'"'`)}'`;
}

const MIQP_CLI_PARAM_KEYS = new Set([
  'input',
  'solution-npz',
  'exact-binary-limit',
  'max-block-size',
  'candidate-limit',
  'max-iterations',
  'seed',
  'seeds',
  'block-pool',
  'blocks-per-iteration',
  'candidate-budget-per-block',
  'max-lp-evals',
  'qaoa-max-qubits',
  'weight-objective',
  'weight-coupling',
  'weight-mixed',
  'weight-binary',
  'post-polish-rounds',
  'polish-candidate-limit',
]);

function instanceNameFromInput(input: string): string {
  const fileName = input.split(/[\\/]/).pop() ?? input;
  return fileName.replace(/\.npz$/i, '');
}

function renderTemplate(template: string, ctx: Record<string, string>): string {
  return template.replace(/\{([a-zA-Z][a-zA-Z0-9]*)\}/g, (match, key: string) => ctx[key] ?? match);
}

function stripAnsi(v: string): string {
  return v
    .replace(/\x1B\][^\x07]*(?:\x07|\x1B\\)/g, '')
    .replace(/\x1B\[[0-?]*[ -/]*[@-~]/g, '');
}

function outputTail(v: string, maxLen = 4000): string {
  return v.length > maxLen ? v.slice(-maxLen) : v;
}

function hasShellPrompt(output: string): boolean {
  const clean = stripAnsi(output).replace(/\r/g, '');
  const tail = clean.slice(-500);
  return /(?:^|\n)[^\n]*[\w.-]+@[\w.-]+:[^\n]*[$#]\s*$/.test(tail);
}

function createConnection(): Promise<Client> {
  return new Promise((resolve, reject) => {
    const conn = new Client();

    conn.on('ready', () => {
      console.log('[jump-host] ssh connected');
      sharedConn = conn;
      resolve(conn);
    });

    conn.on('error', (err) => {
      console.log('[jump-host] ssh connection error:', err.message);
      if (sharedConn === conn) sharedConn = null;
      reject(err);
    });

    conn.on('end', () => {
      console.log('[jump-host] ssh connection ended');
      if (sharedConn === conn) sharedConn = null;
    });

    conn.on('close', () => {
      console.log('[jump-host] ssh connection closed');
      if (sharedConn === conn) sharedConn = null;
    });

    console.log('[jump-host] connect ssh:', `${JUMP_USER}@${JUMP_HOST}:${JUMP_PORT}`);
    conn.connect({
      host: JUMP_HOST,
      port: JUMP_PORT,
      username: JUMP_USER,
      password: JUMP_PASSWORD,
      readyTimeout: 20_000,
    });
  });
}

async function getConnection(): Promise<Client> {
  if (sharedConn) return sharedConn;
  if (connectPromise) return connectPromise;

  connectPromise = createConnection()
    .then((conn) => {
      connectPromise = null;
      return conn;
    })
    .catch((err) => {
      connectPromise = null;
      throw err;
    });

  return connectPromise;
}

async function execRemote(command: string): Promise<{ stdout: string; stderr: string }> {
  const conn = await getConnection();
  console.log('[jump-host] exec remote command:', command);

  return new Promise((resolve, reject) => {
    conn.shell({ term: 'xterm' }, (err, stream) => {
      if (err) {
        reject(err);
        return;
      }

      let stdout = '';
      let stderr = '';
      const sentinel = `__QH_EXIT_${Date.now()}__`;
      let done = false;
      let commandSent = false;

      const sendCommand = () => {
        if (commandSent || done) return;
        commandSent = true;
        stream.write(`${command}\n`);
        stream.write(`echo ${sentinel}:$?\n`);
      };

      const timer = setTimeout(() => {
        if (done) return;
        done = true;
        stream.end('exit\n');
        reject(new Error(`remote_command_timeout: ${outputTail(stderr || stdout || 'no output')}`));
      }, 45_000);

      const finish = (ok: boolean, payload: { stdout: string; stderr: string } | Error) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        stream.end('exit\n');
        if (ok) resolve(payload as { stdout: string; stderr: string });
        else reject(payload as Error);
      };

      stream.on('data', (chunk: Buffer | string) => {
        stdout += chunk.toString();
        if (!commandSent && hasShellPrompt(stdout)) {
          sendCommand();
          return;
        }

        const m = stdout.match(new RegExp(`${sentinel}:(-?\\d+)`));
        if (m) {
          const code = Number(m[1]);
          if (code === 0) finish(true, { stdout, stderr });
          else finish(false, new Error(`remote_command_failed(code=${code}): ${outputTail(stderr || stdout || 'no output')}`));
        }
      });

      stream.stderr.on('data', (chunk: Buffer | string) => {
        stderr += chunk.toString();
      });

      stream.on('close', () => {
        if (!done && !stdout.includes(sentinel)) {
          finish(false, new Error(`remote_command_failed(no_exit_code): ${outputTail(stderr || stdout || 'no output')}`));
        }
      });
    });
  });
}

export async function closeJumpHostConnection() {
  if (!sharedConn) return;
  console.log('[jump-host] closing ssh connection');
  sharedConn.end();
  sharedConn = null;
}

export async function runOnJumpHost(command: string) {
  return execRemote(command);
}

export function buildPythonCommand(execParam: TaskExecParam, taskId: string) {
  console.log('[jump-host] build python command for task:', taskId);
  for (const [k, v] of Object.entries(execParam)) {
    console.log(`[jump-host]   ${k}: ${typeof v === 'object' ? JSON.stringify(v) : String(v)}`);
  }

  const instanceName = instanceNameFromInput(execParam.input);
  const ctx = { taskId, instanceName };
  const outputPath = `results/${taskId}.json`;
  const route7AliasPath = execParam.route7Alias ? renderTemplate(execParam.route7Alias, ctx) : null;
  const args: string[] = ['python', '-m', 'quantum_hackathon.miqp_cli'];
  for (const [k, v] of Object.entries(execParam)) {
    if (k === 'output') continue;
    if (!MIQP_CLI_PARAM_KEYS.has(k)) continue;
    if (!/^[a-zA-Z][a-zA-Z0-9-]*$/.test(k)) {
      console.log('[jump-host] skip invalid param key:', k);
      continue;
    }
    if (v === undefined || v === null || v === '') continue;
    if (v === false) continue;
    args.push(`--${k}`);
    if (v !== true) args.push(String(v));
  }
  args.push('--output');
  args.push(outputPath);

  const cli = args.map((x) => shEscape(x)).join(' ');
  const remoteSteps = [
    cli,
    route7AliasPath ? `cp ${shEscape(outputPath)} ${shEscape(route7AliasPath)}` : '',
  ].filter(Boolean);

  const baseline = execParam.baselineStudy;
  if (baseline?.enabled) {
    const baselineOutputDir = renderTemplate(baseline['output-dir'], ctx);
    const route7JsonDir = renderTemplate(baseline['route7-json-dir'], ctx);
    const baselineInputs = (baseline.inputs?.length ? baseline.inputs : [execParam.input]).map((input) =>
      renderTemplate(input, { ...ctx, input: execParam.input }),
    );
    remoteSteps.push(
      `mkdir -p ${shEscape(route7JsonDir)}`,
      `cp ${shEscape(outputPath)} ${shEscape(`${route7JsonDir}/${instanceName}_route7.json`)}`,
      [
        'python',
        'scripts/miqp_baseline_study.py',
        '--inputs',
        ...baselineInputs,
        '--output-dir',
        baselineOutputDir,
        '--route7-json-dir',
        route7JsonDir,
        '--random-reads',
        String(baseline['random-reads']),
        '--sa-reads',
        String(baseline['sa-reads']),
        '--sa-sweeps',
        String(baseline['sa-sweeps']),
        '--qaoa-block-size',
        String(baseline['qaoa-block-size']),
        '--qaoa-shots',
        String(baseline['qaoa-shots']),
        '--meta-population',
        String(baseline['meta-population']),
        '--meta-iterations',
        String(baseline['meta-iterations']),
      ]
        .map((x) => shEscape(x))
        .join(' '),
    );
  }

  const remoteScript = `cd /root/quantum_hackathon_repro_1bf21b3 && ${remoteSteps.join(' && ')}`;
  return [
    'cd /home/infra',
    'docker exec -d qiskit bash -lc ' + shEscape(remoteScript),
  ].join(' && ');
}
