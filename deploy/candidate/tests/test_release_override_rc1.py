import importlib.util,json
from pathlib import Path

def module():
    path=Path(__file__).parents[2]/'release_candidate.py'
    spec=importlib.util.spec_from_file_location('rc1_release_controller',path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def test_repair_replaces_nested_static_mount_and_preserves_required_mounts(tmp_path):
    release=module();original=tmp_path/'original.json';one=tmp_path/'one.json';two=tmp_path/'two.json'
    original.write_text(json.dumps({'services':{'bff':{'environment':{'IDENTITY':'required'},'volumes':['cfg:/run/hbos-reference:ro','public:/parent:ro']},'frontend':{'volumes':['sites:/sites:ro']},'service':{'volumes':['audit:/audit']}}}))
    images={'bff':'bff-immutable','service':'service-immutable','frontend':'frontend-immutable'}
    release.override(one,original,images,tmp_path/'first')
    release.override(two,one,images,tmp_path/'second')
    data=json.loads(two.read_text())['services']
    assert data['bff']['environment']=={'IDENTITY':'required'}
    assert 'cfg:/run/hbos-reference:ro' in data['bff']['volumes']
    assert sum(release.BFF_STATIC in v for v in data['bff']['volumes'])==1
    assert sum(release.FRONT_STATIC in v for v in data['frontend']['volumes'])==1
    assert str(tmp_path/'first') not in two.read_text()
    assert data['service']['volumes']==['audit:/audit']
