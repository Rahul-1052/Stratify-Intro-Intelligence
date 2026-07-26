# Real Pipeline Reliability and Evidence Audit V1

## Production execution map

The application calls `stratify_platform.module_registry.run_module("intro_intelligence")`, whose registered runner is `core.stratify_report.run_stratify_report`.

| Stage | Concrete production path |
|---|---|
| URL context acquisition | `core.youtube_client.get_full_youtube_context` from `run_stratify_report` |
| YouTube intro acquisition | `core.acquisition.acquisition_service.acquire_video_intro` → `core.acquisition.youtube_acquisition.acquire_intro_clip` |
| Uploaded/local video handling | `app.save_uploaded_video` → `run_stratify_report(uploaded_video_path=...)` → `core.pipeline.intro_pipeline._acquire_from_local_video` |
| Clip preparation | `utils.video_utils.extract_intro_clip` |
| Frame extraction | `utils.frame_extractor.extract_frames_from_clip` |
| Frame/visual observation | `core.vision_analyzer.analyze_intro_frames` and `core.intro_observer.observe_intro` |
| Temporal observation | `core.observers.temporal_evidence.build_temporal_evidence` |
| Semantic observation | `core.observers.semantic_observer.observe_semantics` |
| Creative structure/understanding | `core.understanding.understand_creative_opening` and `build_intro_understanding` |
| Benchmark discovery | `core.benchmark_collector.collect_benchmark_videos` and `core.benchmark_feature_extractor.extract_benchmark_features` |
| Evidence qualification | `core.benchmark_qualification.qualify_observed_benchmarks` and `core.evidence_engine.build_evidence` |
| Creative reasoning | functions in `core.reasoning`, ending with `build_creative_reasoning` |
| Experiment generation | `core.experiment_engine.generate_experiment_board`; Creator experiments are selected by `core.creator_report.build_creator_report` |
| Creator report construction | `core.creator_report.build_creator_report` |
| Project persistence | `stratify_platform.projects.VideoProject.record_result`; Product Validation uses `core.product_validation.storage.ValidationStore.save_report` |
| Creator Memory persistence | `core.memory.service.CreatorMemoryService.save_report` → repository/schema modules |
| Saved-report reconstruction | `core.memory.reconstruction.reconstruct_creator_report`; UI reuse is in `ui.memory` and `ui.report.render_report` |

## Trace architecture

`core.product_validation.pipeline_trace` defines a JSON-safe `PipelineTrace` and `PipelineStageTrace` for acquisition through reconstruction. Status transitions are validated. Original error type/message, warnings, evidence counts, outputs, retry count, timestamps, durations, and provenance are retained.

Tracing wraps Product Validation’s existing call to the production module. It does not modify thresholds, benchmark selection, recommendations, failure status, or unavailable evidence. Stages that are inferred from the final serialized report say `derived from production report`; this is intentionally distinct from direct internal timing.

The failure taxonomy is stable and includes source, network, downloader, media, clip, frame, corruption, observation, benchmark, qualification, reasoning, report, persistence, reconstruction, dependency, environment, and unknown failures.

## Bounded pilot

```powershell
.\.venv\Scripts\python.exe tools\run_real_pipeline_audit.py --input-dir temp_clips --limit 5 --no-network --trace-export
.\.venv\Scripts\python.exe tools\run_real_pipeline_audit.py --limit 5 --resume latest --skip-existing --no-network
.\.venv\Scripts\python.exe tools\run_real_pipeline_audit.py --limit 5 --case local-01 --no-network
```

The runner uses at most five readable, nonduplicate cached MP4 clips, never downloads in `--no-network` mode, checkpoints after every case, continues after failures, and performs no retries. It does not infer creator, title, niche, or URL from filenames.

Outputs under `.stratify_validation/exports/<run-id>/` include discovered-input metadata, per-case trace JSON references, aggregate evidence availability JSON, failure CSV, and Markdown audit.

## Evidence availability

The audit reports sampled frames, temporal windows, human presence, text overlay, scene type, visual energy, motion, lighting, color feel, benchmark candidates, qualified benchmarks, supported opportunities, and supported experiments as:

- unavailable
- available but weak
- available and qualified

An unavailable serialized field means the final report did not expose qualifying evidence; it does not claim the internal function never executed.

## Privacy and limitations

Validation artifacts remain ignored and separate from Creator Memory. Builder Mode may display preserved errors; Creator Mode never exposes pipeline traces. Cached clips may contain sensitive media and lack trustworthy provenance, so review them before sharing. This audit diagnoses the existing pipeline and must not be used to justify video-specific production rules.
