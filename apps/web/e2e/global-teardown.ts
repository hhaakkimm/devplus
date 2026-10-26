import { stopWorker } from "./worker";

export default async function globalTeardown() {
  await stopWorker();
}
