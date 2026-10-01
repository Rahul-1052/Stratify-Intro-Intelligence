type TimelineItem = {time?: string; moment?: string; confidence?: string};
type Experiment = {title?: string; variable?: string; structural_dimension?: string; change?: string; recommendation?: string; what_stays_constant?: string; how_to_compare?: string; confidence?: string; limitation?: string};
type CreatorReport = {
  opening_snapshot?: {summary?: string};
  intro_timeline?: TimelineItem[];
  biggest_opportunity?: {title?: string; summary?: string; why_test?: string; limitation?: string; supported?: boolean};
  experiments?: Experiment[];
  confidence_breakdown?: {observation_confidence?: string; interpretation_confidence?: string; recommendation_confidence?: string};
  confidence_summary?: {plain_language?: string; text_evidence?: string};
  limitations?: string[];
};
type Finding = {finding_id?: string; observation_type?: string; start_time?: number; end_time?: number; measured_value?: unknown; evidence_strength?: string; availability_state?: string; limitations?: string[]};
type Report = {creator_report?: CreatorReport; intelligence_v3?: {findings?: Finding[]}; warnings?: string[]};
const label = (value?: string) => (value || 'limited').replaceAll('_', ' ');
function Measurement({value}: {value: unknown}) {
  if (typeof value === 'string' || typeof value === 'number') return <p>{String(value)}</p>;
  if (!value || typeof value !== 'object' || Array.isArray(value)) return <p>Not measured</p>;
  const data = value as Record<string, unknown>;
  const stable = data.longest_stable_interval as {start_time?: number; end_time?: number; duration?: number} | undefined;
  const entries = Object.entries(data).filter(([,item])=>typeof item === 'number' || typeof item === 'boolean');
  return <dl className="measurement-list">{entries.map(([key,item])=><div key={key}><dt>{label(key)}</dt><dd>{typeof item === 'boolean' ? (item ? 'Yes' : 'No') : String(item)}{key.includes('time') ? 's' : ''}</dd></div>)}{stable && <div><dt>Longest stable interval</dt><dd>{stable.start_time}s–{stable.end_time}s ({stable.duration}s)</dd></div>}</dl>;
}
export default function CreatorReportView({report}: {report: Report}) {
  const creator = report.creator_report || {};
  const opportunity = creator.biggest_opportunity || {};
  const experiment = opportunity.supported ? creator.experiments?.[0] : undefined;
  const findings = (report.intelligence_v3?.findings || []).filter(item => item.availability_state === 'available_and_qualified');
  const strongest = findings[0];
  const confidence = creator.confidence_breakdown || {};
  return <section className="creator-report" aria-live="polite">
    <div className="report-kicker">CREATOR REPORT V4</div>
    <div className="report-verdict"><div><span>Opening verdict</span><h2>{opportunity.summary || creator.opening_snapshot?.summary || 'The available evidence does not support a creative change yet.'}</h2></div><strong>{opportunity.supported ? opportunity.title : 'No supported change yet'}</strong></div>
    <div className="confidence-row">{[['Observation', confidence.observation_confidence], ['Interpretation', confidence.interpretation_confidence], ['Recommendation', opportunity.supported ? confidence.recommendation_confidence : 'abstained']].map(([name,value]) => <div key={name}><span>{name}</span><b>{label(value)}</b></div>)}</div>
    <div className="report-section"><h3>Story of the intro</h3>{creator.intro_timeline?.length ? <ol className="timeline">{creator.intro_timeline.map((item,index)=><li key={`${item.time}-${index}`}><time>{item.time || '—'}</time><div><b>{item.moment?.replaceAll('_', ' ') || 'Observed change'}</b><span>{label(item.confidence)} evidence</span></div></li>)}</ol> : <p className="muted">No qualified chronological visual change was established.</p>}</div>
    <div className="report-section"><h3>Strongest supported finding</h3>{strongest ? <div className="finding"><div><b>{label(strongest.observation_type)}</b><span>{label(strongest.evidence_strength)} evidence · {(strongest.start_time || 0).toFixed(1)}s–{(strongest.end_time || 0).toFixed(1)}s</span></div><Measurement value={strongest.measured_value}/>{strongest.limitations?.[0] && <small>{strongest.limitations[0]}</small>}</div> : <p className="muted">No qualified finding is strong enough to elevate above the raw observations.</p>}</div>
    <div className="report-section"><h3>Primary experiment</h3>{experiment ? <div className="experiment"><div className="experiment-head"><span>ONE CONTROLLED TEST</span><b>{experiment.title || opportunity.title}</b></div><dl><dt>Change</dt><dd>{experiment.change || experiment.recommendation || 'Not specified'}</dd><dt>Keep constant</dt><dd>{experiment.what_stays_constant || 'Keep the remaining opening decisions unchanged.'}</dd><dt>Compare</dt><dd>{experiment.how_to_compare || 'Compare the isolated versions before attributing performance.'}</dd><dt>Confidence</dt><dd>{label(experiment.confidence)}</dd></dl>{experiment.limitation && <small>{experiment.limitation}</small>}</div> : <div className="abstention"><b>No experiment is supported yet.</b><p>{opportunity.limitation || 'A controlled alternative cannot be justified from the available evidence.'}</p></div>}</div>
    <div className="report-section"><h3>Evidence and limits</h3><p className="muted">{creator.confidence_summary?.plain_language || 'Confidence remains tied to the observed evidence.'}</p><ul className="limits">{[...(creator.limitations || []), ...(report.warnings || [])].filter((item,index,array)=>item && array.indexOf(item)===index).map(item=><li key={item}>{item}</li>)}</ul></div>
  </section>;
}
