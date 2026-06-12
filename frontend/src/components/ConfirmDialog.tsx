import Modal from './Modal';

interface Props {
  title: string;
  message: string;
  open: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  destructive?: boolean;
}

export default function ConfirmDialog({ title, message, open, onConfirm, onCancel, destructive = true }: Props) {
  return (
    <Modal title={title} open={open} onClose={onCancel}>
      <p className="text-table text-slate-700 mb-4">{message}</p>
      <div className="flex justify-end gap-2">
        <button className="f-btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button className={destructive ? 'f-btn-danger' : 'f-btn-primary'} onClick={onConfirm}>
          Confirm
        </button>
      </div>
    </Modal>
  );
}
