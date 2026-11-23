"""Correction automatique des noms d'assets selon la convention Unreal (SM_PascalCase)."""
from __future__ import annotations

import re

from game_asset_validator.rules import PREFIXES


def fix_asset_name(name: str, kind: str = "static_mesh") -> str:
    """« wooden crate » -> « SM_WoodenCrate » ; « SM_oil_barrel » -> « SM_OilBarrel »."""
    prefix = PREFIXES[kind]
    body = name[len(prefix):] if name.startswith(prefix) else name
    words = re.findall(r"[A-Za-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", body))
    pascal = "".join(w[0].upper() + w[1:] for w in words)
    if not pascal or not pascal[0].isalpha():
        pascal = "Asset" + pascal
    return prefix + pascal
