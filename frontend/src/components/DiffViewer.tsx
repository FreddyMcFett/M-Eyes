interface Props {
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
}

function format(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export default function DiffViewer({ before, after }: Props) {
  const keys = Array.from(
    new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})]),
  ).filter((k) => !k.startsWith('_') && k !== 'updated_at');

  return (
    <table className="f-table font-mono text-xs">
      <thead>
        <tr>
          <th>Field</th>
          <th>Before</th>
          <th>After</th>
        </tr>
      </thead>
      <tbody>
        {keys.map((key) => {
          const beforeValue = format(before?.[key]);
          const afterValue = format(after?.[key]);
          const changed = beforeValue !== afterValue;
          return (
            <tr key={key} className={changed ? 'bg-amber-50' : ''}>
              <td className="font-semibold">{key}</td>
              <td className={changed ? 'text-red-700 line-through' : 'text-muted'}>{beforeValue}</td>
              <td className={changed ? 'text-accent-dark font-semibold' : 'text-muted'}>{afterValue}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
