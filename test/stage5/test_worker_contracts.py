"""Exercise installed vendor glue with controlled outputs and no network traffic."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("source",["sherlock","maigret","holehe","whatsmyname","hibp","spiderfoot","spiderfoot_dns_failure"])
def test_vendor_glue_preserves_match_and_original_url_without_live_requests(source,tmp_path):
    python=ROOT/".tools/live"/source/"Scripts/python.exe" if source in ("sherlock","maigret","holehe") else Path(sys.executable)
    if not python.is_file():
        pytest.skip("optional source environment missing; rebuild with scripts/install-live-sources.ps1")
    code = '''
import json,sys,os,logging
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import patch
import importlib.util
spec=importlib.util.spec_from_file_location('live_worker',Path('spiderfoot/live_worker.py'))
w=importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
source=sys.argv[1]
payload={'work_dir':sys.argv[2]}
url='https://example.org/profile'
if source=='sherlock':
    from sherlock_project.result import QueryStatus
    with patch('sherlock_project.sherlock.sherlock',return_value={'Example':{'status':N(status=QueryStatus.CLAIMED),'url_user':url}}):
        result=w.sherlock('synthetic_demo',payload)
elif source=='maigret':
    from maigret.result import MaigretCheckStatus
    async def fake(*a,**kw): return {'Example':{'status':N(status=MaigretCheckStatus.CLAIMED),'url_user':url}}
    with patch('maigret.checking.maigret',fake): result=w.maigret('synthetic_demo',payload)
elif source=='holehe':
    async def fake(query,client,out):out.append({'name':'Example','domain':'example.org','exists':True,'rateLimit':False})
    with patch('holehe.modules.programing.github.github',fake),patch('holehe.modules.cms.gravatar.gravatar',fake):
        result=w.holehe('alice@example.invalid',payload)
elif source=='whatsmyname':
    class FakeTransport(w.ModuleTransport):
        def __init__(self,cache):
            super().__init__(json.dumps({'sites':[{'name':'GitLab','cat':'coding','uri_check':url+'/{account}',
                'e_code':200,'m_code':404,'e_string':'profile-found','m_string':'not-found'}]}))
        def fetchUrl(self,*a,**kw):
            self.codes.append(200)
            return {'code':'200','content':'synthetic_demo profile-found'}
    with patch.object(w,'ModuleTransport',FakeTransport):
        result=w.whatsmyname('synthetic_demo',payload)
elif source=='hibp':
    os.environ['SF_HIBP_API_KEY']='test-placeholder-not-a-real-key'
    with patch.object(w.ModuleTransport,'fetchUrl',return_value={'code':'200','content':'[{"Name":"Example"}]'}):
        result=w.hibp('alice@example.invalid',payload)
elif source=='spiderfoot_dns_failure':
    import socket
    from spiderfoot import SpiderFootDb
    def fake_scan(*a,**kw):
        try: socket.gethostbyname_ex('example.org')
        except OSError: pass
        return N(status='FINISHED')
    with patch('socket.gethostbyname_ex',side_effect=socket.gaierror(socket.EAI_AGAIN,'controlled timeout')),patch('sfscan.SpiderFootScanner',side_effect=fake_scan),patch.object(SpiderFootDb,'scanResultEvent',return_value=[]),patch.object(SpiderFootDb,'scanErrors',return_value=[]):
        result=w.spiderfoot('example.org',payload)
else:
    from spiderfoot import SpiderFootDb
    row=[1700000000,url,'seed','sfp_dnsresolve','LINK',75,1,0,'hash','parent','Link','DATA','scan',0,0]
    seed=list(row); seed[3]='SpiderFoot UI'
    root=list(row);root[4]='ROOT'
    with patch('sfscan.SpiderFootScanner',return_value=N(status='FINISHED')),patch.object(SpiderFootDb,'scanResultEvent',return_value=[root,seed,row]),patch.object(SpiderFootDb,'scanErrors',return_value=[]):
        result=w.spiderfoot('example.org',payload)
print(json.dumps(result))
'''
    result=subprocess.run([str(python),"-B","-c",code,source,str(tmp_path)],cwd=ROOT,
        capture_output=True,text=True,encoding="utf-8",timeout=20,env=dict(os.environ,PYTHONIOENCODING="utf-8"))
    assert result.returncode==0,result.stderr
    data=json.loads(result.stdout)
    if source=="spiderfoot_dns_failure":
        assert data["status"]=="failed" and data["items"]==[]
        return
    assert data["status"]=="completed" and data["items"]
    assert all(item["url"].startswith("https://") for item in data["items"])
    if source=="spiderfoot":
        assert len(data["items"])==1
