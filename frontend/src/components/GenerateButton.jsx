export default function GenerateButton({ onGenerate, onReset, isLoading, disabled }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      <button
        type="button"
        onClick={onReset}
        className="bashi-btn-secondary rounded-2xl px-6 py-4 text-base font-medium"
      >
        &larr; 返回重新输入
      </button>

      <button
        type="button"
        onClick={onGenerate}
        disabled={disabled || isLoading}
        className="bashi-btn-accent flex-1 rounded-2xl px-6 py-4 text-lg font-semibold"
      >
        {isLoading ? '正在生成 PPT...' : '生成 PPT 并下载'}
      </button>
    </div>
  );
}
