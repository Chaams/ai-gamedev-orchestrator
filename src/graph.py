"""Graphe LangGraph : brief -> génération Blender -> validation -> (correction) -> import Unreal -> rapport.

    START -> generate -> validate --ok--------------> import_engine -> report -> END
                            |--nom corrigeable------> fix_name -> generate (boucle, max `max_attempts`)
                            '--autre erreur---------> report (asset rejeté, rien n'est importé)
"""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from game_asset_validator import validate
from langgraph.graph import END, START, StateGraph

from .naming import fix_asset_name
from .tools import GameTools

FIXABLE = {"NAME_PREFIX", "NAME_FORMAT"}


class State(TypedDict, total=False):
    brief: dict          # kind, name, size, profile, out_dir, destination
    attempt: int
    asset: dict
    issues: list
    ok: bool
    imported: dict
    status: str          # imported | rejected
    report: str


def build_graph(tools: GameTools, max_attempts: int = 3):
    async def generate(state: State) -> State:
        b = state["brief"]
        asset = await tools.generate_prop(b["kind"], b["name"], b["out_dir"], b.get("size", 1.0))
        return {"asset": asset, "attempt": state.get("attempt", 0) + 1}

    async def validate_node(state: State) -> State:
        report = validate(state["asset"], state["brief"].get("profile", "pc"))
        return {"ok": report.ok, "issues": [i.__dict__ for i in report.issues]}

    async def fix_name(state: State) -> State:
        brief = dict(state["brief"])
        brief["name"] = fix_asset_name(brief["name"])
        return {"brief": brief}

    async def import_engine(state: State) -> State:
        b = state["brief"]
        fbx = str(Path(b["out_dir"]) / f"{b['name']}.fbx")
        return {"imported": await tools.import_to_engine(fbx, b.get("destination", "/Game/Props")), "status": "imported"}

    async def report(state: State) -> State:
        status = state.get("status", "rejected")
        errors = [i for i in state.get("issues", []) if i["severity"] == "error"]
        if status == "imported":
            text = (f"{state['brief']['name']} : importé dans Unreal ({', '.join(state['imported']['imported'])}) "
                    f"après {state['attempt']} tentative(s).")
        else:
            text = (f"{state['brief']['name']} : REJETÉ après {state['attempt']} tentative(s) — "
                    + "; ".join(f"{i['code']}: {i['message']}" for i in errors))
        return {"status": status, "report": text}

    def route(state: State) -> str:
        if state["ok"]:
            return "import_engine"
        errors = {i["code"] for i in state["issues"] if i["severity"] == "error"}
        if errors <= FIXABLE and state["attempt"] < max_attempts:
            return "fix_name"
        return "report"

    g = StateGraph(State)
    for name, fn in [("generate", generate), ("validate", validate_node), ("fix_name", fix_name),
                     ("import_engine", import_engine), ("report", report)]:
        g.add_node(name, fn)
    g.add_edge(START, "generate")
    g.add_edge("generate", "validate")
    g.add_conditional_edges("validate", route, ["import_engine", "fix_name", "report"])
    g.add_edge("fix_name", "generate")
    g.add_edge("import_engine", "report")
    g.add_edge("report", END)
    return g.compile()
