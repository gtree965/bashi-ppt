// Dev-only verification harness (not part of the production build).
// Runs each Mermaid diagram type through the real mermaid-to-excalidraw bridge and
// classifies the output as hand-drawn (native Excalidraw shapes) vs image-fallback
// (a single embedded Mermaid SVG) vs error. Open /diagram-matrix.html under `npm run dev`.

import { parseMermaidToExcalidraw } from '@excalidraw/mermaid-to-excalidraw';
import { convertToExcalidrawElements } from '@excalidraw/excalidraw';

const SAMPLES = [
  ['flowchart', 'flowchart TD\n  A[开始] --> B{判断?}\n  B -->|是| C[处理]\n  B -->|否| D[结束]'],
  ['sequenceDiagram', 'sequenceDiagram\n  Alice->>Bob: 你好\n  Bob-->>Alice: 回复'],
  ['classDiagram', 'classDiagram\n  Animal <|-- Dog\n  Animal : +String name'],
  ['erDiagram', 'erDiagram\n  CUSTOMER ||--o{ ORDER : places'],
  ['stateDiagram-v2', 'stateDiagram-v2\n  [*] --> Idle\n  Idle --> Running\n  Running --> [*]'],
  ['mindmap', 'mindmap\n  root((核心))\n    分支A\n    分支B'],
  ['timeline', 'timeline\n  title 历史\n  2020 : A\n  2021 : B'],
  ['gantt', 'gantt\n  title 计划\n  section S\n  任务 :a1, 2020-01-01, 30d'],
  ['pie', 'pie title 占比\n  "A" : 40\n  "B" : 60'],
  ['journey', 'journey\n  title 旅程\n  section 上午\n  起床: 5: 我'],
  ['gitGraph', 'gitGraph\n  commit\n  branch dev\n  commit'],
  ['quadrantChart', 'quadrantChart\n  title Q\n  x-axis Low --> High\n  y-axis Low --> High\n  A: [0.3, 0.6]'],
];

function classify(elements) {
  if (!elements || elements.length === 0) return { kind: 'empty', detail: '0 elements' };
  const counts = {};
  for (const el of elements) counts[el.type] = (counts[el.type] || 0) + 1;
  const types = Object.keys(counts);
  const detail = types.map((t) => `${t}×${counts[t]}`).join(', ');
  const onlyImage = types.every((t) => t === 'image');
  return { kind: onlyImage ? 'image-fallback' : 'hand-drawn', detail };
}

async function run() {
  const tbody = document.getElementById('rows');
  for (const [name, def] of SAMPLES) {
    let result;
    try {
      const { elements } = await parseMermaidToExcalidraw(def);
      result = classify(convertToExcalidrawElements(elements));
    } catch (error) {
      result = { kind: 'error', detail: error?.message || String(error) };
    }
    const color =
      result.kind === 'hand-drawn' ? '#137333' :
      result.kind === 'image-fallback' ? '#b06000' : '#b00020';
    const tr = document.createElement('tr');
    tr.innerHTML =
      `<td>${name}</td>` +
      `<td style="color:${color};font-weight:600">${result.kind}</td>` +
      `<td><code>${result.detail}</code></td>`;
    tbody.appendChild(tr);
  }
}

run();
