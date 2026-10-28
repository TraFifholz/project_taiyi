#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const ROOT = path.resolve(__dirname, '../..');
const OUT = path.join(ROOT, 'records/prep/ep03-fvtt-20260903');
const SOURCE = 'records/prep/ep03-追风大劫案-module.md';
const SCOPE = 'world';
const TAG = 'taiyiEp03';
const SUPER = 'swade-supers-companion.superPower';
const id = key => crypto.createHash('sha256').update('taiyi-ep03-20260903:'+key).digest('hex').slice(0,16);
const esc = s => String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const p = s => `<p>${esc(s)}</p>`;
const flag = key => ({[SCOPE]:{[TAG]:{key,version:1}}});
const attrs = ['agility','smarts','spirit','strength','vigor'];
const skills = {
  athletics:['运动','agility'], fighting:['格斗','agility'], shooting:['射击','agility'],
  notice:['察觉','smarts'], driving:['驾驶','agility'], persuasion:['交涉','spirit'],
  repair:['修理','smarts'], stealth:['潜行','agility'], intimidation:['威吓','spirit'],
  occult:['神秘学','smarts'], focus:['集中','spirit'], research:['调查','smarts'],
  electronics:['电子学','smarts'], healing:['医疗','smarts'], 'common-knowledge':['通用知识','smarts'],
  hacking:['骇客','smarts']
};
const change = (key,value,type='add') => ({key,value,type,phase:'initial',priority:null});
const skillKey = (key,field) => `@Skill{${skills[key][0]}}[system.die.${field}]`;
function effect(key,name,changes) {
  return {_id:id('effect:'+key),name,type:'base',transfer:true,disabled:false,system:{changes},flags:flag(key)};
}
function item(key,name,type,system={},changes=[]) {
  return {_id:id('item:'+key),name,type,img:type===SUPER?'modules/swade-supers-companion/assets/icons/Supers_Icons_Power.webp':`systems/swade/assets/icons/${type==='skill'?'skill':type}.svg`,system:{description:'',source:'龙散战记 · EP03 本场构筑',...system},effects:changes.length?[effect(key,name,changes)]:[],flags:flag(key)};
}
const edgeRules = {
  alertness:['警觉','察觉投骰 +2（已自动计入）。',[],{notice:2}],
  block:['招架','格挡 +1（已自动计入）；敌人针对你的围攻加值减少 1，交战时手动处理。',[change('system.stats.parry.value',1)]],
  'combat-reflexes':['战斗反应','从动摇与震慑中恢复的投骰 +2（已自动计入）。',[change('system.attributes.spirit.unShakeBonus',2),change('system.attributes.vigor.unStunBonus',2)]],
  'level-headed':['沉稳冷静','本组抽两张行动卡择一；不增加行动组数量或行动次数。',[change('system.initiative.hasLevelHeaded',true,'override')]],
  command:['指挥','5 英寸内龙套盟友从动摇恢复的心魂、从震慑恢复的活力投骰 +1。范围与盟友加值手动结算，不给队员额外行动。'],
  brawler:['搏击手','坚韧 +1（已计入）；拳脚造成力量+d4，另有徒手攻击条目。',[change('system.stats.toughness.value',1)]],
  'iron-jaw':['头铁','化解投骰 +2（已自动计入）；抵抗昏厥打击的活力投骰 +2。',[change('system.attributes.vigor.soakBonus',2)]],
  'nerves-of-steel':['钢铁神经','忽略 1 点损伤减值（已自动计入）。',[change('system.wounds.ignored',1)]],
  'strong-willed':['坚强意志','抵抗基于聪慧或心魂的考验 +2；仅在相应抵抗时手动加值。'],
  ace:['王牌机师','花费助力点，以驾驶代替活力化解自己操作车辆的损伤，每次成功与优良抵消 1 损伤。'],
  acrobat:['特技员','平衡、翻滚或擒抱的运动投骰可免费重投一次；不适用于攀爬、投掷或打断行动。'],
  investigator:['调查员','查文件、邮件、垃圾与残骸时，调查与察觉 +2；条件性加值，不自动用于所有察觉。'],
  'mr-fix-it':['修理先生','修理 +2（已自动计入）；优良将修理时间减半。',[],{repair:2}]
};
function power(key,name,cost,family,description,changes=[],extra={}) {
  return {key,name,cost,family,description,changes,...extra};
}
const superSkills = distribution => power('skills','超级技能',Object.values(distribution).reduce((a,b)=>a+b,0),'super-skill',Object.entries(distribution).map(([k,v])=>`${skills[k][0]}提升${v}级`).join('；')+'。骰阶由效果自动计入。',Object.entries(distribution).map(([k,v])=>change(skillKey(k,'sides'),2*v)),{skillSteps:distribution});
const superAttr = (key,steps) => power('attr-'+key,'超级属性·'+({agility:'灵巧',smarts:'聪慧',spirit:'心魂',strength:'力量',vigor:'活力'}[key]),steps*2,'super-attribute-'+key,`该属性提升 ${steps} 级，已由效果自动计入。`,[change(`system.attributes.${key}.die.sides`,steps*2)],{attributeSteps:{[key]:steps}});
const superEdges = names => power('edges','超级专长',names.length*2,'super-edge',names.map(k=>edgeRules[k][0]).join('、')+'；各专长另列，效果只计算一次。',[],{edges:names});
const toughness = n => power('toughness','坚韧',n,'toughness',`坚韧 +${n}，不是护甲，穿甲不削减此加值。`,[change('system.stats.toughness.value',n)],{toughness:n});
const bonus = (key,value) => power('bonus-'+key,'技能加值·'+skills[key][0],value===1?2:4,'skill-bonus',`${skills[key][0]}投骰 +${value}，已自动计入。`,[change(skillKey(key,'modifier'),value)],{skillBonus:{[key]:value}});
const reflexes = () => power('reflexes','离奇反射',3,'uncanny-reflexes','回避时忽略通常的 −2 灵巧减值；原本不可回避的范围攻击可按 −2 尝试回避。扔回手雷的运动减值减少 2。按情境手动选择回避，不增加主动行动。');
const pistol = {key:'pistol',name:'手枪',damage:'2d6',range:'12/24/48',shots:12};
const baton = {key:'baton',name:'电击棍',damage:'@str+d4',melee:true,nonlethal:true};
const smg = {key:'smg',name:'消音冲锋枪',damage:'2d6',range:'12/24/48',ap:1,shots:30,rof:3};
const qingAction='与辛桦、闻笙及两名队员共一张行动卡；全组每轮合计一次调位、跳帮、援助、救援、考验或攻击。必要驾驶按模组处理。';
const maAction='与司机共一张卡；每轮最多一次攻击、考验、跳帮、夺人、夺车或搬箱，必要驾驶另算；司机不另加火力。';
const convoyAction='与交管7号车队共一张卡；每轮只选一项系统行动或夏满弓的一项主动行动，无人机也从这同一额度支出。';
const cleanupAction='罗恺与四名清理员共一张卡；每轮全组最多一次拆除贡献与两次战斗行动。追逐中默认单发；车身连接、舱内或架稳后才可用射速3。';
const named = [
 {key:'xia-mangong',name:'夏满弓',npcId:'LS-NPC-051',budget:18,school:'烛龙眼；盲区感',role:'M-3 随车安保／近身阻拦',base:[8,6,6,6,8],baseSkills:{athletics:6,fighting:4,shooting:6,notice:6,driving:6,persuasion:6,repair:6,stealth:4},armor:2,
  powers:[power('blindspot','盲区感',2,'special-blindspot','本场特殊构筑，费用2点。花一个动作，感到长期巡逻辖区内最可能被突破的一处盲区，须亲自换位防守。只给入口选择，不揭示闯入者、时间与目的；陌生辖区无效，不自动识破潜伏或既成预埋接口。此为既有能力的局部规则化，不使用完整版扫描或预知。',[],{manual:true}),superSkills({athletics:1,fighting:2,notice:1,driving:1}),superEdges(['alertness','block','combat-reflexes']),superAttr('smarts',1),reflexes()],
  weapons:[pistol,baton],gear:['轻型护甲','安全绳','短距通话设备'],hindrances:[['职责（重大）','保住审计员、匣体和交接记录。'],['贪财（轻微）','出售自己能控制的便利；不会为收钱牺牲乘员。']],action:convoyAction,
  tactics:'先挡接线者、护住审计员；马铁鹰挟人夺车时优先对付马。只有对方使用致命武力或直接威胁乘员才拔枪。救人、保签章并交涉成功可谈一次接管+1，仍需累计3点。被绕过不清空接管进度。',knowledge:'只知道本次任务、岗哨与亲眼见闻；不知预制案情、付款链与零号库历史。'},
 {key:'wen-sheng',name:'闻笙',npcId:'LS-NPC-N3',budget:15,school:'烛龙眼；余响测定',role:'青梢队测量者／救援支援',base:[8,6,6,4,6],baseSkills:{athletics:6,notice:6,occult:4,stealth:8,fighting:4,shooting:4,persuasion:4,repair:6,focus:6},armor:1,
  powers:[power('echo','余响测定',1,'scan','扫描2点，重大限制−2，费用最低1点。只检视眼前实际可接近的人、物与已取得记录的余纹，比较强弱、新旧和大致来向；不采用一英里／深度扫描范围，不购校准、寻踪。每次检视占一动作。连续使用引起偏头痛、失色或短时失明；强源可过载，具体由现场情境判断。无法读心、回放历史、定位未知Z-0、判定主犯或确认AI觉醒。',[],{manual:true}),superSkills({notice:2,occult:2,athletics:1}),superAttr('smarts',1),superAttr('spirit',1),superEdges(['alertness']),reflexes()],
  weapons:[pistol],gear:['内衬护甲','抓钩','安全绳','短距通话设备','余响测量工具'],hindrances:[['好奇（轻微）','希望复核异常读数，遇危险仍优先救回同伴。'],['忠诚（轻微）','不丢下跳帮队员。']],action:qingAction,
  tactics:'先观察、固定连接或救坠落者，不把金瞳与喉部义体当武器。李好可凭外貌认出棍木女，本名待她自行介绍；沿用现有Actor显示名。木签检查留到脱离火线后，原物归还。',knowledge:'只比较实际接触的余响；没有自动副本，不替PC选择交管7号的保存方案。'},
 {key:'ma-tieying',name:'马铁鹰',npcId:'LS-NPC-067',budget:24,school:'普通人；体能与极端训练的等值构筑',role:'阿奎拉家族执行人／夺车强袭',base:[8,6,8,6,6],baseSkills:{athletics:6,fighting:6,shooting:6,notice:6,intimidation:6,persuasion:6,driving:6},armor:2,
  powers:[superAttr('strength',2),superAttr('vigor',2),superSkills({fighting:2,intimidation:2,athletics:1,shooting:1}),superEdges(['brawler','iron-jaw','nerves-of-steel','strong-willed']),toughness(2)],
  weapons:[{...pistol,name:'重型手枪',damage:'2d6+1'}, {key:'hammer',name:'短柄破拆锤',damage:'@str+d6',melee:true},{key:'fists',name:'拳脚（搏击手）',damage:'@str+d4',melee:true}],gear:['轻型护甲','登车安全绳'],hindrances:[['贪婪（重大）','想省掉芯片收货款，夺车后勒索。'],['固执（轻微）','不愿当众认输，但会用货物和退路换妥协。']],action:maAction,
  tactics:'先压制守车的夏满弓，再对付拦路的辛桦或实际持货者。动作须具备同卡、接触与登车条件；一次不能同时抢人抢车搬箱。受重创、失去抢货机会或退路受阻就撤或谈。',knowledge:'明确未觉醒，不获得数据因子、能量攻击或反觉醒装备；河图手环只留作后续线索。他不知道方泰安与零号库历史。'},
 {key:'luo-kai',name:'罗恺',budget:21,school:'专业清理领队；训练等值构筑，不新增觉醒设定',role:'穗安合规设备回收主管／Z-0 拆除',base:[6,6,6,6,8],baseSkills:{athletics:6,fighting:6,shooting:6,notice:6,stealth:6,persuasion:6,repair:6,driving:6},armor:2,
  powers:[superSkills({athletics:1,fighting:1,shooting:1,notice:1,stealth:1,repair:2}),superEdges(['alertness','level-headed','command']),superAttr('smarts',1),superAttr('agility',1),toughness(1),reflexes()],
  weapons:[smg,baton],gear:['轻型护甲','拆卸遥控器','冷却箱','定向烧毁药剂（任务工具）'],hindrances:[['贪财（轻微）','以为现金可以买走PC。'],['职责（重大）','优先取走目标板、烧接口、撤离。']],action:cleanupAction,
  tactics:'首次有人认真提出钱、芯片或撤离交易时，停一轮拆除听条件。任务优先：本轮首次清理员成功援助拆除，使下一次阻止行动−1；不叠加。倒下后清理员带箱撤。',knowledge:'只知道清点-07、重建外包账户与三组路线删除任务；不知兔子洞、红皇后或白念秋。'},
 {key:'xin-hua',name:'辛桦',budget:18,school:'青梢队领队；训练等值构筑，不新增觉醒设定',role:'抢芯片／驾驶与谈判',base:[6,6,6,6,6],baseSkills:{athletics:6,fighting:6,shooting:6,notice:6,persuasion:6,driving:6,stealth:6},armor:1,
  powers:[superSkills({shooting:1,driving:2,athletics:1,persuasion:1}),superEdges(['ace','acrobat','command']),superAttr('spirit',1),superAttr('agility',1),toughness(1),bonus('persuasion',1)],weapons:[pistol],gear:['内衬护甲','抓钩枪（工具）','安全绳','短距通话设备'],hindrances:[['忠诚（重大）','尽量把四名队员全部带走。'],['准则（轻微）','不主动射击乘客；误伤后先救人。']],action:qingAction,
  tactics:'原想卖两箱芯片¥16,000。马撕约抢车后优先压制马；可用芯片归属和接回队员与PC合作。拿货后撤，只有PC保证接回跳帮成员才为闻笙多留一轮取证。',knowledge:'不知道司机退款计划和幕后指使，不解释棍木会核心秘密。'},
 {key:'zhao-mingzhi',name:'赵明芝',npcId:'LS-NPC-033',budget:15,school:'普通司机；职业训练等值构筑',role:'委托人／支援车驾驶，不上主战线',base:[8,6,6,4,6],baseSkills:{athletics:4,notice:4,driving:4,persuasion:6,repair:4,healing:4,'common-knowledge':6},armor:0,
  powers:[superSkills({driving:3,persuasion:1,notice:1}),superEdges(['ace','strong-willed']),superAttr('spirit',1),bonus('driving',2)],weapons:[],gear:['旧式手机','十七名司机封号通知与结算副本','车载急救包'],hindrances:[['忠诚（重大）','不会为自保诬指欲子；愿为其他司机留下。'],['职责（轻微）','照顾病休丈夫与互助账户。']],action:'后方联系与支援车驾驶；不额外加入默认战斗发牌。',tactics:'驾驶接应、稳定司机证词、救人和核对到账。不会命令PC杀乘客或普通司机。',knowledge:'十一年夜班经验与互助账目；知道本次真委托，不知道完整骗局。'},
 {key:'xia-lei',name:'夏磊',budget:15,school:'前调度员工；职业训练等值构筑',role:'情报源／维修与查档支援',base:[6,6,6,4,6],baseSkills:{athletics:4,notice:4,repair:4,electronics:6,research:6,persuasion:4,driving:6,'common-knowledge':6},armor:0,
  powers:[superSkills({repair:2,electronics:1,research:1,notice:1}),superEdges(['mr-fix-it','investigator']),superAttr('smarts',2),bonus('electronics',1)],weapons:[],gear:['旧调度终端','维修工具','匿名邮件原件'],hindrances:[['固执（轻微）','想证明自己不只会抱怨。'],['秘密（轻微）','起初隐瞒调度表来自匿名邮箱。']],action:'支援车内维修、核对接口与文件；不额外加入默认战斗发牌。',tactics:'匿名来源被揭穿后会留下帮忙，不逃跑；技能高不能使他提前知道骗局。',knowledge:'车队编号、维修场与结算接口；不掌握历史路线正文与上家身份。'}
];
function edgeItem(owner,key) {
  const [name,desc,changes=[],bonuses={}] = edgeRules[key];
  return item(`${owner}:edge:${key}`,name,'edge',{description:p(desc),swid:key},[...changes,...Object.entries(bonuses).map(([k,v])=>change(skillKey(k,'modifier'),v))]);
}
function weaponItem(owner,w) {
  const description=[w.nonlethal?'非致命伤害，电击不是额外的免费震慑。':'',w.rof===3?'追逐默认单发；射速3只在车身连接、舱内或武器架稳后使用，消耗正常弹药，且不突破本组行动额度。':'',w.melee?'需实际近战接触。':'使用射击投骰。'].filter(Boolean).join(' ');
  return item(`${owner}:weapon:${w.key}`,w.name,'weapon',{description:p(description),swid:'ep03-'+w.key,damage:w.damage,range:w.range||'',rangeType:w.melee?0:1,rof:w.melee?1:(w.rof||1),ap:w.ap||0,shots:w.shots||0,currentShots:w.shots||0,reloadType:w.shots?'magazine':'none',equipStatus:3,equippable:true,favorite:true,quantity:1,actions:{trait:w.melee?'格斗':'射击',traitMod:'',dmgMod:'',additional:{}},...w.system});
}
function createNpc(n) {
  const key=n.key, expectedAttrs=Object.fromEntries(attrs.map((a,i)=>[a,n.base[i]]));
  const expectedSkills=Object.fromEntries(Object.entries(n.baseSkills).map(([k,v])=>[k,{sides:v,modifier:0}]));
  let parryBonus=0,toughnessBonus=0;
  const powers=n.powers||[]; const budget=n.budget||0; const cap=Math.max(5,Math.floor(budget/3));
  assert.equal(powers.reduce((sum,x)=>sum+x.cost,0),budget,n.name+' budget');
  const grouped={}; for(const x of powers) {grouped[x.family]=(grouped[x.family]||0)+x.cost; for(const [a,v] of Object.entries(x.attributeSteps||{}))expectedAttrs[a]+=2*v; for(const [a,v] of Object.entries(x.skillSteps||{}))expectedSkills[a].sides+=2*v; for(const [a,v] of Object.entries(x.skillBonus||{}))expectedSkills[a].modifier+=v; toughnessBonus+=x.toughness||0; for(const ed of x.edges||[]) {if(ed==='block')parryBonus++; if(ed==='brawler')toughnessBonus++;for(const [a,v] of Object.entries(edgeRules[ed][3]||{}))expectedSkills[a].modifier+=v;} }
  for(const [group,total] of Object.entries(grouped))assert(total<=cap,n.name+' grouped cap '+group);
  for(const v of Object.values(expectedAttrs))assert(v>=4&&v<=12);
  for(const v of Object.values(expectedSkills))assert(v.sides>=4&&v.sides<=12);
  const allEdges=powers.flatMap(x=>x.edges||[]);
  if(allEdges.includes('ace'))assert(expectedAttrs.agility>=8);
  if(allEdges.includes('acrobat'))assert(expectedAttrs.agility>=8&&expectedSkills.athletics.sides>=8);
  if(allEdges.includes('block'))assert(expectedSkills.fighting.sides>=8);
  if(allEdges.includes('level-headed'))assert(expectedAttrs.smarts>=8);
  if(allEdges.includes('brawler'))assert(expectedAttrs.strength>=8&&expectedAttrs.vigor>=8);
  if(allEdges.includes('iron-jaw')||allEdges.includes('nerves-of-steel'))assert(expectedAttrs.vigor>=8);
  if(allEdges.includes('strong-willed'))assert(expectedAttrs.spirit>=8);
  if(allEdges.includes('investigator'))assert(expectedAttrs.smarts>=8&&expectedSkills.research.sides>=8);
  if(allEdges.includes('mr-fix-it'))assert(expectedSkills.repair.sides>=8);
  const entries=Object.entries(n.baseSkills).map(([k,v])=>item(`${key}:skill:${k}`,skills[k][0],'skill',{swid:k,attribute:skills[k][1],die:{sides:v,modifier:0},'wild-die':{sides:6},isCoreSkill:['athletics','notice','persuasion','stealth','common-knowledge'].includes(k)}));
  for(const x of powers) {
    entries.push(item(`${key}:power:${x.key}`,x.name,SUPER,{swid:x.family,description:p(x.description),trapping:n.school,range:'',duration:'',favorite:true,level:1,build:{cost:x.cost,level:1,limit:cap},actions:{trait:'',traitMod:'',dmgMod:'',additional:{}}},x.changes));
    for(const ed of x.edges||[])entries.push(edgeItem(key,ed));
  }
  entries.push(...(n.weapons||[]).map(w=>weaponItem(key,w)));
  if(n.armor) entries.push(item(`${key}:armor`,n.armor===1?'内衬护甲':'轻型护甲','armor',{swid:'ep03-armor',armor:n.armor,equipStatus:3,equippable:true,quantity:1,locations:{torso:true,arms:true,legs:false,head:false},description:p(`护甲 +${n.armor}，已穿戴。不是重型护甲。`)}));
  for(const g of n.gear||[])if(!/护甲/.test(g))entries.push(item(`${key}:gear:${g}`,g,'gear',{quantity:1,description:p(g)}));
  for(const [name,desc] of n.hindrances||[])entries.push(item(`${key}:hindrance:${name}`,name,'hindrance',{description:p(desc),major:name.includes('重大')}));
  entries.push(item(`${key}:action-budget`,'本场行动额度','ability',{description:p(n.action||''),favorite:true}));
  if(n.special)entries.push(item(`${key}:special`,n.special[0],'ability',{description:p(n.special[1]),favorite:true}));
  const wildcard=n.wildcard??true;
  const system={attributes:Object.fromEntries(attrs.map((a,i)=>[a,{die:{sides:n.base[i],modifier:0},'wild-die':{sides:6}}])),wildcard,wounds:{value:0,max:wildcard?3:0},bennies:{value:wildcard?2:0,max:wildcard?2:0},pace:{base:n.fly?'fly':'ground',ground:6,fly:n.fly||null},stats:{size:0,toughness:{value:0,armor:0,modifier:0},parry:{value:0,modifier:0,shield:0}},details:{autoCalcToughness:true,autoCalcParry:true,parryBaseSwid:'fighting',archetype:n.role,biography:{value:p(n.role)+p(n.school||'普通龙套')},notes:p(n.action||'')+p(n.tactics||'')+p(n.knowledge||'')},powerPoints:{general:{value:0,max:0}},advances:{mode:'expanded',value:8,rank:'Veteran'}};
  const armor=n.armor||0;
  const expected={attributes:expectedAttrs,skills:expectedSkills,parry:2+Math.floor((expectedSkills.fighting?.sides||0)/2)+parryBonus,toughness:2+Math.floor(expectedAttrs.vigor/2)+armor+toughnessBonus,armor,spent:budget,wildcard,soak:allEdges.includes('iron-jaw')?2:0,woundsIgnored:allEdges.includes('nerves-of-steel')?1:0};
  const data={_id:id('actor:'+key),name:n.name,type:'npc',img:'icons/svg/mystery-man.svg',system,items:entries,effects:[],ownership:{default:0},prototypeToken:{name:n.name,actorLink:false,disposition:-1,texture:{src:'icons/svg/mystery-man.svg'},bar1:{attribute:'wounds'},bar2:{attribute:'fatigue'}},flags:flag(key)};
  return {key,name:n.name,npcId:n.npcId||null,budget,cap,role:n.role,school:n.school||'',expected,data,powerLedger:powers.map(({name,cost,family,description,skillSteps,attributeSteps,edges})=>({name,cost,family,description,skillSteps,attributeSteps,edges}))};
}
const extras=[
 {key:'cleaner',name:'合规清理员',role:'龙套模板 ×4；两名拆除、两名掩护',base:[8,6,6,6,6],baseSkills:{athletics:6,fighting:6,shooting:8,notice:6,stealth:6,repair:6,driving:6},armor:2,weapons:[smg,baton],gear:['维修工具','冷却箱背带'],wildcard:false,action:cleanupAction,tactics:'罗恺倒下后优先带箱撤离，不死战。'},
 {key:'qingshao',name:'青梢队成员',role:'龙套模板 ×2',base:[8,6,6,6,6],baseSkills:{athletics:8,fighting:6,shooting:6,notice:6,driving:6,stealth:6},armor:1,weapons:[pistol],gear:['抓钩','安全绳'],wildcard:false,action:qingAction,tactics:'搬箱、撤离与救人；不是另加两次攻击。'},
 {key:'drone',name:'追风警戒无人机',role:'龙套模板 ×2；记录与拖延',base:[8,6,6,4,6],baseSkills:{athletics:8,notice:8,shooting:6,stealth:6},armor:2,weapons:[{key:'dart',name:'电击针',damage:'2d6',range:'12/24/48',nonlethal:true}],gear:['探照灯'],fly:12,wildcard:false,action:convoyAction,tactics:'非致命电击，不追杀倒地者。飞行步调12；停机一架不等于杀死交管7号。',special:['探照灯','占车队本轮系统行动，以察觉对抗目标潜行；成功使其分神。不自动揭露所有隐形目标。']},
 {key:'ma-driver',name:'冷藏车司机',role:'龙套 ×1；只驾驶',base:[6,6,6,6,6],baseSkills:{athletics:6,notice:6,driving:6,persuasion:6},armor:0,weapons:[],wildcard:false,action:maAction,tactics:'留在驾驶室，不增加射击；车辆重创则停车、撤离或投降。'},
 {key:'auditor',name:'M-3 随车审计员',role:'无武装乘员 ×1；保护与救援目标',base:[4,6,6,4,6],baseSkills:{athletics:4,notice:6,research:6,persuasion:4,electronics:6},armor:0,weapons:[],gear:['审计终端','安全带'],wildcard:false,action:'无独立战斗行动。移动与救援按所在车厢和实际危险处理。',tactics:'留存原始操作账。被挟持不自动取消结算匣退款权限。'}
];
function vehicle(key,name,size,handling,speed,tough,armor,seats,description,drive=8) {
  return {key,name,budget:0,cap:0,role:'载具',expected:{toughness:tough,armor,wounds:4},data:{_id:id('actor:'+key),name,type:'vehicle',img:'icons/svg/wing.svg',system:{size,handling,topspeed:{value:speed,unit:'km/h'},toughness:{total:tough,armor},wounds:{value:0,max:4},crew:{required:{max:1},optional:{value:0,max:seats-1},members:[]},driver:{skill:'driving'},description:p(description)+p(`参考驾驶 d${drive}；载具不拥有独立战斗火力或额外行动卡。`),classification:'陆地载具'},items:[item(`${key}:driving`,'驾驶参考','ability',{description:p(`无人驾驶／本场驾驶参考 d${drive}。驾驶由实际驾驶角色投骰，自动驾驶用GM速查中的骰池。`)})],ownership:{default:0},prototypeToken:{name,actorLink:false,texture:{src:'icons/svg/wing.svg'},bar1:{attribute:'wounds'}},flags:flag(key)}};
}
const vehicles=[
 vehicle('m3','中继车 M-3',5,0,120,14,2,8,'默认3点接管，保留签章才能向原账户退款。常规接管不攻击设备损伤栏。若坚持破坏节点：安防d8、坚韧6、鲁棒性2、骇入难度4，仅同卡短距或物理接入。夏满弓与审计员在车内。'),
 vehicle('z0','零号库载车 Z-0',5,-1,100,16,5,6,'内舱门坚韧12(4)。摧毁本车使零号库拆除+2并危及乘员。本次最多取得事件记录、历史目录与删除哈希，不提供第四话历史路线正文。',10),
 vehicle('passenger','追风载客轿车／空诱饵车',4,1,120,10,2,4,'按12辆车实际编组复制。载客型受1损伤后，交管7号优先让其退出火线；空诱饵型不虚构乘客。'),
 vehicle('cold-truck','马铁鹰的短轴冷藏厢车',5,-1,100,12,2,8,'开局第5卡，非追风12辆编组。驾驶室马与司机；货厢最多六名PC与一冷却箱，额外伤员需腾载荷。无反觉醒设备。',6),
 vehicle('white-suv','罗恺的白色 SUV',5,0,120,12,2,5,'与Z-0同卡，开场罗恺与四名清理员均在车内。后两人进入Z-0。速度、操控、坚韧为本轮补定值；不是楚A·4B4B3CCx无人黑车。',6),
 vehicle('qing-vehicle','青梢队行动车',5,0,120,11,1,5,'开局第2卡，辛桦、闻笙与两名街面成员。四人共一个行动额度。车辆数值为本轮补定值。',10),
 vehicle('patrol-suv','欲子的退役玄盾巡逻越野车',5,1,130,13,0,8,'无牌、无侧窗，已拆防弹玻璃；绿色银色之翼车身醒目，弹孔可能致炸缸。维修成功：首次机械故障失控可重投；优良再修一次伪装或标识。此为本话预备卡，不覆盖旧面包车或任何玩家资产。',6)
];
const actors=[...named.map(createNpc),...extras.map(createNpc),...vehicles];
const before=JSON.parse(fs.readFileSync(path.join(OUT,'server-before.json'),'utf8'));
assert.equal(before.world,'taiyi'); assert.equal(before.system,'swade');
for(const a of actors) {
  const matches=before.actors.filter(x=>a.npcId?x.flags?.world?.taiyiNpc?.id===a.npcId:x.flags?.world?.taiyiEp03?.key===a.key||x.name===a.name);
  assert(matches.length<=1,`Ambiguous actor ${a.name}`);
  if(matches.length) {
    const old=matches[0]; assert.equal(old.type,a.data.type); assert.equal(old.items.length,0,`Nonempty actor needs merge review: ${a.name}`);
    a.existingId=old._id; a.data._id=old._id; a.data.name=old.name;
    a.baselineHash=crypto.createHash('sha256').update(JSON.stringify(old)).digest('hex');
    a.expectedOriginal={name:old.name,img:old.img,prototypeToken:old.prototypeToken,ownership:old.ownership,folder:old.folder,flags:old.flags};
  }
}
const gmHtml='<h1>EP03 · 追风大劫案</h1>'+p('本场已备7名具名NPC、5种龙套模板、7种载具。角色链接见下方；保留原NPC目录与人物显示名。')+
 '<h2>发牌与数量</h2><ul>'+[convoyAction,cleanupAction,qingAction,maAction,'龙套数量：清理员4、青梢队成员2、无人机2、冷藏车司机1、审计员1。赵明芝与夏磊在后方，不默认加入火线。'].map(s=>'<li>'+esc(s)+'</li>').join('')+'</ul>'+
 '<h2>时钟</h2>'+p('警戒0–6；案情定稿0–6；拆除0–4。退款正常3点（压缩版2点），必须保有完整签章。攻击程序3★毁损接管不立即支付，且启动零号库清理。')+p('拆除启动后每轮末+1；当轮成功破坏拆卸架、控制核心车、迫使罗恺自保或取得交管7号协助，停止本轮推进。多个成功不倒退。')+
 '<h2>交管7号：没有可击杀的人形身体</h2>'+p('换位：交换两枚功能标记。封路：目标驾驶−2，失败冲撞一张卡。锁车：关门窗、安全带，可用贼活／力量／骇客解除。降质：抹去影像细节，不影响已保存本地副本。保人：载客车规避退出火线，优先级最高。每轮只选其一，或由夏满弓／无人机占此额度。')+
 '<h2>构筑说明</h2>'+p('具名NPC共15–24点，已购项目总和就是构筑费用，普通SWADE奇术消耗池保持0。普通人以体能、职业训练与专長的等值方式计价，不因此成为觉醒者。盲区感为2点本场特殊构筑；余响测定为受严格限制的扫描。')+p('常驻骰阶、格挡、坚韧、警觉、修理先生、头铁与钢铁神经由活动效果计入；不得再手加一次。条件性考验／回避／指挥范围与剧情时钟由GM结算。单项上限：15点为5，18点为6，21点为7，24点为8；同类超级技能、超级专长与技能加值合并检查。')+
 '<h2>角色索引</h2>'+actors.map(a=>p(`@UUID[Actor.${a.data._id}]{${a.name}} — ${a.role}${a.budget?'；'+a.budget+'点':''}`)).join('');
