"""Browser QA with synthetic media and an isolated disposable memory store."""
import os,secrets,subprocess,time,sys,tempfile
from pathlib import Path
import cv2,numpy as np,requests
root=Path(__file__).resolve().parents[1];qa=Path(os.getenv('STRATIFY_QA_DIR') or tempfile.mkdtemp(prefix='stratify-browser-'));qa.mkdir(exist_ok=True)
for name,changing in [('owned',True),('stable',False)]:
 w=cv2.VideoWriter(str(qa/f'{name}.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),10,(160,120))
 for i in range(120):w.write(np.full((120,160,3),220 if changing and i>=20 else 25,dtype=np.uint8))
 w.release()
env=dict(os.environ,STRATIFY_QA_DIR=str(qa),STRATIFY_SERVICE_TOKEN=secrets.token_urlsafe(32),STRATIFY_LOCAL_MEDIA_ENABLED='1',STRATIFY_API_URL='http://127.0.0.1:8005',STRATIFY_WEB_ORIGIN='http://127.0.0.1:3005',STRATIFY_MEMORY_DB=str(qa/'memory.db'),NEXT_TELEMETRY_DISABLED='1')
with (qa/'services.log').open('w') as logs:
 api=subprocess.Popen([sys.executable,'-m','uvicorn','api.main:app','--host','127.0.0.1','--port','8005'],cwd=root,env=env,stdout=logs,stderr=logs)
 web=subprocess.Popen(['node','node_modules/next/dist/bin/next','dev','--hostname','127.0.0.1','--port','3005'],cwd=root/'web',env=env,stdout=logs,stderr=logs)
 try:
  for _ in range(100):
   try:
    if requests.get('http://127.0.0.1:3005',timeout=2).ok and requests.get('http://127.0.0.1:8005/healthz',timeout=1).ok:break
   except requests.RequestException:pass
   time.sleep(.2)
  subprocess.run(['node',str(root/'web/tests/browser-memory.cjs')],env=env,check=True)
 finally:
  api.terminate();web.terminate();api.wait(timeout=10);web.wait(timeout=10)
