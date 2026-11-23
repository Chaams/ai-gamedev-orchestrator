"""CLI :  python -m src.run --kind crate --name "wooden crate" --profile mobile --project C:\\Jeu\\Jeu.uproject"""
from __future__ import annotations

import argparse
import asyncio
import tempfile

from .graph import build_graph
from .tools import default_tools


async def main(args) -> int:
    out_dir = args.out_dir or tempfile.mkdtemp(prefix="gamedev_")
    graph = build_graph(default_tools(args.project))
    state = await graph.ainvoke({"brief": {"kind": args.kind, "name": args.name, "size": args.size,
                                           "profile": args.profile, "out_dir": out_dir,
                                           "destination": args.destination}})
    print(state["report"])
    return 0 if state["status"] == "imported" else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--kind", default="crate", choices=["crate", "barrel"])
    p.add_argument("--name", required=True)
    p.add_argument("--size", type=float, default=1.0)
    p.add_argument("--profile", default="pc", choices=["mobile", "pc", "hero"])
    p.add_argument("--project", required=True, help="chemin du .uproject")
    p.add_argument("--destination", default="/Game/Props")
    p.add_argument("--out-dir")
    raise SystemExit(asyncio.run(main(p.parse_args())))
