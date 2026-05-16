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
      const timer = setTimeout(() => {
        if (done) return;
        done = true;
        stream.end('exit\n');
        reject(new Error(`remote_command_timeout: ${stderr || stdout || 'no output'}`));
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
        const m = stdout.match(new RegExp(`${sentinel}:(-?\\d+)`));
        if (m) {
          const code = Number(m[1]);
          if (code === 0) finish(true, { stdout, stderr });
          else finish(false, new Error(`remote_command_failed(code=${code}): ${stderr || stdout || 'no output'}`));
        }
      });

      stream.stderr.on('data', (chunk: Buffer | string) => {
        stderr += chunk.toString();
      });

      stream.on('close', () => {
        if (!done && !stdout.includes(sentinel)) {
          finish(false, new Error(`remote_command_failed(no_exit_code): ${stderr || stdout || 'no output'}`));
        }
      });

      stream.write(`${command}\n`);
      stream.write(`echo ${sentinel}:$?\n`);
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
    console.log(`[jump-host]   --${k} ${String(v)}`);
  }

  const args: string[] = ['python', '-m', 'quantum_hackathon.miqp_cli'];
  for (const [k, v] of Object.entries(execParam)) {
    if (k === 'output') continue;
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
  args.push(`results/${taskId}.json`);

  const cli = args.map((x) => shEscape(x)).join(' ');
  return [
    'cd /home/infra',
    'docker exec -d qiskit bash -lc ' + shEscape(`cd root/quantum_hackathon_repro_1bf21b3 && ${cli}`),
  ].join(' && ');
}
