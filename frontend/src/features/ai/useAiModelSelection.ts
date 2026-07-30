import { useEffect, useState } from "react";

import { getAiModels } from "./api";
import type { AiModelList } from "./types";

const MODEL_STORAGE_KEY = "teacher-assistant.ai-model";

export function useAiModelSelection() {
  const [modelList, setModelList] = useState<AiModelList | null>(null);
  const [selectedModel, setSelectedModelState] = useState("");
  const [modelError, setModelError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const loaded = await getAiModels(controller.signal);
        const stored = window.localStorage.getItem(MODEL_STORAGE_KEY);
        const selected =
          stored && loaded.models.some((model) => model.id === stored)
            ? stored
            : loaded.default_model;
        window.localStorage.setItem(MODEL_STORAGE_KEY, selected);
        setModelList(loaded);
        setSelectedModelState(selected);
      } catch (error) {
        if (!controller.signal.aborted) {
          setModelError(
            error instanceof Error
              ? error.message
              : "AI model choices could not be loaded.",
          );
        }
      }
    }
    void load();
    return () => controller.abort();
  }, []);

  function setSelectedModel(model: string) {
    if (!modelList?.models.some((option) => option.id === model)) return;
    setSelectedModelState(model);
    window.localStorage.setItem(MODEL_STORAGE_KEY, model);
  }

  return {
    modelList,
    selectedModel,
    setSelectedModel,
    modelError,
    isModelLoading: modelList === null && modelError === null,
  };
}
