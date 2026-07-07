\# Stratify 2.0 Architecture Map v1



\## North Star



Stratify answers one question:



> Why would a viewer continue watching?



\---



\## 1. Acquisition Layer



Owns: getting video data, intro clip, and frames.



Current modules:

\- core/youtube\_client.py

\- core/intro\_acquisition.py

\- core/acquisition/youtube\_acquisition.py

\- utils/video\_downloader.py

\- utils/video\_utils.py

\- utils/frame\_extractor.py



Status:

\- Keep `core/intro\_acquisition.py` as the stable interface.

\- Keep `core/acquisition/youtube\_acquisition.py` experimental for now.



\---



\## 2. Observation Layer



Owns: raw visual evidence from frames.



Current modules:

\- core/vision\_analyzer.py

\- core/observers/visual\_observer.py

\- core/observers/story\_observer.py

\- core/observers/audience\_observer.py

\- core/observers/observation\_schema.py

\- core/intro\_observer.py



Issue:

\- Observer logic is split across old and new systems.



Decision needed:

\- Decide whether `core/observers/` becomes the future observation package.

\- Decide whether `core/intro\_observer.py` should be deprecated later.



\---



\## 3. Understanding Layer



Owns: turning observations into meaning.



Current modules:

\- core/understanding/video\_understanding.py

\- core/understanding/event\_understanding.py

\- core/understanding/temporal\_understanding.py

\- core/understanding/narrative\_understanding.py

\- core/understanding/understanding\_engine.py

\- core/content\_understanding.py



Status:

\- `understanding\_engine.py` should become the single entry point.

\- `narrative\_understanding.py` is draft only, not trusted yet.



\---



\## 4. Benchmark Retrieval Layer



Owns: finding comparable videos.



Current modules:

\- core/benchmark\_collector.py

\- core/benchmark\_cleaner.py

\- core/benchmark\_feature\_extractor.py

\- core/pipeline/intro\_pipeline.py



Status:

\- Benchmark collector is now resilient.

\- Cleaner is dynamic, not hardcoded.

\- Benchmark videos now use the shared intro pipeline.



\---



\## 5. Pattern Comparison Layer



Owns: comparing user intro vs benchmark intros.



Current modules:

\- core/pattern\_discovery.py

\- core/benchmark\_comparison.py

\- core/semantic\_comparison.py



Issue:

\- This layer may still be too feature-driven.



Future direction:

\- Compare creator decisions and viewer continuation signals, not only raw features.



\---



\## 6. Brain / Reasoning Layer



Owns: deciding what matters.



Current modules:

\- core/brain/

\- core/stratify\_brain.py

\- core/big\_insight.py

\- core/emotional\_center.py

\- core/meaning\_engine.py

\- core/context\_intelligence.py



Issue:

\- Some older modules may overlap with the new brain package.



Decision needed:

\- Keep one primary brain entry point.



\---



\## 7. Evidence Layer



Owns: explaining why Stratify believes something.



Current modules:

\- core/evidence\_engine.py



Rule:

\- No recommendation without evidence.

\- No conclusion without benchmark comparison.

\- No comparison without normalized understanding.



\---



\## 8. Experiment Layer



Owns: suggesting what to test next.



Current modules:

\- core/experiment\_engine.py

\- core/recommendation\_engine.py



Issue:

\- Recommendation and experiment logic may overlap.



Future direction:

\- Prefer “experiments to test” over confident advice.



\---



\## 9. Report / UI Layer



Owns: final user-facing output.



Current modules:

\- core/stratify\_report.py

\- app.py



Rule:

\- UI should display evidence-backed insights only.

\- Hide backend complexity from creator.



\---



\## Cleanup Candidates



Review later:

\- core/budget\_planner.py

\- core/competitor\_intelligence.py

\- core/growth\_blueprint.py

\- core/pattern\_discovery\_engine.py

\- core/trend\_engine.py

\- core/video\_processor.py

\- core/vlm\_engine.py



Do not delete yet.



\---



\## Next Architecture Decision



The next major decision:



Should Stratify’s reasoning be feature-first or creator-decision-first?



Recommended direction:



Observation → Interpretation → Comparison → Reasoning → Experiment