const manifest={version:1,world:'taiyi',system:'swade',source:SOURCE,sourceSha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(ROOT,SOURCE))).digest('hex'),folder:{_id:id('folder'),name:'EP03 · 追风大劫案',type:'Actor',color:'#bc783c'},journal:{_id:id('journal'),name:'EP03 · 追风大劫案 · GM速查',ownership:{default:0},pages:[{_id:id('journal-page'),name:'行动与角色索引',type:'text',text:{content:gmHtml,format:1}}],flags:flag('gm-reference')},actors};
fs.mkdirSync(OUT,{recursive:true});fs.writeFileSync(path.join(OUT,'manifest.json'),JSON.stringify(manifest,null,2));
const md=['# EP03 角色与遭遇构筑','',`源稿：../ep03-追风大劫案-module.md；SHA-256 ${manifest.sourceSha256}`,'','点数为构筑点，不是消耗池。普通人的相应条目仅表现训练与体能，不新增觉醒设定。常驻数值由效果自动计入。','',...actors.flatMap(a=>[
 `## ${a.name}${a.budget?' · '+a.budget+'点':''}`,'',a.role,'',a.school||'',...(a.budget?['',`单项上限 ${a.cap}；`+a.powerLedger.map(x=>`${x.name} ${x.cost}`).join(' + ')+` = ${a.budget}`]:[]),'',`格挡 ${a.expected.parry??'—'}；坚韧 ${a.expected.toughness}（护甲 ${a.expected.armor}）。`,...(a.expected.skills?['',Object.entries(a.expected.skills).map(([k,v])=>`${skills[k][0]} d${v.sides}${v.modifier?'+'+v.modifier:''}`).join('，')]:[]),'',...((a.powerLedger||[]).flatMap(x=>[`- ${x.name}：${x.description}`])),'',`Actor ID：${a.data._id}；${a.existingId?'补全现有卡，保留身份、图像、目录与权限':'新建GM卡'}`,''])];
fs.writeFileSync(path.join(OUT,'构筑清单.md'),md.join('\n'));
console.log(JSON.stringify({actors:actors.length,named:named.length,extras:extras.length,vehicles:vehicles.length,existing:actors.filter(a=>a.existingId).map(a=>a.name),budgets:named.map(n=>[n.name,n.budget]),allBudgetsAndPrerequisitesPassed:true},null,2));
