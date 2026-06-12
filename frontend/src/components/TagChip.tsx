import { Tag } from '../api/types';

export default function TagChip({ tag }: { tag: Tag }) {
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs border border-line bg-white mr-1"
      title={tag.name}
    >
      <span className="w-2 h-2 rounded-full" style={{ backgroundColor: tag.color }} />
      {tag.name}
    </span>
  );
}
