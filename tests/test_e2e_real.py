"""Test de bout en bout RÉEL (≈ 1 min) : l'orchestrateur parle MCP à blender-mcp-pipeline et unreal-mcp-bridge,
qui pilotent le vrai Blender puis le vrai Unreal. Ignoré si Blender, Unreal ou les dépôts voisins sont absents.
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.graph import build_graph
from src.tools import default_tools

ROOT = Path(__file__).resolve().parent.parent.parent
BLENDER_DIR, UNREAL_DIR = ROOT / "blender-mcp-pipeline", ROOT / "unreal-mcp-bridge"


def _works(directory: Path, code: str) -> bool:
    """Les deux dépôts voisins s'appellent « src » : on teste leurs détecteurs dans des processus séparés."""
    if not directory.exists():
        return False
    return subprocess.run([sys.executable, "-c", code], cwd=directory, capture_output=True).returncode == 0


def _available() -> bool:
    return (_works(BLENDER_DIR, "from src import blender_runner as b; b.find_blender()")
            and _works(UNREAL_DIR, "from src import ue_runner as u; u.find_editor_cmd()"))


pytestmark = pytest.mark.skipif(not _available(), reason="Blender / Unreal / dépôts voisins absents")


def test_prop_goes_from_blender_to_unreal(tmp_path):
    project = tmp_path / "Game" / "Game.uproject"
    project.parent.mkdir()
    project.write_text(json.dumps({
        "FileVersion": 3, "EngineAssociation": "5.4", "Category": "", "Description": "",
        "Plugins": [{"Name": "PythonScriptPlugin", "Enabled": True},
                    {"Name": "EditorScriptingUtilities", "Enabled": True},
                    {"Name": "Bridge", "Enabled": False}]}), encoding="utf-8")

    graph = build_graph(default_tools(str(project)))
    state = asyncio.run(graph.ainvoke({"brief": {
        "kind": "barrel", "name": "oil barrel", "size": 1.2, "profile": "mobile",
        "out_dir": str(tmp_path / "out"), "destination": "/Game/Props"}}))

    assert state["status"] == "imported", state["report"]
    assert state["attempt"] == 2                                   # le nom « oil barrel » a été corrigé
    assert state["brief"]["name"] == "SM_OilBarrel"
    assert state["imported"]["imported"] == ["/Game/Props/SM_OilBarrel.SM_OilBarrel"]
