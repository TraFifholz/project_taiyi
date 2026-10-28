import { StylishShopApp } from './apps/StylishShopApp.js';

const MODULE_ID = 'smartphone-shop-app';

Hooks.once('init', () => {
    // 쇼핑 앱 테마 설정 (설정 앱 '앱 테마' 메뉴에서 선택)
    game.settings.register(MODULE_ID, 'shopTheme', {
        name: 'Shop App Theme',
        scope: 'world',
        config: false,
        type: String,
        default: 'light',
        onChange: (value) => StylishShopApp.applyThemeToOpenInstance(value)
    });

    game.settings.register(MODULE_ID, 'storefrontName', {
        name: 'SMARTPHONE.apps.stylishshop.settings.storefrontName',
        hint: 'SMARTPHONE.apps.stylishshop.settings.storefrontNameHint',
        scope: 'world',
        config: false,
        restricted: true,
        type: String,
        default: 'SUPPLYNET',
        onChange: () => StylishShopApp.applyStorefrontBrandingToOpenInstance()
    });

    game.settings.register(MODULE_ID, 'storefrontIconMode', {
        name: 'SMARTPHONE.apps.stylishshop.settings.storefrontIcon',
        scope: 'world',
        config: false,
        restricted: true,
        type: String,
        default: 'default',
        onChange: () => StylishShopApp.applyStorefrontBrandingToOpenInstance()
    });

    game.settings.register(MODULE_ID, 'storefrontIconClass', {
        name: 'SMARTPHONE.apps.stylishshop.settings.iconClass',
        scope: 'world',
        config: false,
        restricted: true,
        type: String,
        default: 'fas fa-bag-shopping',
        onChange: () => StylishShopApp.applyStorefrontBrandingToOpenInstance()
    });

    game.settings.register(MODULE_ID, 'storefrontIconImage', {
        name: 'SMARTPHONE.apps.stylishshop.settings.iconImage',
        scope: 'world',
        config: false,
        restricted: true,
        type: String,
        default: '',
        onChange: () => StylishShopApp.applyStorefrontBrandingToOpenInstance()
    });
});

// 'setup' 훅을 사용하여 코어 모듈의 API가 준비된 후 앱을 등록합니다.
Hooks.once('setup', () => {
    const smartphoneApi = game.modules.get('smartphone-widget')?.api;

    if (!smartphoneApi || typeof smartphoneApi.registerApp !== 'function') {
        console.error("Smartphone Shop App | Smartphone Widget API not found. App not registered.");
        return;
    }
    if (!game.modules.get('stylish-shop')?.active) {
        console.warn("Smartphone Shop App | Stylish Shop is not active. App not registered.");
        return;
    }

    console.log("Smartphone Shop App | Registering with Smartphone Widget API...");
    smartphoneApi.registerApp({
        id: 'stylishshop',
        name: game.i18n.localize("SMARTPHONE.apps.stylishshop.title"),
        icon: StylishShopApp.launcherIcon,
        color: '#18b3d8',
        category: 'shopping',
        appClass: StylishShopApp
    });

    // 설정 앱 '앱 테마' 메뉴에 쇼핑 앱 테마 항목 등록 (smartphone-widget 2.2.7+)
    if (typeof smartphoneApi.registerAppTheme === 'function') {
        smartphoneApi.registerAppTheme({
            id: 'stylishshop',
            label: 'SMARTPHONE.apps.stylishshop.themes.menuLabel',
            icon: 'fas fa-bag-shopping',
            namespace: MODULE_ID,
            settingKey: 'shopTheme',
            choices: [
                { id: 'terminal', label: 'SMARTPHONE.apps.stylishshop.themes.terminal' },
                { id: 'light', label: 'SMARTPHONE.apps.stylishshop.themes.light' },
                { id: 'ember', label: 'SMARTPHONE.apps.stylishshop.themes.ember' }
            ]
        });
    } else {
        console.warn("Smartphone Shop App | registerAppTheme API not found. Update smartphone-widget to pick themes from the Settings app.");
    }
});

// Stylish Shop이 카탈로그 API를 제공하는 버전(1.7.0+)인지 확인합니다.
Hooks.once('ready', () => {
    if (!game.modules.get('stylish-shop')?.active) return;
    const shopApi = game.modules.get('stylish-shop')?.api;
    if (!shopApi || typeof shopApi.getShopDirectory !== 'function') {
        console.error("Smartphone Shop App | Stylish Shop catalog API not found. Update stylish-shop to 1.7.0 or newer.");
        ui.notifications?.error(game.i18n.localize("SMARTPHONE.apps.stylishshop.errors.apiMissing"));
    }
});
