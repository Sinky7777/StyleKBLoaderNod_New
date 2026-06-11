import os
import shutil
from pathlib import Path

from .nodes.style_technique_nodes import (
    NODE_CLASS_MAPPINGS,
    NODE_DISPLAY_NAME_MAPPINGS,
)

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]


def _ensure_kb_files():
    """把插件根目录之外的示例知识库自动同步到 knowledge_base 目录，
    便于开箱即用。已存在同名文件时不覆盖。"""
    kb_dir = Path(__file__).resolve().parent / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)
    default_name = "style_technique_knowledge_base.json"
    if (kb_dir / default_name).exists():
        return
    candidates = []
    parent = kb_dir.parent.parent
    for pattern in ("*knowledge_base*.json", "*style_technique*.json"):
        candidates.extend(parent.glob(pattern))
        candidates.extend((parent / "..").glob(pattern))
    candidates = [p for p in candidates if p.exists() and p.is_file()]
    for src in candidates:
        dst = kb_dir / default_name
        shutil.copyfile(src, dst)
        return


try:
    _ensure_kb_files()
except Exception:
    pass
