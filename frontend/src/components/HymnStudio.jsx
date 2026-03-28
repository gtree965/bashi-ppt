import { useState, useEffect } from 'react';
import LyricsInput from './LyricsInput';
import LyricsPreview from './LyricsPreview';
import { getLyricsConfig, previewLyrics, generateLyricsPptx } from '../api/client';

export default function HymnStudio() {
  const [config, setConfig] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [warnings, setWarnings] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lastPayload, setLastPayload] = useState(null);

  // Load config on mount
  useEffect(() => {
    getLyricsConfig()
      .then(setConfig)
      .catch((err) => setError(`无法加载歌词配置: ${err.message}`));
  }, []);

  const handlePreview = async (payload) => {
    setIsLoading(true);
    setError(null);
    setWarnings([]);
    setLastPayload(payload);

    try {
      const data = await previewLyrics(payload);
      if (data.success) {
        setPreview(data);
        setWarnings(data.warnings || []);
      } else {
        setError(data.error || '预览失败');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerate = async (payload) => {
    setIsLoading(true);
    setError(null);

    try {
      await generateLyricsPptx(payload);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bashi-card mx-auto max-w-3xl rounded-2xl border border-red-400/40 bg-red-500/10 px-5 py-4 text-sm text-red-100">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="font-semibold">出现问题</div>
              <div className="mt-1 text-red-100/90">{error}</div>
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              className="text-xl leading-none text-red-200 transition hover:text-white"
            >
              &times;
            </button>
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="bashi-card mx-auto max-w-3xl rounded-2xl border border-amber-300/30 bg-amber-400/10 px-5 py-4 text-sm text-amber-50">
          <div className="font-semibold text-amber-100">检测提示</div>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-amber-50/90">
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <LyricsInput
        onPreview={handlePreview}
        onGenerate={handleGenerate}
        isLoading={isLoading}
        config={config}
      />

      {preview && (
        <LyricsPreview
          slides={preview.slides}
          theme={lastPayload?.theme || 'classic_dark'}
          totalPages={preview.total_pages}
        />
      )}
    </div>
  );
}
