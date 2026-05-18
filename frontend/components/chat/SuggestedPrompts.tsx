const defaultPrompts = [
  "khoa học dữ liệu học những môn gì",
  "ngành này có học lập trình không?",
  "hôm nay tôi cần làm gì",
  "bạn là ai",
  "tôi có task nào chưa xong"
];

export function SuggestedPrompts({
  prompts = defaultPrompts,
  onSelect,
  compact = false
}: {
  prompts?: string[];
  onSelect: (prompt: string) => void;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "flex flex-col gap-2" : "grid gap-2 sm:grid-cols-2"}>
      {prompts.map((prompt) => (
        <button
          key={prompt}
          type="button"
          onClick={() => onSelect(prompt)}
          className="focus-ring min-h-10 rounded-lg border border-line bg-white px-3 py-2 text-left text-sm leading-5 text-slate-700 hover:border-cyan-300 hover:bg-cyan-50"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}
