import { type ChildProcess, spawn } from "node:child_process";

export const origin = "http://localhost:3000";

// The api and the worker build the same Settings, and both answer with the fake LLM.
// DATABASE_URL comes from the environment (make exports .env).
export const apiEnv = {
  ALLOWED_GITHUB_LOGINS: "e2e-user",
  APP_ORIGIN: origin,
  COOKIE_SECURE: "false",
  GITHUB_CLIENT_ID: "e2e",
  GITHUB_CLIENT_SECRET: "e2e",
  EVALS_LLM_BACKEND: "fake",
  REDIS_URL: process.env.REDIS_URL ?? "redis://localhost:6379/0",
};

let worker: ChildProcess | undefined;

function killGroup(child: ChildProcess | undefined, signal: NodeJS.Signals) {
  // negative pid: the group, so the python processes under `uv run` go down as well
  try {
    if (child?.pid) process.kill(-child.pid, signal);
  } catch {
    // already gone
  }
}

// Same command as `make worker`: one process, because taskiq starts two by default.
// Resolves once the worker has run its start-up recovery, rejects if it crashes instead.
export async function startWorker() {
  const child = spawn(
    "uv",
    "run taskiq worker app.worker:broker --workers 1 --max-async-tasks 2".split(
      " ",
    ),
    {
      cwd: "../api",
      env: { ...process.env, ...apiEnv },
      detached: true,
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  worker = child;
  process.once("exit", () => killGroup(worker, "SIGKILL")); // when the runner dies without a teardown

  let output = "";
  let timer: NodeJS.Timeout | undefined;
  try {
    await new Promise<void>((resolve, reject) => {
      timer = setTimeout(
        () => reject(new Error("worker did not start in 60 s")),
        60_000,
      );
      const onData = (chunk: Buffer) => {
        output = (output + chunk).slice(-4000); // keeps draining the pipes, and the tail for errors
        // taskiq restarts a crashed worker in a loop, so a traceback is the failure
        if (output.includes("Traceback")) reject(new Error("worker crashed"));
        else if (output.includes("worker started")) resolve();
      };
      child.stdout?.on("data", onData);
      child.stderr?.on("data", onData);
      child.once("exit", (code) =>
        reject(new Error(`worker exited with code ${code}`)),
      );
      child.once("error", reject);
    });
  } catch (e) {
    await stopWorker();
    throw new Error(`${(e as Error).message}\n${output}`);
  } finally {
    clearTimeout(timer);
  }
}

export async function stopWorker() {
  const child = worker;
  worker = undefined;
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  const exited = new Promise((resolve) => child.once("exit", resolve));
  killGroup(child, "SIGTERM");
  const hard = setTimeout(() => killGroup(child, "SIGKILL"), 10_000);
  await exited;
  clearTimeout(hard);
}
