"""Accès aux outils de la chaîne de production.

`GameTools` est l'interface utilisée par le graphe. `McpTools` l'implémente en parlant VRAIMENT MCP
(client stdio) aux serveurs `blender-mcp-pipeline` et `unreal-mcp-bridge` ; les tests utilisent une
implémentation factice pour rester rapides.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Protocol

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class GameTools(Protocol):
    async def generate_prop(self, kind: str, name: str, out_dir: str, size: float) -> dict: ...

    async def import_to_engine(self, fbx_path: str, destination: str) -> dict: ...


def _parse(result):
    if result.isError:
        raise RuntimeError("erreur MCP : " + " ".join(getattr(c, "text", "") for c in result.content))
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return structured["result"] if set(structured) == {"result"} else structured
    return json.loads(result.content[0].text)


class McpServer:
    """Lance un serveur MCP (stdio) le temps d'un appel d'outil."""

    def __init__(self, directory: str, env: dict | None = None, command: str | None = None):
        self.directory = directory
        self.env = {**os.environ, **(env or {})}
        self.command = command or sys.executable

    async def call(self, tool: str, arguments: dict):
        params = StdioServerParameters(command=self.command, args=["-m", "src.server"],
                                       cwd=self.directory, env=self.env)
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return _parse(await session.call_tool(tool, arguments))


class McpTools:
    def __init__(self, blender_dir: str, unreal_dir: str, unreal_project: str):
        self.blender = McpServer(blender_dir)
        self.unreal = McpServer(unreal_dir, env={"UE_PROJECT": unreal_project})

    async def generate_prop(self, kind: str, name: str, out_dir: str, size: float) -> dict:
        return await self.blender.call("generate_prop", {"kind": kind, "name": name, "out_dir": out_dir, "size": size})

    async def import_to_engine(self, fbx_path: str, destination: str) -> dict:
        return await self.unreal.call("import_fbx", {"fbx_path": fbx_path, "destination": destination})


def default_tools(unreal_project: str) -> McpTools:
    """Dépôts voisins par défaut : ../blender-mcp-pipeline et ../unreal-mcp-bridge (surchargeables par variables d'environnement)."""
    root = Path(__file__).resolve().parent.parent.parent
    return McpTools(os.environ.get("BLENDER_MCP_DIR", str(root / "blender-mcp-pipeline")),
                    os.environ.get("UNREAL_MCP_DIR", str(root / "unreal-mcp-bridge")), unreal_project)
