import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Trash2 } from 'lucide-react';
import { api } from '../../api/client';
import { ManagedUser } from '../../api/types';
import DataTable from '../../components/DataTable';
import ConfirmDialog from '../../components/ConfirmDialog';
import FormField from '../../components/FormField';
import SlideOver from '../../components/SlideOver';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../components/Toast';

interface Form {
  username: string;
  password: string;
  role: string;
  email: string;
  display_name: string;
}

const EMPTY: Form = { username: '', password: '', role: 'viewer', email: '', display_name: '' };

export default function Users() {
  const toast = useToast();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<Form>(EMPTY);
  const [deleting, setDeleting] = useState<ManagedUser | null>(null);

  const { data: users = [], refetch } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get<ManagedUser[]>('/api/v1/users'),
  });

  const create = useMutation({
    mutationFn: (f: Form) => api.post('/api/v1/users', f),
    onSuccess: () => {
      toast('success', 'User created');
      setOpen(false);
      qc.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const update = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: Partial<ManagedUser> }) => api.patch(`/api/v1/users/${id}`, patch),
    onSuccess: () => {
      toast('success', 'User updated');
      qc.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  const remove = useMutation({
    mutationFn: (u: ManagedUser) => api.delete(`/api/v1/users/${u.id}`),
    onSuccess: () => {
      toast('success', 'User deleted');
      setDeleting(null);
      qc.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (err: Error) => toast('error', err.message),
  });

  return (
    <>
      <h1 className="text-lg font-semibold mb-1">Users &amp; Roles</h1>
      <p className="text-table text-muted mb-3">
        Role-based access control. <strong>admin</strong> manages everything; <strong>operator</strong> can
        change DDI data, run integrations and automation; <strong>viewer</strong> is read-only. SSO users are
        provisioned automatically and their role is driven by the group mappings under SSO.
      </p>
      <DataTable
        columns={[
          { header: 'Username', searchText: (u: ManagedUser) => u.username, render: (u) => <span className="font-medium">{u.username}</span> },
          { header: 'Name', render: (u) => <span className="text-xs">{u.display_name || '—'}</span> },
          {
            header: 'Role',
            render: (u) => (
              <select className="f-input text-xs w-28 py-0.5" value={u.role} onChange={(e) => update.mutate({ id: u.id, patch: { role: e.target.value } })}>
                <option value="viewer">viewer</option>
                <option value="operator">operator</option>
                <option value="admin">admin</option>
              </select>
            ),
          },
          { header: 'Source', render: (u) => <StatusBadge value={u.auth_source === 'saml' ? 'info' : 'free'} /> },
          {
            header: 'Active',
            render: (u) => (
              <label className="inline-flex">
                <input type="checkbox" checked={u.is_active} onChange={(e) => update.mutate({ id: u.id, patch: { is_active: e.target.checked } })} />
              </label>
            ),
          },
          { header: 'Last login', render: (u) => <span className="text-xs text-muted">{u.last_login_at ? new Date(u.last_login_at).toLocaleString() : '—'}</span> },
          {
            header: 'Actions',
            render: (u) => (
              <button onClick={() => setDeleting(u)} className="text-danger hover:opacity-70" title="Delete">
                <Trash2 size={14} />
              </button>
            ),
          },
        ]}
        rows={users}
        rowKey={(u) => u.id}
        onCreate={() => { setForm(EMPTY); setOpen(true); }}
        createLabel="New User"
        onRefresh={() => refetch()}
      />

      <SlideOver title="New user" open={open} onClose={() => setOpen(false)}>
        <FormField label="Username">
          <input className="f-input" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} />
        </FormField>
        <FormField label="Password" hint="At least 6 characters">
          <input className="f-input" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </FormField>
        <FormField label="Role">
          <select className="f-input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="viewer">viewer</option>
            <option value="operator">operator</option>
            <option value="admin">admin</option>
          </select>
        </FormField>
        <div className="grid grid-cols-2 gap-2">
          <FormField label="Display name">
            <input className="f-input" value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          </FormField>
          <FormField label="Email">
            <input className="f-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </FormField>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button className="f-btn-secondary" onClick={() => setOpen(false)}>Cancel</button>
          <button className="f-btn-primary" disabled={create.isPending || !form.username || form.password.length < 6} onClick={() => create.mutate(form)}>
            Create
          </button>
        </div>
      </SlideOver>

      <ConfirmDialog
        title="Delete user"
        message={`Delete user ${deleting?.username}?`}
        open={deleting !== null}
        onCancel={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </>
  );
}
