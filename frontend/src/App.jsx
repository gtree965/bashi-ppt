import { useState } from 'react';
import Header from './components/Header';
import TopicInput from './components/TopicInput';
import OutlineEditor from './components/OutlineEditor';
import TemplateSelector from './components/TemplateSelector';
import GenerateButton from './components/GenerateButton';
import HymnStudio from './components/HymnStudio';
import { generateOutline, generatePptx } from './api/client';

const STEPS = {
  IDLE: 'idle',
  GENERATING_OUTLINE: 'generating_outline',
  EDITING: 'editing',
  GENERATING_PPTX: 'generating_pptx',
};

const TEMPLATE_BY_SCENARIO = {
  teaching: 'teaching',
  church: 'church',
  parents: 'teaching',
  general: 'teaching',
};

const MODES = {
  PRESENTATION: 'presentation',
  HYMN: 'hymn',
};

function App() {
  const [mode, setMode] = useState(MODES.PRESENTATION);
  const [step, setStep] = useState(STEPS.IDLE);
  const [outline, setOutline] = useState(null);
  const [template, setTemplate] = useState('teaching');
  const [scenario, setScenario] = useState('teaching');
  const [error, setError] = useState(null);
  const [warnings, setWarnings] = useState([]);

  const handleTopicSubmit = async ({ topic, numSlides, scenario, language, referenceText }) => {
    const autoTemplate = TEMPLATE_BY_SCENARIO[scenario] || 'teaching';
    setScenario(scenario);
    setTemplate(autoTemplate);
    setStep(STEPS.GENERATING_OUTLINE);
    setError(null);
    setWarnings([]);

    try {
      const data = await generateOutline(topic, numSlides, scenario, language, referenceText);
      if (data.success) {
        setOutline(data.outline);
        setWarnings(data.warnings || []);
        setStep(STEPS.EDITING);
      } else {
        setError(data.error || 'Outline generation failed');
        setStep(STEPS.IDLE);
      }
    } catch (err) {
      setError(err.message);
      setStep(STEPS.IDLE);
    }
  };

  const handleGeneratePptx = async () => {
    setStep(STEPS.GENERATING_PPTX);
    setError(null);
    try {
      await generatePptx(outline, template);
      setStep(STEPS.EDITING);
    } catch (err) {
      setError(err.message);
      setStep(STEPS.EDITING);
    }
  };

  const handleReset = () => {
    setStep(STEPS.IDLE);
    setOutline(null);
    setError(null);
    setWarnings([]);
    setScenario('teaching');
    setTemplate('teaching');
  };

  return (
    <>
      <div className="bg-animation" aria-hidden="true">
        <div className="wave wave1" />
        <div className="wave wave2" />
        <div className="wave wave3" />
      </div>

      <div className="relative min-h-screen px-4 py-8 md:px-6 md:py-10">
        <div className="mx-auto max-w-5xl">
          <Header />

          {/* Mode switcher */}
          <div className="mt-6 flex justify-center">
            <div className="inline-flex rounded-full border border-bashi-border bg-black/20 p-1">
              <button
                type="button"
                onClick={() => setMode(MODES.PRESENTATION)}
                className={`rounded-full px-5 py-2 text-sm font-medium transition ${
                  mode === MODES.PRESENTATION
                    ? 'bg-bashi-copper/20 text-bashi-copper'
                    : 'text-bashi-text-muted hover:text-bashi-text-secondary'
                }`}
              >
                演示文稿 PPT
              </button>
              <button
                type="button"
                onClick={() => setMode(MODES.HYMN)}
                className={`rounded-full px-5 py-2 text-sm font-medium transition ${
                  mode === MODES.HYMN
                    ? 'bg-bashi-copper/20 text-bashi-copper'
                    : 'text-bashi-text-muted hover:text-bashi-text-secondary'
                }`}
              >
                赞美诗歌词 PPT
              </button>
            </div>
          </div>

          {error && mode === MODES.PRESENTATION && (
            <div className="bashi-card mt-6 rounded-2xl border border-red-400/40 bg-red-500/10 px-5 py-4 text-sm text-red-100">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-semibold">生成时出现问题</div>
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

          {mode === MODES.PRESENTATION && warnings.length > 0 && (
            <div className="bashi-card mt-6 rounded-2xl border border-amber-300/30 bg-amber-400/10 px-5 py-4 text-sm text-amber-50">
              <div className="font-semibold text-amber-100">AI 已自动修正部分内容</div>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-amber-50/90">
                {warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-8 space-y-6">
            {mode === MODES.PRESENTATION && (
              <>
                {(step === STEPS.IDLE || step === STEPS.GENERATING_OUTLINE) && (
                  <TopicInput
                    onSubmit={handleTopicSubmit}
                    isLoading={step === STEPS.GENERATING_OUTLINE}
                  />
                )}

                {(step === STEPS.EDITING || step === STEPS.GENERATING_PPTX) && (
                  <>
                    <TemplateSelector scenario={scenario} selected={template} />
                    <OutlineEditor outline={outline} onOutlineChange={setOutline} />
                    <GenerateButton
                      onGenerate={handleGeneratePptx}
                      onReset={handleReset}
                      isLoading={step === STEPS.GENERATING_PPTX}
                      disabled={!outline}
                    />
                  </>
                )}
              </>
            )}

            {mode === MODES.HYMN && <HymnStudio />}
          </div>

          <footer className="mt-12 text-center text-sm text-bashi-text-muted">
            巴适PPT · Bashi PPT · Local AI Presentation Builder
          </footer>
        </div>
      </div>
    </>
  );
}

export default App;
