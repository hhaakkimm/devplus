import type { Module } from "@/lib/content";

// Counts only the module's own lessons, so marks for deleted lessons are ignored.
export function moduleProgress(module: Module, done: ReadonlySet<string>) {
  return {
    done: module.lessons.filter((l) => done.has(l.slug)).length,
    total: module.lessons.length,
  };
}
