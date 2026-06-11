import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


def _sanitize(text: str) -> str:
    if not text:
        return ""
    return text.strip().lower()


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    tokens = re.split(r"[\s,，、。；;：:\/\|()（）\[\]【】]+", text)
    return [t for t in tokens if t]


def _score_entry(entry: Dict[str, Any], query_tokens: List[str]) -> int:
    if not query_tokens:
        return 0
    haystacks = [
        entry.get("style_special_word", ""),
        entry.get("prompt_phrase", ""),
        entry.get("search_text", ""),
    ]
    aliases = entry.get("aliases") or []
    haystacks.extend(aliases)
    techniques = entry.get("techniques") or []
    for t in techniques:
        haystacks.append(t.get("primary", ""))
        haystacks.append(t.get("secondary", ""))
        haystacks.append(t.get("dimension_zh", ""))
    combined = " ".join(haystacks)
    combined_l = combined.lower()
    score = 0
    for tok in query_tokens:
        if not tok:
            continue
        if tok in combined_l:
            score += combined_l.count(tok) + 2
    return score


class StyleTechniqueKnowledgeBase:
    """加载并索引风格技法知识库。

    该节点会在首次调用时读取 knowledge_base 目录下的 JSON 文件，并将
    风格名称列表缓存下来，方便下游节点进行选择和检索。
    """

    _cache: Optional[Dict[str, Any]] = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "kb_file": (
                    "STRING",
                    {
                        "default": "style_technique_knowledge_base.json",
                        "tooltip": "knowledge_base 目录下的知识库文件名",
                    },
                ),
                "reload": (["false", "true"], {"default": "false"}),
            }
        }

    RETURN_TYPES = ("STYLE_KB", "STRING", "INT")
    RETURN_NAMES = ("knowledge_base", "style_list_json", "total_entries")
    FUNCTION = "load_kb"
    CATEGORY = "StyleTechnique"

    def _kb_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "knowledge_base"

    def _resolve_path(self, kb_file: str) -> Path:
        candidate = Path(kb_file)
        if candidate.is_absolute() and candidate.exists():
            return candidate
        kb_dir = self._kb_dir()
        kb_path = kb_dir / kb_file
        if kb_path.exists():
            return kb_path
        for p in kb_dir.glob("*.json"):
            if "knowledge" in p.stem.lower() or "style" in p.stem.lower():
                return p
        raise FileNotFoundError(
            f"未在 knowledge_base 目录找到知识库文件: {kb_file}"
        )

    def load_kb(self, kb_file: str, reload: str):
        if reload == "true":
            StyleTechniqueKnowledgeBase._cache = None
        if StyleTechniqueKnowledgeBase._cache is not None:
            cache = StyleTechniqueKnowledgeBase._cache
        else:
            kb_path = self._resolve_path(kb_file)
            with open(kb_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            entries = data.get("entries") or []
            style_names: List[str] = []
            seen = set()
            for e in entries:
                name = e.get("style_special_word") or ""
                if not name or name in seen:
                    continue
                style_names.append(name)
                seen.add(name)
            cache = {
                "data": data,
                "entries": entries,
                "style_names": style_names,
                "path": str(kb_path),
            }
            StyleTechniqueKnowledgeBase._cache = cache

        style_list_json = json.dumps(cache["style_names"], ensure_ascii=False)
        total = len(cache["style_names"])
        return (cache, style_list_json, total)


class StyleTechniquePicker:
    """从知识库中按风格名称精确选择一条记录，输出可直接拼接的提示词。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "knowledge_base": ("STYLE_KB",),
                "style_name": ("STRING", {"default": "瓷眸凝釉风格"}),
                "separator": ("STRING", {"default": ", "}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("prompt_phrase", "style_special_word", "search_text")
    FUNCTION = "pick"
    CATEGORY = "StyleTechnique"

    def pick(self, knowledge_base: Dict[str, Any], style_name: str, separator: str):
        entries = knowledge_base.get("entries", [])
        name = _sanitize(style_name)
        matched: Optional[Dict[str, Any]] = None
        for e in entries:
            if _sanitize(e.get("style_special_word", "")) == name:
                matched = e
                break
        if matched is None:
            for e in entries:
                aliases = e.get("aliases") or []
                if any(_sanitize(a) == name for a in aliases):
                    matched = e
                    break
        if matched is None:
            return ("", "", "")
        phrase = matched.get("prompt_phrase", "") or ""
        phrase = phrase.replace("，", separator).replace(",", separator)
        return (
            phrase,
            matched.get("style_special_word", "") or "",
            matched.get("search_text", "") or "",
        )


class StyleTechniqueSearch:
    """按关键词模糊检索风格条目，返回前 N 条结果的提示词文本。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "knowledge_base": ("STYLE_KB",),
                "query": ("STRING", {"default": "冷色 平刷 线稿", "multiline": True}),
                "top_k": ("INT", {"default": 3, "min": 1, "max": 50, "step": 1}),
                "separator": ("STRING", {"default": " | "}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("joined_prompts", "joined_style_names", "results_json")
    FUNCTION = "search"
    CATEGORY = "StyleTechnique"

    def search(
        self,
        knowledge_base: Dict[str, Any],
        query: str,
        top_k: int,
        separator: str,
    ):
        entries = knowledge_base.get("entries", [])
        query_tokens = [t for t in _tokenize(_sanitize(query)) if len(t) > 0]
        scored: List[Tuple[int, Dict[str, Any]]] = []
        for e in entries:
            s = _score_entry(e, query_tokens)
            if s > 0:
                scored.append((s, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        picked = [e for _, e in scored[:top_k]]
        if not picked and query_tokens:
            picked = entries[:top_k]
        prompts = [e.get("prompt_phrase", "") or "" for e in picked]
        names = [e.get("style_special_word", "") or "" for e in picked]
        joined_prompts = separator.join(prompts)
        joined_names = separator.join(names)
        results_json = json.dumps(
            [
                {
                    "style_special_word": e.get("style_special_word", ""),
                    "prompt_phrase": e.get("prompt_phrase", ""),
                    "search_text": e.get("search_text", ""),
                }
                for e in picked
            ],
            ensure_ascii=False,
        )
        return (joined_prompts, joined_names, results_json)


class StyleTechniqueMerge:
    """将多条提示词拼接成一段可直接放入 ComfyUI Clip 的文本。"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_a": ("STRING", {"default": "", "multiline": True}),
                "text_b": ("STRING", {"default": "", "multiline": True}),
                "separator": ("STRING", {"default": ", "}),
            },
            "optional": {
                "text_c": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("merged_text",)
    FUNCTION = "merge"
    CATEGORY = "StyleTechnique"

    def merge(self, text_a: str, text_b: str, separator: str, text_c: str = ""):
        parts = [t.strip() for t in (text_a, text_b, text_c or "") if t and t.strip()]
        merged = separator.join(parts)
        return (merged,)


NODE_CLASS_MAPPINGS = {
    "StyleTechniqueKnowledgeBase": StyleTechniqueKnowledgeBase,
    "StyleTechniquePicker": StyleTechniquePicker,
    "StyleTechniqueSearch": StyleTechniqueSearch,
    "StyleTechniqueMerge": StyleTechniqueMerge,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "StyleTechniqueKnowledgeBase": "Style Technique Knowledge Base (Load)",
    "StyleTechniquePicker": "Style Technique Picker (By Name)",
    "StyleTechniqueSearch": "Style Technique Search (By Keyword)",
    "StyleTechniqueMerge": "Style Technique Merge Text",
}
