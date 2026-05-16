declare module 'ssh2' {
  import { EventEmitter } from 'events';

  export interface ConnectConfig {
    host?: string;
    port?: number;
    username?: string;
    password?: string;
    privateKey?: string | Buffer;
    readyTimeout?: number;
  }

  export class Client extends EventEmitter {
    connect(config: ConnectConfig): this;
    exec(
      command: string,
      cb: (
        err: Error | undefined,
        stream: EventEmitter & {
          stderr: EventEmitter;
          on(event: 'data', listener: (chunk: Buffer | string) => void): any;
          on(event: 'close', listener: (code: number | null) => void): any;
        },
      ) => void,
    ): void;
    shell(
      options: { term?: string },
      cb: (
        err: Error | undefined,
        stream: EventEmitter & {
          stderr: EventEmitter;
          write(data: string): any;
          end(data?: string): any;
          on(event: 'data', listener: (chunk: Buffer | string) => void): any;
          on(event: 'close', listener: () => void): any;
        },
      ) => void,
    ): void;
    end(): void;
  }
}
