import { useQuery } from '@tanstack/react-query';
import { marked } from 'marked';
import { Download, RefreshCw } from 'lucide-react';
import { api } from '../api/client';

interface RunbookResponse {
  markdown: string;
  config_version: number;
  generated_at: string;
}

export default function Runbook() {
  const { data, refetch, isFetching } = useQuery({
    queryKey: ['runbook'],
    queryFn: () => api.get<RunbookResponse>('/api/v1/runbook'),
  });

  const download = () => {
    if (!data) return;
    const blob = new Blob([data.markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `m-eyes-runbook-v${data.config_version}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <div className="flex items-center gap-3 mb-3">
        <h1 className="text-lg font-semibold">Log &amp; Report — Configuration Runbook</h1>
        {data && (
          <span className="text-xs text-muted">
            config v{data.config_version} · generated {new Date(data.generated_at).toLocaleString()}
          </span>
        )}
        <div className="ml-auto flex gap-2">
          <button className="f-btn-secondary" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw size={14} /> Regenerate
          </button>
          <button className="f-btn-primary" onClick={download} disabled={!data}>
            <Download size={14} /> Download .md
          </button>
        </div>
      </div>
      <div className="f-card p-6">
        {data ? (
          <div
            className="prose prose-sm max-w-none [&_table]:f-table [&_h1]:text-xl [&_h2]:text-base [&_h2]:font-semibold [&_h2]:mt-5 [&_table]:w-full [&_th]:text-left [&_th]:bg-table-header [&_th]:px-2 [&_th]:py-1 [&_td]:px-2 [&_td]:py-1 [&_td]:border-b [&_td]:border-line [&_code]:bg-slate-100 [&_code]:px-1 [&_code]:rounded [&_blockquote]:border-l-4 [&_blockquote]:border-accent [&_blockquote]:pl-3 [&_blockquote]:text-muted"
            dangerouslySetInnerHTML={{ __html: marked.parse(data.markdown) as string }}
          />
        ) : (
          <p className="text-muted text-table">Loading…</p>
        )}
      </div>
    </>
  );
}
