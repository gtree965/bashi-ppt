import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { searchImages } from '../api/client';

export default function ImageSearchModal({ isOpen, onClose, onSelectImage, initialQuery }) {
  const [query, setQuery] = useState('');
  const [images, setImages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      const q = initialQuery || '';
      setQuery(q);
      if (q.trim()) {
        handleSearch(q);
      } else {
        setImages([]);
        setError(null);
      }
    }
  }, [isOpen, initialQuery]);

  const handleSearch = async (searchQuery) => {
    const q = typeof searchQuery === 'string' ? searchQuery : query;
    if (!q.trim()) return;

    setIsLoading(true);
    setError(null);
    try {
      const res = await searchImages(q);
      if (res.success && res.images) {
        setImages(res.images);
      } else {
        setError(res.error || '无法加载图片');
      }
    } catch (err) {
      setError(err.message || '搜索请求发生错误');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  // Render via a portal to <body> so the fixed overlay isn't trapped by an ancestor
  // with backdrop-filter (.bashi-card), which would otherwise anchor it mid-page.
  return createPortal(
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm transition-opacity" 
        onClick={onClose}
      />
      
      {/* Container */}
      <div className="fixed inset-0 z-[101] flex items-center justify-center p-4">
        <div className="bashi-card w-full max-w-2xl rounded-[28px] p-6 shadow-2xl bg-[#1a1a2e]/95 border border-bashi-border max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-bashi-border pb-4">
            <div>
              <h3 className="text-xl font-semibold text-bashi-text">🔍 搜索免费高清配图</h3>
              <p className="mt-1 text-xs text-bashi-text-secondary">来自 Pixabay 优质免版税图库</p>
            </div>
            <button 
              type="button" 
              onClick={onClose}
              className="text-2xl leading-none text-bashi-text-muted hover:text-bashi-text transition"
            >
              &times;
            </button>
          </div>

          {/* Search bar */}
          <form 
            onSubmit={(e) => { e.preventDefault(); handleSearch(); }}
            className="mt-4 flex gap-2"
          >
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入英文或中文关键字..."
              className="bashi-input flex-1 rounded-2xl px-4 py-3 text-sm focus:outline-none"
              disabled={isLoading}
              autoFocus
            />
            <button
              type="submit"
              disabled={isLoading}
              className="bashi-btn-primary rounded-2xl px-6 py-3 text-sm font-semibold transition"
            >
              {isLoading ? '搜索中...' : '搜索'}
            </button>
          </form>

          {/* Results grid */}
          <div className="mt-6 flex-1 overflow-y-auto min-h-[300px]">
            {isLoading && (
              <div className="flex flex-col items-center justify-center py-16 gap-3">
                <div className="bashi-progress-track max-w-xs">
                  <div className="bashi-progress-indeterminate" />
                </div>
                <span className="text-sm text-bashi-text-secondary">正在搜索图片...</span>
              </div>
            )}

            {error && (
              <div className="rounded-2xl border border-red-500/20 bg-red-500/10 p-4 text-center text-sm text-red-300">
                {error}
              </div>
            )}

            {!isLoading && !error && images.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-center text-bashi-text-muted text-sm">
                <span>没有找到相关图片，请尝试更换关键词</span>
                <span className="text-xs mt-1">（例如：输入 "bible", "computer", "learning"）</span>
              </div>
            )}

            {!isLoading && !error && images.length > 0 && (
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {images.map((img) => (
                  <button
                    key={img.id}
                    type="button"
                    onClick={() => {
                      onSelectImage(img.webformat_url);
                      onClose();
                    }}
                    className="group relative aspect-video overflow-hidden rounded-xl border border-white/5 bg-black/40 transition hover:border-bashi-copper hover:scale-[1.02] active:scale-[0.98]"
                    title={`Tags: ${img.tags}`}
                  >
                    <img
                      src={img.preview_url}
                      alt={img.tags}
                      className="h-full w-full object-cover opacity-80 group-hover:opacity-100 transition"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition flex items-end p-2">
                      <span className="text-[10px] text-white/90 truncate w-full text-left font-light">
                        {img.tags.split(',')[0]}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>,
    document.body
  );
}
