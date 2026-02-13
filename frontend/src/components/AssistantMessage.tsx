import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from 'recharts';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message, ChartData } from '../types';
import type { StepState } from '../hooks/useSSE';
import ThinkingCollapsible from './ThinkingCollapsible';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

function ChartRenderer({ chart }: { chart: ChartData }) {
  const data = chart.data.map((d) => ({ name: d.label, value: d.value }));

  return (
    <div className="my-2">
      <p className="mb-1 text-sm font-medium text-gray-300">{chart.title}</p>
      <ResponsiveContainer width="100%" height={250}>
        {chart.type === 'bar' ? (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} labelStyle={{ color: '#f3f4f6' }} itemStyle={{ color: '#d1d5db' }} cursor={{ fill: 'rgba(255,255,255,0.06)' }} />
            <Bar dataKey="value" fill="#3b82f6" />
          </BarChart>
        ) : chart.type === 'line' ? (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" stroke="#9ca3af" />
            <YAxis stroke="#9ca3af" />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} labelStyle={{ color: '#f3f4f6' }} itemStyle={{ color: '#d1d5db' }} cursor={{ stroke: '#6b7280' }} />
            <Line type="monotone" dataKey="value" stroke="#3b82f6" />
          </LineChart>
        ) : chart.type === 'pie' ? (
          <PieChart>
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} labelStyle={{ color: '#f3f4f6' }} itemStyle={{ color: '#d1d5db' }} />
            <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        ) : (
          <ScatterChart>
            <CartesianGrid stroke="#374151" />
            <XAxis dataKey="name" stroke="#9ca3af" />
            <YAxis dataKey="value" stroke="#9ca3af" />
            <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }} labelStyle={{ color: '#f3f4f6' }} itemStyle={{ color: '#d1d5db' }} cursor={{ stroke: '#6b7280' }} />
            <Scatter data={data} fill="#3b82f6" />
          </ScatterChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

interface AssistantMessageProps {
  message: Message;
  streamingSteps?: StepState[];
  isStreaming?: boolean;
}

export default function AssistantMessage({ message, streamingSteps, isStreaming }: AssistantMessageProps) {
  return (
    <div className="max-w-lg space-y-2 rounded-lg bg-gray-800 px-4 py-2 text-gray-100">
      {streamingSteps && streamingSteps.length > 0 && (
        <ThinkingCollapsible steps={streamingSteps} isStreaming={isStreaming ?? false} />
      )}

      {!streamingSteps && message.pipeline_data && (
        <ThinkingCollapsible pipelineData={message.pipeline_data} />
      )}

      {message.content && (
        <div className="prose prose-sm prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      )}

      {message.table_data && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                {message.table_data.columns.map((col) => (
                  <th key={col} className="border-b border-gray-600 px-2 py-1 text-left font-medium text-gray-300">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {message.table_data.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j} className="border-b border-gray-700 px-2 py-1 text-gray-300">
                      {String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {message.chart_data && <ChartRenderer chart={message.chart_data} />}
    </div>
  );
}
