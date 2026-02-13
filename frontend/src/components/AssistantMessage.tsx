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
import type { Message, ChartData } from '../types';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

function ChartRenderer({ chart }: { chart: ChartData }) {
  const data = chart.data.map((d) => ({ name: d.label, value: d.value }));

  return (
    <div className="my-2">
      <p className="mb-1 text-sm font-medium text-gray-700">{chart.title}</p>
      <ResponsiveContainer width="100%" height={250}>
        {chart.type === 'bar' ? (
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#3b82f6" />
          </BarChart>
        ) : chart.type === 'line' ? (
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#3b82f6" />
          </LineChart>
        ) : chart.type === 'pie' ? (
          <PieChart>
            <Tooltip />
            <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80}>
              {data.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        ) : (
          <ScatterChart>
            <CartesianGrid />
            <XAxis dataKey="name" />
            <YAxis dataKey="value" />
            <Tooltip />
            <Scatter data={data} fill="#3b82f6" />
          </ScatterChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

export default function AssistantMessage({ message }: { message: Message }) {
  return (
    <div className="max-w-lg space-y-2 rounded-lg bg-gray-100 px-4 py-2 text-gray-900">
      {message.content && <p className="whitespace-pre-wrap">{message.content}</p>}

      {message.table_data && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr>
                {message.table_data.columns.map((col) => (
                  <th key={col} className="border-b px-2 py-1 text-left font-medium">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {message.table_data.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j} className="border-b px-2 py-1">
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
