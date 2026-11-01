from fastapi.testclient import TestClient
from uuid import uuid4
import main


def sample(**overrides):
    data={"client_id":str(uuid4()), "area":"Demo area, Sylhet", "lat":24.9, "lng":91.8,
          "details":"This is a controlled test of the SOS workflow.", "people_affected":6,
          "children_count":2,"mobility_support":1,"trapped":True,"water_rising":True,
          "medical_need":False,"contact":"01000000000","consent":True}
    return {**data,**overrides}


def test_sos_private_and_idempotent(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DB_PATH',tmp_path/'sos.db')
    monkeypatch.setattr(main,'ADMIN_TOKEN','test-reviewer-token')
    monkeypatch.setattr(main,'RELAY_TOKEN','test-relay-token')
    main.SOS_RATE_LIMIT.clear()
    with TestClient(main.app) as client:
        data=sample()
        res=client.post('/api/sos',json=data)
        assert res.status_code==201,res.text
        assert res.json()['public_id'].startswith('SOS-')
        assert res.json()['server_received'] is True
        assert 'contact' not in res.json()
        duplicate=client.post('/api/sos',json=data)
        assert duplicate.status_code==201
        assert duplicate.json()['duplicate'] is True
        assert duplicate.json()['public_id']==res.json()['public_id']
        assert client.get('/api/rescue/sos').status_code==401
        assert client.get('/api/rescue/sos',headers={'X-Admin-Token':'incorrect'}).status_code==401
        rows=client.get('/api/rescue/sos',headers={'X-Admin-Token':'test-reviewer-token'}).json()
        assert len(rows)==1
        assert rows[0]['contact']==data['contact']
        assert rows[0]['triage_tier']=='critical'
        assert 'trapped' in rows[0]['triage_reasons'].lower()
        # These private SOS records must not be published on the existing public map.
        assert res.json()['public_id'] not in [r['public_id'] for r in client.get('/api/reports').json()]
        status=client.patch('/api/rescue/sos/'+res.json()['public_id'],headers={'X-Admin-Token':'test-reviewer-token'},json={'status':'reviewing'})
        assert status.status_code==200
        assert status.json()['status']=='reviewing'
        assert client.patch('/api/rescue/sos/'+res.json()['public_id'],json={'status':'closed'}).status_code==401
        assert client.get('/sw.js').status_code==200


def test_sos_validation_and_relay_security(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DB_PATH',tmp_path/'sos2.db')
    monkeypatch.setattr(main,'ADMIN_TOKEN','test-reviewer-token')
    monkeypatch.setattr(main,'RELAY_TOKEN','test-relay-token')
    main.SOS_RATE_LIMIT.clear()
    with TestClient(main.app) as client:
        assert client.post('/api/sos',json=sample(consent=False)).status_code==422
        assert client.post('/api/sos',json=sample(lat=None,lng=91.8)).status_code==422
        assert client.post('/api/sos',json=sample(children_count=100)).status_code==422
        assert client.post('/api/sos',json=sample(lat=0,lng=91)).status_code==422
        assert client.post('/api/relay/ingest',json=sample()).status_code==401
        response=client.post('/api/relay/ingest',headers={'X-Relay-Token':'test-relay-token'},json=sample(trapped=False,water_rising=False,children_count=0,mobility_support=0,people_affected=1))
        assert response.status_code==201,response.text
        rows=client.get('/api/rescue/sos',headers={'X-Admin-Token':'test-reviewer-token'}).json()
        assert rows[0]['source']=='relay-gateway'
        assert rows[0]['triage_tier']=='standard'
