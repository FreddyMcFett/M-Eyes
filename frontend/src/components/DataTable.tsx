import { ReactNode, useMemo, useState } from 'react';
import { Plus, RefreshCw, Search } from 'lucide-react';

export interface Column<T> {
  header: string;
  render: (row: T) => ReactNode;
  searchText?: (row: T) => string;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => number | string;
  onCreate?: () => void;
  createLabel?: string;
  onRefresh?: () => void;
  emptyText?: string;
  toolbar?: ReactNode;
}

export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  onCreate,
  createLabel = 'Create New',
  onRefresh,
  emptyText = 'No entries',
  toolbar,
}: Props<T>) {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search.trim()) return rows;
    const needle = search.toLowerCase();
    return rows.filter((row) =>
      columns.some((col) => {
        const text = col.searchText
          ? col.searchText(row)
          : String((col.render(row) as { props?: { children?: unknown } })?.props?.children ?? '');
        return text.toLowerCase().includes(needle);
      }),
    );
  }, [rows, search, columns]);

  return (
    <div className="f-card">
      <div className="flex items-center gap-2 px-3.5 py-2.5 border-b border-line">
        {onCreate && (
          <button className="f-btn-primary" onClick={onCreate}>
            <Plus size={14} /> {createLabel}
          </button>
        )}
        {toolbar}
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search
              size={15}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted"
            />
            <input
              className="f-input !pl-9 w-56"
              placeholder="Search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          {onRefresh && (
            <button className="f-btn-secondary" onClick={onRefresh} aria-label="Refresh">
              <RefreshCw size={14} />
            </button>
          )}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="f-table">
          <thead>
            <tr>
              {columns.map((col) => (
                <th key={col.header}>{col.header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={columns.length} className="text-center text-muted py-6">
                  {emptyText}
                </td>
              </tr>
            )}
            {filtered.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((col) => (
                  <td key={col.header}>{col.render(row)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
