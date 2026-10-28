/**
 * swade-StylishActionHud-main.mjs
 * Orchestrator for SWADE, Better Rolls 2, and Stylish HUD.
 * Focus: Clean names, no technical prefixes, and full automation.
 *
 * Orquestrador para SWADE, Better Rolls 2 e Stylish HUD.
 * Foco: Nomes limpos, sem prefixos técnicos e automação total.
 */

import { rollAttribute } from './swade-StylishActionHud-attributes.mjs';
import { rollSkill } from './swade-StylishActionHud-skills.mjs';
import { rollCombat } from './swade-StylishActionHud-combat.mjs';
import { SUPER_POWER_TYPE, useSuperPower } from './swade-StylishActionHud-powers.mjs';
import { useConsumable } from './swade-StylishActionHud-consumables.mjs';

// WORKAROUND: Fix for "app.element.find is not a function" error in V13
// The main Stylish Action HUD module tries to use jQuery .find() on native elements
//
// WORKAROUND: Correção para erro "app.element.find is not a function" no V13
// O módulo principal do Stylish Action HUD tenta usar jQuery .find() em elementos nativos
if (typeof HTMLElement !== "undefined" && !HTMLElement.prototype.find) {
    HTMLElement.prototype.find = function (selector) {
        return $(this).find(selector);
    };
}

// WORKAROUND: Suppresses 'message.user' deprecation warning from other modules.
// The SWADE system for v12+ uses 'message.author', but older modules (like Stylish Action HUD)
// might still access 'message.user'. This attaches the 'user' property to the message object
// before other hooks access it, preventing the SWADE compatibility getter from triggering,
// which generates the console warning.
//
// WORKAROUND: Suprime o aviso de depreciação de 'message.user' vindo de outros módulos.
// O sistema SWADE para v12+ usa 'message.author', mas módulos mais antigos (como o Stylish Action HUD)
// podem ainda acessar 'message.user'. Isso anexa a propriedade 'user' ao objeto de mensagem
// antes que outros hooks a acessem, evitando o acionamento do getter de compatibilidade do SWADE,
// que gera o aviso no console.
Hooks.on('preCreateChatMessage', (message) => {
    if (message.author && !Object.hasOwn(message, 'user')) {
        // In V13, `message.user` is a getter that logs a deprecation warning.
        // We cannot assign a value directly. Instead, we define it as a new
        // property on the instance to prevent the prototype getter from being called.
        //
        // Em V13, `message.user` é um getter que loga um aviso de depreciação.
        // Não podemos atribuir um valor diretamente. Em vez disso, definimos como uma nova
        // propriedade na instância para evitar que o getter no protótipo seja chamado.
        Object.defineProperty(message, 'user', {
            value: message.author,
            configurable: true
        });
    }
});

Hooks.on('swadeSpendBenny', (actor) => {
    game.modules.get("cinematic-cut-ins").api.play({
        "groupId": "",
        "inheritGroupTriggers": true,
        "img": actor.img,
        "theme": "brush",
        "customDuration": 3.5,
        "format": "popout",
        "hideBackground": false,
        "hideCharacter": false,
        "videoLoop": true,
        "screenPosX": 50,
        "screenPos": 50,
        "charScale": 1,
        "charOffsetX": 0,
        "charOffsetY": 0,
        "charRotation": 0,
        "charMirror": false,
        "textOffsetMode": "legacy",
        "text": "使用助力点",
        "hideMainText": false,
        "mainFontSize": 8,
        "mainOffsetX": 0,
        "mainOffsetY": 0,
        "subText": actor.name,
        "hideSubText": false,
        "subFontSize": 2,
        "subOffsetX": 0,
        "subOffsetY": 0,
        "fontFamily": "Teko",
        "fontBold": true,
        "fontItalic": false,
        "subFontFamily": "Teko",
        "subFontBold": true,
        "subFontItalic": false,
        "mainTextColor": "#ffffff",
        "subTextColor": "#000000",
        "color": "#e67f1e",
        "borderWidth": 0,
        "borderColor": "#ffffff",
        "charShadowColor": "#000000",
        "hideCharShadow": false,
        "shakeIntensity": 0,
        "dimIntensity": 0,
        "soundList": {
          "0": ""
        },
        "sfxList": {
          "0": "modules/cinematic-cut-ins/sounds/sfx_brush.mp3"
        },
        "soundVolume": 80,
        "sfxVolume": 80,
        "keepAudioPlaying": false,
        "audioOnly": false,
        "localOnly": false,
        "videoAudio": false,
        "triggers": {
          "turnStart": {
            "0": {
              "round": "",
              "presetId": "XZl7LKsY80jy5gpH",
              "macroId": ""
            }
          },
          "defaultSpellPreset": ""
        },
        "variations": [],
        "layers": [],
        "presetName": "SpendBenny",
        "id": "XM1hUOg5qper6YYm",
        "sound": "",
        "sfx": "modules/cinematic-cut-ins/sounds/sfx_brush.mp3",
        "actorId": "Actor.nJxWvLzZvBNXObjk"
      });
});

