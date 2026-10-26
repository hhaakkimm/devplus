"use client";

import { useRef } from "react";
import { Field, selectClass } from "@/components/lab/form-parts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  GRADER_TYPES,
  MAX_GRADERS,
  type GraderRow,
  type GraderType,
} from "@/lib/graders";

const MODELS = ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"];

function Settings({ k, type }: { k: number; type: GraderType }) {
  const name = (field: string) => `${k}.${field}`;
  switch (type) {
    case "exact":
      return (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name={name("ignore_case")} />
          Не учитывать регистр
        </label>
      );
    case "regex":
      return (
        <>
          <Field label="Регулярное выражение">
            <Input
              name={name("pattern")}
              required
              maxLength={1024}
              className="font-mono"
            />
          </Field>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" name={name("must_match")} defaultChecked />
            Должно найтись в ответе
          </label>
        </>
      );
    case "json_schema":
      return (
        <Field label="JSON-схема ответа">
          <Textarea
            name={name("schema")}
            required
            rows={4}
            placeholder='{"type": "object"}'
            className="font-mono"
          />
        </Field>
      );
    case "llm_judge":
      return (
        <>
          <Field
            label="Рубрика"
            hint="По строке на раздел: Название | Описание | вес (вес необязателен)"
          >
            <Textarea
              name={name("rubric")}
              required
              rows={3}
              placeholder="Тон | Вежливо ли отвечено | 1"
            />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Порог, 0–1">
              <Input
                name={name("threshold")}
                type="number"
                required
                min={0}
                max={1}
                step="any"
                defaultValue={0.7}
              />
            </Field>
            <Field label="Модель судьи">
              <select name={name("model")} className={selectClass}>
                {MODELS.map((m) => (
                  <option key={m}>{m}</option>
                ))}
              </select>
            </Field>
          </div>
        </>
      );
  }
}

// Controlled list of grader rows; the settings inputs are uncontrolled and read by `buildGraders`.
export function GradersField({
  rows,
  onChange,
}: {
  rows: GraderRow[];
  onChange: (rows: GraderRow[]) => void;
}) {
  const nextKey = useRef(1);
  const picked = useRef<HTMLSelectElement>(null);

  return (
    <fieldset className="grid gap-3">
      <legend className="mb-1 text-sm font-medium">Оценщики</legend>
      {rows.map((row) => (
        <fieldset
          key={row.key}
          className="grid gap-3 rounded-lg border p-3"
          aria-label={`Оценщик ${row.type}`}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-sm">{row.type}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onChange(rows.filter((r) => r.key !== row.key))}
            >
              Убрать
            </Button>
          </div>
          <Settings k={row.key} type={row.type} />
        </fieldset>
      ))}
      <div className="flex gap-2">
        <select
          ref={picked}
          aria-label="Тип оценщика"
          className={selectClass}
          defaultValue="exact"
        >
          {GRADER_TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <Button
          variant="outline"
          disabled={rows.length >= MAX_GRADERS}
          onClick={() =>
            onChange([
              ...rows,
              {
                key: nextKey.current++,
                type: picked.current!.value as GraderType,
              },
            ])
          }
        >
          Добавить оценщик
        </Button>
      </div>
    </fieldset>
  );
}
