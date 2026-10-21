"""Use stored event risk, never a distinct-value count as a risk score."""
import sqlite3
import time
import uuid

import pytest
from test.stage2.test_isolation_http import alice, bob


@pytest.mark.parametrize('risk,count,fp,module,expected', [
    (80,1,0,'synthetic_review_fixture','HIGH'),
    (60,2,0,'synthetic_review_fixture','MEDIUM'),
    (0,55,0,'synthetic_review_fixture',None),
    (90,1,1,'synthetic_review_fixture',None),
    (90,1,0,'SpiderFoot UI',None),
])
def test_risk_alert_uses_risk_and_active_event_count(alice,bob,http_server,risk,count,fp,module,expected):
    client,url=alice
    other,_=bob
    sid=uuid.uuid4().hex
    now=int(time.time()*1000)
    with sqlite3.connect(http_server[3]) as db:
        db.execute('INSERT INTO web_scan_owners(scan_id,user_id) VALUES (?,?)',(sid,2))
        db.execute('INSERT INTO tbl_scan_instance(guid,name,seed_target,created,started,ended,status) VALUES (?,?,?,?,?,?,?)',
                   (sid,'合成风险字段回归','risk.example.invalid',now,now,now,'FINISHED'))
        for index in range(count):
            db.execute('INSERT INTO tbl_scan_results(scan_instance_id,hash,type,generated,risk,module,data,false_positive,source_event_hash) VALUES (?,?,?,?,?,?,?,?,?)',
                       (sid,uuid.uuid4().hex,'EMAILADDR',now,risk,module,f'demo{index}@example.invalid',fp,'ROOT'))
    response=client.get(url+'/riskalerts')
    assert response.status_code==200
    alerts=[row for row in response.json() if row['scanId']==sid]
    if expected:
        assert len(alerts)==1
        assert alerts[0]['risk']==expected
        assert alerts[0]['eventCount']==count
        assert '***@example.invalid' in alerts[0]['detail']
    else:
        assert alerts==[]
    assert all(row['scanId']!=sid for row in other.get(url+'/riskalerts').json())
