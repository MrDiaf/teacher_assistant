import type { AiModelList } from "./types";

export async function getAiModels(signal?: AbortSignal): Promise<AiModelList> {
  const response = await fetch("/api/v1/ai/models", { signal });
  if (!response.ok) {
    throw new Error("AI model choices could not be loaded.");
  }
  return (await response.json()) as AiModelList;
}
