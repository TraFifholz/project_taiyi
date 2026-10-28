# Smartphone 首轮更新（2026-09-03）

已部署到个人服务器 taiyi 世界，使用已授权的 AssistantAgent。

## 已完成

- 修复状态栏时钟：原版冷启动停在 00:00，手动刷新后为 22:28；补丁持续刷新并监听 smartphoneTimeChanged。重新加载页面后已自动显示 **22:28**，确认加载的是补丁代码。
- 默认开放手机商城 stylishshop、浏览器 browserapp，并加入可用应用列表。已有每部手机的自选安装列表保持一致。
- 增加 22 个中文应用名，保留已有自定义名称。Chirp 保留原品牌名。
- 新建 browserapp 日志（SgsIhS7xmowgyUjA）：城市索引、城区速查、机构名录、地铁图，共 4 页。内容精简自玩家 Wiki，不添加剧情消息。六个普通玩家账号均通过 OBSERVER 权限检查。
- 上传现有地铁 SVG；浏览器实际解码尺寸 1293 × 959。
- 验证页面点击、文星搜索；最终结果为「longsan.city/districts城区与地点」，搜索框提示为「搜索城区、机构」。

## 保留待核对

8 条 S4 旧 Chirp 私信的虚构发送者及会话键尚未迁移，旧帖日期也未批量更改。旧私信含过期剧情草稿，未将它们投递为玩家的新消息。世界时间保持 1904509738（日历 2030-05-08 22:28）。

未执行购买、扣款、转账或场景移动。商城美术和手机商城的进一步外观验收由独立任务 01a06576-ff82-7a81-bf4c-a63836367484 继续；已关闭本任务浏览器并交回账号。

## 验证与文件

- 独立时钟测试覆盖日历延迟就绪、即时事件刷新、12/24 小时制、现实时间、重复启动和关闭清理。原版在延迟就绪检查失败，补丁通过。
- HTTP 和 SSH 确认补丁与地铁图哈希；浏览器重载核对补丁和实际时钟。
- 对比更新前后世界时间、逐手机 installed-apps、Chirp 帖子 ID 和私信键，均一致。未对完整消息正文做哈希比较。
- 界面遮挡来自 Calendaria 浮窗；移动测试手机后页面点击成功，未修改应用启动逻辑。移动仅影响测试窗口。
- 页面已实测 GM 会话；普通玩家权限通过文档权限 API 核对，未代登录玩家。

实现文件：D:/Project Taiyi/scripts/fvtt/smartphone-20260903/（WidgetClock.js、test-clock.cjs、configure-runtime.js、polish-browser-runtime.js）。

证据：settings-before.json、configured.json、cold-start.json、verified.json、browser-polish.json、browser-after.png。

本次没有修改 Wiki 正文、未提交 Git。原有不相关工作区改动保持不变。

## 恢复位置

服务器原时钟备份：C:/foundryvtt/Backups/taiyi-smartphone-20260903/WidgetClock.before.js。当前目标：C:/foundryvtt/Data/modules/smartphone-widget/scripts/core/widget/WidgetClock.js。

原文件 SHA256：3A54E462BF0497A6AA22E554EBFE611A9E795A9BACFFE12DE2DB9DA23186F7AF。
补丁 SHA256：F1BB763679286C86016146308D08B5982259D1C636CF16AFC4716F27CBD3A6BD。
地铁图 SHA256：41FA82D6CF408827F663B636ED056F39684D8CBB7C631B39F49878ED3A095CDA。

这是 Smartphone Widget 2.3.4 的局部源码修复。以后升级此模块时应核对上游是否已修复，否则更新可能覆盖补丁。手机设置可从 settings-before.json 按键恢复；新日志有 world.taiyiPhoneDirectory=20260903 标记。
