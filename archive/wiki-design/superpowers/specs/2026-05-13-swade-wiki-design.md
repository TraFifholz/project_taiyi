# SWADE Wiki Design

## Summary

将 Tiddlywiki.json（560条SWADE核心规则条目，TiddlyWiki Text格式）一次性转为 Markdown，后续以 Markdown 维护，通过 VitePress 部署到 GitHub Pages。

## Data: Tiddlywiki.json

- 560 entries, all under `核心规则` namespace
- 3-level hierarchy: `核心规则/大类/子页`
- Fields: `title`, `text`, `中文名`, `英文名`, `created`, `modified`
- Content: TiddlyWiki Text with HTML divs, `[[links]]`, `<<mylist>>` macros, wiki markup

## Tech Stack

-  **VitePress**  — static site generator, Markdown-based, built-in sidebar/nav/search/dark mode
-  **Node.js convert script**  — one-shot JSON to Markdown
-  **GitHub Actions**  — CI build and deploy to GitHub Pages
-  **Markdown**  — ongoing content maintenance format

## Directory Structure

```
d:\Project Taiyi\
├── src/                        # Wiki content (Markdown)
│   ├── index.md               # Homepage
│   └── 核心规则/
│       ├── index.md
│       ├── 介绍.md
│       ├── 角色/
│       │   ├── index.md
│       │   ├── 特性.md
│       │   ├── 族裔/
│       │   │   ├── index.md
│       │   │   └── ...
│       │   ├── 负赘/
│       │   └── 专长/
│       └── ...
├── .vitepress/
│   └── config.js              # Sidebar config, nav, theme settings
├── scripts/
│   └── convert.js             # One-shot conversion script
├── package.json
└── .github/workflows/
    └── deploy.yml
```

## Conversion Rules

| TiddlyWiki | Markdown |
|------------|----------|
| `<div class="statblock">` + `</div>` | Removed (content kept) |
| `!!! Title` | `## Title` |
| `!! Title` | `### Title` |
| `''text''` | ` **text** ` |
| `* list item` | `- list item` |
| `[[display\|path]]` | `[display](./path.md)` |
| `[[path]]` | `[path](./path.md)` |
| `<<<` (quote blocks) | `>` (blockquote) |
| `<<mylist "filter">>` | Placeholder comment `<!-- TODO: mylist filter -->` (manual fix, 20 occurrences) |

- Entry `title` → file path: `核心规则/专长/战斗` → `核心规则/专长/战斗.md`
- Directories get auto-generated `index.md` with child page listing
- Frontmatter added to each page with `title`, `中文名`, `英文名`

## Sidebar

Auto-generated from directory structure, config written by convert script to `.vitepress/config.js`. Manual tuning over time.

## Deployment

GitHub Actions: push to main → `npm ci` → `npm run build` → deploy `src/.vitepress/dist` to `gh-pages` branch.

## What's Out of Scope

- Online editing (static read-only)
- Full-text search — VitePress built-in, no extra work
- `<<mylist>>` macros — 20 instances left as manual TODO
