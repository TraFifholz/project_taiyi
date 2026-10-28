# FVTT Smartphone / Chirp CDP 操作指南

用途：给后续 agent 说明如何通过 Chrome DevTools Protocol 登录 Foundry VTT，并更新 `smartphone-chirp-app` 的 Chirp 内容。

当前推荐脚本：

- `scripts/fvtt/cdp_session04_import.cjs`
- 默认读取 `records/prep/session-04-foundry-prep.json`
- 默认目标 `https://fvtt.univare.icu/game`

## 快速命令

不要把账号密码写进文件。只在当前 PowerShell 会话里设置环境变量：

```powershell
$env:FVTT_USER='AssistantAgent'
$env:FVTT_PASSWORD='<password>'
$env:FVTT_URL='https://fvtt.univare.icu/game'
```

先只读检查：

```powershell
node scripts\fvtt\cdp_session04_import.cjs --inspect
```

写入并立刻验证：

```powershell
node scripts\fvtt\cdp_session04_import.cjs --write
```

独立读回验证：

```powershell
node scripts\fvtt\cdp_session04_import.cjs --verify
```

## CDP 登录流程

脚本会做这些事：

1. 尝试连接 `http://127.0.0.1:9223/json/version`。
2. 如果没有可用 CDP，就启动独立 Chrome：
   - `--remote-debugging-port=9223`
   - `--user-data-dir=%TEMP%\codex-cdp-taiyi-fvtt`
   - 打开 `FVTT_URL`
3. 找到 `fvtt.univare.icu` 的页面 WebSocket。
4. 通过 CDP `Runtime.evaluate` 操作页面。
5. 如果在 Foundry join screen，就选择 `FVTT_USER`、填写 `FVTT_PASSWORD`、提交表单。
6. 等待 `game.ready === true`。
7. 继续等待目标模块完成注册：
   - `smartphone-chirp-app.chirp-accounts`
   - `CONFIG.JournalEntryPage.dataModels["calendaria.calendarnote"]`
   - `swade-StylishActionHud-integration` active

注意：Foundry ready 不代表模块设置已经注册完。直接 `game.settings.get("smartphone-chirp-app", "chirp-accounts")` 可能会报 setting 未注册，所以必须等待。

## Chirp 数据实际写在哪里

`smartphone-chirp-app` 不把 Chirp 内容写成 Actor、Item 或 Journal。它使用 world settings：

```js
game.settings.get("smartphone-chirp-app", "chirp-accounts")
game.settings.get("smartphone-chirp-app", "chirp-posts")
game.settings.get("smartphone-chirp-app", "chirp-trends")
game.settings.get("smartphone-chirp-app", "chirp-dms")
```

写入时使用：

```js
await game.settings.set("smartphone-chirp-app", "chirp-accounts", accounts);
await game.settings.set("smartphone-chirp-app", "chirp-posts", posts);
await game.settings.set("smartphone-chirp-app", "chirp-trends", trends);
await game.settings.set("smartphone-chirp-app", "chirp-dms", dms);
```

不要直接改 Foundry world 数据库文件。

## 本项目的数据约定

导入源是 `records/prep/session-04-foundry-prep.json`：

- `chirpAccounts`
- `chirpTrends`
- `chirpPosts`
- `directMessages`

脚本使用稳定 ID，方便重跑：

- 账号 `socialId`: `taiyi_s4_<handle>`
- 帖子 `id`: `taiyi_s4_chirp_01`、`taiyi_s4_chirp_02` ...
- 私信 key: `taiyi_s4_dm_<n>_<receiver>`

重跑前会清理旧的 `taiyi_s4_*` Chirp 数据，再按当前 JSON 重建。这样本地稿件删除某个账号或帖子后，FVTT 里的旧内容也会被删掉。

## Chirp 对象形状

账号大致形状：

