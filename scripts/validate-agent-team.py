"""Validate project Codex role wiring without reading account state."""
import json
from pathlib import Path
import tomllib

ROOT=Path(__file__).resolve().parents[1]
team=json.loads((ROOT/'config/agents.json').read_text(encoding='utf-8'))
config=tomllib.loads((ROOT/'.codex/config.toml').read_text(encoding='utf-8'))
assert set(config)=={'features','agents'}, 'Team must not override account/model/permissions'
assert config['features']=={'multi_agent':True}
roles={key for key in config['agents'] if key not in ('max_threads','max_depth')}
assert roles==set(team['roles']), 'Native roles and catalog differ'
assert config['agents']['max_depth']==1
for name,role in team['roles'].items():
    file=(ROOT/'.codex'/config['agents'][name]['config_file']).resolve()
    assert file==(ROOT/role['config']).resolve()
    data=tomllib.loads(file.read_text(encoding='utf-8'))
    assert set(data)=={'developer_instructions'}, 'Role must inherit model/account/permissions'
    assert role['skill'] in data['developer_instructions']
    for relative in [role['config'],role['skill'],*role['references']]:
        target=(ROOT/relative).resolve()
        assert target.is_relative_to(ROOT) and target.is_file(), relative
for selected in team['routes'].values():
    assert selected and all(role in team['roles'] for role in selected)
print(json.dumps({'roles':list(team['roles']),'schema':'Codex CLI 0.135 role config','passed':True}))
