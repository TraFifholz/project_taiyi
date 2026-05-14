const fs = require('fs');

const newHindrances = [
  {
    name: '多情 Amorous',
    type: '次要负赘 Minor',
    text: `这个角色容易被浪漫情愫冲昏头脑。在涉及对其有吸引力的NPC时，角色的察觉以及与专注相关的特性投骰遭受-1。GM可以援引此负赘，迫使角色在关键时刻因为感情纠葛而分心，或是在不理智的时刻追求感情目标。`,
    after: '一窍不通 All Thumbs'
  },
  {
    name: '失忆 Amnesia',
    type: '次要负赘 Minor 或 主要负赘 Major',
    text: `这名角色罹患失忆，记不起生涯中的部分或全部记忆。这可能归因于一次意外、药物测试、企业安保程序的后遗症，或是遭到敌对势力绑架成为了潜伏特工。

若是次要负赘，角色只会失去一部分记忆（数天、数月乃至数年），失落时光的后果由GM决定。

若属于主要负赘，那角色的过去就是一张白纸。其无法选择任何与过往经历相关的背景专长，且通用知识投骰-1。GM可以随着游戏的推进逐步揭示角色过去的碎片。`,
    after: '多情 Amorous'
  },
  {
    name: '双相情感障碍 Bipolar',
    type: '次要负赘 Minor 或 主要负赘 Major',
    text: `角色患有双相情感障碍，在躁狂与抑郁的极端情绪间摇摆。

若是次要负赘，选择其中一种状态（躁狂或抑郁），角色在游戏中会周期性地进入该状态。

• 躁狂期：心魂投骰+1，但察觉投骰-2，且容易做出冲动鲁莽的决策。
• 抑郁期：心魂投骰-2，且所有基于力量和活力的特性投骰-1。

若为主要负赘，角色会在躁狂与抑郁两种状态间周期性转换（GM决定转换时机，通常每次游戏一次），承受两种状态的完整效果。`,
    after: '大嘴巴 Big Mouth'
  },
  {
    name: '合群 Conformist',
    type: '次要负赘 Minor',
    text: `角色有强烈的从众需求，渴望被群体接纳。威吓投骰遭受-2。当团队做出决定时，角色即便内心有不同意见也会随大流——无法成为那个唱反调的人。在需要坚持己见或反对群体的场合，GM可以判定角色的心魂投骰有-2减值。`,
    after: '荣耀信条 Code of Honor'
  },
  {
    name: '依存性人格 Dependent',
    type: '次要负赘 Minor 或 主要负赘 Major',
    text: `角色对他人的依赖远超正常范畴。

若是次要负赘，角色极端依附于某个特定人物（伴侣、导师、密友等）。当该人物不在场时，角色的所有特性投骰遭受-1。

若为主要负赘，角色几乎无法独立行事。独处时所有特性投骰-2，且GM可能判定角色在没有依赖对象陪伴的情况下陷入犹豫不决或恐慌。依赖对象若死亡或永久离开，此负赘会转化为同级的其他精神负赘（如恐惧症或意志消沉），由GM决定。`,
    after: '妄想 Delusional'
  },
  {
    name: '蒙羞 Disgraced',
    type: '次要负赘 Minor',
    text: `角色曾经做过一个错误的决定，或是犯下错误导致被先前的公司或组织开除。这可能是在云梦科技、重黎工业、引资银行等机构留下污点，也可能意味着在天穹信用系统中留有不良记录。

与来自相同行业或背景的人员接触时，交涉投骰-1。知道角色底细的人可能对其投以异样的眼光，或在关键时刻旧事重提。`,
    after: '依存性人格 Dependent'
  },
  {
    name: '极端政治光谱 Extreme Politics',
    type: '次要负赘 Minor',
    text: `角色持有极为激进的政治立场——无论是在企业自由主义、AI管控主义、劳工运动还是其他意识形态光谱的末端。在与持相反政治观点的对象交涉时，投骰遭受-2。此外，这种极端立场可能会被TAIYI的社会监测系统标记，吸引不必要的注意。`,
    after: '夙敌 Enemy'
  },
  {
    name: 'LPI公民 Limited Permission',
    type: '次要负赘 Minor',
    text: `角色持有限制权限识别码（LPI），安全信息评级仅为2级。龙散市内部分绿区、重点医疗设施、优质公共资源对其大门紧闭。与公职人员、企业HR或高信用评级对象交涉时投骰-1。通过某些城区的地铁闸口可能需要绕道或额外盘查。

角色在创建时，额外的起始资金减半（不计负赘点带来的资金加成）。`,
    after: '嫉妒 Jealous'
  },
  {
    name: '新兵 New Recruit',
    type: '次要负赘 Minor',
    text: `角色在当前的生存环境中没有任何实战经验，身边的人都称其为"新手"或是菜鸟。通用知识投骰遭受-2。角色不能具备与其核心生存领域（街头、企业、地下等）相关的背景专长。

在角色达到行家位阶后，玩家可以在得到GM同意的前提下使用一次升格来移除此负赘。`,
    after: '默言 Mute'
  },
  {
    name: '强迫症 Obsessive-Compulsive',
    type: '次要负赘 Minor',
    text: `角色有强迫性思维或行为模式——可能表现为反复检查、计数、对称摆放、清洁仪式或其他重复性行为。当角色的常规或秩序感被严重打乱时（由GM判断），所有特性投骰遭受-1，直到其能花至少10分钟恢复秩序或完成仪式为止。

在战斗或高压环境下，角色仍会被强迫性冲动干扰，但无法停下来完成仪式——这会导致其陷入分神状态。`,
    after: '义务 Obligation'
  },
  {
    name: '傀儡 Puppet',
    type: '次要负赘 Minor 或 主要负赘 Major',
    text: `这名角色对某名强大人物有所亏负——企业高管、帮派头目、情报掮客，或是在天穹系统中握有角色把柄的人。对方可以操纵角色，对其下达指令。

根据GM的判断，角色可能会在任务期间或日常生活中的任何时刻收到帮忙做事的要求。负赘的等级代表了这位傀儡主子的影响力有多大，以及这个人情有多深重。

若是角色拒绝履行人情，则傀儡负赘会转化为同级的夙敌负赘——那个曾经的"主子"不会善罢甘休。`,
    after: '贫穷 Poverty'
  },
  {
    name: '实名上网 Real Name Online',
    type: '次要负赘 Minor',
    text: `角色的所有网络活动都与其真实身份牢牢绑定——也许是因为天穹钱包的实名认证过于彻底，也许是其曾经的身份信息已被公开。

任何试图隐藏身份的网络行动，包括骇客、利用假身份交涉、匿名购买敏感物品等，均遭受-2减值。TAIYI及企业安防系统可以轻易追溯其数字足迹，角色无法有效"抹除行踪"。`,
    after: '怪癖 Quirk'
  },
  {
    name: '亚文化爱好者 Subculture Enthusiast',
    type: '次要负赘 Minor',
    text: `角色深度沉浸于某种主流社会难以理解或排斥的亚文化中——《妖刃计划》死忠粉、旧城探险者、地下义体改装圈、骇客集会常客，或任何在龙散市主流眼光中"不太正常"的圈子。

与主流社会人士交涉时投骰-1（对方觉得角色"怪"或不可靠），但与同圈子亚文化成员交涉时投骰+1。角色在亚文化相关的通用知识投骰上获得+2。`,
    after: '顽固 Stubborn'
  },
  {
    name: '软脚虾 Tenderfoot',
    type: '主要负赘 Major',
    text: `角色对疼痛和伤害的承受力极差。小小的割伤和擦伤都会让他痛不欲生。

只要角色身上有至少一个损伤，他的所有特性投骰都会遭受额外的-1惩罚（叠加在损伤本身的效果之上）。这意味着即使只有一个损伤，其总减值也比正常情况更重。`,
    after: '多疑 Suspicious'
  },
  {
    name: '大扫把星 Trouble Magnet',
    type: '次要负赘 Minor 或 主要负赘 Major',
    text: `对这个角色来说，事情从来不是一帆风顺的。

若是次要负赘，每当角色掷出大失败时，后果在某种程度上会比正常情况更加恶化，由GM裁定。此外，大失败的攻击投骰也会导致角色的武器被破坏或卡壳（如果有此可能的话）。

若为主要负赘，额外增加以下效果：每当GM需要选择一个"随机角色"来承受攻击、意外流弹、突如其来的厄运或其他负面事件时——这个倒霉鬼就是这个角色的不二人选。`,
    after: '拙舌 Tongue-Tied'
  },
];

