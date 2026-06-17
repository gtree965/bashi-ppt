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

export async function generateOutline(topic, numSlides, scenario, language, referenceText = '') {
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
        language,
        reference_text: referenceText.trim() || undefined,
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
export async function generateDraft(topic, numSlides, scenario, language, referenceText = '') {
  return postWithOutlineTimeout('/generate-draft', {
    topic,
    num_slides: numSlides,
    scenario,
    language,
    reference_text: referenceText.trim() || undefined,
  });
}

// Refine step: regenerate article + outline from the prior article and a correction.
export async function refineDraft({ topic, numSlides, scenario, language, referenceText = '', priorArticle, correction }) {
  return postWithOutlineTimeout('/refine-draft', {
    topic,
    num_slides: numSlides,
    scenario,
    language,
    reference_text: referenceText.trim() || undefined,
    prior_article: priorArticle,
    correction,
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

