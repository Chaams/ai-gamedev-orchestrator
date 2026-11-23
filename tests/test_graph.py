"""Tests rapides du graphe avec des outils factices : aucun Blender ni Unreal requis."""
import asyncio
from pathlib import Path

import pytest

from src.graph import build_graph
from src.naming import fix_asset_name


class FakeTools:
    """Imite blender-mcp-pipeline et unreal-mcp-bridge ; garde la trace des appels."""

    def __init__(self, tri_count=1200, has_uv=True):
        self.tri_count, self.has_uv = tri_count, has_uv
        self.generated: list[str] = []
        self.imported: list[str] = []

    async def generate_prop(self, kind, name, out_dir, size):
        self.generated.append(name)
        return {"name": name, "kind": "static_mesh", "tri_count": self.tri_count, "has_uv": self.has_uv,
                "materials": 1, "scale": [1, 1, 1], "dimensions": [size] * 3, "textures": []}

    async def import_to_engine(self, fbx_path, destination):
        self.imported.append(fbx_path)
        stem = fbx_path.replace("\\", "/").rsplit("/", 1)[-1][:-4]
        return {"ok": True, "imported": [f"{destination}/{stem}.{stem}"]}


def run(tools, **brief):
    base = {"kind": "crate", "name": "SM_WoodenCrate", "size": 1.0, "profile": "mobile", "out_dir": "/tmp/out"}
    return asyncio.run(build_graph(tools).ainvoke({"brief": {**base, **brief}}))


@pytest.mark.parametrize("raw,expected", [
    ("wooden crate", "SM_WoodenCrate"), ("SM_oil_barrel", "SM_OilBarrel"),
    ("woodenCrate", "SM_WoodenCrate"), ("SM_WoodenCrate", "SM_WoodenCrate"), ("42 crate", "SM_Asset42Crate"),
])
def test_fix_asset_name(raw, expected):
    assert fix_asset_name(raw) == expected


def test_valid_asset_is_imported_in_one_attempt():
    tools = FakeTools()
    state = run(tools)
    assert state["status"] == "imported" and state["attempt"] == 1
    assert [Path(p) for p in tools.imported] == [Path("/tmp/out/SM_WoodenCrate.fbx")]


def test_bad_name_is_fixed_then_imported():
    tools = FakeTools()
    state = run(tools, name="wooden crate")
    assert tools.generated == ["wooden crate", "SM_WoodenCrate"]   # 2e génération avec le nom corrigé
    assert state["status"] == "imported" and state["attempt"] == 2
    assert [Path(p) for p in tools.imported] == [Path("/tmp/out/SM_WoodenCrate.fbx")]


def test_over_budget_asset_is_rejected_and_never_imported():
    tools = FakeTools(tri_count=50_000)
    state = run(tools)
    assert state["status"] == "rejected" and tools.imported == []
    assert "TRI_BUDGET" in state["report"]


def test_missing_uv_is_not_auto_fixable():
    tools = FakeTools(has_uv=False)
    state = run(tools)
    assert state["status"] == "rejected" and state["attempt"] == 1 and tools.imported == []


def test_fix_loop_is_bounded():
    class AlwaysBadName(FakeTools):
        async def generate_prop(self, kind, name, out_dir, size):
            asset = await super().generate_prop(kind, name, out_dir, size)
            return {**asset, "name": "not_valid"}   # le générateur ignore le nom demandé

    tools = AlwaysBadName()
    state = asyncio.run(build_graph(tools, max_attempts=3).ainvoke(
        {"brief": {"kind": "crate", "name": "x", "size": 1.0, "profile": "mobile", "out_dir": "/tmp/o"}}))
    assert state["status"] == "rejected" and state["attempt"] == 3 and tools.imported == []