const file = 'src/核心规则/负赘.md';
let content = fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n');

function findSectionEnd(content, sectionHeadingName) {
  // Find the start of the named section
  const headingMarker = '## ' + sectionHeadingName;
  const startIdx = content.indexOf(headingMarker);
  if (startIdx === -1) return -1;

  // Find the closing --- that ends this section
  // It should be the next --- on its own line after the heading
  const afterHeading = content.indexOf('\n---\n', startIdx);
  if (afterHeading === -1) return -1;

  // Make sure there's no other ## between the heading and this ---
  // (in case the --- is from an inner table or the next section)
  const nextHeading = content.indexOf('\n## ', startIdx + headingMarker.length);
  if (nextHeading !== -1 && nextHeading < afterHeading) {
    // There's another heading before the ---, so find the --- before that heading
    const beforeNext = content.lastIndexOf('\n---\n', nextHeading);
    return beforeNext + 5; // after the \n---\n
  }

  return afterHeading + 5; // position after \n---\n
}

// Process in reverse order to avoid position shifts
for (const h of newHindrances.reverse()) {
  const insertAt = findSectionEnd(content, h.after);
  if (insertAt === -1) {
    console.log('WARNING: Could not find section: ' + h.after);
    continue;
  }

  const typeLine = '_' + h.type + '_';
  const body = h.text.replace(/\n/g, '\n\n');
  const entry = '\n## ' + h.name + '\n\n' + typeLine + '  \n\n' + body + '  \n\n---\n';

  content = content.slice(0, insertAt) + entry + content.slice(insertAt);
  console.log('Inserted: ' + h.name + ' after ' + h.after);
}

fs.writeFileSync(file, content, 'utf8');
console.log('\nDone. Added ' + newHindrances.length + ' new hindrances.');
