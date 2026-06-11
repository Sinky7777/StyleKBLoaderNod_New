# comfyui-style-technique-nodes

一个用于在 **ComfyUI** 中接入「风格技法知识库」的自定义节点包。

它会读取插件 `knowledge_base/` 目录下的 JSON 知识库，并在 ComfyUI 中提供 4 类节点：

- **Style Technique Knowledge Base (Load)** — 加载知识库，输出 `knowledge_base` / 风格名称列表 / 条目总数
- **Style Technique Picker (By Name)** — 根据风格名称精确取出一条 `prompt_phrase`，可直接送入 `CLIP Text Encode`
- **Style Technique Search (By Keyword)** — 关键词模糊检索，返回前 K 条风格的提示词
- **Style Technique Merge Text** — 把多条提示词拼接到一起（`,` / `|` 或自定义分隔符）

> 本插件 **不依赖任何第三方包**，开箱即用。

## 安装

把整个项目文件夹放到 ComfyUI 的 `custom_nodes/` 下即可：

```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/YOUR_USERNAME/comfyui-style-technique-nodes.git
```

然后重启 ComfyUI，在节点菜单的 `StyleTechnique` 分类下就能看到新节点。

如果你没有安装 git，也可以直接把 `comfyui-style-technique-nodes` 文件夹整个拖到 `custom_nodes/` 目录里。

## 替换/更新你自己的知识库

1. 把你的 JSON 文件放到 `comfyui-style-technique-nodes/knowledge_base/` 目录。
2. 默认文件名是 `style_technique_knowledge_base.json`，你也可以在 `Style Technique Knowledge Base (Load)` 节点的 `kb_file` 里填自定义文件名。
3. JSON 结构要求：
   ```json
   {
     "entries": [
       {
         "style_special_word": "瓷眸凝釉风格",
         "aliases": ["瓷眸凝釉"],
         "prompt_phrase": "瓷眸凝釉风格，无线稿，瓷面高光边，……",
         "techniques": [...],
         "search_text": "瓷眸凝釉风格 无线稿 瓷面高光边 ……"
       }
     ]
   }
   ```

## 一个最简单的工作流

```
Style Technique Knowledge Base (Load)
       │
       ▼
Style Technique Picker (By Name)  ── style_name: "瓷眸凝釉风格"
       │
       ▼  prompt_phrase
CLIP Text Encode (Prompt)  ── (把 prompt_phrase 粘到 prompt 里)
       │
       ▼
KSampler ──► VAE Decode ──► Save Image
```

## 许可

MIT
