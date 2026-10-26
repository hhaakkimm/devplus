// Same pattern as _VAR in apps/api/app/modules/evals/template.py: change both together.
// Python's \s spelled out, because JS \s differs on U+001C-U+001F, U+0085 and U+FEFF.
const S = String.raw`[\t-\r\x1C-\x20\x85\xA0  -     　]`;
const VAR = new RegExp(
  String.raw`\{\{${S}*([A-Za-z_][A-Za-z0-9_]*)${S}*\}\}`,
  "g",
);

export function templateVariables(t: string): string[] {
  return [...new Set(Array.from(t.matchAll(VAR), (m) => m[1]))];
}
