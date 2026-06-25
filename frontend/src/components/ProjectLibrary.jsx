import { useEffect, useState } from 'react';
import { listAllProjects } from '../api/client';
import { ProjectRow } from './RecentProjects';

export default function ProjectLibrary({ isOpen, onClose, onOpen }) {
  const [projects, setProjects] = useState([]);
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    let alive = true;
    const load = async () => {
      setIsLoading(true);
      setError(null);
      setQuery('');
      try {
        const data = await listAllProjects();
        if (alive) setProjects(data.projects || []);
      } catch (err) {
        if (alive) setError(err.message || '加载项目失败');
      } finally {
        if (alive) setIsLoading(false);
      }
    };
    load();
    return () => {
      alive = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const q = query.trim().toLowerCase();
  const filtered = q
    ? projects.filter((p) => {
        const hay = `${p.title || ''} ${p.summary?.topic || ''}`.toLowerCase();
        return hay.includes(q);
      })
    : projects;

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-bashi-border bg-[#1a1a2e] shadow-2xl">
          <div className="flex items-center justify-between border-b border-bashi-border px-6 py-4">
            <span className="font-semibold text-bashi-text">📂 全部过往项目</span>
            <button
              type="button"
              onClick={onClose}
              className="text-2xl leading-none text-bashi-text-muted hover:text-bashi-text"
            >
              &times;
            </button>
          </div>

          <div className="border-b border-bashi-border px-6 py-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索项目标题或主题…"
              className="bashi-input w-full rounded-xl px-4 py-2 text-sm"
              autoFocus
            />
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-4">
            {isLoading && (
              <div className="py-8 text-center text-sm text-bashi-text-muted">加载中…</div>
            )}
            {error && (
              <div className="py-8 text-center text-sm text-red-300">{error}</div>
            )}
            {!isLoading && !error && filtered.length === 0 && (
              <div className="py-8 text-center text-sm text-bashi-text-muted">
                {projects.length === 0 ? '还没有保存的项目。' : '没有匹配的项目。'}
              </div>
            )}
            {!isLoading && !error && filtered.length > 0 && (
              <div className="flex flex-col gap-2">
                {filtered.map((project) => (
                  <ProjectRow
                    key={project.id}
                    project={project}
                    onOpen={(id) => {
                      onOpen(id);
                      onClose();
                    }}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="border-t border-bashi-border px-6 py-3 text-[11px] text-bashi-text-muted">
            共 {projects.length} 个项目 · 保存在本机 <code>projects/</code> 文件夹，绝不上传。
          </div>
        </div>
      </div>
    </>
  );
}
