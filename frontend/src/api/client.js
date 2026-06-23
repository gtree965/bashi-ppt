const API_BASE = '/api';
const OUTLINE_TIMEOUT_MS = 1200000;  // Increased to 20 minutes to handle heavy reasoning models

async function parseJsonResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    const message = payload?.error || payload?.error_en || `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function getTemplates() {
  const res = await fetch(`${API_BASE}/templates`);
  return res.json();
}

export async function recommendSlides({
  topic,
  referenceText = '',
  scenario,
  outputLanguage,
  signal,
}) {
  const res = await fetch(`${API_BASE}/recommend-slides`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      topic,
      reference_text: referenceText.trim() || undefined,
      scenario,
      output_language: outputLanguage,
    }),
    signal,
  });
  return await parseJsonResponse(res);
}

export async function prepareGroundedFacts({
  referenceText,
}) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), OUTLINE_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}/prepare-grounded-facts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reference_text: referenceText.trim(),
      }),
      signal: controller.signal,
    });
    return await parseJsonResponse(res);
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('材料事实提取超时，请检查当前 AI 模型连接。');
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function generateOutline(
  topic,
  numSlides,
  scenario,
  outputLanguage,
  referenceText = '',
  generationMode = 'creative',
  slideCountMode = 'manual',
  factTable = null
) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), OUTLINE_TIMEOUT_MS);

  try {
    const res = await fetch(`${API_BASE}/generate-outline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic,
        num_slides: numSlides,
        scenario,
        output_language: outputLanguage,
        reference_text: referenceText.trim() || undefined,
        generation_mode: generationMode,
        slide_count_mode: slideCountMode,
        fact_table: factTable || undefined,
      }),
      signal: controller.signal,
    });
    return await parseJsonResponse(res);
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('本地模型响应超时，请检查LM Studio是否正在运行并已加载模型。');
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function postWithOutlineTimeout(path, body) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), OUTLINE_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    return await parseJsonResponse(res);
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('本地模型响应超时，请检查LM Studio是否正在运行并已加载模型。');
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

// Draft step: generate an article + an outline derived from it.
export async function generateDraft(
  topic,
  numSlides,
  scenario,
  outputLanguage,
  referenceText = '',
  slideCountMode = 'manual'
) {
  return postWithOutlineTimeout('/generate-draft', {
    topic,
    num_slides: numSlides,
    scenario,
    output_language: outputLanguage,
    reference_text: referenceText.trim() || undefined,
    slide_count_mode: slideCountMode,
  });
}

// Refine step: regenerate article + outline from the prior article and a correction.
export async function refineDraft({
  topic,
  numSlides,
  scenario,
  outputLanguage,
  referenceText = '',
  priorArticle,
  correction,
  slideCountMode = 'manual',
}) {
  return postWithOutlineTimeout('/refine-draft', {
    topic,
    num_slides: numSlides,
    scenario,
    output_language: outputLanguage,
    reference_text: referenceText.trim() || undefined,
    prior_article: priorArticle,
    correction,
    slide_count_mode: slideCountMode,
  });
}

export async function exportPrepArticle({ title, article, format }) {
  const res = await fetch(`${API_BASE}/export-article`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, article, format }),
  });

  if (!res.ok) {
    try {
      await parseJsonResponse(res);
    } catch (error) {
      throw new Error(error.message || 'Prep article export failed');
    }
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const printableTitle = [...(title || '备课文章')]
    .map((character) => (character.charCodeAt(0) < 32 ? '_' : character))
    .join('');
  const safeTitle = printableTitle.replace(/[<>:"/\\|?*]/g, '_');
  const a = document.createElement('a');
  a.href = url;
  a.download = `${safeTitle}.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

// Speaker notes: generate a per-slide lecture script for the current outline.
export async function generateSpeakerNotes({
  outline,
  article,
  outputLanguage,
  duration,
  style,
  generationMode = 'creative',
  factTable = [],
}) {
  return postWithOutlineTimeout('/generate-notes', {
    outline,
    article: article || undefined,
    output_language: outputLanguage,
    duration,
    style,
    generation_mode: generationMode,
    fact_table: factTable,
  });
}

export async function getLyricsConfig() {
  const res = await fetch(`${API_BASE}/lyrics-config`);
  return await parseJsonResponse(res);
}

export async function previewLyrics(payload) {
  const res = await fetch(`${API_BASE}/preview-lyrics`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return await parseJsonResponse(res);
}

export async function generateLyricsPptx(payload) {
  const res = await fetch(`${API_BASE}/generate-lyrics-pptx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    try {
      await parseJsonResponse(res);
    } catch (error) {
      throw new Error(error.message || 'Lyrics PPTX generation failed');
    }
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${payload.title || 'Hymn'}.pptx`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function generatePptx(outline, templateId, bulletStyle = 'dot', themeId = null) {
  const res = await fetch(`${API_BASE}/generate-pptx`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      outline,
      template_id: templateId,
      bullet_style: bulletStyle,
      theme_id: themeId,
    }),
  });

  if (!res.ok) {
    try {
      await parseJsonResponse(res);
    } catch (error) {
      throw new Error(error.message || 'PPTX generation failed');
    }
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${outline.title}.pptx`;
  a.click();
  URL.revokeObjectURL(url);
}

// ─── LLM Settings ────────────────────────────────────────────────────────────

export async function getLLMSettings() {
  const res = await fetch(`${API_BASE}/settings/llm`);
  return await parseJsonResponse(res);
}

export async function saveLLMSettings(payload) {
  const res = await fetch(`${API_BASE}/settings/llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return await parseJsonResponse(res);
}

export async function testLLMSettings(payload) {
  const res = await fetch(`${API_BASE}/settings/test-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return await parseJsonResponse(res);
}

export async function getRecommendedModels() {
  const res = await fetch(`${API_BASE}/settings/recommended-models`);
  return await parseJsonResponse(res);
}

export async function getOpenRouterFreeModels() {
  const res = await fetch(`${API_BASE}/settings/openrouter/free-models`);
  return await parseJsonResponse(res);
}

export async function searchImages(query) {
  const res = await fetch(`${API_BASE}/images/search?q=${encodeURIComponent(query)}`);
  return await parseJsonResponse(res);
}

