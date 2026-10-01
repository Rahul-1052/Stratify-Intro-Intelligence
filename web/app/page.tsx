'use client';
import { useState } from 'react';
import IntroEvidence, {type Evidence} from './intro-evidence';
import CreatorMemory from './creator-memory';
import ChannelWorkspace from './channel-workspace';
export default function Home() {
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  return <div className="shell"><a className="skip-link" href="#workspace">Skip to workspace</a>
    <aside><a href="/" className="brand"><span className="mark">s</span>stratify<span className="dot">.</span></a>
      <p className="nav-label">YOUR WORKSPACE</p><a className="nav-item selected" href="#workspace">◈ <span>Content intelligence</span></a>
      <div className="aside-bottom"><span className="status-dot"/> Private development<br/><small>Evidence before advice.</small></div>
    </aside>
    <main id="workspace" tabIndex={-1}><header><span>Workspace <span className="slash">/</span> Content intelligence</span><span className="badge">EARLY ACCESS BUILD</span></header>
      <section className="intro"><p className="eyebrow">A CLEARER NEXT MOVE</p><h1>Understand your channel.<br/>Decide what comes next.</h1><p className="lede">Bring your questions and your goals.<br/>See the evidence, its limits, and what needs investigating.</p></section>
      <ChannelWorkspace/>
      <IntroEvidence onEvidence={setEvidence}/><CreatorMemory report={evidence?.report} uploadName={evidence?.upload_name} contentDigest={evidence?.asset_sha256}/>
      <footer><span>ASK <b>→</b> OBSERVE <b>→</b> UNDERSTAND <b>→</b> DECIDE</span><span>Built on evidence.</span></footer>
    </main></div>;
}