Hooks.once("stylish-action-hud.apiReady", (api) => {
    class SwadeIntegrationAdapter {
        constructor() {
            this.systemId = "swade";
        }

        /**
         * Smart Cleaning: Removes 'SWADE.' and 'Attr' prefixes only from technical keys.
         * Prevents 'Attributes' from becoming 'Ibutes'.
         *
         * Limpeza Inteligente: Remove prefixos 'SWADE.' e 'Attr' apenas de chaves técnicas.
         * Evita que a palavra 'Attributes' vire 'Ibutes'.
         */
        _cleanLabel(label, isInternalKey = false) {
            if (!label) return "";

            // If the label doesn't have the system dot (SWADE.), it's already clean.
            // Se o label não tem o ponto do sistema (SWADE.), ele já está limpo.
            if (!label.includes(".")) return label;

            // Gets only the last part after the dot (e.g. AttrAgility)
            // Pega apenas a última parte após o ponto (ex: AttrAgility)
            let clean = label.split(".").pop();

            // If it's an internal attribute key, remove the "Attr" prefix
            // Se for uma chave interna de atributo, removemos o "Attr" prefixado
            if (isInternalKey) {
                clean = clean.replace(/^Attr/, "");
            }

            // Returns capitalized (e.g. Agility)
            // Retorna capitalizado (ex: Agility)
            return clean.charAt(0).toUpperCase() + clean.slice(1);
        }

        /**
         * Gets actor stats for the HUD.
         * Supports user-configured attributes and defaults.
         *
         * Obtém estatísticas do ator para o HUD.
         * Suporta atributos configurados pelo usuário e defaults.
         */
        getStats(actor, configAttributes) {
            if (!configAttributes || configAttributes.length === 0) return [];

            // Default color mapping for fallback (Fix for gray bars)
            // Mapeamento de cores padrão para fallback (Correção para barras cinzas)
            const defaultColors = {
                "system.wounds": "#e61c34",
                "system.fatigue": "#f39c12",
                "system.bennies": "#2ecc71",
                "system.powerPoints.general": "#3498db"
            };

            return configAttributes.map((attr) => {
                const raw = foundry.utils.getProperty(actor, attr.path);
                let value = 0;
                let max = 0;

                if (typeof raw === "object" && raw !== null) {
                    value = raw.value ?? 0;
                    max = raw.max ?? 0;
                } else if (typeof raw === "number") {
                    value = raw;
                }

                // Fallback for Wounds and Fatigue Max if 0 (e.g. path pointing to .value)
                // Fallback para Max de Ferimentos e Fadiga se for 0 (ex: path apontando para .value)
                if (max === 0) {
                    // SWADE Default (4 wounds before incapacitated)
                    // Padrão SWADE (4 ferimentos antes de incapacitado)
                    if (attr.path.includes("wounds")) max = 4;
                    // SWADE Default (2 fatigue before exhausted)
                    // Padrão SWADE (2 fadiga antes de exausto)
                    if (attr.path.includes("fatigue")) max = 2;
                }

                let percent = 0;
                // Invert bar for Wounds and Fatigue (0 is full/good)
                // Inverte a barra para Ferimentos e Fadiga (0 é cheio/bom)
                if (attr.path.includes("wounds") || attr.path.includes("fatigue")) {
                    if (max > 0) {
                        percent = Math.clamp(((max - value) / max) * 100, 0, 100);
                    } else {
                        percent = value > 0 ? 0 : 100;
                    }
                } else {
                    if (max > 0) {
                        percent = Math.clamp((value / max) * 100, 0, 100);
                    }
                }

                // Robust Color Logic: Configured > Specific Default > Generic Default (PP) > Gray
                // Lógica de Cor Robusta: Configurada > Padrão Específica > Padrão Genérica (PP) > Cinza
                let color = attr.color;
                if (!color || color === "#cccccc") {
                    if (defaultColors[attr.path]) {
                        color = defaultColors[attr.path];
                    } else if (attr.path.includes("powerPoints")) {
                        color = "#3498db";
                    } else {
                        color = "#cccccc";
                    }
                }

                const stat = {
                    path: attr.path,
                    label: game.i18n.localize(attr.label),
                    color: color,
                    value: value,
                    max: max,
                    percent: percent,
                    style: attr.style || "bar",
                    subtype: "resource",
                    icon: attr.icon,
                    img: attr.img
                };

                // Adds specific icon for Bennies (Badge)
                // Adiciona ícone específico para Bennies (Badge)
                if (attr.path.includes("bennies")) {
                    if (!stat.img && !stat.icon) {
                        stat.img = "systems/swade/assets/benny.webp";
                        // Default icon for Badge
                        // Icone padrão para Badge
                        stat.icon = "fa-solid fa-bullseye";
                    }
                }

                // Adds icons for Parry and Toughness badges (inspired by D&D AC)
                // Adiciona ícones para badges de Aparar e Resistência (inspirado no AC do D&D)
                if (attr.style === 'badge' || attr.style === 'number') {
                    if (attr.path.includes("parry") && !stat.icon && !stat.img) {
                        stat.icon = "fa-solid fa-shield";
                    }
                    if (attr.path.includes("toughness") && !stat.icon && !stat.img) {
                        // Using a different icon to distinguish from Parry
                        // Usando um ícone diferente para distinguir de Parry
                        stat.icon = "fa-solid fa-shield-heart";
                    }
                }

                return stat;
            });
        }

        /**
         * REQUIRED: Gets active conditions (Shaken, Distracted, etc) for HUD display.
         * Fixes "hud.adapter.getConditions is not a function" error.
         *
         * OBRIGATÓRIO: Obtém condições ativas (Shaken, Distracted, etc) para exibição no HUD.
         * Corrige o erro "hud.adapter.getConditions is not a function".
         */
        getConditions(actor) {
            const effects = actor.temporaryEffects || [];
            return effects
                .filter(e => e.img && !e.disabled)
                .map((e) => ({
                    id: e.id || e.name,
                    src: e.img,
                    name: e.name || e.label || "未知",
                    value: null
                }));
        }

        /**
         * Checks if a stat can be rolled.
         * Required to avoid TemplateBuilder error.
         *
         * Verifica se uma estatística pode ser rolada.
         * Necessário para evitar erro no TemplateBuilder.
         */
        isStatRollable(actor, path) {
            return false;
        }

        /**
         * Executes a stat roll.
         * Fixes "hud.adapter.rollStat is not a function" error.
         *
         * Executa a rolagem de uma estatística.
         * Corrige o erro "hud.adapter.rollStat is not a function".
         */
        async rollStat(actor, path) {
            // Empty implementation to avoid crash when clicking Wounds/Fatigue.
            // Implementação vazia para evitar crash ao clicar em Ferimentos/Fadiga.
        }

        /**
         * Sidebar categories with translated and clean names.
         * Categorias laterais com nomes traduzidos e limpos.
         */
        getActionCategories() {
            // Restructured categories inspired by D&D preset for better organization.
            // Categorias reestruturadas inspiradas no preset de D&D para melhor organização.
            return [
                { id: "combat", label: "战斗", icon: "fa-solid fa-swords", type: "submenu" },
                { id: "skills", label: "特性", icon: "fa-solid fa-list", type: "submenu" },
                { id: "superpowers", label: "超能奇能", icon: "fa-solid fa-wand-magic-sparkles", type: "submenu" },
                { id: "inventory", label: "装备", icon: "fa-solid fa-box-open", type: "submenu" },
                { id: "utility", label: "通用", icon: "fa-solid fa-dice-d20", type: "submenu" }
            ];
        }

        /**
         * Populates menus with actor items.
         * Preenche os menus com itens do ator.
         */
        async getSubMenuData(actor, categoryId) {
            switch (categoryId) {
                case "combat": return this._getCombatMenu(actor);
                case "skills": return this._getSkillsMenu(actor);
                case "superpowers": return this._getSuperPowersMenu(actor);
                case "inventory": return this._getInventoryMenu(actor);
                case "utility": return this._getUtilityMenu(actor);
                default: return { title: "", items: [] };
            }
        }

        // Private methods to generate submenu data
        // Métodos privados para gerar dados de submenu

        _getCombatMenu(actor) {
            const weapons = actor.items.filter(i => i.type === 'weapon');
            const actions = actor.items.filter(i => i.type === 'action' && i.system.category === 'Situational Rules');
            return {
                title: "战斗",
                hasTabs: true,
                items: {
                    weapons: weapons.map(i => ({ id: i.id, name: i.name, img: i.img })),
                    actions: actions.map(i => ({ id: i.id, name: i.name, img: i.img })),
                },
                tabLabels: { weapons: "武器", actions: "战斗动作" }
            };
        }

        _getSkillsMenu(actor) {
            const skills = actor.items.filter(i => i.type === 'skill').sort((a, b) => a.name.localeCompare(b.name));
            const attributeLabels = {
                agility: "敏捷",
                smarts: "智慧",
                spirit: "精神",
                strength: "力量",
                vigor: "活力"
            };
            const attributes = Object.keys(actor.system.attributes).map(k => ({
                id: k,
                name: attributeLabels[k] ?? this._cleanLabel(game.i18n.localize(`SWADE.Attr${k.charAt(0).toUpperCase() + k.slice(1)}`), true),
                img: "icons/svg/dice-target.svg"
            }));
            return {
                title: "特性",
                hasTabs: true,
                items: {
                    skills: skills.map(i => ({ id: i.id, name: i.name, img: i.img })),
                    attributes: attributes
                },
                tabLabels: { skills: "技能", attributes: "属性" }
            };
        }

        _getSuperPowersMenu(actor) {
            const powers = actor.items.filter(i => i.type === SUPER_POWER_TYPE);
            return {
                title: "超能奇能",
                items: powers.map(p => ({
                    id: p.id, name: p.name, img: p.img,
                    cost: p.system.build?.cost ? `${p.system.build.cost} 点` : "",
                    description: p.system.trapping || ""
                }))
            };
        }

        _getInventoryMenu(actor) {
            const consumables = actor.items.filter(i => i.type === 'consumable');
            const gear = actor.items.filter(i => i.type === 'gear');
            const armor = actor.items.filter(i => i.type === 'armor');
            const shield = actor.items.filter(i => i.type === 'shield');
            return {
                title: "装备",
                hasTabs: true,
                items: {
                    consumables: consumables.map(i => ({ id: i.id, name: i.name, img: i.img, uses: { value: i.system.charges?.charges?.[0]?.value, max: i.system.charges?.charges?.[0]?.max } })),
                    gear: gear.map(i => ({ id: i.id, name: i.name, img: i.img })),
                    armor: armor.map(i => ({ id: i.id, name: i.name, img: i.img })),
                    shield: shield.map(i => ({ id: i.id, name: i.name, img: i.img })),
                },
                tabLabels: { consumables: "消耗品", gear: "物品", armor: "护甲", shield: "盾牌" }
            };
        }

        _getUtilityMenu(actor) {
            const items = [
                { id: 'utility-benny', name: '花费 Benny', img: 'icons/svg/coins.svg' },
                { id: 'utility-soak', name: '吸收伤害', img: 'icons/svg/degen.svg' },
                { id: 'utility-unshake', name: '摆脱动摇', img: 'icons/svg/sun.svg' },
                { id: 'utility-run', name: '奔跑', img: 'icons/svg/wingfoot.svg' }
            ];
            if (actor.system.details.conviction?.value > 0) {
                items.push({ id: 'utility-conviction', name: '使用信念', img: 'icons/svg/aura.svg' });
            }
            return { title: "通用", items: items };
        }

        /**
         * Routes click to the corresponding action or item.
         * Roteia o clique para a ação ou item correspondente.
         */
        async useItem(actor, actionId, categoryId) {
            // Route for utility actions that are not items
            // Rota para ações de utilidade que não são itens
            if (actionId.startsWith('utility-')) {
                const action = actionId.replace('utility-', '');
                switch (action) {
                    case 'benny': return actor.spendBenny();
                    case 'soak':
                        if (typeof actor.rollSoak === 'function') {
                            return actor.rollSoak();
                        }

                        // Fallback: Execute Soak manually (Spend Benny + Roll Vigor)
                        // Fallback: Executa Soak manualmente (Gasta Benny + Rola Vigor)
                        if (actor.system.bennies.value > 0) {
                            if (typeof actor.spendBenny === 'function') await actor.spendBenny();
                            else await actor.update({ "system.bennies.value": actor.system.bennies.value - 1 });

                            ChatMessage.create({ content: `${actor.name} 尝试吸收伤害！`, speaker: ChatMessage.getSpeaker({ actor }) });

                            const soakRoll = await actor.rollAttribute('vigor');
                            if (soakRoll) {
                                const total = soakRoll.total;
                                if (total >= 4) {
                                    const woundsToHeal = 1 + Math.floor((total - 4) / 4);
                                    const currentWounds = actor.system.wounds.value;
                                    if (currentWounds > 0) {
                                        const newWounds = Math.max(0, currentWounds - woundsToHeal);
                                        const healed = currentWounds - newWounds;
                                        await actor.update({ 'system.wounds.value': newWounds });
                                        ChatMessage.create({ content: `${actor.name} 吸收了 ${healed} 点伤口！`, speaker: ChatMessage.getSpeaker({ actor }) });
                                    } else {
                                        ChatMessage.create({ content: `${actor.name} 通过了吸收检定！`, speaker: ChatMessage.getSpeaker({ actor }) });
                                    }
                                }
                            }
                            return;
                        } else {
                            ui.notifications.warn(game.i18n.localize("SWADE.NoBennies") || "没有可用的 Benny！");
                        }
                        return;
                    case 'unshake':
                        const unshakeRoll = await actor.rollAttribute('spirit');
                        if (unshakeRoll) {
                            const success = unshakeRoll.total >= 4;
                            let message = success ? `${actor.name} 不再动摇！` : `${actor.name} 仍处于动摇。`;

                            if (success) {
                                // Remove Shaken status
                                // Remove o status Abalado (Shaken)
                                const shaken = actor.effects.find(e => e.statuses.has("shaken"));
                                if (shaken) await shaken.delete();
                            }
                            ChatMessage.create({ content: message, speaker: ChatMessage.getSpeaker({ actor }) });
                        }
                        return;
                    case 'run':
                        if (typeof actor.rollRunning === 'function') {
                            return actor.rollRunning();
                        }

                        // Fallback: Manual Running roll
                        // Fallback: Rolagem manual de Corrida
                        const runDie = actor.system.pace?.running?.die || 6;
                        const runMod = actor.system.pace?.running?.mod || 0;
                        let runFormula = `1d${runDie}`;
                        if (runMod !== 0) runFormula += runMod > 0 ? `+${runMod}` : `${runMod}`;

                        const runRoll = await new Roll(runFormula).evaluate();
                        return runRoll.toMessage({
                            speaker: ChatMessage.getSpeaker({ actor: actor }),
                            flavor: `${actor.name} 奔跑！`
                        });
                    case 'conviction':
                        if (actor.system.details.conviction.value > 0) {
                            await actor.update({ 'system.details.conviction.value': actor.system.details.conviction.value - 1 });
                            ChatMessage.create({ content: `${actor.name} 使用信念！`, speaker: ChatMessage.getSpeaker({ actor }) });
                        }
                        return;
                }
            }

            // Route for attribute rolls
            // Rota para rolagens de atributo
            if (Object.keys(actor.system.attributes).includes(actionId)) {
                return rollAttribute(actor, actionId);
            }

            // Route for item-based actions
            // Rota para ações baseadas em itens
            const item = actor.items.get(actionId);
            if (!item) return;

            switch (item.type) {
                case 'skill': return await rollSkill(actor, actionId);
                case 'weapon': return await rollCombat(actor, actionId);
                case SUPER_POWER_TYPE: return await useSuperPower(actor, actionId);
                case 'power': return item.show();
                case 'consumable': return await useConsumable(actor, actionId);
                default: return item.show();
            }
        }
    }

    // Registers the adapter with priority to override the default
    // Registra o adaptador com prioridade para sobrepor o padrão
    api.registerSystemAdapter("swade", SwadeIntegrationAdapter, { priority: 110 });

    // Registers default attributes (Wounds, Fatigue, Bennies)
    // Registra atributos padrão (Vida, Fadiga, Bennies)
    api.registerDefaultAttributes("swade", [
        { path: "system.wounds", label: "SWADE.Wounds", color: "#e61c34", style: "bar" },
        { path: "system.fatigue", label: "SWADE.Fatigue", color: "#f39c12", style: "bar" },
        { path: "system.bennies", label: "SWADE.Bennies", color: "#2ecc71", style: "badge" },
        { path: "system.powerPoints.general", label: "SWADE.PowerPoints", color: "#3498db", style: "bar" },
        { path: "system.stats.parry.value", label: "SWADE.Parry", style: "number", color: "#95a5a6" },
        { path: "system.stats.toughness.value", label: "SWADE.Toughness", style: "number", color: "#7f8c8d" }
    ]);

    // Registers attribute suggestions for the settings menu
    // Registra sugestões de atributos para o menu de configurações
    api.registerTrackableAttributes("swade", (context) => {
        const attributes = [];
        if (context.actor?.system) {
            // Default Resources
            // Recursos Padrão
            attributes.push({ path: "system.wounds", label: "SWADE.Wounds", color: "#e61c34" });
            attributes.push({ path: "system.fatigue", label: "SWADE.Fatigue", color: "#f39c12" });
            attributes.push({ path: "system.bennies", label: "SWADE.Bennies", color: "#2ecc71", style: "badge" });

            // Power Points (Detects all available pools: general, magic, miracles, etc)
            // Power Points (Detecta todos os pools disponíveis: general, magic, miracles, etc)
            if (context.actor.system.powerPoints) {
                for (const [key, pool] of Object.entries(context.actor.system.powerPoints)) {
                    // Safety
                    // Segurança
                    if (typeof pool !== 'object') continue;

                    let label = "SWADE.PowerPoints";
                    if (key !== "general") {
                        label += ` (${key.charAt(0).toUpperCase() + key.slice(1)})`;
                    }
                    attributes.push({ path: `system.powerPoints.${key}`, label: label, color: "#3498db" });
                }
            }

            // Useful Derived Stats
            // Estatísticas Derivadas Úteis
            attributes.push({ path: "system.stats.parry.value", label: "SWADE.Parry", color: "#95a5a6", style: "number" });
            attributes.push({ path: "system.stats.toughness.value", label: "SWADE.Toughness", color: "#7f8c8d", style: "number" });
        }
        return attributes;
    });

    console.log("SWADE HUD | Adapter finished and loaded.");
});
