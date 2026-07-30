import { useId } from "react";

import type { AiModelList } from "./types";

export function AiModelSelector({
  disabled = false,
  label = "AI model",
  modelList,
  onChange,
  value,
}: {
  disabled?: boolean;
  label?: string;
  modelList: AiModelList | null;
  onChange: (model: string) => void;
  value: string;
}) {
  const id = useId();
  return (
    <label className="ai-model-selector" htmlFor={id}>
      <span>{label}</span>
      <select
        disabled={disabled || !modelList}
        id={id}
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {!modelList && <option value="">Loading models…</option>}
        {modelList?.models.map((model) => (
          <option key={model.id} value={model.id}>
            {model.label}
          </option>
        ))}
      </select>
    </label>
  );
}
