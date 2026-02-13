export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface PipelineStepData {
  name: string;
  status: string;
  summary?: string;
  query_strategy?: string;
  queries?: string[];
  exploration_notes?: string;
}

export interface PipelineData {
  steps: PipelineStepData[];
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string | null;
  table_data: TableData | null;
  chart_data: ChartData | null;
  pipeline_data: PipelineData | null;
  created_at: string;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface PlanOutput {
  reasoning: string;
  query_strategy: string;
  expected_answer_type: 'scalar' | 'dataset' | 'chart';
  suggested_chart_type?: 'bar' | 'line' | 'pie' | 'scatter';
  tables_to_explore: string[];
}

export interface ExploreOutput {
  queries_executed: { sql: string; result_summary: string }[];
  raw_data: unknown;
  exploration_notes: string;
  schema_context: Record<string, unknown>;
}

export interface AnswerOutput {
  text_answer: string;
  table_data?: TableData;
  chart_data?: ChartData;
}

export interface TableData {
  columns: string[];
  rows: unknown[][];
}

export interface ChartData {
  type: 'bar' | 'line' | 'pie' | 'scatter';
  title: string;
  x_axis: string;
  y_axis: string;
  data: { label: string; value: number }[];
}
