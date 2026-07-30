export interface AiModelOption {
  id: string;
  label: string;
}

export interface AiModelList {
  default_model: string;
  models: AiModelOption[];
}
