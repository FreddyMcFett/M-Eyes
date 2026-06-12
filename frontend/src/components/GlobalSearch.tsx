import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { api } from '../api/client';
import { SearchResult } from '../api/types';

const TYPE_LABELS: Record<string, string> = {
  network: 'Network',
  ip_address: 'IP',
  zone: 'Zone',
  record: 'Record',
  host: 'Host',
  rpz_rule: 'DNS FW',
};

/** Infoblox-style global search across every object family. */
export default function GlobalSearch() {
  const navigate = useNavigate();
  const [term, setTerm] = useState('');
  const [debounced, setDebounced] = useState('');
  const [open, setOpen] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(term.trim()), 300);
    return () => clearTimeout(timer);
  }, [term]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (wrapper.current && !wrapper.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const { data } = useQuery({
    queryKey: ['global-search', debounced],
    queryFn: () =>
      api.get<{ results: SearchResult[] }>(`/api/v1/search?q=${encodeURIComponent(debounced)}`),
    enabled: debounced.length >= 2,
  });

  const results = debounced.length >= 2 ? data?.results ?? [] : [];

  return (
    <div className="relative" ref={wrapper}>
      <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-muted" />
      <input
        className="f-input pl-7 w-64"
        placeholder="Search everything…"
        value={term}
        onChange={(e) => {
          setTerm(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
      />
      {open && debounced.length >= 2 && (
        <div className="absolute right-0 mt-1 w-96 max-h-96 overflow-y-auto bg-white border border-line rounded shadow-lg z-50">
          {results.length === 0 && (
            <div className="px-3 py-2 text-table text-muted">No matches</div>
          )}
          {results.map((r) => (
            <button
              key={`${r.type}-${r.id}`}
              className="w-full flex items-center gap-2 px-3 py-1.5 text-left text-table hover:bg-slate-100"
              onClick={() => {
                navigate(r.url);
                setOpen(false);
                setTerm('');
              }}
            >
              <span className="px-1.5 py-0.5 rounded bg-slate-200 text-[10px] uppercase shrink-0">
                {TYPE_LABELS[r.type] ?? r.type}
              </span>
              <span className="font-mono truncate">{r.label}</span>
              <span className="ml-auto text-muted truncate">{r.detail}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
