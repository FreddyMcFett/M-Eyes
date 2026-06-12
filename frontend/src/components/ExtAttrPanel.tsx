import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Save, Tags, Trash2 } from 'lucide-react';
import { api } from '../api/client';
import { ExtAttrDef, ExtAttrValues } from '../api/types';
import { useToast } from './Toast';

interface Props {
  objectType: string;
  objectId: number | string;
}

/** Infoblox-style extensible attributes editor, embeddable on any detail page. */
export default function ExtAttrPanel({ objectType, objectId }: Props) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [values, setValues] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState('');

  const { data: defs = [] } = useQuery({
    queryKey: ['extattr-defs'],
    queryFn: () => api.get<ExtAttrDef[]>('/api/v1/extattr-defs'),
  });
  const { data: current } = useQuery({
    queryKey: ['extattrs', objectType, objectId],
    queryFn: () => api.get<ExtAttrValues>(`/api/v1/extattrs/${objectType}/${objectId}`),
  });

  useEffect(() => {
    if (current) setValues(current.values);
  }, [current]);

  const save = useMutation({
    mutationFn: () => api.put(`/api/v1/extattrs/${objectType}/${objectId}`, { values }),
    onSuccess: () => {
      toast('success', 'Extensible attributes saved');
      queryClient.invalidateQueries({ queryKey: ['extattrs', objectType, objectId] });
      queryClient.invalidateQueries({ queryKey: ['extattr-defs'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const unused = defs.filter((d) => !(d.name in values));
  const dirty = JSON.stringify(values) !== JSON.stringify(current?.values ?? {});

  const input = (def: ExtAttrDef | undefined, name: string) => {
    if (def?.type === 'enum') {
      return (
        <select
          className="f-input"
          value={values[name] ?? ''}
          onChange={(e) => setValues({ ...values, [name]: e.target.value })}
        >
          <option value="">— select —</option>
          {(def.allowed_values ?? []).map((v) => (
            <option key={v} value={v}>{v}</option>
          ))}
        </select>
      );
    }
    return (
      <input
        className="f-input"
        value={values[name] ?? ''}
        placeholder={def?.type === 'date' ? 'YYYY-MM-DD' : def?.type ?? ''}
        onChange={(e) => setValues({ ...values, [name]: e.target.value })}
      />
    );
  };

  return (
    <div className="f-card mt-4">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-line">
        <Tags size={14} className="text-muted" />
        <span className="text-table font-semibold">Extensible Attributes</span>
        <div className="ml-auto flex items-center gap-2">
          {unused.length > 0 && (
            <select
              className="f-input w-44"
              value={adding}
              onChange={(e) => {
                const name = e.target.value;
                if (name) setValues({ ...values, [name]: '' });
                setAdding('');
              }}
            >
              <option value="">+ Add attribute…</option>
              {unused.map((d) => (
                <option key={d.id} value={d.name}>{d.name}</option>
              ))}
            </select>
          )}
          <button className="f-btn-primary" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
            <Save size={14} /> Save
          </button>
        </div>
      </div>
      <div className="p-3">
        {Object.keys(values).length === 0 && (
          <div className="text-table text-muted">
            {defs.length === 0
              ? 'No extensible attributes defined — create them under System → Extensible Attrs.'
              : 'No attributes set on this object.'}
          </div>
        )}
        {Object.keys(values).sort().map((name) => {
          const def = defs.find((d) => d.name === name);
          return (
            <div key={name} className="flex items-center gap-2 mb-2">
              <span className="w-40 text-table text-muted shrink-0" title={def?.comment}>
                {name}
              </span>
              {input(def, name)}
              <button
                className="text-danger hover:opacity-70 shrink-0"
                title="Remove attribute"
                onClick={() => {
                  const next = { ...values };
                  delete next[name];
                  setValues(next);
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
