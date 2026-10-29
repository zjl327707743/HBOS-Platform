"""Run candidate contracts against the installed app, avoiding nested package ambiguity."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'apps' / 'hb_knowledge_app'
sys.path.insert(0, str(APP))

# The repository contains an outer compatibility __init__.py as well as the real app.
# Import the real package before pytest derives test module names from that outer file.
import hb_knowledge_app.hb_knowledge
import pytest

assert Path(hb_knowledge_app.hb_knowledge.__file__).resolve() == APP / 'hb_knowledge_app/hb_knowledge/__init__.py'
targets=[str(APP/'tests')]
if (ROOT/'scripts/knowledge/tests').is_dir():targets.append(str(ROOT/'scripts/knowledge/tests'))
raise SystemExit(pytest.main(['--import-mode=importlib', *targets, '-q', '-p', 'no:cacheprovider', *sys.argv[1:]]))
