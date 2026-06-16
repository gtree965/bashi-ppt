// Renders a Mermaid string into a hand-drawn Excalidraw PNG (base64 data-URL).
//
// This is the Option B "frontend bridge": the LLM (or the user) supplies Mermaid,
// we convert it to Excalidraw elements and export them to a PNG headlessly — without
// ever mounting the <Excalidraw> React component, so React 19 compatibility is a
// non-issue. The resulting data-URL is attached to the slide as `diagram_image`
// and decoded server-side in engine.py.

import { parseMermaidToExcalidraw } from '@excalidraw/mermaid-to-excalidraw';
import { convertToExcalidrawElements, exportToBlob } from '@excalidraw/excalidraw';

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error('Failed to read blob'));
    reader.readAsDataURL(blob);
  });
}

/**
 * Convert Mermaid syntax to a hand-drawn PNG data-URL.
 * @param {string} mermaid - Mermaid diagram code (e.g. "flowchart LR; A-->B").
 * @returns {Promise<string|null>} a "data:image/png;base64,..." string, or null on failure.
 */
export async function mermaidToPngDataUrl(mermaid) {
  const source = (mermaid || '').trim();
  if (!source) return null;

  try {
    const { elements } = await parseMermaidToExcalidraw(source);
    const excalidrawElements = convertToExcalidrawElements(elements);
    if (!excalidrawElements.length) return null;

    const blob = await exportToBlob({
      elements: excalidrawElements,
      files: null,
      mimeType: 'image/png',
      exportPadding: 16,
      appState: {
        exportBackground: true,
        viewBackgroundColor: '#ffffff',
      },
    });
    return await blobToDataUrl(blob);
  } catch (error) {
    // Invalid Mermaid is an expected, recoverable case (LLM or user typo).
    console.warn('Diagram render failed:', error?.message || error);
    return null;
  }
}
