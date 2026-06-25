import { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import TopicInput from './components/TopicInput';
import GroundedFactReview from './components/GroundedFactReview';
import OutlineEditor from './components/OutlineEditor';
import DraftReview from './components/DraftReview';
import TemplateSelector from './components/TemplateSelector';
import GenerateButton from './components/GenerateButton';
import HymnStudio from './components/HymnStudio';
import LLMSettings from './components/LLMSettings';
import RecentProjects from './components/RecentProjects';
import ProjectLibrary from './components/ProjectLibrary';
import {
  generateOutline,
  prepareGroundedFacts,
  generateDraft,
  refineDraft,
  generatePptx,
  listProjects,
  getProject,
  saveProject,
} from './api/client';
import { mermaidToPngDataUrl } from './utils/diagramRenderer';

const STEPS = {
  IDLE: 'idle',
  PREPARING_FACTS: 'preparing_facts',
  REVIEWING_FACTS: 'reviewing_facts',
  GENERATING_OUTLINE: 'generating_outline',
  DRAFTING: 'drafting',
  REVIEW: 'review',
  EDITING: 'editing',
  GENERATING_PPTX: 'generating_pptx',
};

const TEMPLATE_BY_SCENARIO = {
  teaching: 'teaching',
  church: 'church',
  parents: 'professional',
  general: 'default',
};

const THEME_BY_TEMPLATE = {
  teaching: 'clean_blue',
  church: 'church_grace',
  professional: 'warm_earth',
  default: 'clean_blue',
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
  const [showSettings, setShowSettings] = useState(false);
  const [bulletStyle, setBulletStyle] = useState('dot');
  const [selectedTheme, setSelectedTheme] = useState('clean_blue');
  const [article, setArticle] = useState('');
  const [outputLanguage, setOutputLanguage] = useState('zh');
  const [draftParams, setDraftParams] = useState(null);
  const [draftBusy, setDraftBusy] = useState(false);
  const [lastInputParams, setLastInputParams] = useState(null);
  const [groundedParams, setGroundedParams] = useState(null);
  const [preparedFacts, setPreparedFacts] = useState([]);
  const [groundedBusy, setGroundedBusy] = useState(false);
  const [generationContext, setGenerationContext] = useState({
    mode: 'creative',
    factTable: [],
    audit: null,
  });
  const [recentProjects, setRecentProjects] = useState([]);
  const [showLibrary, setShowLibrary] = useState(false);
  const projectIdRef = useRef(null);

  const refreshRecent = () => {
    listProjects(5)
      .then((data) => setRecentProjects(data.projects || []))
      .catch(() => {});
  };

  useEffect(() => {
    refreshRecent();
  }, []);

  const serializeProject = () => ({
    inputParams: lastInputParams,
    article,
    outline,
    scenario,
    template,
    bulletStyle,
    selectedTheme,
    outputLanguage,
    generationContext,
  });

  // Auto-save (debounced) whenever an outline exists and the snapshot changes.
  // Best-effort: failures are swallowed so saving never blocks editing.
  useEffect(() => {
    if (!outline) return undefined;
    const handle = setTimeout(async () => {
      try {
        const title = outline?.title || lastInputParams?.topic || '未命名项目';
        const data = await saveProject({
          id: projectIdRef.current,
          title,
          state: serializeProject(),
        });
        if (data?.id) projectIdRef.current = data.id;
        refreshRecent();
      } catch {
        // ignore — autosave is best-effort
      }
    }, 1500);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [outline, article, lastInputParams, scenario, template, bulletStyle, selectedTheme, outputLanguage, generationContext]);

  const handleOpenProject = async (id) => {
    try {
      const data = await getProject(id);
      const project = data.project || {};
      const state = project.state || {};
      projectIdRef.current = project.id || null;
      setLastInputParams(state.inputParams || null);
      setArticle(state.article || '');
      setOutline(state.outline || null);
      setScenario(state.scenario || 'teaching');
      setTemplate(state.template || 'teaching');
      setBulletStyle(state.bulletStyle || 'dot');
      setSelectedTheme(state.selectedTheme || 'clean_blue');
      setOutputLanguage(state.outputLanguage || 'zh');
      setGenerationContext(
        state.generationContext || { mode: 'creative', factTable: [], audit: null }
      );
      setError(null);
      setWarnings([]);
      setShowLibrary(false);
      setStep(STEPS.EDITING);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleTopicSubmit = async ({
    topic,
    numSlides,
    scenario,
    outputLanguage,
    referenceText,
    draftFirst,
    generationMode,
    slideCountMode,
  }) => {
    const submittedParams = {
      topic,
      numSlides,
      scenario,
      outputLanguage,
      referenceText,
      draftFirst,
      generationMode,
      slideCountMode,
    };
    setLastInputParams(submittedParams);
    const autoTemplate = TEMPLATE_BY_SCENARIO[scenario] || 'teaching';
    setScenario(scenario);
    setOutputLanguage(outputLanguage);
    setTemplate(autoTemplate);
    setSelectedTheme(THEME_BY_TEMPLATE[autoTemplate] || 'clean_blue');
    setError(null);
    setWarnings([]);

    // Draft-first path: generate an article, then review before the outline editor.
    if (draftFirst) {
      setDraftParams({
        topic,
        numSlides,
        scenario,
        outputLanguage,
        referenceText,
        slideCountMode,
      });
      setStep(STEPS.DRAFTING);
      try {
        const data = await generateDraft(
          topic,
          numSlides,
          scenario,
          outputLanguage,
          referenceText,
          slideCountMode
        );
        if (data.success) {
          setArticle(data.article || '');
          setOutline(data.outline);
          setWarnings(data.warnings || []);
          setGenerationContext({ mode: 'creative', factTable: [], audit: null });
          setDraftParams((current) => ({
            ...current,
            numSlides: data.effective_num_slides || numSlides,
            slideCountMode: data.slide_count_mode || slideCountMode,
            slideRecommendationReason: data.slide_recommendation_reason || '',
          }));
          setStep(STEPS.REVIEW);
        } else {
          setError(data.error || 'Draft generation failed');
          setStep(STEPS.IDLE);
        }
      } catch (err) {
        setError(err.message);
        setStep(STEPS.IDLE);
      }
      return;
    }

    if (generationMode === 'grounded') {
      setGroundedParams(submittedParams);
      setStep(STEPS.PREPARING_FACTS);
      try {
        const data = await prepareGroundedFacts({ referenceText });
        if (data.success) {
          setPreparedFacts(data.fact_table || []);
          setStep(STEPS.REVIEWING_FACTS);
        } else {
          setError(data.error || 'Fact extraction failed');
          setStep(STEPS.IDLE);
        }
      } catch (err) {
        setError(err.message);
        setStep(STEPS.IDLE);
      }
      return;
    }

    // Fast path: straight to outline.
    setStep(STEPS.GENERATING_OUTLINE);
    try {
      const data = await generateOutline(
        topic,
        numSlides,
        scenario,
        outputLanguage,
        referenceText,
        generationMode,
        slideCountMode
      );
      if (data.success) {
        setOutline(data.outline);
        setWarnings(data.warnings || []);
        setGenerationContext({
          mode: data.generation_mode || generationMode || 'creative',
          factTable: data.fact_table || [],
          audit: data.generation_audit || null,
        });
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

  const handleConfirmGroundedFacts = async (confirmedFacts) => {
    if (!groundedParams || confirmedFacts.length === 0) return;
    setGroundedBusy(true);
    setError(null);
    setWarnings([]);
    try {
      const data = await generateOutline(
        groundedParams.topic,
        groundedParams.numSlides,
        groundedParams.scenario,
        groundedParams.outputLanguage,
        groundedParams.referenceText,
        'grounded',
        groundedParams.slideCountMode,
        confirmedFacts
      );
      if (data.success) {
        setOutline(data.outline);
        setWarnings(data.warnings || []);
        setGenerationContext({
          mode: 'grounded',
          factTable: data.fact_table || confirmedFacts,
          audit: data.generation_audit || null,
        });
        setPreparedFacts(data.fact_table || confirmedFacts);
        setStep(STEPS.EDITING);
      } else {
        setError(data.error || 'Outline generation failed');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGroundedBusy(false);
    }
  };

  const handleBackFromGroundedFacts = () => {
    setPreparedFacts([]);
    setGroundedParams(null);
    setStep(STEPS.IDLE);
  };

  const handleRefineDraft = async (correction) => {
    if (!draftParams) return;
    setDraftBusy(true);
    setError(null);
    try {
      const data = await refineDraft({ ...draftParams, priorArticle: article, correction });
      if (data.success) {
        setArticle(data.article || '');
        setOutline(data.outline);
        setWarnings(data.warnings || []);
        setDraftParams((current) => ({
          ...current,
          numSlides: data.effective_num_slides || current?.numSlides,
          slideCountMode: data.slide_count_mode || current?.slideCountMode,
          slideRecommendationReason:
            data.slide_recommendation_reason || current?.slideRecommendationReason || '',
        }));
      } else {
        setError(data.error || 'Draft refinement failed');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setDraftBusy(false);
    }
  };

  const handleConfirmDraft = () => {
    // Phase 2 will generate speaker notes here before proceeding.
    setStep(STEPS.EDITING);
  };

  // Render every content slide's Mermaid diagram to a fresh PNG right before export,
  // so the embedded image always matches the current `diagram` text (no stale cache).
  // A search image takes precedence over a diagram (the slide's right column holds
  // only one graphic), so we clear diagram_image when image_url is present.
  const ensureDiagramImages = async (sourceOutline) => {
    const slides = await Promise.all(
      sourceOutline.slides.map(async (slide) => {
        if (slide.slide_type !== 'content') return slide;
        const mermaid = (slide.diagram || '').trim();
        if (!mermaid || slide.image_url) {
          return slide.diagram_image ? { ...slide, diagram_image: undefined } : slide;
        }
        const dataUrl = await mermaidToPngDataUrl(mermaid);
        return { ...slide, diagram_image: dataUrl || undefined };
      })
    );
    return { ...sourceOutline, slides };
  };

  const handleGeneratePptx = async () => {
    setStep(STEPS.GENERATING_PPTX);
    setError(null);
    try {
      const exportOutline = await ensureDiagramImages(outline);
      await generatePptx(exportOutline, template, bulletStyle, selectedTheme);
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
    setBulletStyle('dot');
    setSelectedTheme('clean_blue');
    setArticle('');
    setOutputLanguage('zh');
    setDraftParams(null);
    setDraftBusy(false);
    setLastInputParams(null);
    setGroundedParams(null);
    setPreparedFacts([]);
    setGroundedBusy(false);
    setGenerationContext({ mode: 'creative', factTable: [], audit: null });
    projectIdRef.current = null;  // next generation starts a fresh project
    setShowLibrary(false);
    refreshRecent();
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

          {/* Settings gear button */}
          <div className="absolute right-4 top-4 md:right-6 md:top-6">
            <button
              type="button"
              onClick={() => setShowSettings(true)}
              title="AI 模型设置"
              className="flex h-10 w-10 items-center justify-center rounded-full border border-bashi-border bg-black/20 text-bashi-text-muted transition hover:border-bashi-copper hover:text-bashi-copper"
            >
              ⚙️
            </button>
          </div>

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
                {step === STEPS.IDLE && (
                  <RecentProjects
                    projects={recentProjects}
                    onOpen={handleOpenProject}
                    onBrowseAll={() => setShowLibrary(true)}
                  />
                )}

                {(step === STEPS.IDLE
                  || step === STEPS.PREPARING_FACTS
                  || step === STEPS.GENERATING_OUTLINE
                  || step === STEPS.DRAFTING) && (
                  <TopicInput
                    onSubmit={handleTopicSubmit}
                    initialValues={lastInputParams}
                    loadingStage={
                      step === STEPS.PREPARING_FACTS
                        ? 'facts'
                        : (step === STEPS.DRAFTING ? 'draft' : 'outline')
                    }
                    isLoading={
                      step === STEPS.PREPARING_FACTS
                      || step === STEPS.GENERATING_OUTLINE
                      || step === STEPS.DRAFTING
                    }
                  />
                )}

                {step === STEPS.REVIEWING_FACTS && (
                  <GroundedFactReview
                    topic={groundedParams?.topic}
                    facts={preparedFacts}
                    onConfirm={handleConfirmGroundedFacts}
                    onBack={handleBackFromGroundedFacts}
                    isBusy={groundedBusy}
                  />
                )}

                {step === STEPS.REVIEW && (
                  <DraftReview
                    title={outline?.title || draftParams?.topic || '备课文章'}
                    slideRecommendationReason={draftParams?.slideRecommendationReason}
                    article={article}
                    onArticleChange={setArticle}
                    outline={outline}
                    onRefine={handleRefineDraft}
                    onConfirm={handleConfirmDraft}
                    isBusy={draftBusy}
                  />
                )}

                {(step === STEPS.EDITING || step === STEPS.GENERATING_PPTX) && (
                  <>
                    <TemplateSelector
                      scenario={scenario}
                      selected={template}
                      bulletStyle={bulletStyle}
                      onBulletStyleChange={setBulletStyle}
                      selectedTheme={selectedTheme}
                      onThemeChange={setSelectedTheme}
                    />
                    <OutlineEditor
                      outline={outline}
                      onOutlineChange={setOutline}
                      scenario={scenario}
                      outputLanguage={outputLanguage}
                      article={article}
                      generationMode={generationContext.mode}
                      factTable={generationContext.factTable}
                      generationAudit={generationContext.audit}
                    />
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

      <ProjectLibrary
        isOpen={showLibrary}
        onClose={() => setShowLibrary(false)}
        onOpen={handleOpenProject}
      />

      {/* Settings slide-out overlay */}
      {showSettings && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowSettings(false)}
          />
          {/* Panel */}
          <div className="fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col overflow-y-auto bg-[#1a1a2e] shadow-2xl">
            <div className="flex items-center justify-between border-b border-bashi-border px-6 py-4">
              <span className="font-semibold text-bashi-text">⚙️ AI 模型设置</span>
              <button
                type="button"
                onClick={() => setShowSettings(false)}
                className="text-2xl leading-none text-bashi-text-muted hover:text-bashi-text"
              >
                &times;
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <LLMSettings onClose={() => setShowSettings(false)} />
            </div>
          </div>
        </>
      )}
    </>
  );
}

export default App;
