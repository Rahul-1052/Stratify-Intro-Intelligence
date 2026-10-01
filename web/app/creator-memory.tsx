'use client';
import {FormEvent, useEffect, useState} from 'react';
import CreatorReportView from './creator-report';

type HistoryItem = {id: string; title?: string; revision_count?: number; latest_analysis_at?: string; revisions?: {id: string; revision?: number; created_at?: string}[]};
type Experiment = {id: string; dimension: string; status: string; confidence: string; change_description: string; result_summary?: string; creator_notes?: string};
type Dashboard = {profile: null | {display_name?: string; channel_name?: string}; counts: {videos: number; analyses: number}; history: HistoryItem[]; experiments: Experiment[]};
type Props = {report: Parameters<typeof CreatorReportView>[0]['report']; uploadName: string; contentDigest: string};

export default function CreatorMemory({report, uploadName, contentDigest}: Props) {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [reopened, setReopened] = useState<Parameters<typeof CreatorReportView>[0]['report'] | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const [channelName, setChannelName] = useState('');
  async function load() {
    const response = await fetch('/api/memory', {cache: 'no-store'});
    if (response.ok) setDashboard(await response.json());
  }
  useEffect(() => {void load();}, []);
  async function profile(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('');
    try {
      const response = await fetch('/api/memory', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: 'profile', display_name: displayName, channel_name: channelName})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Profile could not be saved.');
      setMessage('Creator Memory profile saved.'); await load();
    } catch (error) {setMessage(error instanceof Error ? error.message : 'Profile could not be saved.');}
    finally {setBusy(false);}
  }
  async function save() {
    setBusy(true); setMessage('');
    try {
      const response = await fetch('/api/memory', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: 'save', report, upload_name: uploadName, content_digest: contentDigest})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Analysis could not be saved.');
      setDashboard(data.dashboard); setMessage(data.decision === 'existing_project_new_revision' ? 'Saved as a new revision.' : 'Saved to Creator Memory.');
    } catch (error) {setMessage(error instanceof Error ? error.message : 'Analysis could not be saved.');}
    finally {setBusy(false);}
  }
  async function reopen(analysisId: string) {
    setBusy(true); setMessage('');
    try {
      const response = await fetch(`/api/memory?analysis_id=${encodeURIComponent(analysisId)}`, {cache: 'no-store'});
      const data = await response.json();
      if (!response.ok || data.status !== 'reconstructed') throw new Error(data.message || data.detail || 'Saved analysis is incomplete.');
      setReopened(data.report); setMessage('Opened saved analysis without rerunning the pipeline.');
    } catch (error) {setMessage(error instanceof Error ? error.message : 'Saved analysis could not be opened.');}
    finally {setBusy(false);}
  }
  async function updateExperiment(experimentId: string, status: string) {
    setBusy(true); setMessage('');
    try {
      const response = await fetch('/api/memory', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({action: 'experiment', experiment_id: experimentId, status})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Experiment could not be updated.');
      setDashboard(data); setMessage('Experiment status saved as creator-entered state.');
    } catch (error) {setMessage(error instanceof Error ? error.message : 'Experiment could not be updated.');}
    finally {setBusy(false);}
  }
  return <section className="creator-memory" aria-labelledby="memory-title">
    <div className="memory-heading"><div><p className="report-kicker">CREATOR MEMORY</p><h2 id="memory-title">Keep the evidence, not just the output.</h2></div>{dashboard?.profile && <button onClick={save} disabled={busy}>Save this analysis</button>}</div>
    {!dashboard?.profile ? <form className="memory-profile" onSubmit={profile}><p className="muted">Create a local profile before saving analyses. This migration still uses the recovered local memory store; PostgreSQL comes later.</p><div className="memory-fields"><label>Creator name<input required maxLength={120} value={displayName} onChange={e=>setDisplayName(e.target.value)}/></label><label>Channel name<input required maxLength={160} value={channelName} onChange={e=>setChannelName(e.target.value)}/></label></div><button disabled={busy}>Create local profile</button></form> : <>
      <div className="memory-summary"><div><span>Profile</span><b>{dashboard.profile.display_name || 'Creator'}</b></div><div><span>Projects</span><b>{dashboard.counts.videos}</b></div><div><span>Analyses</span><b>{dashboard.counts.analyses}</b></div></div>
      <div className="memory-grid"><div><h3>Saved analyses</h3>{dashboard.history.length ? dashboard.history.map(item=><article className="memory-row" key={item.id}><div><b>{item.title || 'Owned video'}</b><span>{item.revision_count || 0} revision{item.revision_count === 1 ? '' : 's'}</span></div><div className="memory-actions">{item.revisions?.slice(0,3).map(revision=><button className="secondary" key={revision.id} disabled={busy} onClick={()=>reopen(revision.id)}>Open r{revision.revision || 1}</button>)}</div></article>) : <p className="muted">No saved analyses yet.</p>}</div>
      <div><h3>Experiments</h3>{dashboard.experiments.length ? dashboard.experiments.slice(0,5).map(item=><article className="experiment-row" key={item.id}><div><b>{item.dimension.replaceAll('_',' ')}</b><span>{item.confidence} confidence · {item.status}</span><p>{item.change_description}</p></div><select aria-label={`Experiment status for ${item.dimension}`} value={item.status} disabled={busy} onChange={e=>updateExperiment(item.id,e.target.value)}><option value="suggested">Suggested</option><option value="planned">Planned</option><option value="running">Running</option><option value="completed">Completed</option><option value="rejected">Rejected</option><option value="archived">Archived</option></select></article>) : <p className="muted">No supported experiment has been saved.</p>}</div></div>
    </>}
    {message && <p className="memory-message" role="status">{message}</p>}
    {reopened && <div className="reopened-report"><div className="reopened-label"><span>SAVED HISTORY</span><button className="secondary" onClick={()=>setReopened(null)}>Close</button></div><CreatorReportView report={reopened}/></div>}
  </section>;
}