```js
{
  socialId,
  ownerActorId: null,
  handle,
  name,
  bio,
  location,
  website: "",
  joinedDate: "May 2030",
  profilePal: ["#color1", "#color2"],
  bannerColor: "#color",
  verified,
  followers: [],
  following: [],
  fakeFollowers,
  fakeFollowing,
  chirpIds: []
}
```

帖子大致形状：

```js
{
  id,
  authorSocialId,
  content,
  media: [],
  timestamp,       // 毫秒时间戳
  likes: [],
  rechirps: [],
  bookmarks: [],
  replies: [],
  replyTo: null,
  quoteChirpId: null,
  poll: null,
  pinned: false,
  isHidden: false,
  publishTimestamp: null,
  fakeLikes,
  fakeRechirps,
  fakeBookmarks,
  fakeReplies
}
```

趋势大致形状：

```js
{ cat, name, count, purpose }
```

私信大致形状：

```js
{
  id,
  fromSocialId,
  text,
  timestamp
}
```

## 验证标准

`--verify` 至少要确认：

- Chirp 设置已注册：`settingsReady === true`
- `accountsFound === accountsExpected`
- `postsFound === postsExpected`
- `trendsFound === trendsExpected`
- `dmsFound === dmsExpected`
- 特定禁用/撤回内容不存在时，加入针对性断言

例：撤掉 `@anonymous_dog` 后，脚本验证：

```js
forbiddenAnonymousDog.accountExists === false
forbiddenAnonymousDog.postCount === 0
```

## 重要坑点

1. Foundry flag scope 必须是 active package。
   - 不要用随手起的 flag scope，例如 `taiyi-prep`。
   - 当前脚本用 active 模块 `swade-StylishActionHud-integration`。

2. `game.ready` 不等于模块可写。
   - 等 `game.settings.settings.has("smartphone-chirp-app.chirp-accounts")`。

3. 玩家可见 Chirp 不要承载 GM 剧透。
   - 账号简介尤其显眼，不要写“谜底解释”或“彩蛋说明”。
   - 线索应放在 Journal/手牌里，由 GM 控制何时给玩家。

4. 用稳定 ID 保持幂等。
   - 新内容用固定前缀。
   - 重跑前清理旧前缀数据。
   - 否则会出现删除了本地稿但 FVTT 旧数据残留的问题。

5. 不要把密码写进脚本、Markdown、JSON。
   - 通过环境变量传入。
   - 终端历史里也尽量避免真实长期密码。

6. 不要直接编辑 world 数据库。
   - 通过浏览器内 `game.settings.set` 写入，走 Foundry 正常保存路径。

## 最小手动 CDP 片段

如果不使用现成脚本，核心浏览器内逻辑是：

```js
const moduleId = "smartphone-chirp-app";

const accounts = foundry.utils.deepClone(game.settings.get(moduleId, "chirp-accounts") || {});
const posts = foundry.utils.deepClone(game.settings.get(moduleId, "chirp-posts") || {});
const trends = foundry.utils.deepClone(game.settings.get(moduleId, "chirp-trends") || []);
const dms = foundry.utils.deepClone(game.settings.get(moduleId, "chirp-dms") || {});

// 修改 accounts/posts/trends/dms...

await game.settings.set(moduleId, "chirp-accounts", accounts);
await game.settings.set(moduleId, "chirp-posts", posts);
await game.settings.set(moduleId, "chirp-trends", trends);
await game.settings.set(moduleId, "chirp-dms", dms);
```

执行前先确认：

```js
game.user.isGM
game.modules.get("smartphone-chirp-app")?.active
game.settings.settings.has("smartphone-chirp-app.chirp-accounts")
```

## 内容准则

Chirp 是玩家手机界面，默认当作玩家会直接阅读的公开内容：

- 可以放街面传闻、营销、公共公告、角色口吻。
- 可以放假线索，但不能替 GM 揭示谜底。
- 账号 bio 应像真实账号简介，不要解释“这是某条线索的彩蛋”。
- 真线索、解释、幕后机制放 Journal 或 GM-only 手牌。
