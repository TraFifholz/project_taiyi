"""Start four independent AGY conversations, one per event, via local Clash."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import datetime
import json
import os
import subprocess

root = Path(r'D:\Project Taiyi')
base = root / 'campaign/prep/agy/event-expansion-20260911'
logs = root / 'maintenance/agy-20260911/four-events'
base.mkdir(parents=True, exist_ok=True)
logs.mkdir(parents=True, exist_ok=True)
source = (root / 'campaign/prep/sessions/ep03尾声-ep04-流程与事件卡.md').read_text(encoding='utf-8')
shared = '''用户要求：每个事件卡交给一个独立 AGY 会话分别扩写，主会话负责检查衔接和连接；事件前后每个各写5个事项，每个1句话，包括传言、可能发生的事情、NPC现状等。

你是四个独立 AGY 会话之一，只负责下方指定的一张卡，其他卡由另外会话扩写。请把这张卡写成主持人拿来能推进的完整事件：约数小时的连续行动，含地形怎么相连、敌人如何行动和变招、玩家可改变什么、胜利所得、逃脱或提前取胜怎样继续；扩充具体事件，不重复空泛设计原则。参考篇幅约2000—3500汉字，必要时稍长。少抒情、少官话，不写大量无关道具。碰头的地点/怎么见/说什么几句即可。不要硬塞调查解密链。无需给精细规则数值，有限敌人编组、明显破绽与战术足够。

卡首“## 事件前五项”及卡尾“## 事件后五项”各列恰好5条编号事项，每条恰好一句话；传言标明传言，条件结果用如果/若，不把可选战果写成必然已发生。正文不能只有概要或评审意见。

既定龙骨不可改：A追风外包队为劫案猎杀欲子，连续作战中偶遇梁，梁瘫痪一台追风自走机；A只露本领/权限，不露高管职位，更不露梁是方的间接上游。B方借公权力围捕李好，何凌直接给方购买失踪服务、前辈被害和地下灾备厅的黑料；方是凶恶觉醒者，B提前露面及护他的超级特工。C方袭击义胜盟，PC与帮派反打车场换重装备与支援。D多种方法攻灾备厅，救人、打垮觉醒者方；上级特工先护方受他使唤，败局后灭口、撤离，留下未解上游。梁的真实善意、何凌参与及义胜盟作用保留。犯罪事实只能使官方不再保护方，不能取代武力。不要把幕后梁洗白或让玩家看到采购关系。

衔接约定：默认A-B-C-D，但A/B可互换，C可跳过，B追方可直达D；若未遇梁，技术型PC可先做技术任务，不让人凭空入队。D若未跑B先展示特工护主。伤势、俘虏、损坏机器、夺来的车辆和已知情报跨卡延续，不复活不刷新。C拿下车场则其人手不给D新增；未打掉的车场守军才可能赶来。不要提前把固定终局写在B完成，也不要靠无敌免伤硬保方；接近终局时可直接连接D的战斗。事件时长是桌上预计，不是剧情里精确固定钟点。

第三话已实跑结束、劫匣交密钥、司机468300退款、十人离城；欲子尾款34830待补结，不重复发。旧SUV坏了不能直接开。剩余3休整回合先结算，第四话从已宣布5/14之后继续。老周/码头派单人/赵明芝/另一司机均已死，不拿来做新活人求救任务。白念秋最后到管委会已知，不重新解锁。何凌变猫与过目不忘，不随手给空间传送等新能力。

文风与规则：只有利益和武力能撬动对手，打架优先，允许突然事件和巧合，不需要给每次袭击编完整侦察链；但角色身份、空间衔接、死亡和已得战果不能乱。玩家不必经历固定失败才能见梁，不强制耗尽弹药，不禁潜入，不让NPC一键赢。方念动掀抛/拖拽/压制，特工短距位移与精确射击；具体能力强度仍由现用规则决定。D方死且特工撤离是既定结尾，不能许诺可以永久活捉后再暗改；也不能顺带抹掉玩家成功带出的资料。技术型PC可以接替NPC关键操作。

文件背景可读 campaign/prep/sessions/ep03尾声-ep04-流程与事件卡.md、ep04-已出场NPC反应表.md、records/memory/session-12.md、campaign/npcs/stories/ 下相关人物。主会话正在维护其他卡和连接稿，所以你的创作文件使用下述专属路径，避免改其他卡/索引/正式人物史。旧文件内与本输入冲突的废稿不是定案。
'''
names = {'A': 'PMC猎杀欲子', 'B': '管委会围捕李好', 'C': '义胜盟开战', 'D': '灾备厅决战'}
for key, name in names.items():
    start = source.index('## ' + key + '｜')
    end = source.find('\n## ', start + 4)
    card = source[start:end if end >= 0 else len(source)]
    output = f'campaign/prep/agy/event-expansion-20260911/{key}-{name}-AGY原稿.md'
    prompt = shared + f'\n本会话负责事件{key}：{name}。\n请将完整扩写正文保存为 {output}，最终回复说明保存位置即可。\n\n原卡如下：\n\n' + card
    (base / f'{key}-input.md').write_text(prompt, encoding='utf-8')

def run(key):
    env = os.environ.copy()
    proxy = 'http://127.0.0.1:7890'
    for name in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'):
        env[name] = proxy
    env['NO_PROXY'] = env['no_proxy'] = 'localhost,127.0.0.1,::1'
    prompt = (base / f'{key}-input.md').read_text(encoding='utf-8')
    args = [r'D:\Tools\agy\agy.exe', '--model','gemini-3.1-pro-high', '--effort','high',
            '--mode','accept-edits','--dangerously-skip-permissions',
            '--output-format','stream-json','--print-timeout','30m','-p',prompt]
    meta = {'event':key, 'proxy':proxy, 'new_conversation':True,
            'started_at':datetime.datetime.now().astimezone().isoformat()}
    with (logs / f'{key}.ndjson').open('wb') as stdout, (logs / f'{key}.stderr.log').open('wb') as stderr:
        proc = subprocess.Popen(args,cwd=root,env=env,stdout=stdout,stderr=stderr,creationflags=subprocess.CREATE_NO_WINDOW)
        meta['pid'] = proc.pid
        (logs / f'{key}.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
        print(json.dumps({'event':key,'pid':proc.pid,'status':'running'}),flush=True)
        meta['exit_code'] = proc.wait()
    for line in (logs / f'{key}.ndjson').read_text(encoding='utf-8',errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get('event') == 'result':
            result = event['result']
            meta['conversation_id'] = result.get('conversation_id')
            meta['status'] = result.get('status')
            (logs / f'{key}-response.txt').write_text(result.get('response',''),encoding='utf-8')
    meta['ended_at'] = datetime.datetime.now().astimezone().isoformat()
    (logs / f'{key}.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    return meta

if __name__ == '__main__':
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for completed in as_completed([pool.submit(run,key) for key in names]):
            result = completed.result()
            results.append(result)
            print(json.dumps(result),flush=True)
    (logs / 'manifest.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
