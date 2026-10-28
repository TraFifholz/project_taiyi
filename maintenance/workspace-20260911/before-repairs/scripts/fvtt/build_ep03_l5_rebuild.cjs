#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const out = path.join(root, 'records/prep/ep03-fvtt-20260903/rebuild-ma-xia-l5');
const before = JSON.parse(fs.readFileSync(path.join(out, 'server-before.json'), 'utf8'));
const SUPER = 'swade-supers-companion.superPower';
const id = key => crypto.createHash('sha256').update('taiyi-ep03-l5:' + key).digest('hex').slice(0, 16);
const clone = value => JSON.parse(JSON.stringify(value));
const p = value => '<p>' + String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;') + '</p>';
const canonical = value => JSON.stringify(value, (_k, v) => v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.entries(v).sort(([a], [b]) => a.localeCompare(b))) : v);
const keys = ['agility', 'smarts', 'spirit', 'strength', 'vigor'];
const skills = {athletics:['运动','agility'],fighting:['格斗','agility'],shooting:['射击','agility'],notice:['察觉','smarts'],stealth:['潜行','agility'],persuasion:['交涉','spirit'],'common-knowledge':['通用知识','smarts'],driving:['驾驶','agility'],focus:['集中','spirit'],repair:['修理','smarts'],intimidation:['威吓','spirit']};
const core = ['athletics','notice','stealth','persuasion','common-knowledge'];
const change = (key, value, type = 'add') => ({key, value, type, phase:'initial', priority:null});
const edgeDefinitions = {
  alertness:['警觉','人类初始专长。察觉 +2，已计入。',[change('@Skill{察觉}[system.die.modifier]',2)]],
  block:['招架','第4次升级。行家、格斗d8；格挡 +1，已计入。敌人针对你的围攻加值减少1。',[change('system.stats.parry.value',1)]],
  'combat-reflexes':['战斗反应','第5次升级。行家；从动摇、震慑恢复的投骰 +2，已计入。',[change('system.attributes.spirit.unShakeBonus',2),change('system.attributes.vigor.unStunBonus',2)]],
  brawler:['搏击手','人类初始专长。力量d8、活力d8；坚韧 +1，已计入。拳脚伤害d4，与武术家合并后成为d6。',[change('system.stats.toughness.value',1)]],
  'martial-artist':['武术家','第1次升级。格斗d6；拳脚视为天生武器，拳脚攻击 +1，已计入拳脚条目；与搏击手合并，拳脚基础伤害为力量+d6。',[]],
  'iron-jaw':['头铁','第4次升级。活力d8；化解 +2，已计入。抵抗昏厥打击的活力投骰另加2。',[change('system.attributes.vigor.soakBonus',2)]],
  'nerves-of-steel':['钢铁神经','第5次升级。活力d8；忽略1点损伤减值，已计入。',[change('system.wounds.ignored',1)]]
};
const definitions = [
  {key:'ma-tieying',name:'马铁鹰',actorId:'7aQZVS47M2oWodIk',npcId:'LS-NPC-067',budget:24,
    initialAttributes:[6,4,6,8,6],hindranceAttribute:'vigor',humanEdge:'brawler',
    initialSkills:{athletics:8,fighting:8,shooting:6,notice:4,stealth:4,persuasion:4,'common-knowledge':4,intimidation:6,driving:6},
    advances:[{type:0,edge:'martial-artist',text:'武术家；拳脚成为天生武器，拳脚攻击+1，与搏击手合并为力量+d6。'},{type:3,attribute:'agility',text:'灵巧 d6 → d8；入门位阶唯一一次属性提升。'},{type:1,skills:['fighting'],text:'格斗 d8 → d10；此时格斗等于关联灵巧，消耗整次升级。'},{type:0,edge:'iron-jaw',text:'头铁；活力d8，化解+2。'},{type:0,edge:'nerves-of-steel',text:'钢铁神经；活力d8，忽略1点损伤减值。'}],
    powers:[
      {slot:'super-skill',swid:'melee-attack',name:'近战攻击 · 破门重拳',cost:8,level:2,damage:'@str+2d6',text:'近战伤害+2d6（4点）＋粉碎（3点）＋劲力（1点）＝8点。额外2d6应用到全部武装及徒手格斗伤害，已合入拳脚与破拆锤，不要再加一次。每回合可宣告一次粉碎，忽略该击对无生命物件或载具的护甲，并使自己脆弱至下回合结束；不能借此忽略人员护甲。实际形成击退时，距离再+1d6，不是每次命中自动击退。拳脚是力量+d6+2d6，含搏击手与武术家的合并伤害。特效为力量运用与破拆技法。'},
      {slot:'super-attribute-strength',swid:'super-attribute-strength',name:'超级属性 · 力量',cost:4,level:2,text:'力量提升两级：普通构筑d8 → d12，已自动计入。表现为极端体能与长期重体力训练；本卡不新增觉醒事件。',changes:[change('system.attributes.strength.die.sides',4)]},
      {slot:'toughness',swid:'toughness',name:'坚韧 · 抗打躯体',cost:5,level:5,text:'坚韧+5，已计入。此值不是护甲，不受穿甲削减；未另购护甲奇能。',changes:[change('system.stats.toughness.value',5)]},
      {slot:'super-edge',swid:'hardy',name:'顽强',cost:2,level:1,text:'已动摇时，另一次仅造成动摇的伤害结果不会额外造成损伤。正常优良伤害仍会造成损伤。原生SWADE hardy标记已启用。'},
      {slot:'super-attribute-vigor',swid:'pace',name:'移速 · 登车步法',cost:3,level:1,text:'移速2点＋神行客1点：地面移速6 → 8，奔跑d6 → d8，已自动计入；忽略困难地形。跳上车身仍须满足距离、接触与正常检定，不获得免费跳帮动作。',changes:[change('system.pace.ground',2),change('system.pace.running.die',2)]},
      {slot:null,swid:'parry',name:'格挡 · 贴身架势',cost:2,level:2,text:'格挡+2，已自动计入；用于贴身架开武器，不增加反击或主动行动。',changes:[change('system.stats.parry.value',2)]}
    ],
    expected:{attributes:{agility:8,smarts:4,spirit:6,strength:12,vigor:8},parry:9,toughness:14,armor:2,pace:8,running:8,soak:2,woundsIgnored:1,hardy:true},
    weaponChanges:{'ep03-fists':{name:'拳脚 · 破门重拳',damage:'@str+d6+2d6',ap:0,traitMod:'+1'},'ep03-hammer':{name:'短柄破拆锤',damage:'@str+d6+2d6',ap:0,traitMod:''}},
    note:'5级按入门建卡后5次升级计算，位阶为行家。24奇术点单独记账；超级技能0，超级专长0。普通技能池13点（12基础+1负赘），人类专长为搏击手。原有重大贪婪与轻微固执共3点：2点提升活力，1点增补技能池。力量奇能与武艺只是本场机械构筑，不改既有未觉醒身份。'
  },
  {key:'xia-mangong',name:'夏满弓',actorId:'WLZGos0f2rJ17PVL',npcId:'LS-NPC-051',budget:18,
    initialAttributes:[8,6,6,4,6],hindranceAttribute:'vigor',humanEdge:'alertness',
    initialSkills:{athletics:6,fighting:6,shooting:6,notice:8,stealth:6,persuasion:4,'common-knowledge':6,driving:4,focus:4,repair:4},
    advances:[{type:3,attribute:'strength',text:'力量 d4 → d6；入门位阶唯一一次属性提升。'},{type:2,skills:['fighting','driving'],text:'格斗 d6 → d8、驾驶 d4 → d6；两者原骰阶都低于灵巧d8。'},{type:2,skills:['focus','persuasion'],text:'集中 d4 → d6、交涉 d4 → d6；两者原骰阶都低于心魂d6。'},{type:0,edge:'block',text:'招架；达到行家且格斗d8，格挡+1。'},{type:0,edge:'combat-reflexes',text:'战斗反应；行家，从动摇与震慑恢复+2。'}],
    powers:[
      {slot:'special-blindspot',swid:'special-blindspot',name:'盲区感',cost:2,level:1,text:'保留既有2点本场特殊构筑。花一个动作，感到长期巡逻辖区最可能被突破的一处盲区；只给入口选择，仍须亲自换位防守。不能知道闯入者、时间或目的，陌生辖区无效；不获得完整预知、扫描或自动识破潜伏。'},
      {slot:'super-edge',swid:'parry',name:'格挡 · 拱卫一方',cost:5,level:3,text:'格挡+3（3点）＋拱卫一方（2点）＝5点。+3已计入自己的格挡。可用自由动作把其中1—3点转交邻接盟友；转交多少，自己就暂时减少多少，不复制加值，也不能转交招架专长的+1。此分配由GM手动调整，离开邻接或撤回时恢复。',changes:[change('system.stats.parry.value',3)]},
      {slot:'super-attribute-smarts',swid:'dodge',name:'躲闪 · 护卫一隅',cost:4,level:2,text:'直接远程攻击减值-2（2点）＋中型爆发盖板护卫一隅（2点）＝4点。以自身为中心的中型爆发范围内，盟友也受此防护；不降低范围攻击伤害。不与自己重复计两份。表现为近身护卫、借掩体与及时提醒，非新增读心或弹道预知。对来袭射击／投掷的-2由GM手动计入，尚未安装目标端自动光环。'},
      {slot:'uncanny-reflexes',swid:'uncanny-reflexes',name:'离奇反射',cost:3,level:1,text:'回避时忽略通常的-2灵巧减值；原本不可回避的范围攻击可以按-2尝试回避；扔回手雷的运动减值减少2。条件性调整手动处理，不增加行动次数。'},
      {slot:'super-skill',swid:'melee-attack',name:'近战攻击 · 贴身截击',cost:4,level:2,damage:'@str+2d6',text:'近战伤害+2d6，4点，已合入电击棍伤害：力量+d4+2d6。表现为贴身截击与关节打击，不改变盲区感的情报边界。电击棍仍按非致命伤害处理，不免费施加震慑。'}
    ],
    expected:{attributes:{agility:8,smarts:6,spirit:6,strength:6,vigor:8},parry:10,toughness:8,armor:2,pace:6,running:6,soak:0,woundsIgnored:0,hardy:false},
    weaponChanges:{'ep03-baton':{name:'电击棍 · 贴身截击',damage:'@str+d4+2d6',ap:0,traitMod:''}},
    note:'5级按入门建卡后5次升级计算，位阶为行家。18奇术点单独记账；超级技能0，超级专长0，也未购买超级属性。普通技能池13点（12基础+1负赘），人类专长为警觉。原有重大职责与轻微贪财共3点：2点提升活力，1点增补技能池。新防守条目表现为护卫训练与反应，盲区感的情报范围不扩大。'
  }
];
function newItem(owner, key, name, type, system) {
  return {_id:id(owner+':'+key),name,type,img:type===SUPER?'modules/swade-supers-companion/assets/icons/Supers_Icons_Power.webp':'systems/swade/assets/icons/'+type+'.svg',system,effects:[],flags:{world:{taiyiEp03:{key:owner+':'+key,version:2}}}};
}
function replaceEffects(item, changes) {
  // Update existing effect documents in place. No permanent deletions.
  // Retired effect slots become inert receipts, with every old change removed.
  const oldEffects = item.effects || [];
  if (changes.length) {
    const effect = oldEffects[0] || {_id:id(item._id+':effect'),type:'base',transfer:true,flags:{}};
    Object.assign(effect,{name:item.name,disabled:false,transfer:true,system:{...effect.system,changes}});
    item.effects=[effect,...oldEffects.slice(1).map(e=>({...e,name:'旧版停用记录',disabled:true,system:{...e.system,changes:[]}}))];
  } else item.effects=oldEffects.map(e=>({...e,name:'说明项（无自动数值）',disabled:true,system:{...e.system,changes:[]}}));
}
const manifest={version:2,world:'taiyi',system:'swade',levelDefinition:'入门建卡后5次升级；行家位阶',actors:[]};
for(const n of definitions) {
  const old=before.actors.find(a=>a._id===n.actorId);
  assert(old && old.name===n.name && old.flags?.world?.taiyiNpc?.id===n.npcId,'Identity mismatch');
  assert.equal(old.type,'npc');
  const data=clone(old), items=data.items;
  const attrs=Object.fromEntries(keys.map((k,i)=>[k,n.initialAttributes[i]]));
  assert.equal(Object.values(attrs).reduce((sum,v)=>sum+(v-4)/2,0),5,'Initial attribute points');
  attrs[n.hindranceAttribute]+=2;
  let skillCost=0;
  for(const [k,v] of Object.entries(n.initialSkills)) {
    let current=core.includes(k)?4:2;
    while(current<v){current+=2;skillCost+=current<=attrs[skills[k][1]]?1:2;}
  }
  assert.equal(skillCost,13,n.name+' skill budget');
  assert(core.every(k=>k in n.initialSkills));
  const finalSkills=clone(n.initialSkills), ordinaryEdges=[n.humanEdge];
  const attrAdvancesByRank={};
  n.advances.forEach((a,i)=>{
    const rank=Math.floor((i+1)/4);
    if(a.attribute){attrAdvancesByRank[rank]=(attrAdvancesByRank[rank]||0)+1;assert(attrAdvancesByRank[rank]<=1);attrs[a.attribute]+=2;}
    if(a.skills){
      if(a.type===2){assert.equal(a.skills.length,2);for(const k of a.skills)assert(finalSkills[k]<attrs[skills[k][1]],n.name+' two-skill advance');}
      else {assert.equal(a.skills.length,1);assert(finalSkills[a.skills[0]]>=attrs[skills[a.skills[0]][1]]);}
      for(const k of a.skills)finalSkills[k]+=2;
    }
    if(a.edge){
      if(['block','combat-reflexes'].includes(a.edge))assert(i+1>=4);
      if(a.edge==='block')assert(finalSkills.fighting>=8);
      if(a.edge==='martial-artist')assert(finalSkills.fighting>=6);
      if(['iron-jaw','nerves-of-steel'].includes(a.edge))assert(attrs.vigor>=8);
      ordinaryEdges.push(a.edge);
    }
  });
  if(n.humanEdge==='brawler')assert(n.initialAttributes[3]>=8&&n.initialAttributes[4]+2>=8);
  const oldPowerIds=new Set(items.filter(i=>i.type===SUPER).map(i=>i._id));
  for(const power of n.powers) {
    let item=power.slot?items.find(i=>i.type===SUPER&&i.system.swid===power.slot):null;
    if(power.slot)assert(item,n.name+' missing power slot '+power.slot);
    if(!item){item=newItem(n.key,'power:'+power.swid,power.name,SUPER,{});items.push(item);}
    oldPowerIds.delete(item._id);
    item.name=power.name;
    Object.assign(item.system,{swid:power.swid,description:p(power.text),source:'龙散战记 · EP03 5级重车',trapping:n.name==='马铁鹰'?'身体素质、武艺与登车步法；不新增觉醒事件':'烛龙眼盲区感与近身护卫训练',favorite:true,level:power.level,build:{cost:power.cost,level:power.level,limit:n.budget/3},damage:power.damage||'',ap:0,actions:{trait:power.damage?'格斗':'',traitMod:'',dmgMod:'',additional:{}}});
    replaceEffects(item,power.changes||[]);
  }
  assert.equal(oldPowerIds.size,0,'Unconverted old power');
  for(const [k,v] of Object.entries(finalSkills)) {
    let item=items.find(i=>i.type==='skill'&&i.system.swid===k);
    if(!item){item=newItem(n.key,'skill:'+k,skills[k][0],'skill',{});items.push(item);}
    Object.assign(item.system,{swid:k,attribute:skills[k][1],die:{sides:v,modifier:0},'wild-die':{sides:6},isCoreSkill:core.includes(k)});
  }
  assert(items.filter(i=>i.type==='skill').every(i=>i.system.swid in finalSkills));
  const oldEdges=items.filter(i=>i.type==='edge'), used=new Set();
  for(const key of ordinaryEdges) {
    let item=oldEdges.find(i=>i.system.swid===key&&!used.has(i._id));
    if(!item)item=oldEdges.find(i=>!ordinaryEdges.includes(i.system.swid)&&!used.has(i._id));
    const [name,description,changes]=edgeDefinitions[key];
    if(!item){item=newItem(n.key,'edge:'+key,name,'edge',{});items.push(item);}
    used.add(item._id);item.name=name;Object.assign(item.system,{swid:key,description:p(description),source:'普通建卡／5次升级，不消耗奇术点'});replaceEffects(item,changes);
  }
  assert(oldEdges.every(i=>used.has(i._id)),'Unconverted old edge');
  for(const [swid,w] of Object.entries(n.weaponChanges)) {
    const item=items.find(i=>i.type==='weapon'&&i.system.swid===swid);assert(item,'Missing weapon');
    item.name=w.name;Object.assign(item.system,{damage:w.damage,ap:w.ap});item.system.actions.traitMod=w.traitMod;
    item.system.description+=p('5级重车：近战攻击的额外2d6已经合入此伤害；不可重复叠加。'+(swid==='ep03-fists'?'武术家攻击+1已计入，视为天生武器。':''));
  }
  for(const [k,v] of Object.entries(attrs))data.system.attributes[k].die={sides:v,modifier:0};
  data.system.advances={mode:'expanded',value:5,rank:'Seasoned',details:p(n.note),list:n.advances.map((a,i)=>({id:id(n.key+':advance:'+i).slice(0,8),type:a.type,sort:i+1,planned:false,notes:p(a.text)}))};
  data.system.details.notes=old.system.details.notes+p('【5级重车】'+n.note)+p(n.name==='马铁鹰'?'粉碎会使自己脆弱至下回合结束；只忽略物件/载具护甲。顽强不抵消优良伤害。':'格挡转交、护卫一隅的射击/投掷-2、回避调整由GM按情境结算；没有自动给盟友加第二份数值。');
  data.flags.world.taiyiEp03={...data.flags.world.taiyiEp03,version:2,budget:n.budget,powerLimit:n.budget/3};
  data.flags.world.taiyiL5={version:1,advances:5,budget:n.budget,ordinaryEdges,initialAttributePoints:5,initialSkillPoints:13,hindrancePoints:3,superSkillCount:0,superEdgeCount:0};
  if(n.name==='马铁鹰'){data.flags.swade??={};data.flags.swade.hardy=true;}
  assert.equal(n.powers.reduce((sum,x)=>sum+x.cost,0),n.budget);
  assert(n.powers.every(x=>x.cost<=n.budget/3));
  assert(items.filter(i=>i.type===SUPER).every(i=>!['super-skill','super-edge','skill-bonus'].includes(i.system.swid)));
  for(const oldItem of old.items)assert(items.some(i=>i._id===oldItem._id),'No item deletion');
  const expected={...n.expected,advances:5,powerCount:n.powers.length,spent:n.budget,skills:Object.fromEntries(Object.entries(finalSkills).map(([k,v])=>[k,{sides:v,modifier:k==='notice'&&n.humanEdge==='alertness'?2:0}]))};
  manifest.actors.push({key:n.key,name:n.name,npcId:n.npcId,budget:n.budget,cap:n.budget/3,beforeCanonical:canonical(old),data,expected,powerLedger:n.powers.map(x=>({name:x.name,cost:x.cost,description:x.text})),buildLedger:{initialAttributes:n.initialAttributes,hindrance:'3点：活力升一级（2点）＋1技能点',initialSkills:n.initialSkills,skillCost,humanEdge:n.humanEdge,advances:n.advances,ordinaryEdges}});
}
fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2));
const report=['# 马铁鹰与夏满弓 · 5级重车','', '等级口径：入门建卡后5次升级，位阶为行家；不是5次购买奇能，也不是5个数据因子。','', '原有头像、立绘、人物ID、关系、权限、装备弹药与伤势保留。全部旧Item原位改写，不删除；旧效果槽若无用途则清空变更并停用。', '',...manifest.actors.flatMap(s=>['## '+s.name,'','普通建卡：5属性点、13技能点（12+1），3负赘点。人类专长：'+edgeDefinitions[s.buildLedger.humanEdge][0]+'。','',...s.buildLedger.advances.map((a,i)=>(i+1)+'. '+a.text),'','奇术点：'+s.powerLedger.map(x=>x.name+' '+x.cost).join(' + ')+' = '+s.budget+'；单项上限 '+s.cap+'。','',...s.powerLedger.map(x=>'- '+x.name+'：'+x.description),'','预期：格挡 '+s.expected.parry+'；坚韧 '+s.expected.toughness+'（护甲 '+s.expected.armor+'）；移速 '+s.expected.pace+'，奔跑d'+s.expected.running+'。','','超级技能：0；超级专长：0。普通专长由人类与升级获得。',''])];
fs.writeFileSync(path.join(out,'重车说明.md'),report.join('\n'));
console.log(JSON.stringify({actors:manifest.actors.map(s=>({name:s.name,advances:5,spent:s.budget,powers:s.expected.powerCount,parry:s.expected.parry,toughness:s.expected.toughness,items:s.data.items.length})),buildLedgerPassed:true,noItemDeletion:true},null,2));
