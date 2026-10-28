import { BaseApp } from '../../smartphone-widget/scripts/apps/BaseApp.js';
import { SmartphoneWidget } from '../../smartphone-widget/scripts/smartphone-widget.js';
import { getRecent, getWishlist, isWished, pushRecent, removeWish, toggleWish, updateWishSnapshots, wishKey } from './wishlist.js';
import { addToCart, getCart, getCartCount, removeCartEntries, removeFromCart, setCartQty } from './cart.js';
import { getOrders, recordOrder } from './orders.js';

const APP_ID = 'stylishshop';
const MODULE_ID = 'smartphone-shop-app';
const L = 'SMARTPHONE.apps.stylishshop';
const THEME_IDS = ['terminal', 'light', 'ember'];
const ALL_SHOP_CATEGORY_ID = '__all__';
const STOREFRONT_ICON_MODES = ['default', 'fontawesome', 'image'];
const DEFAULT_STOREFRONT_ICON_CLASS = 'fas fa-bag-shopping';

function esc(str) {
    return String(str ?? '').replace(/[&<>"']/g, c => (
        { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
    ));
}

/** 상점명 등의 **강조** 표기를 데스크톱 Shop Directory와 동일하게 <strong>으로 렌더링. */
function remph(str) {
    return esc(str).replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>');
}

function loc(key) {
    return game.i18n.localize(`${L}.${key}`);
}

function locf(key, data) {
    return game.i18n.format(`${L}.${key}`, data);
}

function actorIdentityUuids(value) {
    const actor = typeof value === 'string' ? null : value;
    const uuid = typeof value === 'string' ? value : actor?.uuid;
    const identities = new Set();
    if (uuid) {
        identities.add(uuid);
        const syntheticId = uuid.match(/\.Actor\.([^.]+)$/)?.[1];
        if (syntheticId) identities.add(`Actor.${syntheticId}`);
    }
    if (actor?.baseActor?.uuid) identities.add(actor.baseActor.uuid);
    if (actor?.id) identities.add(`Actor.${actor.id}`);
    return identities;
}

function isSameActorIdentity(left, right) {
    const leftIds = actorIdentityUuids(left);
    const rightIds = actorIdentityUuids(right);
    return Array.from(leftIds).some(uuid => rightIds.has(uuid));
}

function listOf(value) {
    return Array.isArray(value) ? value : [];
}

function normalizedSearchText(value) {
    return String(value ?? '')
        .normalize('NFKC')
        .replace(/\*\*/g, '')
        .trim()
        .toLocaleLowerCase();
}

function uniqueStrings(values) {
    return [...new Set(listOf(values).map(value => String(value ?? '').trim()).filter(Boolean))];
}

function storefrontIconMode(value) {
    return STOREFRONT_ICON_MODES.includes(value) ? value : 'default';
}

function storefrontIconClass(value) {
    const tokens = String(value ?? '')
        .trim()
        .split(/\s+/)
        .filter(token => /^[a-z0-9_-]+$/i.test(token));
    const stylePattern = /^(?:fa[rsbltdk]|fa-(?:solid|regular|brands|light|thin|duotone|sharp|sharp-solid|sharp-regular|sharp-light|sharp-thin))$/i;
    const modifierPattern = /^fa-(?:2xs|xs|sm|lg|xl|2xl|(?:[1-9]|10)x|fw|ul|li|border|pull-left|pull-right|spin|pulse|beat|fade|beat-fade|bounce|flip|shake|rotate-(?:90|180|270)|flip-(?:horizontal|vertical|both)|stack|stack-1x|stack-2x|inverse)$/i;
    const icon = tokens.find(token => /^fa-[a-z0-9-]+$/i.test(token)
        && !stylePattern.test(token)
        && !modifierPattern.test(token));
    if (!icon) return DEFAULT_STOREFRONT_ICON_CLASS;
    if (!tokens.some(token => stylePattern.test(token))) tokens.unshift('fas');
    return tokens.join(' ');
}

function storefrontIconImage(value) {
    const path = String(value ?? '').trim();
    if (!path || /[<>"'`]/.test(path)) return '';
    if (/^data:image\/(?:avif|gif|jpe?g|png|svg\+xml|webp);base64,/i.test(path)) return path;
    const pathname = path.split(/[?#]/, 1)[0];
    return /\.(?:apng|avif|bmp|gif|ico|jpe?g|png|svg|tiff?|webp)$/i.test(pathname) ? path : '';
}

function storefrontIconImageLoads(value, timeout = 5000) {
    const source = storefrontIconImage(value);
    if (!source || typeof Image === 'undefined') return Promise.resolve(false);
    return new Promise(resolve => {
        const img = new Image();
        let settled = false;
        const finish = result => {
            if (settled) return;
            settled = true;
            clearTimeout(timer);
            img.onload = null;
            img.onerror = null;
            resolve(result);
        };
        const timer = setTimeout(() => finish(false), timeout);
        img.onload = () => finish(img.naturalWidth > 0 && img.naturalHeight > 0);
        img.onerror = () => finish(false);
        img.src = source;
    });
}

function readStorefrontBranding() {
    const read = (key, fallback) => {
        try {
            return game.settings.get(MODULE_ID, key);
        } catch (e) {
            return fallback;
        }
    };
    return {
        name: String(read('storefrontName', 'SUPPLYNET') ?? '').trim() || 'SUPPLYNET',
        iconMode: storefrontIconMode(read('storefrontIconMode', 'default')),
        iconClass: storefrontIconClass(read('storefrontIconClass', DEFAULT_STOREFRONT_ICON_CLASS)),
        iconImage: storefrontIconImage(read('storefrontIconImage', ''))
    };
}

function defaultStorefrontMarkHtml() {
    return `
        <svg class="ssa-logo-mark" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <defs><linearGradient id="ssaLogoGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" style="stop-color:var(--ssa-logo-1, #45dcff)"/>
                <stop offset="1" style="stop-color:var(--ssa-logo-2, #2f7bff)"/>
            </linearGradient></defs>
            <path fill="url(#ssaLogoGrad)" d="M12 1 21 6.5v11L12 23 3 17.5v-11z"/>
            <path style="fill:var(--ssa-logo-ink, #071018)" d="M13.6 5.5 8 13.2h3.2L9.8 18.9l6.2-8.2h-3.3z"/>
        </svg>`;
}

function storefrontMarkHtml({ iconMode = 'default', iconClass = DEFAULT_STOREFRONT_ICON_CLASS, iconImage = '' } = {}) {
    const mode = storefrontIconMode(iconMode);
    const image = storefrontIconImage(iconImage);
    if (mode === 'image' && image) {
        return `<img class="ssa-logo-mark ssa-logo-mark-image" src="${esc(image)}" alt="">`;
    }
    if (mode === 'fontawesome') {
        return `<span class="ssa-logo-mark ssa-logo-mark-fa" aria-hidden="true"><i class="${esc(storefrontIconClass(iconClass))}"></i></span>`;
    }
    return defaultStorefrontMarkHtml();
}

// 리스트 화면 헤더 워드마크 (인월드 앱 브랜드) — 색상은 테마 CSS 변수를 따름
function logoHtml(name, branding = {}) {
    const normalized = String(name ?? '').trim() || 'SUPPLYNET';
    const wordmark = normalized.toLocaleUpperCase() === 'SUPPLYNET'
        ? 'SUPPLY<em>NET</em>'
        : esc(normalized);
    return `
    <div class="ssa-logo">
        ${storefrontMarkHtml(branding)}
        <span class="ssa-logo-word" title="${esc(normalized)}">${wordmark}</span>
    </div>`;
}

/**
 * Stylish Shop 모바일 프론트엔드 (온라인 쇼핑몰 스타일).
 * 상점 데이터/가격/구매 검증은 전부 stylish-shop의 공개 API(카탈로그 뷰모델 +
 * requestPurchase)를 사용하고, 이 앱은 스마트폰 화면 안의 UI만 담당합니다.
 * 화면: 스토어 목록(브랜드관) → 상점(상품 그리드) → 상세(PDP) → 구매.
 */
export class StylishShopApp extends BaseApp {
    constructor(widget) {
        super(widget);
        this.view = 'list';        // 'list' | 'shop' | 'detail' | 'sell' | 'wishlist' | 'cart' | 'orders' | 'settings' | 'create' | 'manage' | 'manage-items'
        this.shopId = null;
        this.categoryId = null;
        this.itemUuid = null;
        this.qty = 1;
        this.sortMode = 'default'; // 'default' | 'asc' | 'desc'
        this.paymentSource = null; // null = 상점 기본값, 'sheet' | 'bank'
        this.resultBanner = null;  // { success, text } — 구매 직후 1회 표시
        this.pdpTab = 'info';      // 상세 화면 활성 탭
        this._detailOrigin = 'shop'; // 상세 진입 경로 ('home' | 'shop') — 뒤로가기 목적지
        this._bannerIndex = 0;     // 홈 배너 캐러셀 현재 슬라이드
        this._bannerTimer = null;
        this.manageCategoryId = null; // 상품 관리 중인 카테고리
        this._renderSeq = 0;
        this._purchasing = false;
        this._selling = false;
        this._sellRows = null;     // 판매 화면의 행 데이터 (itemId → row)
        this._sellSheet = null;    // 열려 있는 판매 시트 상태 { itemId, qty, max, totalDisplay, valid }
        this._sellQuoteSeq = 0;
        this._wishables = new Map(); // 이번 렌더에 표시된 찜 가능 상품 (key → 스냅샷)
        this._wishAlertBusy = false;
        this._lastRecentKey = null;
        this._checkingOut = false;
        this._cartLines = [];      // 마지막 카트 렌더의 해석된 라인 (체크아웃용)
        this._cartErrors = new Map(); // 직전 체크아웃 실패 사유 (key → 문구)
        this._lastDetailTotal = ''; // 마지막 PDP 총액 표시 (주문 기록용)
        this._payment = null;      // 마지막 detail 조회의 paymentSource 상태
        this._shopMeta = null;     // 마지막 상점 뷰모델의 shop 식별 정보 (PDP 판매자 카드용)
        this._walletInfo = null;   // 마지막 조회의 지갑 정보 (잔액 시트용)
        this._armed = null;        // 2-탭 삭제 확인 상태 { key, until }
        this._hooked = false;
        this._routeHistory = [];
        this._pendingScrollTop = null;
        this._catalogTaxonomy = null;
        this._catalogHome = null;
        this._catalogResults = null;
        this._catalogQuery = '';
        this._catalogFilters = this._defaultCatalogFilters();
        this._catalogCursor = null;
        this._catalogLoading = false;
        this._catalogSearchTimer = null;
        this._catalogSearchSeq = 0;
        this._catalogError = null;
        this._catalogSection = null;
        this._catalogCategoryId = null;
        this._catalogCollectionId = null;
        this._catalogOffers = null;
        this._catalogRelated = [];
        this._catalogHomeShopName = '';
        this._detailCatalogCache = new Map();
        this._manageSaveChains = new Map();
        this._savingAppSettings = false;
        this._settingsBanner = null;
        this._appSettingsDraft = null;
    }

    get api() {
        return game.modules.get('stylish-shop')?.api ?? null;
    }

    /** 현재 테마 ID (설정 미등록/오염 값이면 light 폴백). */
    get theme() {
        let t = 'light';
        try {
            t = game.settings.get(MODULE_ID, 'shopTheme');
        } catch (e) { /* 설정 미등록 시 기본값 */ }
        return THEME_IDS.includes(t) ? t : 'light';
    }

    get storefrontName() {
        return this.storefrontBranding.name;
    }

    get storefrontBranding() {
        return readStorefrontBranding();
    }

    static get launcherIcon() {
        const branding = readStorefrontBranding();
        if (branding.iconMode === 'image' && branding.iconImage) return branding.iconImage;
        if (branding.iconMode === 'fontawesome') return branding.iconClass;
        return DEFAULT_STOREFRONT_ICON_CLASS;
    }

    /** 열려 있는 화면에 테마 클래스를 즉시 적용 (설정 onChange 경로). */
    applyTheme(theme) {
        if (!this.element) return;
        const t = THEME_IDS.includes(theme) ? theme : 'light';
        this.element.classList.remove(...THEME_IDS.map(id => `theme-${id}`));
        this.element.classList.add(`theme-${t}`);
    }

    static async applyThemeToOpenInstance(theme) {
        try {
            const instance = await SmartphoneWidget.getInstance();
            const app = instance?.apps?.get(APP_ID);
            if (app && instance.currentApp === APP_ID && app.element) app.applyTheme(theme);
        } catch (e) { /* 위젯 미초기화 시 무시 */ }
    }

    static async applyStorefrontBrandingToOpenInstance() {
        const definition = SmartphoneWidget.appDefinitions?.get?.(APP_ID);
        if (definition) definition.icon = this.launcherIcon;
        try {
            const instance = await SmartphoneWidget.getInstance();
            const app = instance?.apps?.get(APP_ID);
            if (app && instance.currentApp === APP_ID) app.render();
            else if (instance?.currentApp === 'home') instance.apps?.get('home')?.render();
        } catch (e) { /* 위젯 미초기화 시 무시 */ }
    }

    /** 이 폰의 소유자 액터. ownerId가 유저 ID인 경우 해당 유저의 캐릭터로 폴백. */
    get buyerActor() {
        const id = this.widget?.currentActorId;
        if (id) {
            const actor = game.actors?.get(id);
            if (actor) return actor;
            const userChar = game.users?.get(id)?.character;
            if (userChar) return userChar;
        }
        return game.user?.character ?? null;
    }

    get supportsCatalogApi() {
        return typeof this.api?.getCatalogHome === 'function'
            && typeof this.api?.getCatalogTaxonomy === 'function'
            && typeof this.api?.searchCatalog === 'function';
    }

    _defaultCatalogFilters() {
        return {
            categoryIds: [],
            shopIds: [],
            inStock: false,
            onSale: false,
            unlocked: false,
            affinity: false,
            affordable: false,
            purchasable: false,
            itemTypes: [],
            tags: [],
            sort: 'default'
        };
    }

    _cancelCatalogSearch() {
        if (this._catalogSearchTimer) clearTimeout(this._catalogSearchTimer);
        this._catalogSearchTimer = null;
        this._catalogSearchSeq++;
        this._catalogLoading = false;
    }

    _markCatalogHistoryStale() {
        for (const route of this._routeHistory) {
            if (route?.view !== 'results') continue;
            route.catalogStale = true;
            route.catalogResults = null;
            route.catalogCursor = null;
        }
    }

    _renderPreservingScroll() {
        const scroller = this.element?.querySelector('.ssa-content');
        if (scroller) this._pendingScrollTop = scroller.scrollTop;
        this.render();
    }

    _routeSnapshot() {
        return {
            view: this.view,
            shopId: this.shopId,
            categoryId: this.categoryId,
            itemUuid: this.itemUuid,
            qty: this.qty,
            sortMode: this.sortMode,
            paymentSource: this.paymentSource,
            pdpTab: this.pdpTab,
            detailOrigin: this._detailOrigin,
            catalogQuery: this._catalogQuery,
            catalogFilters: foundry.utils.deepClone(this._catalogFilters),
            catalogResults: this._catalogResults,
            catalogCursor: this._catalogCursor,
            catalogSection: this._catalogSection,
            catalogCategoryId: this._catalogCategoryId,
            catalogCollectionId: this._catalogCollectionId,
            catalogStale: this.view === 'results' && this._catalogResults == null,
            scrollTop: this.element?.querySelector('.ssa-content')?.scrollTop ?? 0
        };
    }

    _applyRouteSnapshot(route) {
        if (!route) return false;
        this.view = route.view ?? 'list';
        this.shopId = route.shopId ?? null;
        this.categoryId = route.categoryId ?? null;
        this.itemUuid = route.itemUuid ?? null;
        this.qty = route.qty ?? 1;
        this.sortMode = route.sortMode ?? 'default';
        this.paymentSource = route.paymentSource ?? null;
        this.pdpTab = route.pdpTab ?? 'info';
        this._detailOrigin = route.detailOrigin ?? 'shop';
        this._catalogQuery = route.catalogQuery ?? '';
        this._catalogFilters = foundry.utils.deepClone(route.catalogFilters ?? this._defaultCatalogFilters());
        const catalogStale = route.catalogStale === true;
        this._catalogResults = catalogStale ? null : (route.catalogResults ?? null);
        this._catalogCursor = route.catalogCursor ?? null;
        this._catalogSection = route.catalogSection ?? null;
        this._catalogCategoryId = route.catalogCategoryId ?? null;
        this._catalogCollectionId = route.catalogCollectionId ?? null;
        this._pendingScrollTop = Number(route.scrollTop) || 0;
        return { catalogStale };
    }

    _navigate(view, patch = {}, { replace = false, resetScroll = true } = {}) {
        if (view !== 'results') this._cancelCatalogSearch();
        if (!replace) this._routeHistory.push(this._routeSnapshot());
        Object.assign(this, patch);
        this.view = view;
        if (resetScroll) this._pendingScrollTop = 0;
        this.render();
    }

    _switchRoot(view) {
        this._cancelCatalogSearch();
        this._routeHistory = [];
        this.view = view;
        this.itemUuid = null;
        this.resultBanner = null;
        this._catalogError = null;
        if (view === 'list') {
            this.shopId = null;
            this.categoryId = null;
            this._shopMeta = null;
            this._walletInfo = null;
            this._catalogQuery = '';
            this._catalogFilters = this._defaultCatalogFilters();
            this._catalogResults = null;
            this._catalogCursor = null;
        }
        if (view === 'departments') {
            this._catalogCategoryId = null;
            this._catalogSection = null;
        }
        this._pendingScrollTop = 0;
        this.render();
    }

    _restoreScrollPosition() {
        if (this._pendingScrollTop == null) return;
        const top = this._pendingScrollTop;
        this._pendingScrollTop = null;
        requestAnimationFrame(() => {
            const scroller = this.element?.querySelector('.ssa-content');
            if (scroller) scroller.scrollTop = top;
        });
    }

    _activeRootTab() {
        if (this.view === 'departments' || this.view === 'results') return 'departments';
        if (this.view === 'cart') return 'cart';
        if (['account', 'wishlist', 'orders'].includes(this.view)) return 'account';
        if (this.view === 'detail' || this.view === 'shop') {
            const origin = [...this._routeHistory].reverse().find(route => ['list', 'departments', 'results', 'cart', 'account'].includes(route.view));
            if (origin?.view === 'departments' || origin?.view === 'results') return 'departments';
            if (origin?.view === 'cart') return 'cart';
            if (origin?.view === 'account') return 'account';
        }
        return 'home';
    }

    _showBottomNav() {
        return !['settings', 'create', 'manage', 'manage-items', 'sell'].includes(this.view);
    }

    show(args = {}) {
        if (args?.shopId) {
            this._routeHistory = [];
            this.shopId = args.shopId;
            this.categoryId = ALL_SHOP_CATEGORY_ID;
            this.sortMode = 'default';
            this.view = 'shop';
        }
        this.resultBanner = null;
        this._hookExternalUpdates();
        this.render();
    }

    async onActorChanged() {
        this._routeHistory = [];
        this._catalogTaxonomy = null;
        this._catalogHome = null;
        this._catalogResults = null;
        this._catalogCursor = null;
        this._catalogQuery = '';
        this._catalogFilters = this._defaultCatalogFilters();
        this._detailCatalogCache.clear();
        this._shopMeta = null;
        this._walletInfo = null;
        this.shopId = null;
        this.categoryId = null;
        this.itemUuid = null;
        this.view = 'list';
    }

    async render() {
        const seq = ++this._renderSeq;
        const api = this.api;
        if (!api || typeof api.getShopDirectory !== 'function') {
            this.updateContent(this._screen(this._titleHtml(loc('title')), 'home', this._notice('exclamation-triangle', loc('errors.apiMissing'))));
            return;
        }
        try {
            let html;
            this._wishables = new Map();
            if (this.view === 'shop') html = await this._buildShopScreen();
            else if (this.view === 'detail') html = await this._buildDetailScreen();
            else if (this.view === 'sell') html = await this._buildSellScreen();
            else if (this.view === 'wishlist') html = await this._buildWishlistScreen();
            else if (this.view === 'cart') html = await this._buildCartScreen();
            else if (this.view === 'orders') html = this._buildOrdersScreen();
            else if (this.view === 'departments') html = await this._buildDepartmentsScreen();
            else if (this.view === 'results') html = await this._buildCatalogResultsScreen();
            else if (this.view === 'account') html = this._buildAccountScreen();
            else if (this.view === 'settings') html = this._buildAppSettingsScreen();
            else if (this.view === 'create') html = this._buildCreateScreen();
            else if (this.view === 'manage') html = await this._buildManageScreen();
            else if (this.view === 'manage-items') html = await this._buildManageItemsScreen();
            else html = await this._buildListScreen();
            if (seq !== this._renderSeq) return; // 더 새로운 렌더가 시작됨
            this.updateContent(html);
            this._restoreScrollPosition();
        } catch (e) {
            console.error('Smartphone Shop App | Render failed:', e);
            if (seq === this._renderSeq) {
                this.updateContent(this._screen(this._titleHtml(loc('title')), 'home', this._notice('exclamation-triangle', loc('errors.generic'))));
            }
        }
    }

    setupListeners() {
        this.removeAllListeners();
        if (!this.element) return;
        if (!this._boundClick) this._boundClick = this._onClick.bind(this);
        if (!this._boundChange) this._boundChange = this._onChange.bind(this);
        if (!this._boundInput) this._boundInput = this._onInput.bind(this);
        this.addListener(this.element, 'click', this._boundClick);
        this.addListener(this.element, 'change', this._boundChange);
        this.addListener(this.element, 'input', this._boundInput);
        for (const el of this.element.querySelectorAll('.ssa-category-tabs, .ssa-store-rail, .ssa-recent-rail, .ssa-product-rail, .ssa-filter-chips')) {
            this._bindHScroll(el);
        }
        this._setupBannerRotation();
        this._bindImageFallbacks();
        if (this.view === 'settings') this._syncStorefrontBrandingEditor();
    }

    /* ------------------------------------------------------------------ */
    /*  홈 배너 캐러셀 (재렌더 없이 DOM 전환)                                  */
    /* ------------------------------------------------------------------ */

    _setupBannerRotation() {
        this._clearBannerTimer();
        const track = this.element?.querySelector('.ssa-feature-track');
        if (!track || track.children.length < 2) return;
        const count = track.children.length;
        this._bannerTimer = setInterval(() => {
            this._goBanner((this._bannerIndex + 1) % count);
        }, 4000);
    }

    _goBanner(index) {
        const track = this.element?.querySelector('.ssa-feature-track');
        if (!track) {
            this._clearBannerTimer();
            return;
        }
        this._bannerIndex = index;
        track.style.transform = `translateX(-${index * 100}%)`;
        this.element.querySelectorAll('.ssa-feature-dot').forEach((dot, i) => {
            dot.classList.toggle('active', i === index);
        });
    }

    _clearBannerTimer() {
        if (this._bannerTimer) {
            clearInterval(this._bannerTimer);
            this._bannerTimer = null;
        }
    }

    /**
     * 가로 스크롤 영역(카테고리 탭, 스토어 레일): 스와이프 시 폰 위젯이
     * 끌려가지 않도록 pointerdown 전파를 막고, 마우스 드래그/휠로 좌우
     * 스크롤을 지원합니다. (요소는 렌더마다 새로 만들어지므로 리스너 누수 없음)
     */
    _bindHScroll(tabs) {
        if (!tabs) return;
        let dragMoved = false;

        tabs.addEventListener('pointerdown', (e) => {
            e.stopPropagation(); // 위젯 드래그 핸들러(폰 이동)로 전파 금지
            dragMoved = false;
            const startX = e.clientX;
            const startLeft = tabs.scrollLeft;
            const onMove = (ev) => {
                const dx = ev.clientX - startX;
                if (Math.abs(dx) > 4) dragMoved = true;
                if (dragMoved) tabs.scrollLeft = startLeft - dx;
            };
            const onUp = () => {
                document.removeEventListener('pointermove', onMove);
                document.removeEventListener('pointerup', onUp);
            };
            document.addEventListener('pointermove', onMove);
            document.addEventListener('pointerup', onUp);
        });

        // 드래그로 스크롤한 직후의 클릭이 카테고리 선택으로 이어지지 않게 차단
        tabs.addEventListener('click', (e) => {
            if (dragMoved) {
                e.stopPropagation();
                e.preventDefault();
                dragMoved = false;
            }
        }, true);

        // 세로 휠 → 가로 스크롤
        tabs.addEventListener('wheel', (e) => {
            if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
            e.preventDefault();
            e.stopPropagation();
            tabs.scrollLeft += e.deltaY;
        }, { passive: false });
    }

    /** 깨진 이미지에 기본 아이콘을 대신 표시합니다. */
    _bindImageFallbacks() {
        if (!this.element) return;
        const selector = '.ssa-product-thumb img, .ssa-pdp-hero img, .ssa-recent-thumb img, img.ssa-req-img, img.ssa-store-logo, img.ssa-feature-logo, img.ssa-rail-logo, img.ssa-hero-logo, img.ssa-seller-art, img.ssa-dept-image, .ssa-rail-product-img img, img.ssa-buyer-avatar, img.ssa-account-avatar, .ssa-receiver-card img, img.ssa-logo-mark-image';
        for (const img of this.element.querySelectorAll(selector)) {
            const isPortrait = img.matches('.ssa-store-logo, .ssa-feature-logo, .ssa-rail-logo, .ssa-hero-logo, .ssa-seller-art, .ssa-buyer-avatar, .ssa-account-avatar, .ssa-receiver-card img');
            const applyFallback = () => {
                if (img.dataset.fallbackApplied) return;
                img.dataset.fallbackApplied = '1';
                img.src = isPortrait ? 'icons/svg/mystery-man.svg' : 'icons/svg/item-bag.svg';
            };
            img.addEventListener('error', applyFallback, { once: true });
            if (img.complete && img.naturalWidth === 0 && !/\.svg(\?|$)/i.test(img.src)) applyFallback();
        }
    }

    handleBack() {
        this._cancelCatalogSearch();
        if (this.view === 'manage-items') {
            this.view = 'manage';
            this.manageCategoryId = null;
            this.render();
        } else if (this.view === 'manage') {
            this.view = 'shop';
            this.render();
        } else if (this.view === 'create') {
            this.view = 'list';
            this.render();
        } else if (this.view === 'sell') {
            this.view = 'shop';
            this._sellRows = null;
            this._sellSheet = null;
            this.resultBanner = null;
            this.render();
        } else if (this._routeHistory.length > 0) {
            const restored = this._applyRouteSnapshot(this._routeHistory.pop());
            this.resultBanner = null;
            this.render();
            if (restored?.catalogStale && this.view === 'results') this._runCatalogSearch({ reset: true });
        } else if (this.view === 'wishlist') {
            this.view = 'list';
            this.render();
        } else if (this.view === 'orders') {
            this.view = 'cart';
            this.render();
        } else if (this.view === 'cart') {
            this.view = 'list';
            this.resultBanner = null;
            this._cartErrors = new Map();
            this.render();
        } else if (this.view === 'detail') {
            // 홈 피드에서 들어온 상품이면 홈으로, 상점 페이지에서 들어왔으면 상점으로
            this.view = this._detailOrigin === 'home' ? 'list' : 'shop';
            this.itemUuid = null;
            this.resultBanner = null;
            this.render();
        } else if (this.view === 'shop') {
            this.view = 'list';
            this.shopId = null;
            this.categoryId = null;
            this.sortMode = 'default';
            this.paymentSource = null;
            this._shopMeta = null;
            this._walletInfo = null;
            this.render();
        } else {
            this.widget.switchApp('home');
        }
    }

    cleanup() {
        this.removeAllListeners();
        this._clearBannerTimer();
        if (this._catalogSearchTimer) clearTimeout(this._catalogSearchTimer);
        this._catalogSearchTimer = null;
        this._catalogSearchSeq++;
        this._catalogLoading = false;
        this._unhookExternalUpdates();
    }

    /* ------------------------------------------------------------------ */
    /*  외부 갱신 훅 (재고 변경, 잔액 변경)                                  */
    /* ------------------------------------------------------------------ */

    _hookExternalUpdates() {
        if (this._hooked) return;
        this._hooked = true;
        this._onShopUpdated = (shopActorId) => {
            this._catalogHome = null;
            this._catalogTaxonomy = null;
            this._detailCatalogCache.clear();
            this._markCatalogHistoryStale();
            // 찜 알림은 다른 앱을 보고 있어도 위젯 토스트로 전달
            this._checkWishAlerts(shopActorId);
            if (this.widget?.currentApp !== APP_ID) return;
            // 관리 화면은 GM 본인이 편집 주체 — 입력 중 자동 재렌더로 내용이 날아가지 않게 제외
            if (this.view === 'manage' || this.view === 'manage-items' || this.view === 'create') return;
            // 판매 화면은 시트 조작 중 재렌더로 시트가 닫히지 않게 제외
            if (this.view === 'sell') return;
            // 체크아웃 중에는 구매 브로드캐스트마다 재렌더하지 않음 (완료 후 일괄 갱신)
            if (this.view === 'cart') {
                if (!this._checkingOut) this._renderPreservingScroll();
                return;
            }
            if (this.view === 'results') {
                this._runCatalogSearch({ reset: true });
                return;
            }
            if (['list', 'departments', 'results', 'wishlist', 'account'].includes(this.view) || shopActorId === this.shopId) this._renderPreservingScroll();
        };
        this._onBalanceChanged = () => {
            if (this.widget?.currentApp !== APP_ID) return;
            this._catalogHome = null;
            this._detailCatalogCache.clear();
            this._markCatalogHistoryStale();
            if (this.view === 'results') {
                this._runCatalogSearch({ reset: true });
                return;
            }
            if (['list', 'account', 'cart', 'shop', 'detail'].includes(this.view)) this._renderPreservingScroll();
        };
        this._onCatalogTaxonomyChanged = () => {
            this._catalogHome = null;
            this._catalogTaxonomy = null;
            this._catalogResults = null;
            this._catalogCursor = null;
            this._manageData = null;
            this._detailCatalogCache.clear();
            this._markCatalogHistoryStale();
            if (this.widget?.currentApp !== APP_ID) return;
            if (this.view === 'manage' || this.view === 'manage-items') {
                this._renderPreservingScroll();
                return;
            }
            if (this.view === 'results') {
                this._runCatalogSearch({ reset: true });
                return;
            }
            if (['list', 'departments', 'shop', 'detail'].includes(this.view)) this._renderPreservingScroll();
        };
        this._onRelationshipProgressChanged = ({ ownerActorUuid } = {}) => {
            if (!ownerActorUuid || !isSameActorIdentity(this.buyerActor, ownerActorUuid)) return;
            if (this.widget?.currentApp !== APP_ID) return;
            if (this._purchasing || this._checkingOut) return;
            this._catalogHome = null;
            this._detailCatalogCache.clear();
            this._markCatalogHistoryStale();
            if (this.view === 'results') {
                this._runCatalogSearch({ reset: true });
                return;
            }
            if (['list', 'departments', 'results', 'shop', 'detail', 'wishlist', 'cart', 'account'].includes(this.view)) this._renderPreservingScroll();
        };
        // 사이드바 아이템을 폰 위로 드래그 → 관리 중인 카테고리에 상품 등록
        this._onItemDrop = async (item) => {
            if (this.widget?.currentApp !== APP_ID) return;
            if (this.view !== 'manage-items' || !game.user.isGM) return;
            const uuid = item?.uuid ?? null;
            const shopActor = game.actors?.get(this.shopId);
            if (!uuid || !shopActor || !this.manageCategoryId) return;
            try {
                await this.api.addItemToCategory(shopActor, this.manageCategoryId, { uuid });
                this.widget.showToastNotification?.(locf('manage.itemAdded', { name: item.name ?? '' }));
                this.render();
            } catch (e) {
                console.error('Smartphone Shop App | Item drop failed:', e);
            }
        };
        Hooks.on('stylishShop.shopUpdated', this._onShopUpdated);
        Hooks.on('stylishShop.catalogTaxonomyChanged', this._onCatalogTaxonomyChanged);
        Hooks.on('glitchsmith-lib.currency.balanceChanged', this._onBalanceChanged);
        Hooks.on('stylish-relationship-tracker.relationshipProgressChanged', this._onRelationshipProgressChanged);
        Hooks.on('smartphone-widget.itemDrop', this._onItemDrop);
    }

    _unhookExternalUpdates() {
        if (!this._hooked) return;
        this._hooked = false;
        Hooks.off('stylishShop.shopUpdated', this._onShopUpdated);
        Hooks.off('stylishShop.catalogTaxonomyChanged', this._onCatalogTaxonomyChanged);
        Hooks.off('glitchsmith-lib.currency.balanceChanged', this._onBalanceChanged);
        Hooks.off('stylish-relationship-tracker.relationshipProgressChanged', this._onRelationshipProgressChanged);
        Hooks.off('smartphone-widget.itemDrop', this._onItemDrop);
    }

    /* ------------------------------------------------------------------ */
    /*  이벤트                                                              */
    /* ------------------------------------------------------------------ */

    _onClick(e) {
        const target = e.target.closest('[data-action]');
        if (!target || !this.element?.contains(target)) return;
        const action = target.dataset.action;

        switch (action) {
            case 'tab-home':
                this._switchRoot('list');
                break;
            case 'tab-departments':
                this._switchRoot('departments');
                break;
            case 'tab-cart':
                this._switchRoot('cart');
                break;
            case 'tab-account':
                this._switchRoot('account');
                break;
            case 'open-wallet-app':
                if (this.widget?.apps?.has?.('wallet')) {
                    this._pendingScrollTop = this.element?.querySelector('.ssa-content')?.scrollTop ?? 0;
                    this.widget.switchApp('wallet', { returnApp: APP_ID });
                }
                else this._openWalletSheet();
                break;
            case 'open-department':
                this._openCatalogResults({ categoryId: target.dataset.categoryId ?? null });
                break;
            case 'open-catalog-section':
                this._openCatalogResults({ sectionId: target.dataset.sectionId ?? null, tag: target.dataset.tag ?? null });
                break;
            case 'catalog-clear':
                this._catalogFilters = this._defaultCatalogFilters();
                this._catalogCategoryId = null;
                this._catalogSection = null;
                this._catalogQuery = '';
                this._runCatalogSearch({ reset: true });
                break;
            case 'catalog-load-more':
                this._runCatalogSearch({ reset: false, append: true });
                break;
            case 'catalog-filter':
                this._toggleCatalogFilter(target.dataset.filter, target.dataset.value);
                break;
            case 'shop-search-global': {
                const input = this.element?.querySelector('[data-field="item-search"]');
                this._catalogQuery = input?.value?.trim() ?? '';
                this._openCatalogResults({ query: this._catalogQuery, shopId: this.shopId });
                break;
            }
            case 'home':
                this.widget.switchApp('home');
                break;
            case 'back':
                this.handleBack();
                break;
            case 'open-app-settings':
                if (!game.user.isGM) break;
                this._settingsBanner = null;
                this._appSettingsDraft = null;
                this._navigate('settings');
                break;
            case 'save-app-settings':
                this._saveAppSettings();
                break;
            case 'open-catalog-category-manager':
                if (!game.user.isGM) break;
                if (typeof this.api?.openCatalogCategoryManager === 'function') this.api.openCatalogCategoryManager();
                else this.widget.showToastNotification?.(loc('settings.catalogCategoriesUnavailable'));
                break;
            case 'pick-storefront-icon-image':
                if (!game.user.isGM) break;
                this._pickStorefrontIconImage();
                break;
            case 'open-shop':
                this._navigate('shop', {
                    shopId: target.dataset.shopId,
                    categoryId: ALL_SHOP_CATEGORY_ID,
                    sortMode: 'default',
                    paymentSource: null,
                    resultBanner: null
                });
                break;
            case 'select-category':
                if (this.categoryId !== target.dataset.categoryId) {
                    this.categoryId = target.dataset.categoryId;
                    this.render();
                }
                break;
            case 'open-item': {
                // 홈 피드에서 진입하면 행에 담긴 상점 ID로 컨텍스트 전환
                const nextShopId = target.dataset.shopId || this.shopId;
                const changingShop = !!nextShopId && nextShopId !== this.shopId;
                this._navigate('detail', {
                    shopId: nextShopId,
                    categoryId: changingShop ? ALL_SHOP_CATEGORY_ID : this.categoryId,
                    paymentSource: changingShop ? null : this.paymentSource,
                    _shopMeta: changingShop ? null : this._shopMeta,
                    _detailOrigin: this.view === 'list' ? 'home' : 'shop',
                    itemUuid: target.dataset.uuid,
                    qty: 1,
                    pdpTab: 'info',
                    resultBanner: null
                });
                break;
            }
            case 'crumb-shop':
                if (!this.shopId) break;
                this.view = 'shop';
                this.itemUuid = null;
                this.resultBanner = null;
                this.render();
                break;
            case 'banner-dot':
                this._goBanner(Number(target.dataset.index) || 0);
                this._setupBannerRotation(); // 수동 선택 직후 바로 넘어가지 않게 타이머 리셋
                break;
            case 'crumb-home':
                this.view = 'list';
                this.shopId = null;
                this.categoryId = null;
                this.itemUuid = null;
                this.sortMode = 'default';
                this.paymentSource = null;
                this._shopMeta = null;
                this._walletInfo = null;
                this.render();
                break;
            case 'pdp-tab': {
                // 재렌더 없이 탭 전환 (수량/배너 상태 유지)
                const tab = target.dataset.tab;
                if (!tab) break;
                this.pdpTab = tab;
                for (const panel of this.element.querySelectorAll('[data-tab-panel]')) {
                    panel.classList.toggle('active', panel.dataset.tabPanel === tab);
                }
                for (const btn of this.element.querySelectorAll('.ssa-tab[data-action="pdp-tab"]')) {
                    btn.classList.toggle('active', btn.dataset.tab === tab);
                }
                break;
            }
            case 'qty-minus':
            case 'qty-plus': {
                if (this._purchasing) break;
                const max = Number(target.dataset.max) || 99;
                const next = this.qty + (action === 'qty-plus' ? 1 : -1);
                const clamped = Math.min(Math.max(1, next), max);
                if (clamped !== this.qty) {
                    this.qty = clamped;
                    this.resultBanner = null;
                    this._renderPreservingScroll();
                }
                break;
            }
            case 'toggle-payment':
                if (this._purchasing) break;
                if (this.paymentSource !== target.dataset.source) {
                    this.paymentSource = target.dataset.source;
                    this.resultBanner = null;
                    this._renderPreservingScroll();
                }
                break;
            case 'wallet-open':
                this._openWalletSheet();
                break;
            case 'wallet-close':
                this._closeWalletSheet();
                break;
            case 'buy':
                this._purchase();
                break;
            case 'open-sell':
                this.view = 'sell';
                this.resultBanner = null;
                this._sellSheet = null;
                this.render();
                break;
            case 'sell-item':
                this._openSellSheet(target.dataset.itemId);
                break;
            case 'sell-close':
                this._closeSellSheet();
                break;
            case 'sell-minus':
            case 'sell-plus': {
                if (!this._sellSheet || this._selling) break;
                const next = this._sellSheet.qty + (action === 'sell-plus' ? 1 : -1);
                this._setSellQty(next);
                break;
            }
            case 'sell-confirm':
                this._confirmSell();
                break;
            case 'open-wishlist':
                this._navigate('wishlist', { resultBanner: null });
                break;
            case 'wish-toggle':
                this._toggleWish(target.dataset.key);
                break;
            case 'wish-remove':
                this._removeWish(target.dataset.key);
                break;
            case 'open-cart':
                this._navigate('cart', { resultBanner: null });
                break;
            case 'open-orders':
                this._navigate('orders');
                break;
            case 'cart-add':
                this._addToCartFromKey(target.dataset.key);
                break;
            case 'cart-remove':
                if (this._checkingOut) break;
                this._cartCall(async (buyer) => removeFromCart(buyer.id, target.dataset.key));
                break;
            case 'cart-minus':
            case 'cart-plus': {
                if (this._checkingOut) break;
                const line = this._cartLines.find(l => l.key === target.dataset.key);
                if (!line) break;
                const max = Number(target.dataset.max) || 99;
                const next = Math.min(Math.max(0, line.qty + (action === 'cart-plus' ? 1 : -1)), max);
                this._cartCall(async (buyer) => setCartQty(buyer.id, line.key, next));
                break;
            }
            case 'checkout':
                this._checkout();
                break;
            case 'sale-start':
                this._startSale();
                break;
            case 'sale-stop':
                if (!game.user.isGM) break;
                this._updateIdentity({ saleEnabled: false });
                break;
            /* ---- GM 관리 ---- */
            case 'create-shop':
                if (!game.user.isGM) break;
                this.view = 'create';
                this.render();
                break;
            case 'create-new-npc':
                this._createShopWithNewActor();
                break;
            case 'create-from-actor':
                this._createShopFromActor(target.dataset.actorId);
                break;
            case 'manage':
                if (!game.user.isGM) break;
                this.view = 'manage';
                this.render();
                break;
            case 'manage-items':
                if (!game.user.isGM) break;
                this.manageCategoryId = target.dataset.categoryId;
                this.view = 'manage-items';
                this.render();
                break;
            case 'save-identity':
                this._saveIdentity();
                break;
            case 'accent-reset':
                this._updateIdentity({ accentColor: '' });
                break;
            case 'pick-art': {
                if (!game.user.isGM) break;
                const artKey = target.dataset.art === 'directoryArt' ? 'directoryArt' : 'npcArt';
                this.selectImageSource(async (path) => {
                    await this._updateIdentity({ [artKey]: path }, { silent: true });
                }, '', {});
                break;
            }
            case 'cat-add':
                this._addCategory();
                break;
            case 'cat-delete': {
                if (!game.user.isGM) break;
                const catId = target.dataset.categoryId;
                if (!this._armDelete(`cat:${catId}`)) break;
                this._manageCall(async (shopActor) => {
                    await this.api.removeCategory(shopActor, catId);
                });
                break;
            }
            case 'mi-delete': {
                if (!game.user.isGM) break;
                const uuid = target.dataset.uuid;
                if (!this._armDelete(`item:${uuid}`)) break;
                this._manageCall(async (shopActor) => {
                    await this.api.removeItemFromCategory(shopActor, this.manageCategoryId, uuid);
                    this.widget.showToastNotification?.(loc('manage.itemRemoved'));
                });
                break;
            }
        }
    }

    async _onChange(e) {
        const sellQtyInput = e.target.closest('[data-field="sell-qty"]');
        if (sellQtyInput) {
            if (this._selling) return;
            this._setSellQty(Math.floor(Number(sellQtyInput.value) || 1));
            return;
        }

        const qtyInput = e.target.closest('[data-field="qty"]');
        if (qtyInput) {
            if (this._purchasing) return;
            const max = Number(qtyInput.dataset.max) || 99;
            this.qty = Math.min(Math.max(1, Math.floor(Number(qtyInput.value) || 1)), max);
            this.resultBanner = null;
            this._renderPreservingScroll();
            return;
        }

        const field = e.target.closest('[data-field]')?.dataset.field;
        if (!field) return;
        const el = e.target;

        if (field === 'sort-select') {
            if (this.sortMode !== el.value) {
                this.sortMode = el.value;
                this.render();
            }
            return;
        }

        if (field === 'catalog-sort') {
            this._catalogFilters.sort = el.value || 'default';
            this._runCatalogSearch({ reset: true });
            return;
        }

        if (field === 'storefront-icon-mode') {
            this._syncStorefrontBrandingEditor();
            return;
        }

        if (!game.user.isGM) return;

        switch (field) {
            case 'm-public':
                await this._updateIdentity({ publicShop: el.checked });
                break;
            case 'm-accent':
                await this._updateIdentity({ accentColor: el.value }, { silent: true });
                break;
            case 'm-layout': {
                const opts = this.api.getShopAppearanceOptions?.();
                const firstTheme = opts?.themes?.[el.value]?.[0] ?? 'default';
                await this._updateIdentity({ layout: el.value, layoutTheme: firstTheme });
                break;
            }
            case 'm-theme':
                await this._updateIdentity({ layoutTheme: el.value });
                break;
            case 'cat-name': {
                const name = el.value.trim();
                if (!name) break;
                await this._manageCall(async (shopActor) => {
                    await this.api.updateCategory(shopActor, el.dataset.categoryId, { name });
                }, { rerender: false });
                break;
            }
            case 'cat-catalog-category': {
                const catalogCategoryId = el.value || '';
                const categoryId = el.dataset.categoryId;
                const shopId = this.shopId;
                await this._queueManageSave(`${shopId}:category:${categoryId}:catalog`, () => this._manageCall(async (shopActor) => {
                    await this.api.updateCategory(shopActor, categoryId, { catalogCategoryId });
                }, { rerender: false, shopId }));
                break;
            }
            case 'mi-catalog-category': {
                const catalogCategoryId = el.value || '';
                const categoryId = this.manageCategoryId;
                const uuid = el.dataset.uuid;
                const shopId = this.shopId;
                await this._queueManageSave(`${shopId}:item:${categoryId}:${uuid}:catalog`, () => this._manageCall(async (shopActor) => {
                    await this.api.updateItemInCategory(shopActor, categoryId, uuid, { catalogCategoryId });
                }, { rerender: false, shopId }));
                break;
            }
            case 'mi-stock': {
                const raw = el.value.trim();
                const patch = raw === ''
                    ? { stock: null, maxStock: null }
                    : (() => {
                        const n = Math.max(0, Math.floor(Number(raw) || 0));
                        const row = this._findManageItem(el.dataset.uuid);
                        const maxStock = (row?.maxStock != null) ? Math.max(row.maxStock, n) : n;
                        return { stock: n, maxStock };
                    })();
                await this._manageCall(async (shopActor) => {
                    await this.api.updateItemInCategory(shopActor, this.manageCategoryId, el.dataset.uuid, patch);
                });
                break;
            }
            case 'mi-price': {
                const raw = el.value.trim();
                // 숫자만 → overridePrice, 문자열(예: "5gp 3sp") → overridePriceSpec, 빈 값 → 원가.
                // 수동 가격 수정 시 생성된 변동가 스탬프는 초기화해 즉시 반영되게 한다.
                let patch;
                if (raw === '') patch = { overridePrice: null, overridePriceSpec: null, priceVarianceSpec: null };
                else if (/^\d+(\.\d+)?$/.test(raw)) patch = { overridePrice: Number(raw), overridePriceSpec: null, priceVarianceSpec: null };
                else patch = { overridePrice: null, overridePriceSpec: raw, priceVarianceSpec: null };
                await this._manageCall(async (shopActor) => {
                    await this.api.updateItemInCategory(shopActor, this.manageCategoryId, el.dataset.uuid, patch);
                });
                break;
            }
        }
    }

    /** 검색 입력 — 재렌더 없이 DOM에서 바로 필터 (포커스 유지). */
    _onInput(e) {
        if (e.target.closest('[data-field="storefront-name"], [data-field="storefront-icon-class"], [data-field="storefront-icon-image"]')) {
            this._syncStorefrontBrandingEditor();
            return;
        }
        const catalogInput = e.target.closest('[data-field="catalog-search"]');
        if (catalogInput) {
            this._scheduleCatalogSearch(catalogInput.value);
            return;
        }
        const input = e.target.closest('[data-field="store-search"], [data-field="item-search"], [data-field="actor-search"], [data-field="sell-search"]');
        if (!input || !this.element) return;
        const q = input.value.trim().toLowerCase();
        const selector = {
            'store-search': '.ssa-store-card',
            'item-search': '.ssa-product-card',
            'actor-search': '.ssa-actor-row',
            'sell-search': '.ssa-sell-row'
        }[input.dataset.field];
        let visible = 0;
        for (const card of this.element.querySelectorAll(selector)) {
            const match = !q || (card.dataset.search ?? '').includes(q);
            card.style.display = match ? '' : 'none';
            if (match) visible++;
        }
        if (input.dataset.field === 'item-search') {
            const globalCta = this.element.querySelector('[data-role="shop-search-global"]');
            if (globalCta) {
                globalCta.hidden = !q;
                const label = globalCta.querySelector('[data-role="shop-search-query"]');
                if (label) label.textContent = input.value.trim();
            }
        }
        const count = this.element.querySelector('[data-role="result-count"]');
        if (!count) return;
        // 홈의 섹션 카운트는 숫자만, 상점 필터바는 "상품 N개" 포맷
        count.innerHTML = count.classList.contains('ssa-section-count')
            ? String(visible)
            : locf('itemsCount', { count: `<strong>${visible}</strong>` });
    }

    /* ------------------------------------------------------------------ */
    /*  구매                                                                */
    /* ------------------------------------------------------------------ */

    async _purchase() {
        if (this._purchasing) return;
        const api = this.api;
        const buyer = this.buyerActor;
        if (!api || !buyer || !this.shopId || !this.itemUuid) return;

        this._purchasing = true;
        const btn = this.element?.querySelector('[data-action="buy"]');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<span><i class="fas fa-spinner fa-spin"></i> ${esc(loc('buying'))}</span>`;
        }

        try {
            const shopActor = game.actors?.get(this.shopId);
            const result = await api.requestPurchase({
                shopActorId: this.shopId,
                shopActorUuid: shopActor?.uuid,
                itemUuid: this.itemUuid,
                buyerActorId: buyer.id,
                buyerActorUuid: buyer.uuid,
                quantity: this.qty,
                paymentSource: this._payment?.available ? this._payment.active : undefined,
                initiatorUserId: game.user.id
            });
            const successText = result?.success
                ? `${locf('purchaseSuccess', { itemName: result.itemName || '' })}${result.affinitySyncPending ? ` ${loc('affinitySyncPending')}` : ''}`
                : '';
            this.resultBanner = result?.success
                ? { success: true, text: successText }
                : { success: false, text: this._errorText(result?.errorCode, result?.message) };
            if (result?.success) {
                const snapshot = this._wishables?.get(wishKey(this.shopId, this.itemUuid));
                recordOrder(buyer.id, {
                    type: 'buy',
                    shopId: this.shopId,
                    shopName: String(this._shopMeta?.name ?? '').replace(/\*\*/g, ''),
                    uuid: this.itemUuid,
                    name: result.itemName || snapshot?.name || '',
                    img: snapshot?.img ?? '',
                    qty: this.qty,
                    totalDisplay: this._lastDetailTotal
                }).catch(e => console.error('Smartphone Shop App | Order record failed:', e));
            }
        } catch (e) {
            console.error('Smartphone Shop App | Purchase failed:', e);
            this.resultBanner = { success: false, text: loc('errors.generic') };
        } finally {
            this._purchasing = false;
        }
        this.render();
    }

    _errorText(errorCode, messageKey) {
        if (errorCode) {
            const key = `${L}.errors.${errorCode}`;
            const localized = game.i18n.localize(key);
            if (localized !== key) return localized;
        }
        if (messageKey) {
            const localized = game.i18n.localize(messageKey);
            if (localized !== messageKey) return localized;
        }
        return loc('errors.generic');
    }

    /* ------------------------------------------------------------------ */
    /*  공통 조각                                                            */
    /* ------------------------------------------------------------------ */

    _screen(titleHtml, backAction, bodyHtml, headerRightHtml = '') {
        const catalogChromeViews = ['list', 'departments', 'results'];
        const buyerStripViews = ['list', 'departments', 'results', 'cart', 'account', 'wishlist', 'orders'];
        const commerceChrome = (catalogChromeViews.includes(this.view) || buyerStripViews.includes(this.view))
            ? this._commerceChrome({
                showSearch: this.supportsCatalogApi && catalogChromeViews.includes(this.view),
                showBuyer: buyerStripViews.includes(this.view)
            })
            : '';
        const bottomNav = this._showBottomNav() ? this._bottomNav() : '';
        return `
            <div class="stylish-shop-app theme-${this.theme} view-${this.view}">
                <div class="app-header">
                    <button class="back-btn" data-action="${backAction}"><i class="fas fa-arrow-left"></i></button>
                    ${titleHtml}
                    ${headerRightHtml}
                </div>
                ${commerceChrome}
                <div class="app-content ssa-content">
                    ${bodyHtml}
                </div>
                ${bottomNav}
            </div>
        `;
    }

    _commerceChrome({ showSearch = false, showBuyer = true } = {}) {
        const search = showSearch ? `
            <div class="ssa-global-search">
                <i class="fas fa-magnifying-glass"></i>
                <input type="search" data-field="catalog-search" value="${esc(this._catalogQuery)}"
                       placeholder="${esc(loc('catalog.searchPlaceholder'))}" autocomplete="off">
                ${this._catalogLoading ? '<i class="fas fa-spinner fa-spin"></i>' : ''}
            </div>` : '';
        return `<div class="ssa-commerce-chrome">${search}${showBuyer ? this._buyerStrip() : ''}</div>`;
    }

    _buyerStrip() {
        const buyer = this.buyerActor;
        if (!buyer) {
            return `
                <div class="ssa-buyer-strip missing">
                    <span class="ssa-buyer-avatar"><i class="fas fa-user-slash"></i></span>
                    <span class="ssa-buyer-meta"><em>${esc(loc('buyer.label'))}</em><strong>${esc(loc('buyer.missing'))}</strong></span>
                </div>`;
        }
        return `
            <div class="ssa-buyer-strip">
                <img class="ssa-buyer-avatar" src="${esc(buyer.img || 'icons/svg/mystery-man.svg')}" alt="">
                <span class="ssa-buyer-meta"><em>${esc(loc('buyer.label'))}</em><strong>${esc(buyer.name)}</strong></span>
                <button class="ssa-wallet-shortcut" data-action="open-wallet-app"><i class="fas fa-wallet"></i>${esc(loc('buyer.wallet'))}</button>
            </div>`;
    }

    _bottomNav() {
        const active = this._activeRootTab();
        const buyer = this.buyerActor;
        const cartCount = buyer ? getCartCount(buyer.id) : 0;
        const tab = (id, icon, label, badge = 0) => `
            <button class="ssa-tabbar-btn ${active === id ? 'active' : ''}" data-action="tab-${id}">
                <span class="ssa-tabbar-icon"><i class="fas fa-${icon}"></i>${badge > 0 ? `<b class="ssa-tab-badge">${badge > 99 ? '99+' : badge}</b>` : ''}</span>
                <span>${esc(label)}</span>
            </button>`;
        return `
            <nav class="ssa-tabbar" aria-label="${esc(loc('title'))}">
                ${tab('home', 'house', loc('nav.home'))}
                ${tab('departments', 'grip', loc('nav.categories'))}
                ${tab('cart', 'cart-shopping', loc('nav.cart'), cartCount)}
                ${tab('account', 'user', loc('nav.account'))}
            </nav>`;
    }

    _titleHtml(text, emphasis = false) {
        return `<h3>${emphasis ? remph(text) : esc(text)}</h3>`;
    }

    _notice(icon, text) {
        return `
            <div class="ssa-notice">
                <i class="fas fa-${icon}"></i>
                <p>${esc(text)}</p>
            </div>
        `;
    }

    /** 지갑 칩. 잔액 데이터가 있으면 탭해서 전체 잔액 시트를 열 수 있습니다. */
    _walletChip(wallet) {
        const display = wallet?.display ?? '---';
        const clickable = Array.isArray(wallet?.balances) && wallet.balances.length > 0;
        if (!clickable) {
            return `<span class="ssa-wallet-chip"><i class="fas fa-coins"></i><span class="ssa-wallet-text">${esc(display)}</span></span>`;
        }
        return `
            <button class="ssa-wallet-chip" data-action="wallet-open" title="${esc(loc('walletTitle'))}">
                <i class="fas fa-coins"></i><span class="ssa-wallet-text">${esc(display)}</span><i class="fas fa-chevron-down ssa-wallet-caret"></i>
            </button>`;
    }

    /* ------------------------------------------------------------------ */
    /*  지갑 잔액 시트 (재렌더 없이 DOM으로만 열고 닫음)                        */
    /* ------------------------------------------------------------------ */

    _openWalletSheet() {
        if (!this.element || this.element.querySelector('.ssa-sheet-wrap')) return;
        const balances = this._walletInfo?.balances ?? [];
        const rows = balances.length
            ? balances.map(b => `
                <div class="ssa-bal-row">
                    <span class="ssa-bal-name">${esc(b.name || b.abbreviation || b.id)}</span>
                    <span class="ssa-bal-amt">${Number(b.amount ?? 0).toLocaleString()}<em>${esc(b.abbreviation ?? '')}</em></span>
                </div>`).join('')
            : `<div class="ssa-bal-empty">${esc(loc('walletEmpty'))}</div>`;

        const sheet = this.createElement(`
            <div class="ssa-sheet-wrap">
                <div class="ssa-sheet-backdrop" data-action="wallet-close"></div>
                <div class="ssa-sheet">
                    <div class="ssa-sheet-head">
                        <span>${esc(loc('walletTitle'))}</span>
                        <button data-action="wallet-close"><i class="fas fa-xmark"></i></button>
                    </div>
                    <div class="ssa-sheet-body">${rows}</div>
                </div>
            </div>
        `);
        sheet.addEventListener('pointerdown', (e) => e.stopPropagation()); // 폰 드래그 방지
        this.element.appendChild(sheet);
        requestAnimationFrame(() => sheet.classList.add('open'));
    }

    _closeWalletSheet() {
        const sheet = this.element?.querySelector('.ssa-sheet-wrap');
        if (!sheet) return;
        sheet.classList.remove('open');
        setTimeout(() => sheet.remove(), 200);
    }

    _banner() {
        if (!this.resultBanner) return '';
        const { success, text } = this.resultBanner;
        return `
            <div class="ssa-banner ${success ? 'success' : 'error'}">
                <i class="fas fa-${success ? 'check-circle' : 'exclamation-circle'}"></i>
                <span>${esc(text)}</span>
            </div>
        `;
    }

    /** GM이 입력한 상점 강조색을 CSS 변수로. 값이 없으면 기본 accent 유지. */
    _accentStyle(color) {
        const clean = String(color ?? '').trim();
        if (!clean) return '';
        return ` style="--ssa-accent:${esc(clean)}"`;
    }

    /** 원가 대비 실제 할인율(%). 개인/호감도 할인이 반영된 최종가 기준. */
    _discountPct(item) {
        const orig = Number(item.originalPrice) || 0;
        const now = Number(item.price) || 0;
        if (!item.hasDiscount || orig <= 0 || now >= orig) return 0;
        return Math.round((1 - now / orig) * 100);
    }

    /* ------------------------------------------------------------------ */
    /*  화면 1: 스토어 목록                                                  */
    /* ------------------------------------------------------------------ */

    /** 홈: 실제 쇼핑몰처럼 상품 피드가 우선, 스토어는 가로 레일로. */
    async _buildListScreen() {
        if (this.supportsCatalogApi) {
            try {
                return await this._buildCatalogHomeScreen();
            } catch (error) {
                console.error('Smartphone Shop App | Catalog home failed; using legacy feed.', error);
            }
        }
        return this._buildLegacyListScreen();
    }

    async _getCatalogTaxonomy({ force = false } = {}) {
        if (typeof this.api?.getCatalogTaxonomy !== 'function') return [];
        const buyerId = this.buyerActor?.id ?? null;
        if (!force && this._catalogTaxonomy && this._catalogTaxonomyBuyerId === buyerId) return this._catalogTaxonomy;
        const response = await this.api.getCatalogTaxonomy({ buyerActorId: buyerId });
        if (!response?.ok) return [];
        this._catalogTaxonomy = listOf(response.categories);
        this._catalogTaxonomyBuyerId = buyerId;
        return this._catalogTaxonomy;
    }

    async _getCatalogHome({ force = false } = {}) {
        const buyerId = this.buyerActor?.id ?? null;
        if (!force && this._catalogHome && this._catalogHomeBuyerId === buyerId) return this._catalogHome;
        const response = await this.api.getCatalogHome({ buyerActorId: buyerId, sectionLimit: 8 });
        if (!response?.ok) throw new Error(response?.error ?? 'CATALOG_HOME_FAILED');
        this._catalogHome = response;
        this._catalogHomeBuyerId = buyerId;
        this._catalogTaxonomy = listOf(response.categories);
        this._catalogTaxonomyBuyerId = buyerId;
        return response;
    }

    _departmentCard(category) {
        const images = listOf(category?.images).filter(Boolean).slice(0, 4);
        const mosaic = images.length
            ? images.map(src => `<img class="ssa-dept-image" src="${esc(src)}" alt="">`).join('')
            : `<span class="ssa-dept-image fallback"><i class="${esc(category?.icon || 'fas fa-box-open')}"></i></span>`;
        return `
            <button class="ssa-dept-card" data-action="open-department" data-category-id="${esc(category?.id)}">
                <span class="ssa-dept-mosaic count-${Math.min(4, Math.max(1, images.length))}">${mosaic}</span>
                <span class="ssa-dept-label">${esc(category?.label || category?.name || category?.id)}</span>
                <span class="ssa-dept-count">${Number(category?.itemCount ?? 0).toLocaleString()}</span>
            </button>`;
    }

    _railProductCard(item) {
        const shopId = item?.shopId ?? this.shopId;
        const wish = this._wishBtnHtml(item, shopId, { shopName: item?.shopName ?? '' });
        return `
            <div class="ssa-rail-product" data-action="open-item" data-uuid="${esc(item?.uuid)}" data-shop-id="${esc(shopId)}">
                <span class="ssa-rail-product-img"><img src="${esc(item?.img || 'icons/svg/item-bag.svg')}" alt="">${wish}</span>
                <span class="ssa-rail-product-name">${esc(item?.name ?? '')}</span>
                ${item?.shopName ? `<span class="ssa-rail-product-shop">${remph(item.shopName)}</span>` : ''}
                <span class="ssa-rail-product-price">${esc(item?.priceDisplay ?? '')}</span>
            </div>`;
    }

    _discoverySection(section, { tag = null } = {}) {
        const items = listOf(section?.items);
        if (items.length === 0) return '';
        const sectionId = section?.id ?? '';
        return `
            <section class="ssa-home-block">
                <div class="ssa-home-head">
                    <span class="ssa-home-title">${section?.icon ? `<i class="${esc(section.icon)}"></i>` : ''}${esc(section?.label || '')}</span>
                    <button class="ssa-home-link" data-action="open-catalog-section" data-section-id="${esc(sectionId)}"${tag ? ` data-tag="${esc(tag)}"` : ''}>${esc(loc('catalog.all'))}</button>
                </div>
                <div class="ssa-product-rail">${items.map(item => this._railProductCard(item)).join('')}</div>
            </section>`;
    }

    _shopRailHtml(rows) {
        if (!rows.length) return '';
        return `
            <section class="ssa-home-block">
                <div class="ssa-home-head"><span class="ssa-home-title">${esc(loc('catalog.sections.shops'))}</span></div>
                <div class="ssa-store-rail">
                    ${rows.map(row => `
                        <div class="ssa-rail-item${row.publicShop ? '' : ' private'}" data-action="open-shop" data-shop-id="${esc(row.id)}"${this._accentStyle(row.accentColor)}>
                            <img class="ssa-rail-logo" src="${esc(row.img)}" alt="">
                            ${row.sale?.active ? `<span class="ssa-rail-sale">${row.sale.percent}%</span>` : ''}
                            <span class="ssa-rail-name">${remph(row.name)}</span>
                        </div>`).join('')}
                </div>
            </section>`;
    }

    async _buildCatalogHomeScreen() {
        const home = await this._getCatalogHome();
        const buyer = this.buyerActor;
        const categories = listOf(home.categories);
        const featuredCategories = categories.filter(category => Number(category.itemCount ?? category.count) > 0);
        const sections = listOf(home.sections);
        const collections = listOf(home.collections);
        const shops = listOf(home.shops).length ? listOf(home.shops) : this.api.getShopDirectory();
        const buyerNotice = buyer ? '' : `<div class="ssa-subnotice"><i class="fas fa-user-slash"></i> ${esc(loc('noBuyer'))}</div>`;

        const promoTarget = sections.find(section => section.id === 'on-sale')
            ?? sections.find(section => section.id === 'available-now')
            ?? null;
        const promoAction = promoTarget
            ? `data-action="open-catalog-section" data-section-id="${esc(promoTarget.id)}"`
            : 'data-action="tab-departments"';
        const promo = `
            <section class="ssa-promo-card" ${promoAction}>
                <span class="ssa-promo-kicker">${esc(loc('promo.kicker'))}</span>
                <strong class="ssa-promo-title">${esc(promoTarget?.label || loc('promo.title'))}</strong>
                <span class="ssa-promo-body">${esc(loc('promo.body'))}</span>
                <i class="fas fa-arrow-right"></i>
            </section>`;
        const categoryBlock = featuredCategories.length ? `
            <section class="ssa-home-block">
                <div class="ssa-home-head">
                    <span class="ssa-home-title">${esc(loc('catalog.categoriesTitle'))}</span>
                    <button class="ssa-home-link" data-action="tab-departments">${esc(loc('catalog.allCategories'))}</button>
                </div>
                <div class="ssa-dept-grid">${featuredCategories.slice(0, 6).map(cat => this._departmentCard(cat)).join('')}</div>
            </section>` : '';

        const knownOrder = ['on-sale', 'available-now', 'affinity'];
        sections.sort((a, b) => {
            const ai = knownOrder.indexOf(a.id);
            const bi = knownOrder.indexOf(b.id);
            return (ai < 0 ? 99 : ai) - (bi < 0 ? 99 : bi);
        });
        const sectionHtml = sections.map(section => this._discoverySection(section)).join('');
        const collectionHtml = collections.slice(0, 3).map(collection => this._discoverySection({
            id: `tag:${collection.tag ?? collection.id}`,
            label: collection.label,
            icon: 'fas fa-tags',
            items: collection.items
        }, { tag: collection.tag ?? collection.id })).join('');

        const body = `
            ${buyerNotice}
            ${promo}
            ${categoryBlock}
            ${sectionHtml}
            ${collectionHtml}
            ${this._recentRailHtml()}
            ${this._shopRailHtml(shops)}
            ${this._footer()}`;
        const createBtn = game.user.isGM
            ? `<button class="ssa-icon-btn" data-action="create-shop" title="${esc(loc('manage.createTitle'))}"><i class="fas fa-plus"></i></button>`
            : '';
        return this._screen(logoHtml(this.storefrontName, this.storefrontBranding), 'home', body, createBtn);
    }

    async _buildLegacyListScreen() {
        const rows = this.api.getShopDirectory();
        const buyer = this.buyerActor;

        let body;
        if (rows.length === 0) {
            body = this._notice('store-slash', loc('emptyDirectory'));
        } else {
            // 프로모 배너 캐러셀 — 공개 상점들을 자동 회전 (최대 8개)
            const bannerRows = rows.slice(0, 8);
            const startIdx = bannerRows.length ? (this._bannerIndex % bannerRows.length) : 0;
            this._bannerIndex = startIdx;
            const slides = bannerRows.map(r => `
                <div class="ssa-feature" data-action="open-shop" data-shop-id="${esc(r.id)}"${this._accentStyle(r.accentColor)}>
                    <img class="ssa-feature-logo" src="${esc(r.img)}" alt="">
                    <div class="ssa-feature-info">
                        <div class="ssa-feature-name">${remph(r.name)}</div>
                        ${r.sale?.active
                            ? `<div class="ssa-feature-sub"><span class="ssa-sale-flag">SALE ${r.sale.percent}%</span> ${esc(r.sale.label || loc('sale.defaultLabel'))}</div>`
                            : (r.subtitle ? `<div class="ssa-feature-sub">${remph(r.subtitle)}</div>` : '')}
                    </div>
                    <span class="ssa-feature-go">${esc(loc('featuredGo'))} <i class="fas fa-chevron-right"></i></span>
                </div>
            `).join('');
            const dots = bannerRows.length > 1 ? `
                <div class="ssa-feature-dots">
                    ${bannerRows.map((_, i) => `<span class="ssa-feature-dot ${i === startIdx ? 'active' : ''}" data-action="banner-dot" data-index="${i}"></span>`).join('')}
                </div>
            ` : '';
            const featuredBanner = `
                <div class="ssa-feature-carousel">
                    <div class="ssa-feature-track" style="transform:translateX(-${startIdx * 100}%)">${slides}</div>
                    ${dots}
                </div>
            `;

            // 스토어 가로 레일 (보조 내비게이션)
            const rail = `
                <div class="ssa-rail-head">${esc(loc('storesTitle'))}</div>
                <div class="ssa-store-rail">
                    ${rows.map(row => `
                        <div class="ssa-rail-item${row.publicShop ? '' : ' private'}" data-action="open-shop" data-shop-id="${esc(row.id)}"${this._accentStyle(row.accentColor)}>
                            <img class="ssa-rail-logo" src="${esc(row.img)}" alt="">
                            ${row.sale?.active ? `<span class="ssa-rail-sale">${row.sale.percent}%</span>` : ''}
                            <span class="ssa-rail-name">${remph(row.name)}</span>
                        </div>
                    `).join('')}
                </div>
            `;

            // 전 상점 상품 피드 (stylish-shop 1.7.0+ getProductFeed)
            let feedSection = '';
            if (typeof this.api.getProductFeed === 'function') {
                const feed = await this.api.getProductFeed({ buyerActorId: buyer?.id ?? null });
                const feedRows = feed.items.map(item => this._productCard(item, { showShop: true })).join('');
                feedSection = `
                    <div class="ssa-section-head">
                        <span class="ssa-section-title">${esc(loc('allProducts'))}</span>
                        <span class="ssa-section-count" data-role="result-count">${feed.total}</span>
                    </div>
                    ${feed.items.length === 0
                        ? `<div class="ssa-notice"><i class="fas fa-box-open"></i><p>${esc(loc('feedEmpty'))}</p></div>`
                        : `<div class="ssa-product-list">${feedRows}</div>`}
                `;
            }

            body = `
                <div class="ssa-section">
                    <div class="ssa-search">
                        <i class="fas fa-magnifying-glass"></i>
                        <input type="text" data-field="item-search" placeholder="${esc(loc('itemSearchPlaceholder'))}">
                    </div>
                </div>
                ${featuredBanner}
                ${rail}
                ${this._recentRailHtml()}
                ${feedSection}
                ${this._footer()}
            `;
        }

        const buyerNotice = buyer ? '' : `<div class="ssa-subnotice"><i class="fas fa-user-slash"></i> ${esc(loc('noBuyer'))}</div>`;
        const wishBtn = buyer
            ? `<button class="ssa-icon-btn" data-action="open-wishlist" title="${esc(loc('wish.title'))}"><i class="fas fa-heart"></i></button>`
            : '';
        const cartCount = buyer ? getCartCount(buyer.id) : 0;
        const cartBtn = buyer
            ? `<button class="ssa-icon-btn ssa-cart-icon" data-action="open-cart" title="${esc(loc('cart.title'))}">
                   <i class="fas fa-cart-shopping"></i>
                   ${cartCount > 0 ? `<span class="ssa-cart-badge">${cartCount > 9 ? '9+' : cartCount}</span>` : ''}
               </button>`
            : '';
        const createBtn = game.user.isGM
            ? `<button class="ssa-icon-btn" data-action="create-shop" title="${esc(loc('manage.createTitle'))}"><i class="fas fa-plus"></i></button>`
            : '';
        return this._screen(logoHtml(this.storefrontName, this.storefrontBranding), 'home', buyerNotice + body, wishBtn + cartBtn + createBtn);
    }

    _buildAppSettingsScreen() {
        if (!game.user.isGM) {
            return this._screen(this._titleHtml(loc('settings.title')), 'back', this._notice('lock', loc('manage.gmOnly')));
        }

        if (!this._appSettingsDraft) {
            const branding = readStorefrontBranding();
            this._appSettingsDraft = {
                name: branding.name,
                iconMode: branding.iconMode,
                iconClass: branding.iconClass,
                iconImage: branding.iconImage
            };
        }
        const draft = this._appSettingsDraft;
        const iconModes = [
            { id: 'default', icon: 'fas fa-bolt', label: loc('settings.iconModeDefault') },
            { id: 'fontawesome', icon: 'fas fa-icons', label: loc('settings.iconModeFontAwesome') },
            { id: 'image', icon: 'fas fa-image', label: loc('settings.iconModeImage') }
        ];

        const banner = this._settingsBanner
            ? `<div class="ssa-banner ${this._settingsBanner.success ? 'success' : 'error'} ssa-settings-banner">
                   <i class="fas fa-${this._settingsBanner.success ? 'check-circle' : 'exclamation-circle'}"></i>
                   <span>${esc(this._settingsBanner.text)}</span>
               </div>`
            : '';
        const body = `
            <section class="ssa-settings-intro">
                <i class="fas fa-store"></i>
                <div>
                    <strong>${esc(loc('settings.title'))}</strong>
                    <span>${esc(loc('settings.description'))}</span>
                </div>
            </section>
            <section class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(loc('settings.storefrontName'))}</span></div>
                <div class="ssa-form-row">
                    <input type="text" class="ssa-input" data-field="storefront-name" value="${esc(draft.name)}"
                           maxlength="40" aria-label="${esc(loc('settings.storefrontName'))}"
                           placeholder="${esc(loc('settings.storefrontNamePlaceholder'))}">
                    <p class="ssa-settings-hint">${esc(loc('settings.storefrontNameHint'))}</p>
                </div>
            </section>
            <section class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(loc('settings.storefrontIcon'))}</span></div>
                <div class="ssa-brand-mode-grid" role="radiogroup" aria-label="${esc(loc('settings.storefrontIcon'))}">
                    ${iconModes.map(mode => `
                        <label class="ssa-brand-mode-option ${draft.iconMode === mode.id ? 'active' : ''}">
                            <input type="radio" name="ssa-storefront-icon-mode" data-field="storefront-icon-mode"
                                   value="${mode.id}" ${draft.iconMode === mode.id ? 'checked' : ''}>
                            <i class="${mode.icon}"></i>
                            <span>${esc(mode.label)}</span>
                        </label>`).join('')}
                </div>
                <p class="ssa-settings-hint">${esc(loc('settings.storefrontIconHint'))}</p>
                <div class="ssa-form-row ssa-brand-mode-panel" data-icon-mode-panel="fontawesome" ${draft.iconMode === 'fontawesome' ? '' : 'hidden'}>
                    <span class="ssa-form-label">${esc(loc('settings.iconClass'))}</span>
                    <input type="text" class="ssa-input" data-field="storefront-icon-class" value="${esc(draft.iconClass)}"
                           maxlength="120" autocomplete="off" spellcheck="false"
                           placeholder="${esc(loc('settings.iconClassPlaceholder'))}">
                    <p class="ssa-settings-hint">${esc(loc('settings.iconClassHint'))}</p>
                </div>
                <div class="ssa-form-row ssa-brand-mode-panel" data-icon-mode-panel="image" ${draft.iconMode === 'image' ? '' : 'hidden'}>
                    <span class="ssa-form-label">${esc(loc('settings.iconImage'))}</span>
                    <div class="ssa-inline-row ssa-brand-image-row">
                        <input type="text" class="ssa-input" data-field="storefront-icon-image" value="${esc(draft.iconImage)}"
                               maxlength="500" autocomplete="off" spellcheck="false"
                               placeholder="${esc(loc('settings.iconImagePlaceholder'))}">
                        <button type="button" class="ssa-mini-btn" data-action="pick-storefront-icon-image">
                            <i class="fas fa-folder-open"></i><span>${esc(loc('settings.chooseImage'))}</span>
                        </button>
                    </div>
                    <p class="ssa-settings-hint">${esc(loc('settings.iconImageHint'))}</p>
                </div>
                <div class="ssa-brand-preview">
                    <span class="ssa-form-label">${esc(loc('settings.preview'))}</span>
                    <div class="ssa-brand-preview-surface" data-role="storefront-brand-preview">
                        ${logoHtml(draft.name, draft)}
                    </div>
                </div>
                ${banner}
                <button class="ssa-mini-btn primary ssa-settings-save" data-action="save-app-settings" ${this._savingAppSettings ? 'disabled' : ''}>
                    ${this._savingAppSettings ? '<i class="fas fa-spinner fa-spin"></i>' : '<i class="fas fa-floppy-disk"></i>'}
                    <span>${esc(loc(this._savingAppSettings ? 'settings.saving' : 'settings.save'))}</span>
                </button>
            </section>
            <section class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(loc('settings.catalogCategories'))}</span></div>
                <p class="ssa-settings-hint">${esc(loc('settings.catalogCategoriesHint'))}</p>
                <button type="button" class="ssa-mini-btn ssa-settings-catalog" data-action="open-catalog-category-manager">
                    <i class="fas fa-layer-group"></i>
                    <span>${esc(loc('settings.manageCatalogCategories'))}</span>
                    <i class="fas fa-arrow-up-right-from-square"></i>
                </button>
            </section>
        `;
        return this._screen(this._titleHtml(loc('settings.title')), 'back', body);
    }

    _syncStorefrontBrandingEditor() {
        if (!this.element || this.view !== 'settings') return;
        const nameInput = this.element.querySelector('[data-field="storefront-name"]');
        const classInput = this.element.querySelector('[data-field="storefront-icon-class"]');
        const imageInput = this.element.querySelector('[data-field="storefront-icon-image"]');
        const checkedMode = this.element.querySelector('[data-field="storefront-icon-mode"]:checked');
        if (!nameInput || !classInput || !imageInput || !checkedMode) return;

        const draft = {
            name: String(nameInput.value ?? ''),
            iconMode: storefrontIconMode(checkedMode.value),
            iconClass: String(classInput.value ?? ''),
            iconImage: String(imageInput.value ?? '')
        };
        this._appSettingsDraft = draft;

        for (const option of this.element.querySelectorAll('.ssa-brand-mode-option')) {
            option.classList.toggle('active', option.querySelector('input')?.checked === true);
        }
        for (const panel of this.element.querySelectorAll('[data-icon-mode-panel]')) {
            panel.hidden = panel.dataset.iconModePanel !== draft.iconMode;
        }

        const preview = this.element.querySelector('[data-role="storefront-brand-preview"]');
        if (!preview) return;
        preview.innerHTML = logoHtml(draft.name, draft);
        const previewImage = preview.querySelector('img.ssa-logo-mark-image');
        if (previewImage) {
            previewImage.addEventListener('error', () => {
                if (previewImage.dataset.fallbackApplied) return;
                previewImage.dataset.fallbackApplied = '1';
                previewImage.src = 'icons/svg/item-bag.svg';
            }, { once: true });
        }
    }

    _pickStorefrontIconImage() {
        if (!game.user.isGM) return;
        this._syncStorefrontBrandingEditor();
        const current = this._appSettingsDraft?.iconImage ?? '';
        this.selectImageSource(async (path) => {
            const draft = this._appSettingsDraft ?? readStorefrontBranding();
            const selectedPath = String(path ?? '').trim();
            this._appSettingsDraft = {
                ...draft,
                iconMode: 'image',
                iconImage: selectedPath
            };
            if (selectedPath && !(await storefrontIconImageLoads(selectedPath))) {
                this._settingsBanner = { success: false, text: loc('settings.imageInvalid') };
            }
            await this.render();
        }, current, {});
    }

    async _saveAppSettings() {
        if (!game.user.isGM || this._savingAppSettings) return;
        this._syncStorefrontBrandingEditor();
        if (!this._appSettingsDraft) return;

        const rawImage = String(this._appSettingsDraft.iconImage ?? '').trim();
        const values = {
            name: String(this._appSettingsDraft.name ?? '').trim(),
            iconMode: storefrontIconMode(this._appSettingsDraft.iconMode),
            iconClass: storefrontIconClass(this._appSettingsDraft.iconClass),
            iconImage: storefrontIconImage(rawImage)
        };
        this._appSettingsDraft = values;
        this._savingAppSettings = true;
        this._settingsBanner = null;
        const button = this.element?.querySelector('[data-action="save-app-settings"]');
        if (button) {
            button.disabled = true;
            button.innerHTML = `<i class="fas fa-spinner fa-spin"></i><span>${esc(loc('settings.saving'))}</span>`;
        }

        try {
            if (values.iconMode === 'image' && rawImage && !(await storefrontIconImageLoads(rawImage))) {
                this._settingsBanner = { success: false, text: loc('settings.imageInvalid') };
                return;
            }
            await Promise.all([
                game.settings.set(MODULE_ID, 'storefrontName', values.name),
                game.settings.set(MODULE_ID, 'storefrontIconMode', values.iconMode),
                game.settings.set(MODULE_ID, 'storefrontIconClass', values.iconClass),
                game.settings.set(MODULE_ID, 'storefrontIconImage', values.iconImage)
            ]);
            this._settingsBanner = { success: true, text: loc('settings.saved') };
            this.widget.showToastNotification?.(loc('settings.saved'));
        } catch (e) {
            console.error('Smartphone Shop App | Failed to save app settings:', e);
            this._appSettingsDraft = readStorefrontBranding();
            this._settingsBanner = { success: false, text: loc('errors.generic') };
        } finally {
            this._savingAppSettings = false;
            this.render();
        }
    }

    async _buildDepartmentsScreen() {
        if (!this.supportsCatalogApi) {
            return this._screen(this._titleHtml(loc('nav.categories')), 'back', this._notice('layer-group', loc('catalog.empty')));
        }
        const categories = await this._getCatalogTaxonomy();
        const body = categories.length
            ? `<section class="ssa-home-block"><div class="ssa-dept-grid">${categories.map(cat => this._departmentCard(cat)).join('')}</div></section>${this._shopRailHtml(this.api.getShopDirectory())}${this._footer()}`
            : this._notice('layer-group', loc('catalog.empty'));
        return this._screen(this._titleHtml(loc('catalog.categoriesTitle')), 'back', body);
    }

    _openCatalogResults({ categoryId = null, sectionId = null, tag = null, query = '', shopId = null } = {}) {
        if (!this.supportsCatalogApi) return;
        this._cancelCatalogSearch();
        const filters = this._defaultCatalogFilters();
        if (categoryId) filters.categoryIds = [categoryId];
        if (shopId) filters.shopIds = [shopId];
        if (tag) filters.tags = [tag];
        if (sectionId === 'on-sale') filters.onSale = true;
        if (sectionId === 'available-now') filters.purchasable = true;
        if (sectionId === 'affinity') filters.affinity = true;
        this._catalogFilters = filters;
        this._catalogCategoryId = categoryId;
        this._catalogSection = sectionId;
        this._catalogCollectionId = tag;
        this._catalogQuery = query ?? '';
        this._catalogResults = null;
        this._catalogCursor = null;
        this._catalogError = null;
        this._navigate('results');
        this._runCatalogSearch({ reset: true });
    }

    _scheduleCatalogSearch(value) {
        this._catalogQuery = String(value ?? '');
        if (this._catalogSearchTimer) clearTimeout(this._catalogSearchTimer);
        const scheduledView = this.view;
        this._catalogSearchTimer = setTimeout(() => {
            this._catalogSearchTimer = null;
            if (this.view !== scheduledView) return;
            if (this.view !== 'results') this._openCatalogResults({ query: this._catalogQuery });
            else this._runCatalogSearch({ reset: true });
        }, 200);
    }

    _toggleCatalogFilter(filter, value = '') {
        if (!filter) return;
        const arrayFields = { category: 'categoryIds', shop: 'shopIds', type: 'itemTypes', tag: 'tags' };
        const arrayField = arrayFields[filter];
        if (arrayField) {
            const selected = new Set(this._catalogFilters[arrayField] ?? []);
            if (selected.has(value)) selected.delete(value);
            else if (value) selected.add(value);
            this._catalogFilters[arrayField] = [...selected];
        } else if (Object.hasOwn(this._catalogFilters, filter) && typeof this._catalogFilters[filter] === 'boolean') {
            this._catalogFilters[filter] = !this._catalogFilters[filter];
        }
        this._catalogCategoryId = this._catalogFilters.categoryIds[0] ?? null;
        this._runCatalogSearch({ reset: true });
    }

    _catalogSearchOptions({ cursor = null } = {}) {
        const filters = this._catalogFilters;
        const priceComparable = this._catalogResults?.priceComparable === true
            || this._catalogResults?.facets?.priceComparable === true
            || filters.shopIds.length === 1;
        if (!priceComparable && String(filters.sort).startsWith('price')) filters.sort = 'default';
        return {
            buyerActorId: this.buyerActor?.id ?? null,
            query: this._catalogQuery.trim(),
            categoryIds: uniqueStrings(filters.categoryIds),
            shopIds: uniqueStrings(filters.shopIds),
            inStock: filters.inStock === true,
            onSale: filters.onSale === true,
            unlocked: filters.unlocked === true,
            affinity: filters.affinity === true,
            affordable: filters.affordable === true,
            purchasable: filters.purchasable === true,
            itemTypes: uniqueStrings(filters.itemTypes),
            tags: uniqueStrings(filters.tags),
            sort: filters.sort || 'default',
            cursor,
            limit: 24
        };
    }

    async _runCatalogSearch({ reset = false, append = false } = {}) {
        if (typeof this.api?.searchCatalog !== 'function') return;
        if (append && this._catalogLoading) return;
        const seq = ++this._catalogSearchSeq;
        if (reset) {
            this._catalogCursor = null;
            this._catalogResults = null;
        }
        this._catalogLoading = true;
        this._catalogError = null;
        try {
            const response = await this.api.searchCatalog(this._catalogSearchOptions({ cursor: append ? this._catalogCursor : null }));
            if (seq !== this._catalogSearchSeq) return;
            if (!response?.ok) throw new Error(response?.error ?? 'CATALOG_SEARCH_FAILED');
            if (response.priceComparable !== true
                && this._catalogFilters.shopIds.length !== 1
                && String(this._catalogFilters.sort).startsWith('price')) {
                this._catalogFilters.sort = 'default';
            }
            const previous = append ? listOf(this._catalogResults?.items) : [];
            const seen = new Set(previous.map(item => item.offerId ?? `${item.shopId}:${item.uuid}`));
            const next = listOf(response.items).filter(item => {
                const key = item.offerId ?? `${item.shopId}:${item.uuid}`;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            });
            this._catalogResults = { ...response, items: [...previous, ...next] };
            this._catalogCursor = response.nextCursor ?? null;
        } catch (error) {
            console.error('Smartphone Shop App | Catalog search failed:', error);
            if (seq === this._catalogSearchSeq) this._catalogError = error;
        } finally {
            if (seq === this._catalogSearchSeq) {
                this._catalogLoading = false;
                if (this.view === 'results') this.render();
            }
        }
    }

    _catalogFilterChip(filter, label, { value = '', active = false } = {}) {
        return `<button class="ssa-filter-chip ${active ? 'active' : ''}" data-action="catalog-filter" data-filter="${esc(filter)}" data-value="${esc(value)}">${esc(label)}</button>`;
    }

    async _buildCatalogResultsScreen() {
        const taxonomy = await this._getCatalogTaxonomy();
        const data = this._catalogResults;
        const items = listOf(data?.items);
        const facets = data?.facets ?? {};
        const facetValue = row => typeof row === 'string' ? row : (row?.id ?? row?.value ?? row?.tag ?? '');
        const facetLabel = row => typeof row === 'string' ? row : (row?.label ?? row?.name ?? row?.id ?? row?.value ?? '');
        const chips = [
            ...taxonomy.map(cat => this._catalogFilterChip('category', cat.label, { value: cat.id, active: this._catalogFilters.categoryIds.includes(cat.id) })),
            this._catalogFilterChip('inStock', loc('filters.inStock'), { active: this._catalogFilters.inStock }),
            this._catalogFilterChip('onSale', loc('filters.onSale'), { active: this._catalogFilters.onSale }),
            this._catalogFilterChip('purchasable', loc('filters.purchasable'), { active: this._catalogFilters.purchasable }),
            this._catalogFilterChip('unlocked', loc('filters.unlocked'), { active: this._catalogFilters.unlocked }),
            this._catalogFilterChip('affinity', loc('filters.affinity'), { active: this._catalogFilters.affinity }),
            this._catalogFilterChip('affordable', loc('filters.affordable'), { active: this._catalogFilters.affordable }),
            ...listOf(facets.shops).slice(0, 4).map(shop => this._catalogFilterChip('shop', facetLabel(shop), { value: facetValue(shop), active: this._catalogFilters.shopIds.includes(facetValue(shop)) })),
            ...listOf(facets.itemTypes).slice(0, 4).map(type => this._catalogFilterChip('type', facetLabel(type), { value: facetValue(type), active: this._catalogFilters.itemTypes.includes(facetValue(type)) })),
            ...listOf(facets.tags).slice(0, 4).map(tag => this._catalogFilterChip('tag', `#${facetLabel(tag)}`, { value: facetValue(tag), active: this._catalogFilters.tags.includes(facetValue(tag)) }))
        ].join('');
        const hasFilters = this._catalogQuery.trim() || Object.entries(this._catalogFilters)
            .some(([key, value]) => key !== 'sort' && (Array.isArray(value) ? value.length > 0 : value === true));
        const clear = hasFilters ? `<button class="ssa-filter-chip clear" data-action="catalog-clear"><i class="fas fa-xmark"></i>${esc(loc('filters.clear'))}</button>` : '';
        const allowPriceSort = data?.priceComparable === true
            || data?.facets?.priceComparable === true
            || this._catalogFilters.shopIds.length === 1;
        const summary = data ? `
            <div class="ssa-results-summary">
                <span>${locf('itemsCount', { count: `<strong>${Number(data.total ?? items.length)}</strong>` })}</span>
                <select class="ssa-sort-select" data-field="catalog-sort">
                    <option value="default" ${this._catalogFilters.sort === 'default' ? 'selected' : ''}>${esc(loc('sortDefault'))}</option>
                    <option value="name" ${this._catalogFilters.sort === 'name' ? 'selected' : ''}>${esc(loc('filters.sortName'))}</option>
                    ${allowPriceSort ? `<option value="price-asc" ${this._catalogFilters.sort === 'price-asc' ? 'selected' : ''}>${esc(loc('sortPriceAsc'))}</option>` : ''}
                </select>
            </div>` : '';
        let content;
        if (this._catalogLoading && !data) content = this._notice('spinner fa-spin', loc('buying'));
        else if (this._catalogError) content = this._notice('triangle-exclamation', loc('errors.generic'));
        else if (items.length === 0) content = this._notice('box-open', loc('catalog.empty'));
        else content = `<div class="ssa-product-list">${items.map(item => this._productCard(item, { showShop: true })).join('')}</div>`;
        const more = data?.hasMore
            ? `<button class="ssa-load-more" data-action="catalog-load-more" ${this._catalogLoading ? 'disabled' : ''}>${this._catalogLoading ? '<i class="fas fa-spinner fa-spin"></i>' : ''}${esc(loc('catalog.loadMore'))}</button>`
            : '';
        return this._screen(this._titleHtml(loc('catalog.resultsTitle')), 'back', `<div class="ssa-filter-chips">${chips}${clear}</div>${summary}${content}${more}${this._footer()}`);
    }

    /** 웹 푸터 (인월드 서비스 데코) */
    _footer() {
        return `<div class="ssa-webfooter">${esc(this.storefrontName)} · REMOTE COMMERCE</div>`;
    }

    /* ------------------------------------------------------------------ */
    /*  화면 2: 상점 (스토어 배너 + 상품 그리드)                               */
    /* ------------------------------------------------------------------ */

    async _buildShopScreen() {
        const vm = await this.api.getShopViewModel(this.shopId, {
            buyerActorId: this.buyerActor?.id ?? null,
            categoryId: this.categoryId,
            paymentSource: this.paymentSource
        });
        if (!vm.ok) {
            return this._screen(this._titleHtml(loc('title')), 'back', this._notice('store-slash', loc('errors.shopGone')));
        }
        this.categoryId = vm.activeCategoryId;
        this._shopMeta = vm.shop;
        this._walletInfo = vm.wallet;

        const hero = this._storeHero(vm);

        const tabs = vm.categories.length > 1 ? `
            <div class="ssa-category-tabs">
                ${vm.categories.map(cat => `
                    <button class="ssa-category-tab ${cat.id === vm.activeCategoryId ? 'active' : ''}"
                            data-action="select-category" data-category-id="${esc(cat.id)}">
                        <span>${cat.icon && cat.icon.startsWith('fa') ? `<i class="${esc(cat.icon)}"></i>` : ''}${esc(cat.name)}</span>
                    </button>
                `).join('')}
            </div>
        ` : '';

        let items = [...vm.items];
        if (this.sortMode === 'asc') items.sort((a, b) => (a.priceBaseUnit ?? 0) - (b.priceBaseUnit ?? 0));
        else if (this.sortMode === 'desc') items.sort((a, b) => (b.priceBaseUnit ?? 0) - (a.priceBaseUnit ?? 0));

        const searchAndToolbar = items.length === 0 ? '' : `
            <div class="ssa-section">
                <div class="ssa-search">
                    <i class="fas fa-magnifying-glass"></i>
                    <input type="text" data-field="item-search" placeholder="${esc(loc('itemSearchPlaceholder'))}">
                </div>
                ${this.supportsCatalogApi ? `
                    <button class="ssa-search-global-cta" data-action="shop-search-global" data-role="shop-search-global" hidden>
                        <i class="fas fa-globe"></i>
                        <span>${esc(loc('catalog.searchThisStore'))} <strong data-role="shop-search-query"></strong></span>
                        <i class="fas fa-chevron-right"></i>
                    </button>` : ''}
            </div>
            ${tabs}
            <div class="ssa-filterbar">
                <span class="ssa-toolbar-count" data-role="result-count">${locf('itemsCount', { count: `<strong>${items.length}</strong>` })}</span>
                <select class="ssa-sort-select" data-field="sort-select">
                    <option value="default" ${this.sortMode === 'default' ? 'selected' : ''}>${esc(loc('sortDefault'))}</option>
                    <option value="asc" ${this.sortMode === 'asc' ? 'selected' : ''}>${esc(loc('sortPriceAsc'))}</option>
                    <option value="desc" ${this.sortMode === 'desc' ? 'selected' : ''}>${esc(loc('sortPriceDesc'))}</option>
                </select>
            </div>
        `;

        const grid = items.length === 0
            ? tabs + this._notice('box-open', loc('emptyCategory'))
            : `<div class="ssa-product-list">${items.map(item => this._productCard(item)).join('')}</div>${this._footer()}`;

        const sellBtn = vm.sell?.available
            ? `<button class="ssa-icon-btn" data-action="open-sell" title="${esc(loc('sell.open'))}"><i class="fas fa-hand-holding-dollar"></i></button>`
            : '';
        const manageBtn = game.user.isGM
            ? `<button class="ssa-icon-btn" data-action="manage" title="${esc(loc('manage.open'))}"><i class="fas fa-sliders"></i></button>`
            : '';
        return this._screen(this._titleHtml(vm.shop.name, true), 'back', hero + searchAndToolbar + grid, sellBtn + manageBtn + this._walletChip(vm.wallet));
    }

    _storeHero(vm) {
        const shop = vm.shop;
        const aff = vm.affinity;
        let affRow = '';
        if (aff?.enabled) {
            const progressPct = Math.round((aff.progress ?? 0) * 100);
            const chipText = aff.tierName
                ? `${esc(aff.tierName)} · ${esc(locf('affinityPoints', { points: aff.points }))}`
                : esc(locf('affinityPoints', { points: aff.points }));
            const nextText = aff.atMax
                ? loc('affinityMax')
                : locf('affinityToNext', { toNext: aff.toNext, tier: aff.nextTierName });
            affRow = `
                <div class="ssa-hero-affrow">
                    <span class="ssa-aff-chip"><i class="fas fa-heart"></i>${chipText}</span>
                    <span class="ssa-aff-bar"><span class="ssa-aff-fill" style="width:${progressPct}%"></span></span>
                    <span class="ssa-aff-next">${esc(nextText)}</span>
                </div>
            `;
        }
        const sale = shop.sale?.active
            ? `
                <div class="ssa-sale-strip">
                    <span class="ssa-sale-flag">SALE ${shop.sale.percent}%</span>
                    <span class="ssa-sale-name">${esc(shop.sale.label || loc('sale.defaultLabel'))}</span>
                    ${this._saleUntilText(shop.sale) ? `<span class="ssa-sale-until">${esc(locf('sale.until', { time: this._saleUntilText(shop.sale) }))}</span>` : ''}
                </div>`
            : '';
        return `
            <div class="ssa-store-hero"${this._accentStyle(shop.accentColor)}>
                <div class="ssa-hero-top">
                    <img class="ssa-hero-logo" src="${esc(shop.npcArt)}" alt="">
                    <div class="ssa-hero-titles">
                        <div class="ssa-hero-name">${remph(shop.name)}</div>
                        ${shop.owner || shop.ownerRole ? `<div class="ssa-hero-role">${esc([shop.owner, shop.ownerRole].filter(Boolean).join(' · '))}</div>` : ''}
                    </div>
                </div>
                ${sale}
                ${affRow}
                ${shop.greeting ? `<div class="ssa-hero-greeting">${esc(shop.greeting)}</div>` : ''}
            </div>
        `;
    }

    /** 상품 리스트 행 (웹 검색결과 스타일). showShop이면 판매처 라벨 표시(홈 피드용). */
    _productCard(item, { showShop = false } = {}) {
        const stateClass = [
            item.locked ? 'locked' : '',
            item.outOfStock ? 'oos' : '',
            item.unavailable ? 'unavailable' : ''
        ].filter(Boolean).join(' ');

        const pct = this._discountPct(item);
        const priceLine = `
            <div class="ssa-price-row">
                ${pct > 0 ? `<span class="ssa-price-pct">${pct}%</span>` : ''}
                <span class="ssa-price-final">${esc(item.priceDisplay)}</span>
                ${item.hasDiscount ? `<span class="ssa-price-orig">${esc(item.originalPriceDisplay)}</span>` : ''}
            </div>
        `;

        let subLine;
        if (item.locked) {
            subLine = `<span class="ssa-sub-lock"><i class="fas fa-lock"></i> ${esc(item.unlock?.buttonLabel || loc('locked'))}</span>`;
        } else if (item.outOfStock) {
            subLine = `<span class="ssa-sub-oos">${esc(loc('outOfStock'))}</span>`;
        } else {
            const bits = [];
            if (item.tag) bits.push(`<span class="ssa-badge ssa-badge-tag">${esc(item.tag)}</span>`);
            if (item.hasLimitedStock) {
                const low = typeof item.stock === 'number' && item.stock <= 3;
                bits.push(`<span class="ssa-product-stock${low ? ' low' : ''}">${esc(locf('stock', { stock: item.stock }))}</span>`);
            }
            subLine = bits.join('');
        }

        const shopAttr = showShop && item.shopId ? ` data-shop-id="${esc(item.shopId)}"` : '';
        const shopLabel = showShop && item.shopName
            ? `<div class="ssa-product-shop">${remph(item.shopName)}${item.catalogCategoryLabel ? ` · ${esc(item.catalogCategoryLabel)}` : ''}</div>`
            : '';
        const searchKey = `${item.name} ${item.kr ?? ''} ${item.shopCategoryName ?? item.categoryName ?? ''} ${item.catalogCategoryLabel ?? ''} ${listOf(item.catalogTags).join(' ')} ${showShop ? (item.shopName ?? '') : ''}`.replace(/\*\*/g, '').toLowerCase();
        const cardShopId = item.shopId ?? this.shopId;
        const cardShopName = item.shopName ?? this._shopMeta?.name ?? '';
        const wishBtn = this._wishBtnHtml(item, cardShopId, { shopName: cardShopName });
        const catalogOffer = !!(item.offerId || item.productId);
        const canQuickAdd = catalogOffer
            && !!this.buyerActor
            && !item.isService
            && !item.locked
            && !item.outOfStock
            && !item.unavailable
            && item.purchasable !== false;
        const quickAdd = canQuickAdd
            ? `<button class="ssa-quick-cart" data-action="cart-add" data-key="${esc(wishKey(cardShopId, item.uuid))}" title="${esc(loc('cart.quickAdd'))}"><i class="fas fa-cart-plus"></i></button>`
            : '';
        return `
            <div class="ssa-product-card ${stateClass}" data-action="open-item" data-uuid="${esc(item.uuid)}"${shopAttr} data-search="${esc(searchKey)}">
                <div class="ssa-product-thumb"><img src="${esc(item.img)}" alt="">${wishBtn}</div>
                <div class="ssa-product-info">
                    ${shopLabel}
                    <div class="ssa-product-name">${esc(item.name)}${item.isService ? `<span class="ssa-badge ssa-badge-service">${esc(loc('service'))}</span>` : ''}</div>
                    ${priceLine}
                    <div class="ssa-product-sub">${subLine}</div>
                </div>
                ${quickAdd}
            </div>
        `;
    }

    /* ------------------------------------------------------------------ */
    /*  화면 3: 상품 상세 (PDP)                                              */
    /* ------------------------------------------------------------------ */

    async _ensureShopMeta() {
        if (this._shopMeta?.id === this.shopId) return;
        const vm = await this.api.getShopViewModel(this.shopId, { buyerActorId: this.buyerActor?.id ?? null });
        if (vm.ok) this._shopMeta = vm.shop;
    }

    _findKnownCatalogOffer(item) {
        const matches = offer => offer?.shopId === this.shopId && offer?.uuid === this.itemUuid;
        const result = listOf(this._catalogResults?.items).find(matches);
        if (result) return result;
        for (const section of listOf(this._catalogHome?.sections)) {
            const found = listOf(section.items).find(matches);
            if (found) return found;
        }
        for (const collection of listOf(this._catalogHome?.collections)) {
            const found = listOf(collection.items).find(matches);
            if (found) return found;
        }
        return item ?? null;
    }

    async _loadDetailCatalogExtras(item) {
        if (typeof this.api?.getProductOffers !== 'function') return { offers: [], related: [] };
        const buyerId = this.buyerActor?.id ?? null;
        const cacheKey = `${buyerId ?? ''}:${this.shopId}:${this.itemUuid}`;
        if (this._detailCatalogCache.has(cacheKey)) return this._detailCatalogCache.get(cacheKey);
        const known = this._findKnownCatalogOffer(item);
        const productId = known?.productId ?? item?.productId ?? this.itemUuid;
        let offers = [];
        let related = [];
        try {
            const offerResponse = await this.api.getProductOffers(productId, { buyerActorId: buyerId });
            if (offerResponse?.ok) offers = listOf(offerResponse.offers);
            const seed = offers.find(offer => offer.shopId === this.shopId && offer.uuid === this.itemUuid) ?? known ?? offers[0];
            if (typeof this.api?.searchCatalog === 'function' && seed) {
                const response = await this.api.searchCatalog({
                    buyerActorId: buyerId,
                    query: '',
                    categoryIds: seed.catalogCategoryId ? [seed.catalogCategoryId] : [],
                    shopIds: [],
                    inStock: false,
                    onSale: false,
                    unlocked: false,
                    affinity: false,
                    affordable: false,
                    purchasable: false,
                    itemTypes: seed.type ? [seed.type] : [],
                    tags: listOf(seed.catalogTags).slice(0, 2),
                    sort: 'default',
                    cursor: null,
                    limit: 8
                });
                if (response?.ok) related = listOf(response.items)
                    .filter(row => row.productId !== productId && !(row.shopId === this.shopId && row.uuid === this.itemUuid))
                    .slice(0, 6);
            }
        } catch (error) {
            console.warn('Smartphone Shop App | Optional catalog detail extras failed:', error);
        }
        const bundle = { offers, related, productId };
        this._detailCatalogCache.set(cacheKey, bundle);
        return bundle;
    }

    _benefitBreakdownHtml(item) {
        const rows = [];
        if (item?.hasDiscount && item.originalPriceDisplay) rows.push([loc('detail.basePrice'), item.originalPriceDisplay]);
        const benefits = [
            ['itemDiscount', item?.discount],
            ['personalDiscount', item?.personalDiscount],
            ['affinityDiscount', item?.affinityDiscount],
            ['saleDiscount', item?.saleDiscount]
        ];
        for (const [key, value] of benefits) {
            const n = Number(value) || 0;
            if (n > 0) rows.push([loc(`detail.${key}`), `-${n}%`]);
        }
        if (rows.length === 0) return '';
        return `
            <section class="ssa-benefit-card">
                <strong>${esc(loc('detail.benefits'))}</strong>
                ${rows.map(([label, value]) => `<div class="ssa-benefit-row"><span>${esc(label)}</span><em>${esc(value)}</em></div>`).join('')}
            </section>`;
    }

    _receiverHtml() {
        const buyer = this.buyerActor;
        if (!buyer) return '';
        return `
            <section class="ssa-receiver-card">
                <img src="${esc(buyer.img || 'icons/svg/mystery-man.svg')}" alt="">
                <span><em>${esc(loc('detail.receiver'))}</em><strong>${esc(buyer.name)}</strong></span>
            </section>`;
    }

    _offersHtml(offers) {
        const other = listOf(offers).filter(offer => !(offer.shopId === this.shopId && offer.uuid === this.itemUuid));
        if (other.length === 0) return '';
        return `
            <section class="ssa-offers-list">
                <div class="ssa-home-head"><span class="ssa-home-title">${esc(loc('detail.offers'))}</span></div>
                ${other.slice(0, 5).map(offer => `
                    <button class="ssa-offer-row" data-action="open-item" data-shop-id="${esc(offer.shopId)}" data-uuid="${esc(offer.uuid)}">
                        <span class="ssa-offer-shop"${this._accentStyle(offer.shopAccent)}>${remph(offer.shopName)}</span>
                        <span class="ssa-offer-price">${esc(offer.priceDisplay ?? '')}</span>
                        <span class="ssa-offer-state ${offer.purchasable ? 'ok' : ''}">${esc(offer.purchasable ? loc('filters.purchasable') : this._errorText(offer.purchaseErrorCode, null))}</span>
                        <i class="fas fa-chevron-right"></i>
                    </button>`).join('')}
            </section>`;
    }

    _relatedHtml(items) {
        if (!items.length) return '';
        return `
            <section class="ssa-home-block">
                <div class="ssa-home-head"><span class="ssa-home-title">${esc(loc('detail.related'))}</span></div>
                <div class="ssa-related-grid">${items.map(item => this._railProductCard(item)).join('')}</div>
            </section>`;
    }

    async _buildDetailScreen() {
        const buyer = this.buyerActor;
        await this._ensureShopMeta();
        const detail = await this.api.getShopItemDetail(this.shopId, this.itemUuid, {
            buyerActorId: buyer?.id ?? null,
            quantity: this.qty,
            paymentSource: this.paymentSource
        });
        if (!detail.ok) {
            return this._screen(this._titleHtml(loc('title')), 'back', this._notice('box-open', loc('errors.itemGone')));
        }

        this.qty = detail.quantity;
        this._payment = detail.wallet.paymentSource;
        this._walletInfo = detail.wallet;
        const item = detail.item;
        const shop = this._shopMeta;
        const pct = this._discountPct(item);
        const catalogExtras = await this._loadDetailCatalogExtras(item);

        // 최근 본 상품 기록 (같은 상품 재렌더로 인한 중복 기록 방지)
        const buyerForRecent = this.buyerActor;
        if (buyerForRecent && !item.isService) {
            const recentKey = wishKey(this.shopId, this.itemUuid);
            if (this._lastRecentKey !== recentKey) {
                this._lastRecentKey = recentKey;
                pushRecent(buyerForRecent.id, {
                    shopId: this.shopId,
                    uuid: this.itemUuid,
                    name: item.name ?? '',
                    img: item.img ?? '',
                    priceDisplay: item.priceDisplay ?? ''
                }).catch(e => console.error('Smartphone Shop App | Recent push failed:', e));
            }
        }

        // 브레드크럼: 홈 › 상점 (상점 크럼은 어디서 왔든 상점 페이지로 이동)
        const crumbs = `
            <div class="ssa-crumbs">
                <span class="ssa-crumb" data-action="crumb-home">${esc(loc('breadcrumbHome'))}</span>
                <i class="fas fa-chevron-right"></i>
                ${shop ? `<span class="ssa-crumb" data-action="crumb-shop">${remph(shop.name)}</span>` : ''}
            </div>
        `;

        // 가격/구성 명세 (웹 PDP 스펙 테이블)
        const specRows = [];
        if (item.hasDiscount) {
            specRows.push(`<div class="ssa-spec-row"><span class="ssa-spec-label">${esc(loc('spec.list'))}</span><span class="ssa-spec-strike">${esc(item.originalPriceDisplay)}</span></div>`);
        }
        specRows.push(`
            <div class="ssa-spec-row ssa-spec-price">
                <span class="ssa-spec-label">${esc(loc('spec.sale'))}</span>
                <span class="ssa-spec-value">${pct > 0 ? `<em>${pct}%</em>` : ''}<strong>${esc(item.priceDisplay)}</strong></span>
            </div>
        `);
        specRows.push(`<div class="ssa-spec-row"><span class="ssa-spec-label">${esc(loc('spec.grant'))}</span><span class="ssa-instant"><i class="fas fa-bolt"></i>${esc(loc('instantGrant'))}</span></div>`);
        const stockValue = item.hasLimitedStock ? String(item.stock ?? 0) : loc('spec.unlimited');
        const ownedSuffix = (detail.ownedCount !== null && detail.ownedCount !== undefined) ? ` · ${locf('owned', { count: detail.ownedCount })}` : '';
        specRows.push(`<div class="ssa-spec-row"><span class="ssa-spec-label">${esc(loc('spec.stock'))}</span><span>${esc(stockValue + ownedSuffix)}</span></div>`);

        const lockNotice = item.locked
            ? `<div class="ssa-lock-notice"><i class="fas fa-lock"></i> ${esc(item.unlock?.buttonLabel || loc('locked'))}</div>`
            : '';

        // 탭: 상품정보 / 구매 조건 / 판매자
        const tabsDef = [];
        if (item.description) tabsDef.push({ id: 'info', label: loc('tabInfo'), html: `<div class="ssa-desc">${item.description}</div>` });
        if (detail.requirements.length || item.locked) {
            tabsDef.push({ id: 'terms', label: loc('tabTerms'), html: lockNotice + this._requirementRows(detail.requirements) });
        }
        if (shop && (shop.owner || shop.ownerRole)) {
            tabsDef.push({ id: 'seller', label: loc('seller'), html: this._sellerRow(shop) });
        }
        if (!tabsDef.some(t => t.id === this.pdpTab)) this.pdpTab = tabsDef[0]?.id ?? null;
        const tabsHtml = tabsDef.length === 0 ? '' : `
            <div class="ssa-tabs">
                ${tabsDef.map(t => `<button class="ssa-tab ${t.id === this.pdpTab ? 'active' : ''}" data-action="pdp-tab" data-tab="${t.id}">${esc(t.label)}</button>`).join('')}
            </div>
            ${tabsDef.map(t => `<div class="ssa-tab-panel ${t.id === this.pdpTab ? 'active' : ''}" data-tab-panel="${t.id}">${t.html}</div>`).join('')}
        `;

        this._lastDetailTotal = detail.totalPriceDisplay ?? '';
        const cartBtn = (!item.isService && this.buyerActor && !item.locked && !item.unavailable)
            ? `<button class="ssa-cart-btn" data-action="cart-add" data-key="${esc(wishKey(this.shopId, this.itemUuid))}"><i class="fas fa-cart-plus"></i> ${esc(loc('cart.add'))}</button>`
            : '';
        const buyDisabled = !detail.purchase.valid || this._purchasing;
        // 담기 버튼과 나란할 때는 폭이 좁아 총액을 붙이지 않는다 (총액은 총 상품금액 바에 표시)
        const buyLabel = detail.purchase.valid
            ? (cartBtn ? loc('buy') : `${loc('buy')} · ${detail.totalPriceDisplay}`)
            : this._errorText(detail.purchase.errorCode, null);
        const totalBar = detail.purchase.valid || (!item.locked && !item.outOfStock && !item.unavailable)
            ? `<div class="ssa-totalbar"><span>${esc(loc('totalPrice'))}</span><strong>${esc(detail.totalPriceDisplay)}</strong></div>`
            : '';

        const sellerLine = shop?.owner
            ? `<div class="ssa-seller-link" data-action="pdp-tab" data-tab="seller">${esc(locf('sellerLine', { name: shop.owner }))} <i class="fas fa-chevron-right"></i></div>`
            : '';

        const body = `
            ${crumbs}
            <div class="ssa-pdp-hero">
                ${item.tag ? `<span class="ssa-flag">${esc(item.tag)}</span>` : ''}
                <img src="${esc(item.img)}" alt="">
            </div>
            <div class="ssa-pdp-info">
                <div class="ssa-pdp-title">${esc(item.name)}${item.isService ? `<span class="ssa-badge ssa-badge-service">${esc(loc('service'))}</span>` : ''}</div>
                ${sellerLine}
            </div>
            <div class="ssa-spec">${specRows.join('')}</div>
            ${this._benefitBreakdownHtml(item)}
            ${this._receiverHtml()}
            ${this._purchaseBlock(detail)}
            ${totalBar}
            ${tabsHtml}
            ${this._offersHtml(catalogExtras.offers)}
            ${this._relatedHtml(catalogExtras.related)}
            ${this._footer()}
            <div class="ssa-buy-bar">
                ${this._banner()}
                <div class="ssa-buy-row">
                    ${this._wishBtnHtml(item, this.shopId, { shopName: shop?.name ?? '', fab: true })}
                    ${cartBtn}
                    <button class="ssa-buy-btn" data-action="buy" ${buyDisabled ? 'disabled' : ''}>
                        ${esc(buyLabel)}
                    </button>
                </div>
            </div>
        `;

        return this._screen(this._titleHtml(item.name), 'back', body, this._walletChip(detail.wallet));
    }

    _purchaseBlock(detail) {
        if (detail.item.locked || detail.item.outOfStock || detail.item.unavailable) return '';
        const payment = detail.wallet.paymentSource;
        const paymentRow = payment?.available ? `
            <div class="ssa-payment-row">
                <span class="ssa-qty-label">${esc(loc('paymentLabel'))}</span>
                <div class="ssa-segmented">
                    <button class="${payment.active === 'sheet' ? 'active' : ''}" data-action="toggle-payment" data-source="sheet">
                        <i class="fas fa-scroll"></i>${esc(loc('paymentSheet'))}
                    </button>
                    <button class="${payment.active === 'bank' ? 'active' : ''}" data-action="toggle-payment" data-source="bank">
                        <i class="fas fa-building-columns"></i>${esc(loc('paymentBank'))}
                    </button>
                </div>
            </div>
        ` : '';
        return `
            <div class="ssa-card-block">
                <div class="ssa-qty-row">
                    <span class="ssa-qty-label">${esc(loc('quantity'))}</span>
                    <div class="ssa-qty-stepper">
                        <button data-action="qty-minus" data-max="${detail.maxQty}" ${this.qty <= 1 ? 'disabled' : ''}><i class="fas fa-minus"></i></button>
                        <input type="number" data-field="qty" data-max="${detail.maxQty}" min="1" max="${detail.maxQty}" value="${this.qty}">
                        <button data-action="qty-plus" data-max="${detail.maxQty}" ${this.qty >= detail.maxQty ? 'disabled' : ''}><i class="fas fa-plus"></i></button>
                    </div>
                    <div class="ssa-qty-total">${esc(loc('total'))}<strong>${esc(detail.totalPriceDisplay)}</strong></div>
                </div>
                ${paymentRow}
            </div>
        `;
    }

    /** 필요 아이템 체크리스트 (탭 패널 내용) */
    _requirementRows(requirements) {
        if (!Array.isArray(requirements) || requirements.length === 0) return '';
        return requirements.map(row => `
            <div class="ssa-req-row ${row.met ? 'met' : 'unmet'}">
                <i class="fas fa-${row.met ? 'circle-check' : 'circle-xmark'}"></i>
                ${row.img ? `<img class="ssa-req-img" src="${esc(row.img)}" alt="">` : ''}
                <span class="ssa-req-label">${esc(row.label)}</span>
                <span class="ssa-req-count">${esc(locf('reqCount', { owned: row.owned, needed: row.needed }))}</span>
                ${row.consume ? `<span class="ssa-badge ssa-badge-consume">${esc(loc('reqConsumed'))}</span>` : ''}
            </div>
        `).join('');
    }

    /** 판매자 정보 (탭 패널 내용) */
    _sellerRow(shop) {
        if (!shop || (!shop.owner && !shop.ownerRole)) return '';
        return `
            <div class="ssa-seller-row">
                <img class="ssa-seller-art" src="${esc(shop.npcArt)}" alt="">
                <div>
                    <div class="ssa-seller-name">${esc(shop.owner || shop.name)}</div>
                    ${shop.ownerRole ? `<div class="ssa-seller-role">${esc(shop.ownerRole)}</div>` : ''}
                </div>
            </div>
        `;
    }

    /* ------------------------------------------------------------------ */
    /*  화면 4: 판매 (내 인벤토리 → 상점)                                     */
    /* ------------------------------------------------------------------ */

    async _buildSellScreen() {
        const seller = this.buyerActor;
        const data = await this.api.getShopSellData(this.shopId, { sellerActorId: seller?.id ?? null });
        if (!data.ok) {
            return this._screen(this._titleHtml(loc('sell.title')), 'back', this._notice('store-slash', loc('errors.shopGone')));
        }
        this._walletInfo = data.wallet;

        this._sellRows = new Map();
        for (const group of data.groups) {
            for (const row of group.items) this._sellRows.set(row.id, row);
        }

        let body;
        if (!data.sell.available) {
            body = this._notice('store-slash', loc('sell.notBuying'));
        } else if (!seller) {
            body = this._notice('user-slash', loc('noBuyer'));
        } else if (!data.sell.open) {
            body = this._notice('door-closed', loc('sell.closed'));
        } else if (data.groups.length === 0) {
            body = this._notice('box-open', loc('sell.empty'));
        } else {
            const groupsHtml = data.groups.map(group => `
                <div class="ssa-sell-group">
                    <div class="ssa-sell-group-head">
                        <span>${esc(group.label)}</span>
                        <em>${group.items.length}</em>
                    </div>
                    ${group.items.map(row => this._sellRowHtml(row)).join('')}
                </div>
            `).join('');
            body = `
                ${this._banner()}
                <div class="ssa-sell-hint"><i class="fas fa-circle-info"></i><span>${esc(loc('sell.hint'))}</span></div>
                <div class="ssa-section">
                    <div class="ssa-search">
                        <i class="fas fa-magnifying-glass"></i>
                        <input type="text" data-field="sell-search" placeholder="${esc(loc('sell.searchPlaceholder'))}">
                    </div>
                </div>
                ${groupsHtml}
                ${this._footer()}
            `;
        }
        return this._screen(this._titleHtml(loc('sell.title')), 'back', body, this._walletChip(data.wallet));
    }

    _sellRowHtml(row) {
        return `
            <div class="ssa-sell-row" data-action="sell-item" data-item-id="${esc(row.id)}" data-search="${esc(row.name.toLowerCase())}">
                <div class="ssa-product-thumb"><img src="${esc(row.img)}" alt=""></div>
                <div class="ssa-sell-info">
                    <div class="ssa-product-name">${esc(row.name)}</div>
                    <div class="ssa-sell-owned">${esc(locf('sell.ownedQty', { count: row.quantity }))}</div>
                </div>
                <div class="ssa-sell-price">
                    <span class="ssa-price-final">${esc(row.sellPriceDisplay)}</span>
                    <span class="ssa-sell-unit">${esc(loc('sell.unit'))}</span>
                </div>
                <i class="fas fa-chevron-right ssa-chevron"></i>
            </div>
        `;
    }

    _openSellSheet(itemId) {
        if (!this.element || this.element.querySelector('.ssa-sheet-wrap')) return;
        const row = this._sellRows?.get(itemId);
        if (!row || this.view !== 'sell') return;
        this._sellSheet = { itemId, qty: 1, max: Math.max(1, row.quantity), totalDisplay: row.sellPriceDisplay, valid: true };

        const sheet = this.createElement(`
            <div class="ssa-sheet-wrap ssa-sellsheet">
                <div class="ssa-sheet-backdrop" data-action="sell-close"></div>
                <div class="ssa-sheet">
                    <div class="ssa-sheet-head">
                        <span>${esc(loc('sell.confirmTitle'))}</span>
                        <button data-action="sell-close"><i class="fas fa-xmark"></i></button>
                    </div>
                    <div class="ssa-sheet-body">
                        <div class="ssa-sellsheet-item">
                            <img class="ssa-sellsheet-img" src="${esc(row.img)}" alt="">
                            <div class="ssa-sellsheet-titles">
                                <div class="ssa-sellsheet-name">${esc(row.name)}</div>
                                <div class="ssa-sellsheet-meta">${esc(locf('sell.ownedQty', { count: row.quantity }))} · ${esc(row.sellPriceDisplay)}</div>
                            </div>
                        </div>
                        <div class="ssa-qty-row">
                            <span class="ssa-qty-label">${esc(loc('quantity'))}</span>
                            <div class="ssa-qty-stepper">
                                <button data-action="sell-minus" disabled><i class="fas fa-minus"></i></button>
                                <input type="number" data-field="sell-qty" min="1" max="${this._sellSheet.max}" value="1">
                                <button data-action="sell-plus" ${this._sellSheet.max <= 1 ? 'disabled' : ''}><i class="fas fa-plus"></i></button>
                            </div>
                        </div>
                        <div class="ssa-sellsheet-total">
                            <span>${esc(loc('sell.totalLabel'))}</span>
                            <strong data-role="sell-total">${esc(row.sellPriceDisplay)}</strong>
                        </div>
                        <button class="ssa-buy-btn ssa-sell-confirm" data-action="sell-confirm">${esc(loc('sell.confirm'))}</button>
                    </div>
                </div>
            </div>
        `);
        sheet.addEventListener('pointerdown', (e) => e.stopPropagation());
        this.element.appendChild(sheet);
        requestAnimationFrame(() => sheet.classList.add('open'));
    }

    _closeSellSheet() {
        this._sellSheet = null;
        const sheet = this.element?.querySelector('.ssa-sellsheet');
        if (!sheet) return;
        sheet.classList.remove('open');
        setTimeout(() => sheet.remove(), 200);
    }

    _setSellQty(next) {
        const sheet = this._sellSheet;
        if (!sheet) return;
        sheet.qty = Math.min(Math.max(1, Math.floor(Number(next) || 1)), sheet.max);
        const wrap = this.element?.querySelector('.ssa-sellsheet');
        if (!wrap) return;
        const input = wrap.querySelector('[data-field="sell-qty"]');
        if (input) input.value = String(sheet.qty);
        wrap.querySelector('[data-action="sell-minus"]')?.toggleAttribute('disabled', sheet.qty <= 1);
        wrap.querySelector('[data-action="sell-plus"]')?.toggleAttribute('disabled', sheet.qty >= sheet.max);
        this._updateSellQuote();
    }

    async _updateSellQuote() {
        const sheet = this._sellSheet;
        if (!sheet) return;
        const seq = ++this._sellQuoteSeq;
        let quote = null;
        try {
            quote = await this.api.getSellQuote(this.shopId, sheet.itemId, {
                sellerActorId: this.buyerActor?.id ?? null,
                quantity: sheet.qty
            });
        } catch (e) {
            console.error('Smartphone Shop App | Sell quote failed:', e);
        }
        if (seq !== this._sellQuoteSeq || this._sellSheet !== sheet) return;
        const wrap = this.element?.querySelector('.ssa-sellsheet');
        if (!wrap) return;
        const totalEl = wrap.querySelector('[data-role="sell-total"]');
        const btn = wrap.querySelector('[data-action="sell-confirm"]');
        sheet.valid = quote?.ok === true && quote.valid === true;
        if (sheet.valid) {
            sheet.totalDisplay = quote.totalDisplay;
            if (totalEl) totalEl.textContent = quote.totalDisplay;
            if (btn && !this._selling) btn.disabled = false;
        } else {
            if (totalEl) totalEl.textContent = '—';
            if (btn) btn.disabled = true;
        }
    }

    async _confirmSell() {
        const sheet = this._sellSheet;
        const seller = this.buyerActor;
        if (!sheet || !seller || this._selling || !sheet.valid) return;
        const row = this._sellRows?.get(sheet.itemId);
        if (!row) return;

        this._selling = true;
        const btn = this.element?.querySelector('.ssa-sellsheet [data-action="sell-confirm"]');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${esc(loc('sell.selling'))}`;
        }

        try {
            const shopActor = game.actors?.get(this.shopId);
            const result = await this.api.requestSell({
                shopActorId: this.shopId,
                shopActorUuid: shopActor?.uuid,
                sellerActorId: seller.id,
                sellerActorUuid: seller.uuid,
                itemId: sheet.itemId,
                quantity: sheet.qty
            });
            this.resultBanner = result?.success
                ? { success: true, text: locf('sell.success', { itemName: result.itemName || row.name, quantity: sheet.qty, total: sheet.totalDisplay }) }
                : { success: false, text: this._errorText(result?.errorCode, result?.message) };
            if (result?.success) {
                recordOrder(seller.id, {
                    type: 'sell',
                    shopId: this.shopId,
                    shopName: String(this._shopMeta?.name ?? '').replace(/\*\*/g, ''),
                    uuid: row.uuid ?? '',
                    name: result.itemName || row.name,
                    img: row.img ?? '',
                    qty: sheet.qty,
                    totalDisplay: sheet.totalDisplay
                }).catch(e => console.error('Smartphone Shop App | Order record failed:', e));
            }
        } catch (e) {
            console.error('Smartphone Shop App | Sell failed:', e);
            this.resultBanner = { success: false, text: loc('errors.sellGeneric') };
        } finally {
            this._selling = false;
        }
        this._sellSheet = null;
        this.render();
    }

    /* ------------------------------------------------------------------ */
    /*  찜(위시리스트) · 최근 본 상품                                          */
    /* ------------------------------------------------------------------ */

    /** 렌더 중인 상품을 찜 후보로 등록하고 하트 버튼 HTML을 돌려준다. */
    _wishBtnHtml(item, shopId, { shopName = '', fab = false } = {}) {
        const buyer = this.buyerActor;
        if (!buyer || !shopId || !item?.uuid || item.isService) return '';
        const key = wishKey(shopId, item.uuid);
        this._wishables.set(key, {
            shopId,
            uuid: item.uuid,
            name: item.name ?? '',
            img: item.img ?? '',
            shopName: String(shopName ?? '').replace(/\*\*/g, ''),
            priceBaseUnit: item.priceBaseUnit ?? null,
            priceDisplay: item.priceDisplay ?? '',
            outOfStock: item.outOfStock === true
        });
        const wished = isWished(buyer.id, shopId, item.uuid);
        const cls = fab ? 'ssa-wish-fab' : 'ssa-wish-btn';
        return `
            <button class="${cls} ${wished ? 'wished' : ''}" data-action="wish-toggle" data-key="${esc(key)}"
                    title="${esc(wished ? loc('wish.removeTip') : loc('wish.addTip'))}">
                <i class="fa${wished ? 's' : 'r'} fa-heart"></i>
            </button>`;
    }

    async _toggleWish(key) {
        const buyer = this.buyerActor;
        const snapshot = this._wishables?.get(key);
        if (!buyer || !snapshot) return;
        try {
            const { added } = await toggleWish(buyer.id, snapshot);
            if (added) this.widget.showToastNotification?.(loc('wish.added'));
            this._renderPreservingScroll();
        } catch (e) {
            console.error('Smartphone Shop App | Wish toggle failed:', e);
        }
    }

    async _removeWish(key) {
        const buyer = this.buyerActor;
        if (!buyer || !key) return;
        try {
            await removeWish(buyer.id, key);
            this._renderPreservingScroll();
        } catch (e) {
            console.error('Smartphone Shop App | Wish remove failed:', e);
        }
    }

    /** 찜한 상품의 재입고/가격 인하를 감지해 폰 토스트로 알리고 스냅샷을 갱신한다. */
    async _checkWishAlerts(shopActorId) {
        const buyer = this.buyerActor;
        const api = this.api;
        if (!buyer || !api || this._wishAlertBusy) return;
        const wished = getWishlist(buyer.id).filter(row => row.shopId === shopActorId);
        if (wished.length === 0) return;

        this._wishAlertBusy = true;
        try {
            const updates = [];
            for (const row of wished) {
                let detail = null;
                try {
                    detail = await api.getShopItemDetail(row.shopId, row.uuid, { buyerActorId: buyer.id });
                } catch (e) { /* 상점/아이템이 사라진 경우 — 다음 항목 계속 */ }
                if (!detail?.ok) continue;

                const item = detail.item;
                const nowOut = item.outOfStock === true;
                const nowPrice = Number.isFinite(Number(item.priceBaseUnit)) ? Number(item.priceBaseUnit) : null;
                const restocked = row.outOfStock === true && !nowOut;
                const dropped = nowPrice != null && row.priceBaseUnit != null && nowPrice < row.priceBaseUnit;

                if (restocked) {
                    this.widget.showToastNotification?.(locf('wish.restocked', { name: item.name ?? row.name }));
                } else if (dropped) {
                    this.widget.showToastNotification?.(locf('wish.priceDrop', { name: item.name ?? row.name, price: item.priceDisplay ?? '' }));
                }

                if (nowOut !== row.outOfStock || nowPrice !== row.priceBaseUnit) {
                    updates.push({
                        key: row.key,
                        priceBaseUnit: nowPrice,
                        priceDisplay: item.priceDisplay ?? '',
                        outOfStock: nowOut,
                        name: item.name ?? '',
                        img: item.img ?? ''
                    });
                }
            }
            if (updates.length) await updateWishSnapshots(buyer.id, updates);
        } catch (e) {
            console.error('Smartphone Shop App | Wish alert check failed:', e);
        } finally {
            this._wishAlertBusy = false;
        }
    }

    _buildAccountScreen() {
        const buyer = this.buyerActor;
        const settingsBtn = game.user.isGM
            ? `<button class="ssa-icon-btn" data-action="open-app-settings" title="${esc(loc('settings.open'))}"><i class="fas fa-gear"></i></button>`
            : '';
        if (!buyer) {
            return this._screen(this._titleHtml(loc('account.title')), 'back', this._notice('user-slash', loc('noBuyer')), settingsBtn);
        }
        const wishCount = getWishlist(buyer.id).length;
        const orderCount = getOrders(buyer.id).length;
        const recentCount = getRecent(buyer.id).length;
        const row = (action, icon, label, count = null) => `
            <button class="ssa-account-row" data-action="${action}">
                <i class="fas fa-${icon}"></i><span>${esc(label)}</span>
                ${count != null ? `<em>${count}</em>` : ''}<i class="fas fa-chevron-right"></i>
            </button>`;
        const body = `
            <section class="ssa-account-hero">
                <img class="ssa-account-avatar" src="${esc(buyer.img || 'icons/svg/mystery-man.svg')}" alt="">
                <div><em>${esc(loc('buyer.label'))}</em><strong>${esc(buyer.name)}</strong></div>
            </section>
            <section class="ssa-account-menu">
                ${row('open-wishlist', 'heart', loc('account.wishlist'), wishCount)}
                ${row('open-orders', 'receipt', loc('account.orders'), orderCount)}
                ${row('open-wallet-app', 'wallet', loc('account.wallet'))}
            </section>
            ${recentCount ? `<div class="ssa-home-head"><span class="ssa-home-title">${esc(loc('account.recent'))}</span><em>${recentCount}</em></div>${this._recentRailHtml({ showHeader: false })}` : ''}
            ${this._footer()}`;
        return this._screen(this._titleHtml(loc('account.title')), 'back', body, settingsBtn);
    }

    async _buildWishlistScreen() {
        const buyer = this.buyerActor;
        if (!buyer) {
            return this._screen(this._titleHtml(loc('wish.title')), 'back', this._notice('user-slash', loc('noBuyer')));
        }

        const rows = getWishlist(buyer.id);
        if (rows.length === 0) {
            return this._screen(this._titleHtml(loc('wish.title')), 'back', this._notice('heart-crack', loc('wish.empty')));
        }

        const resolved = await Promise.all(rows.map(async row => {
            try {
                const detail = await this.api.getShopItemDetail(row.shopId, row.uuid, { buyerActorId: buyer.id });
                return { row, detail: detail?.ok ? detail : null };
            } catch (e) {
                return { row, detail: null };
            }
        }));

        const items = resolved.map(({ row, detail }) => {
            const key = row.key;
            if (!detail) {
                return `
                    <div class="ssa-wl-row gone">
                        <div class="ssa-product-thumb"><img src="${esc(row.img || 'icons/svg/item-bag.svg')}" alt=""></div>
                        <div class="ssa-wl-info">
                            <div class="ssa-product-name">${esc(row.name)}</div>
                            <div class="ssa-wl-shop">${esc(row.shopName)}</div>
                            <div class="ssa-wl-state">${esc(loc('wish.gone'))}</div>
                        </div>
                        <button class="ssa-wl-remove" data-action="wish-remove" data-key="${esc(key)}"><i class="fas fa-xmark"></i></button>
                    </div>`;
            }

            const item = detail.item;
            this._wishables.set(key, {
                shopId: row.shopId,
                uuid: row.uuid,
                name: item.name ?? row.name,
                img: item.img ?? row.img,
                shopName: row.shopName,
                priceBaseUnit: item.priceBaseUnit ?? null,
                priceDisplay: item.priceDisplay ?? '',
                outOfStock: item.outOfStock === true
            });

            const savedPrice = Number(row.priceBaseUnit);
            const nowPrice = Number(item.priceBaseUnit);
            const dropPct = (Number.isFinite(savedPrice) && savedPrice > 0 && Number.isFinite(nowPrice) && nowPrice < savedPrice)
                ? Math.round((1 - nowPrice / savedPrice) * 100)
                : 0;

            let stateBits = '';
            if (item.locked) stateBits = `<span class="ssa-sub-lock"><i class="fas fa-lock"></i> ${esc(loc('locked'))}</span>`;
            else if (item.outOfStock) stateBits = `<span class="ssa-sub-oos">${esc(loc('outOfStock'))}</span>`;

            return `
                <div class="ssa-wl-row" data-action="open-item" data-uuid="${esc(row.uuid)}" data-shop-id="${esc(row.shopId)}">
                    <div class="ssa-product-thumb"><img src="${esc(item.img ?? row.img)}" alt=""></div>
                    <div class="ssa-wl-info">
                        <div class="ssa-product-name">${esc(item.name ?? row.name)}</div>
                        <div class="ssa-wl-shop">${esc(row.shopName)}</div>
                        <div class="ssa-price-row">
                            ${dropPct > 0 ? `<span class="ssa-wl-drop">${esc(locf('wish.dropBadge', { pct: dropPct }))}</span>` : ''}
                            <span class="ssa-price-final">${esc(item.priceDisplay ?? '')}</span>
                        </div>
                        ${stateBits ? `<div class="ssa-product-sub">${stateBits}</div>` : ''}
                    </div>
                    <button class="ssa-wl-remove" data-action="wish-remove" data-key="${esc(key)}" title="${esc(loc('wish.removeTip'))}"><i class="fas fa-heart-crack"></i></button>
                </div>`;
        }).join('');

        const body = `
            <div class="ssa-wl-head">${esc(locf('wish.count', { count: rows.length }))}</div>
            <div class="ssa-wl-list">${items}</div>
            ${this._footer()}
        `;
        return this._screen(this._titleHtml(loc('wish.title')), 'back', body);
    }

    /** 홈 화면의 최근 본 상품 가로 레일. */
    _recentRailHtml({ showHeader = true } = {}) {
        const buyer = this.buyerActor;
        if (!buyer) return '';
        const rows = getRecent(buyer.id);
        if (rows.length === 0) return '';
        return `
            ${showHeader ? `<div class="ssa-rail-head">${esc(loc('wish.recentTitle'))}</div>` : ''}
            <div class="ssa-recent-rail">
                ${rows.map(row => `
                    <div class="ssa-recent-item" data-action="open-item" data-uuid="${esc(row.uuid)}" data-shop-id="${esc(row.shopId)}">
                        <div class="ssa-recent-thumb"><img src="${esc(row.img || 'icons/svg/item-bag.svg')}" alt=""></div>
                        <span class="ssa-recent-name">${esc(row.name)}</span>
                        <span class="ssa-recent-price">${esc(row.priceDisplay)}</span>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /* ------------------------------------------------------------------ */
    /*  장바구니 · 주문 내역                                                  */
    /* ------------------------------------------------------------------ */

    async _cartCall(fn) {
        const buyer = this.buyerActor;
        if (!buyer) return;
        try {
            await fn(buyer);
            this._renderPreservingScroll();
        } catch (e) {
            console.error('Smartphone Shop App | Cart action failed:', e);
        }
    }

    async _addToCartFromKey(key) {
        const buyer = this.buyerActor;
        const snapshot = this._wishables?.get(key);
        if (!buyer || !snapshot) return;
        try {
            const { merged } = await addToCart(buyer.id, snapshot, this.view === 'detail' ? this.qty : 1);
            this.widget.showToastNotification?.(loc(merged ? 'cart.merged' : 'cart.added'));
            this._updateCartBadges();
        } catch (e) {
            console.error('Smartphone Shop App | Cart add failed:', e);
        }
    }

    _updateCartBadges() {
        const buyer = this.buyerActor;
        if (!buyer || !this.element) return;
        const count = getCartCount(buyer.id);
        const tabIcon = this.element.querySelector('[data-action="tab-cart"] .ssa-tabbar-icon');
        if (tabIcon) {
            let badge = tabIcon.querySelector('.ssa-tab-badge');
            if (count > 0 && !badge) {
                badge = document.createElement('b');
                badge.className = 'ssa-tab-badge';
                tabIcon.appendChild(badge);
            }
            if (badge) {
                badge.textContent = count > 99 ? '99+' : String(count);
                badge.hidden = count <= 0;
            }
        }
        const legacyBadge = this.element.querySelector('.ssa-cart-badge');
        if (legacyBadge) legacyBadge.textContent = count > 9 ? '9+' : String(count);
    }

    async _buildCartScreen() {
        const buyer = this.buyerActor;
        const ordersLink = `
            <button class="ssa-orders-link" data-action="open-orders">
                <i class="fas fa-receipt"></i>
                <span>${esc(loc('cart.ordersLink'))}</span>
                <i class="fas fa-chevron-right"></i>
            </button>`;

        if (!buyer) {
            return this._screen(this._titleHtml(loc('cart.title')), 'back', this._notice('user-slash', loc('noBuyer')) + ordersLink);
        }

        const rows = getCart(buyer.id);
        this._cartLines = [];
        if (rows.length === 0) {
            return this._screen(this._titleHtml(loc('cart.title')), 'back',
                this._banner() + this._notice('cart-shopping', loc('cart.empty')) + ordersLink);
        }

        const resolved = await Promise.all(rows.map(async row => {
            try {
                const detail = await this.api.getShopItemDetail(row.shopId, row.uuid, { buyerActorId: buyer.id, quantity: row.qty });
                return { row, detail: detail?.ok ? detail : null };
            } catch (e) {
                return { row, detail: null };
            }
        }));

        const groups = new Map();
        for (const { row, detail } of resolved) {
            if (!groups.has(row.shopId)) groups.set(row.shopId, { shopName: row.shopName, lines: [] });
            groups.get(row.shopId).lines.push({ row, detail });
        }

        const canFormatSubtotal = typeof this.api.getShopPriceDisplay === 'function';
        let validCount = 0;
        const groupsHtml = [...groups.entries()].map(([shopId, group]) => {
            let subtotalBaseUnit = 0;
            let subtotalKnown = true;

            const linesHtml = group.lines.map(({ row, detail }) => {
                if (!detail) {
                    this._cartLines.push({ key: row.key, valid: false });
                    return `
                        <div class="ssa-cart-row gone">
                            <div class="ssa-product-thumb"><img src="${esc(row.img || 'icons/svg/item-bag.svg')}" alt=""></div>
                            <div class="ssa-cart-info">
                                <div class="ssa-product-name">${esc(row.name)}</div>
                                <div class="ssa-wl-state">${esc(loc('wish.gone'))}</div>
                            </div>
                            <button class="ssa-wl-remove" data-action="cart-remove" data-key="${esc(row.key)}"><i class="fas fa-xmark"></i></button>
                        </div>`;
                }

                const item = detail.item;
                const qty = detail.quantity;
                const valid = detail.purchase?.valid === true;
                if (valid) validCount += qty;

                const unitBase = Number(item.priceBaseUnit);
                if (Number.isFinite(unitBase)) subtotalBaseUnit += unitBase * qty;
                else subtotalKnown = false;

                this._cartLines.push({
                    key: row.key,
                    shopId,
                    uuid: row.uuid,
                    qty,
                    name: item.name ?? row.name,
                    img: item.img ?? row.img,
                    shopName: row.shopName,
                    valid,
                    totalDisplay: detail.totalPriceDisplay ?? ''
                });

                const checkoutError = this._cartErrors.get(row.key);
                const invalidText = checkoutError
                    ?? (valid ? '' : this._errorText(detail.purchase?.errorCode, null));

                return `
                    <div class="ssa-cart-row ${valid ? '' : 'invalid'}">
                        <div class="ssa-product-thumb" data-action="open-item" data-uuid="${esc(row.uuid)}" data-shop-id="${esc(shopId)}">
                            <img src="${esc(item.img ?? row.img)}" alt="">
                        </div>
                        <div class="ssa-cart-info">
                            <div class="ssa-product-name" data-action="open-item" data-uuid="${esc(row.uuid)}" data-shop-id="${esc(shopId)}">${esc(item.name ?? row.name)}</div>
                            <div class="ssa-price-row"><span class="ssa-price-final">${esc(detail.totalPriceDisplay ?? '')}</span></div>
                            ${invalidText ? `<div class="ssa-cart-error"><i class="fas fa-circle-exclamation"></i> ${esc(invalidText)}</div>` : ''}
                        </div>
                        <div class="ssa-cart-side">
                            <div class="ssa-qty-stepper compact">
                                <button data-action="cart-minus" data-key="${esc(row.key)}" data-max="${detail.maxQty}"><i class="fas fa-${qty <= 1 ? 'trash-can' : 'minus'}"></i></button>
                                <span class="ssa-cart-qty">${qty}</span>
                                <button data-action="cart-plus" data-key="${esc(row.key)}" data-max="${detail.maxQty}" ${qty >= detail.maxQty ? 'disabled' : ''}><i class="fas fa-plus"></i></button>
                            </div>
                            <button class="ssa-wl-remove" data-action="cart-remove" data-key="${esc(row.key)}" title="${esc(loc('cart.removeTip'))}"><i class="fas fa-xmark"></i></button>
                        </div>
                    </div>`;
            }).join('');

            const subtotal = (canFormatSubtotal && subtotalKnown && subtotalBaseUnit > 0)
                ? this.api.getShopPriceDisplay(shopId, subtotalBaseUnit)
                : '';

            return `
                <div class="ssa-cart-group">
                    <div class="ssa-sell-group-head"><span>${esc(String(group.shopName ?? '').replace(/\*\*/g, ''))}</span></div>
                    ${linesHtml}
                    ${subtotal ? `<div class="ssa-cart-subtotal"><span>${esc(loc('cart.subtotal'))}</span><strong>${esc(subtotal)}</strong></div>` : ''}
                </div>`;
        }).join('');

        const checkoutDisabled = this._checkingOut || validCount === 0;
        const checkoutLabel = this._checkingOut
            ? `<i class="fas fa-spinner fa-spin"></i> ${esc(loc('cart.checkingOut'))}`
            : esc(locf('cart.checkout', { count: validCount }));

        const body = `
            ${this._banner()}
            ${groupsHtml}
            ${ordersLink}
            ${this._footer()}
            <div class="ssa-buy-bar">
                <button class="ssa-buy-btn" data-action="checkout" ${checkoutDisabled ? 'disabled' : ''}>${checkoutLabel}</button>
            </div>
        `;
        return this._screen(this._titleHtml(loc('cart.title')), 'back', body);
    }

    async _checkout() {
        const buyer = this.buyerActor;
        if (!buyer || this._checkingOut) return;
        const lines = this._cartLines.filter(line => line.valid);
        if (lines.length === 0) return;

        this._checkingOut = true;
        this._cartErrors = new Map();
        this.render();

        let ok = 0;
        let failCount = 0;
        let affinitySyncPending = false;
        const doneKeys = [];
        try {
            for (const line of lines) {
                const shopActor = game.actors?.get(line.shopId);
                const lineQty = Math.max(1, Math.floor(Number(line.qty) || 1));
                let result = null;
                try {
                    result = await this.api.requestPurchase({
                        shopActorId: line.shopId,
                        shopActorUuid: shopActor?.uuid,
                        itemUuid: line.uuid,
                        buyerActorId: buyer.id,
                        buyerActorUuid: buyer.uuid,
                        quantity: lineQty,
                        initiatorUserId: game.user.id
                    });
                } catch (e) {
                    console.error('Smartphone Shop App | Checkout purchase failed:', e);
                }

                if (result?.success) {
                    ok += lineQty;
                    if (result.affinitySyncPending) affinitySyncPending = true;
                    doneKeys.push(line.key);
                    recordOrder(buyer.id, {
                        type: 'buy',
                        shopId: line.shopId,
                        shopName: line.shopName,
                        uuid: line.uuid,
                        name: result.itemName || line.name,
                        img: line.img,
                        qty: lineQty,
                        totalDisplay: line.totalDisplay
                    }).catch(e => console.error('Smartphone Shop App | Order record failed:', e));
                } else {
                    failCount += lineQty;
                    this._cartErrors.set(line.key, this._errorText(result?.errorCode, result?.message));
                }
            }
            if (doneKeys.length) await removeCartEntries(buyer.id, doneKeys);
        } finally {
            this._checkingOut = false;
        }

        const checkoutText = failCount === 0
            ? locf('cart.checkoutAllDone', { ok })
            : locf('cart.checkoutDone', { ok, fail: failCount });
        this.resultBanner = {
            success: failCount === 0,
            text: `${checkoutText}${affinitySyncPending ? ` ${loc('affinitySyncPending')}` : ''}`
        };
        this.render();
    }

    _buildOrdersScreen() {
        const buyer = this.buyerActor;
        if (!buyer) {
            return this._screen(this._titleHtml(loc('orders.title')), 'back', this._notice('user-slash', loc('noBuyer')));
        }

        const rows = getOrders(buyer.id);
        if (rows.length === 0) {
            return this._screen(this._titleHtml(loc('orders.title')), 'back', this._notice('receipt', loc('orders.empty')));
        }

        const items = rows.map(row => {
            const when = new Date(row.at).toLocaleString();
            const isSell = row.type === 'sell';
            return `
                <div class="ssa-order-row">
                    <div class="ssa-product-thumb"><img src="${esc(row.img || 'icons/svg/item-bag.svg')}" alt=""></div>
                    <div class="ssa-order-info">
                        <div class="ssa-order-top">
                            <span class="ssa-order-type ${isSell ? 'sell' : 'buy'}">${esc(loc(isSell ? 'orders.sell' : 'orders.buy'))}</span>
                            <span class="ssa-order-when">${esc(when)}</span>
                        </div>
                        <div class="ssa-product-name">${esc(row.name)} <em class="ssa-order-qty">${esc(locf('orders.qty', { qty: row.qty }))}</em></div>
                        <div class="ssa-wl-shop">${esc(String(row.shopName ?? '').replace(/\*\*/g, ''))}</div>
                    </div>
                    <div class="ssa-order-total ${isSell ? 'sell' : ''}">${esc(row.totalDisplay)}</div>
                </div>`;
        }).join('');

        return this._screen(this._titleHtml(loc('orders.title')), 'back', `<div class="ssa-order-list">${items}</div>${this._footer()}`);
    }

    /* ------------------------------------------------------------------ */
    /*  GM 관리: 헬퍼                                                        */
    /* ------------------------------------------------------------------ */

    /** 시스템에 맞는 NPC형 액터 타입을 고른다 ('npc' 우선, 없으면 character가 아닌 첫 타입). */
    _npcActorType() {
        const types = Object.keys(game.model?.Actor ?? {}).filter(t => t !== 'base');
        if (types.includes('npc')) return 'npc';
        return types.find(t => t !== 'character') ?? types[0] ?? 'npc';
    }

    /** 2-탭 삭제 확인: 첫 탭은 무장(3초), 두 번째 탭에서 true. */
    _armDelete(key) {
        const now = Date.now();
        if (this._armed?.key === key && now < this._armed.until) {
            this._armed = null;
            return true;
        }
        this._armed = { key, until: now + 3000 };
        this.render();
        return false;
    }

    _isArmed(key) {
        return this._armed?.key === key && Date.now() < this._armed.until;
    }

    /** 관리용 공통 래퍼: 상점 액터 확인 + 에러 토스트 + 재렌더. */
    async _queueManageSave(key, task) {
        const previous = this._manageSaveChains.get(key) ?? Promise.resolve();
        const next = previous.catch(() => {}).then(task);
        this._manageSaveChains.set(key, next);
        try {
            return await next;
        } finally {
            if (this._manageSaveChains.get(key) === next) this._manageSaveChains.delete(key);
        }
    }

    async _manageCall(fn, { rerender = true, shopId = this.shopId } = {}) {
        if (!game.user.isGM) return;
        const shopActor = game.actors?.get(shopId);
        if (!shopActor) return;
        try {
            await fn(shopActor);
            if (rerender) this.render();
        } catch (e) {
            console.error('Smartphone Shop App | Manage action failed:', e);
            this.widget.showToastNotification?.(loc('manage.actionFailed'));
        }
    }

    async _updateIdentity(patch, { silent = false, rerender = true } = {}) {
        if (!game.user.isGM || !this.shopId) return;
        try {
            const result = await this.api.updateShopIdentity(this.shopId, patch);
            if (result?.ok === false) throw new Error(result.error);
            if (!silent) this.widget.showToastNotification?.(loc('manage.saved'));
            if (rerender) this.render();
        } catch (e) {
            console.error('Smartphone Shop App | Identity update failed:', e);
            this.widget.showToastNotification?.(loc('manage.actionFailed'));
        }
    }

    _saveIdentity() {
        if (!this.element) return;
        const val = (f) => this.element.querySelector(`[data-field="${f}"]`)?.value ?? '';
        this._updateIdentity({
            name: val('m-name').trim(),
            subtitle: val('m-subtitle').trim(),
            owner: val('m-owner').trim(),
            ownerRole: val('m-role').trim(),
            greeting: val('m-greeting').trim()
        });
    }

    async _startSale() {
        if (!game.user.isGM || !this.element) return;
        const pct = Math.floor(Number(this.element.querySelector('[data-field="sale-percent"]')?.value) || 0);
        if (pct <= 0 || pct > 100) {
            this.widget.showToastNotification?.(loc('sale.percentRequired'));
            return;
        }
        const hoursRaw = this.element.querySelector('[data-field="sale-hours"]')?.value ?? '';
        const hours = Number(hoursRaw);
        const hasDuration = hoursRaw !== '' && Number.isFinite(hours) && hours > 0;
        const mode = this.element.querySelector('[data-field="sale-time-mode"]')?.value === 'game' ? 'game' : 'real';
        const label = this.element.querySelector('[data-field="sale-label"]')?.value?.trim() ?? '';
        const patch = { saleEnabled: true, salePercent: pct, saleTimeMode: mode, saleLabel: label };
        if (mode === 'game') {
            const clock = game.modules.get('glitchsmith-lib')?.api?.time ?? null;
            if (clock && hasDuration) {
                patch.saleGameEndsAt = clock.addDuration(clock.now(), { hours });
                patch.saleTimeSource = clock.sourceId();
            } else {
                patch.saleGameEndsAt = null;
                patch.saleTimeSource = '';
            }
        } else {
            patch.saleEndsAt = hasDuration ? Date.now() + hours * 3600000 : null;
        }
        await this._updateIdentity(patch);
    }

    _saleUntilText(sale) {
        if (!sale?.endsAt) return '';
        if (sale.timeMode === 'game') return sale.endsAtDisplay || '';
        return new Date(sale.endsAt).toLocaleString();
    }

    _saleEndsLine(s) {
        if (!s.saleActive) return '';
        if (s.saleTimeMode === 'game') {
            return s.saleGameEndsAtDisplay
                ? `<div class="ssa-sale-ends">${esc(locf('sale.until', { time: s.saleGameEndsAtDisplay }))}</div>`
                : '';
        }
        return s.saleEndsAt
            ? `<div class="ssa-sale-ends">${esc(locf('sale.until', { time: new Date(s.saleEndsAt).toLocaleString() }))}</div>`
            : '';
    }

    async _createShopWithNewActor() {
        if (!game.user.isGM) return;
        const input = this.element?.querySelector('[data-field="new-npc-name"]');
        const name = input?.value?.trim();
        if (!name) {
            this.widget.showToastNotification?.(loc('manage.nameRequired'));
            return;
        }
        try {
            const actor = await Actor.create({ name, type: this._npcActorType() });
            await this.api.createShop(actor);
            this.shopId = actor.id;
            this.view = 'manage';
            this.manageCategoryId = null;
            this.widget.showToastNotification?.(locf('manage.created', { name }));
            this.render();
        } catch (e) {
            console.error('Smartphone Shop App | Shop creation failed:', e);
            this.widget.showToastNotification?.(loc('manage.actionFailed'));
        }
    }

    async _createShopFromActor(actorId) {
        if (!game.user.isGM) return;
        const actor = game.actors?.get(actorId);
        if (!actor) return;
        try {
            await this.api.createShop(actor);
            this.shopId = actor.id;
            this.view = 'manage';
            this.manageCategoryId = null;
            this.widget.showToastNotification?.(locf('manage.created', { name: actor.name }));
            this.render();
        } catch (e) {
            console.error('Smartphone Shop App | Shop creation failed:', e);
            this.widget.showToastNotification?.(loc('manage.actionFailed'));
        }
    }

    async _addCategory() {
        if (!game.user.isGM) return;
        const input = this.element?.querySelector('[data-field="new-cat-name"]');
        const name = input?.value?.trim();
        if (!name) {
            this.widget.showToastNotification?.(loc('manage.nameRequired'));
            return;
        }
        await this._manageCall(async (shopActor) => {
            await this.api.addCategory(shopActor, { name });
        });
    }

    _findManageItem(uuid) {
        for (const cat of this._manageData?.categories ?? []) {
            const row = cat.items.find(i => i.uuid === uuid);
            if (row) return row;
        }
        return null;
    }

    /* ------------------------------------------------------------------ */
    /*  GM 관리: 화면                                                        */
    /* ------------------------------------------------------------------ */

    _buildCreateScreen() {
        if (!game.user.isGM) return this._screen(this._titleHtml(loc('title')), 'back', this._notice('lock', loc('manage.gmOnly')));

        const shopIds = new Set(this.api.getShopDirectory().map(r => r.id));
        const actors = (game.actors ?? [])
            .filter(a => !shopIds.has(a.id))
            .sort((a, b) => (a.name ?? '').localeCompare(b.name ?? ''));

        const actorRows = actors.map(a => `
            <div class="ssa-actor-row" data-action="create-from-actor" data-actor-id="${esc(a.id)}" data-search="${esc((a.name ?? '').toLowerCase())}">
                <img class="ssa-actor-img" src="${esc(a.img || 'icons/svg/mystery-man.svg')}" alt="">
                <span class="ssa-actor-name">${esc(a.name)}</span>
                <span class="ssa-badge ssa-badge-type">${esc(a.type)}</span>
                <i class="fas fa-chevron-right ssa-chevron"></i>
            </div>
        `).join('');

        const body = `
            <div class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(loc('manage.newNpcSection'))}</span></div>
                <div class="ssa-inline-row">
                    <input type="text" class="ssa-input" data-field="new-npc-name" placeholder="${esc(loc('manage.newNpcName'))}">
                    <button class="ssa-mini-btn primary" data-action="create-new-npc"><span>${esc(loc('manage.createAndOpen'))}</span></button>
                </div>
            </div>
            <div class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(loc('manage.pickExisting'))}</span></div>
                <div class="ssa-search">
                    <i class="fas fa-magnifying-glass"></i>
                    <input type="text" data-field="actor-search" placeholder="${esc(loc('manage.actorSearchPlaceholder'))}">
                </div>
                <div class="ssa-actor-list">
                    ${actorRows || `<div class="ssa-bal-empty">${esc(loc('manage.noActors'))}</div>`}
                </div>
            </div>
        `;
        return this._screen(this._titleHtml(loc('manage.createTitle')), 'back', body);
    }

    _suggestCatalogCategory(category, taxonomy) {
        const explicit = category?.suggestedCatalogCategoryId ?? category?.catalogSuggestion?.id ?? null;
        if (explicit && taxonomy.some(row => row.id === explicit)) return taxonomy.find(row => row.id === explicit);
        const needles = uniqueStrings([category?.name, category?.kr, category?.code, category?.tag]).map(normalizedSearchText);
        let best = null;
        let score = 0;
        for (const row of taxonomy) {
            const candidates = uniqueStrings([row.id, row.label, row.name, ...listOf(row.aliases)]).map(normalizedSearchText);
            for (const needle of needles) {
                if (!needle) continue;
                for (const candidate of candidates) {
                    const nextScore = candidate === needle ? 3 : (candidate.includes(needle) || needle.includes(candidate) ? 1 : 0);
                    if (nextScore > score) {
                        score = nextScore;
                        best = row;
                    }
                }
            }
        }
        return best;
    }

    async _buildManageScreen() {
        if (!game.user.isGM) return this._screen(this._titleHtml(loc('title')), 'back', this._notice('lock', loc('manage.gmOnly')));
        const data = await this.api.getShopManageData(this.shopId);
        if (!data.ok) return this._screen(this._titleHtml(loc('manage.title')), 'back', this._notice('store-slash', loc('errors.shopGone')));
        this._manageData = data;
        const s = data.shop;
        const catalogMappingAvailable = Array.isArray(data.taxonomy) || typeof this.api?.getCatalogTaxonomy === 'function';
        const catalogTaxonomy = Array.isArray(data.taxonomy) && data.taxonomy.length
            ? data.taxonomy
            : (catalogMappingAvailable ? await this._getCatalogTaxonomy({ force: true }) : []);

        const opts = this.api.getShopAppearanceOptions?.() ?? { layouts: [], themes: {} };
        const themeChoices = opts.themes?.[s.layout] ?? [];

        const identity = `
            <div class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(loc('manage.identity'))}</span></div>
                <div class="ssa-form-row"><label class="ssa-form-label">${esc(loc('manage.fieldName'))}</label>
                    <input type="text" class="ssa-input" data-field="m-name" value="${esc(s.name)}"></div>
                <div class="ssa-form-row"><label class="ssa-form-label">${esc(loc('manage.fieldSubtitle'))}</label>
                    <input type="text" class="ssa-input" data-field="m-subtitle" value="${esc(s.subtitle)}"></div>
                <div class="ssa-inline-row">
                    <div class="ssa-form-row" style="flex:1"><label class="ssa-form-label">${esc(loc('manage.fieldOwner'))}</label>
                        <input type="text" class="ssa-input" data-field="m-owner" value="${esc(s.owner)}"></div>
                    <div class="ssa-form-row" style="flex:1"><label class="ssa-form-label">${esc(loc('manage.fieldOwnerRole'))}</label>
                        <input type="text" class="ssa-input" data-field="m-role" value="${esc(s.ownerRole)}"></div>
                </div>
                <div class="ssa-form-row"><label class="ssa-form-label">${esc(loc('manage.fieldGreeting'))}</label>
                    <textarea class="ssa-textarea" data-field="m-greeting">${esc(s.greeting)}</textarea></div>
                <button class="ssa-mini-btn primary" data-action="save-identity"><span>${esc(loc('manage.save'))}</span></button>
            </div>
        `;

        const visibility = `
            <div class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(loc('manage.visibility'))}</span></div>
                <label class="ssa-switch-row">
                    <span class="ssa-switch-text">${esc(loc('manage.publicShop'))}<em>${esc(loc('manage.publicHint'))}</em></span>
                    <input type="checkbox" class="ssa-switch" data-field="m-public" ${s.publicShop ? 'checked' : ''}>
                </label>
            </div>
        `;

        const saleBlock = `
            <div class="ssa-card-block">
                <div class="ssa-block-title">
                    <span>${esc(loc('sale.manageTitle'))}</span>
                    ${s.saleActive ? `<em class="ssa-sale-live">LIVE</em>` : ''}
                </div>
                <div class="ssa-inline-row">
                    <div class="ssa-form-row" style="flex:1"><label class="ssa-form-label">${esc(loc('sale.percentLabel'))}</label>
                        <input type="number" class="ssa-input" data-field="sale-percent" value="${s.salePercent || ''}" min="1" max="100" placeholder="20"></div>
                    <div class="ssa-form-row" style="flex:1"><label class="ssa-form-label">${esc(loc('sale.hoursLabel'))}</label>
                        <input type="number" class="ssa-input" data-field="sale-hours" min="0" placeholder="${esc(loc('sale.hoursPlaceholder'))}"></div>
                </div>
                <div class="ssa-form-row"><label class="ssa-form-label">${esc(loc('sale.timeModeLabel'))}</label>
                    <select class="ssa-input" data-field="sale-time-mode">
                        <option value="real" ${s.saleTimeMode === 'game' ? '' : 'selected'}>${esc(loc('sale.timeModeReal'))}</option>
                        <option value="game" ${s.saleTimeMode === 'game' ? 'selected' : ''}>${esc(loc('sale.timeModeGame'))}</option>
                    </select></div>
                <div class="ssa-form-row"><label class="ssa-form-label">${esc(loc('sale.labelLabel'))}</label>
                    <input type="text" class="ssa-input" data-field="sale-label" value="${esc(s.saleLabel)}" placeholder="${esc(loc('sale.labelPlaceholder'))}"></div>
                <div class="ssa-inline-row">
                    <button class="ssa-mini-btn primary" data-action="sale-start"><span>${esc(loc(s.saleActive ? 'sale.update' : 'sale.start'))}</span></button>
                    ${s.saleEnabled ? `<button class="ssa-mini-btn danger" data-action="sale-stop"><span>${esc(loc('sale.stop'))}</span></button>` : ''}
                </div>
                ${this._saleEndsLine(s)}
                ${s.saleSourceChanged ? `<div class="ssa-sale-ends">${esc(loc('sale.sourceChanged'))}</div>` : ''}
            </div>
        `;

        const appearance = `
            <div class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(loc('manage.appearance'))}</span></div>
                <div class="ssa-inline-row">
                    <span class="ssa-form-label" style="flex:1">${esc(loc('manage.accent'))}</span>
                    <input type="color" class="ssa-color" data-field="m-accent" value="${esc(/^#[0-9a-fA-F]{6}$/.test(s.accentColor) ? s.accentColor : '#8f9aa8')}">
                    <button class="ssa-mini-btn" data-action="accent-reset"><span>${esc(loc('manage.reset'))}</span></button>
                </div>
                <div class="ssa-inline-row">
                    <img class="ssa-art-thumb" src="${esc(s.npcArt || 'icons/svg/mystery-man.svg')}" alt="">
                    <span class="ssa-form-label" style="flex:1">${esc(loc('manage.npcArt'))}</span>
                    <button class="ssa-mini-btn" data-action="pick-art" data-art="npcArt"><span>${esc(loc('manage.change'))}</span></button>
                </div>
                <div class="ssa-inline-row">
                    <img class="ssa-art-thumb" src="${esc(s.directoryArt || s.npcArt || 'icons/svg/mystery-man.svg')}" alt="">
                    <span class="ssa-form-label" style="flex:1">${esc(loc('manage.directoryArt'))}</span>
                    <button class="ssa-mini-btn" data-action="pick-art" data-art="directoryArt"><span>${esc(loc('manage.change'))}</span></button>
                </div>
                <div class="ssa-inline-row">
                    <div class="ssa-form-row" style="flex:1"><label class="ssa-form-label">${esc(loc('manage.layout'))}</label>
                        <select class="ssa-input" data-field="m-layout">
                            ${(opts.layouts ?? []).map(l => `<option value="${esc(l)}" ${l === s.layout ? 'selected' : ''}>${esc(l)}</option>`).join('')}
                        </select></div>
                    <div class="ssa-form-row" style="flex:1"><label class="ssa-form-label">${esc(loc('manage.theme'))}</label>
                        <select class="ssa-input" data-field="m-theme">
                            ${themeChoices.map(t => `<option value="${esc(t)}" ${t === s.layoutTheme ? 'selected' : ''}>${esc(t)}</option>`).join('')}
                        </select></div>
                </div>
            </div>
        `;

        const catRows = data.categories.map(cat => {
            const armed = this._isArmed(`cat:${cat.id}`);
            const suggestion = this._suggestCatalogCategory(cat, catalogTaxonomy);
            const currentCatalogCategory = cat.catalogCategoryId ?? '';
            const catalogSelect = catalogMappingAvailable ? `
                <label class="ssa-mcat-catalog">
                    <span>${esc(loc('manage.catalogMappingLabel'))}</span>
                    <select class="ssa-catalog-select" data-field="cat-catalog-category" data-category-id="${esc(cat.id)}">
                        <option value="" ${currentCatalogCategory ? '' : 'selected'}>${esc(suggestion
                            ? locf('manage.catalogSuggested', { name: suggestion.label ?? suggestion.name ?? suggestion.id })
                            : loc('manage.catalogAuto'))}</option>
                        ${catalogTaxonomy.map(row => `<option value="${esc(row.id)}" ${currentCatalogCategory === row.id ? 'selected' : ''}>${esc(row.label ?? row.name ?? row.id)}</option>`).join('')}
                    </select>
                </label>` : '';
            return `
            <div class="ssa-mcat-row">
                <input type="text" class="ssa-input compact" data-field="cat-name" data-category-id="${esc(cat.id)}" value="${esc(cat.name)}">
                ${catalogSelect}
                <button class="ssa-mini-btn" data-action="manage-items" data-category-id="${esc(cat.id)}"><span>${esc(locf('manage.itemsBtn', { count: cat.items.length }))}</span></button>
                <button class="ssa-mini-btn danger ${armed ? 'armed' : ''}" data-action="cat-delete" data-category-id="${esc(cat.id)}"><span>${armed ? esc(loc('manage.confirmAgain')) : '<i class="fas fa-trash"></i>'}</span></button>
            </div>`;
        }).join('');

        const categories = `
            <div class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(loc('manage.categories'))}</span></div>
                ${catRows || `<div class="ssa-bal-empty">${esc(loc('manage.noCategories'))}</div>`}
                <div class="ssa-inline-row">
                    <input type="text" class="ssa-input" data-field="new-cat-name" placeholder="${esc(loc('manage.newCategoryName'))}">
                    <button class="ssa-mini-btn primary" data-action="cat-add"><span>${esc(loc('manage.addCategory'))}</span></button>
                </div>
            </div>
        `;

        return this._screen(this._titleHtml(loc('manage.title')), 'back', identity + visibility + saleBlock + appearance + categories);
    }

    async _buildManageItemsScreen() {
        if (!game.user.isGM) return this._screen(this._titleHtml(loc('title')), 'back', this._notice('lock', loc('manage.gmOnly')));
        const data = await this.api.getShopManageData(this.shopId);
        if (!data.ok) return this._screen(this._titleHtml(loc('manage.title')), 'back', this._notice('store-slash', loc('errors.shopGone')));
        this._manageData = data;
        const itemCatalogMappingAvailable = Array.isArray(data.taxonomy) || typeof this.api?.getCatalogTaxonomy === 'function';
        const itemCatalogTaxonomy = Array.isArray(data.taxonomy) && data.taxonomy.length
            ? data.taxonomy
            : (itemCatalogMappingAvailable ? await this._getCatalogTaxonomy({ force: true }) : []);
        const cat = data.categories.find(c => c.id === this.manageCategoryId);
        if (!cat) {
            this.view = 'manage';
            return this._buildManageScreen();
        }

        const dropHint = `
            <div class="ssa-drop-hint">
                <i class="fas fa-hand-pointer"></i>
                <span>${esc(loc('manage.dropHint'))}</span>
            </div>
        `;

        const rows = cat.items.map(row => {
            const armed = this._isArmed(`item:${row.uuid}`);
            const priceValue = row.overridePriceSpec ?? (row.overridePrice != null ? String(row.overridePrice) : '');
            const itemCatalogSelect = itemCatalogMappingAvailable ? `
                <label class="ssa-mrow-catalog">
                    <span>${esc(loc('manage.itemCatalogMappingLabel'))}</span>
                    <select class="ssa-catalog-select" data-field="mi-catalog-category" data-uuid="${esc(row.uuid)}">
                        <option value="" ${row.catalogCategoryId ? '' : 'selected'}>${esc(loc('manage.itemCatalogInherit'))}</option>
                        ${itemCatalogTaxonomy.map(category => `<option value="${esc(category.id)}" ${row.catalogCategoryId === category.id ? 'selected' : ''}>${esc(category.label ?? category.name ?? category.id)}</option>`).join('')}
                    </select>
                </label>` : '';
            return `
            <div class="ssa-mrow ${row.unavailable ? 'unavailable' : ''}">
                <img class="ssa-mrow-img" src="${esc(row.img)}" alt="">
                <div class="ssa-mrow-info">
                    <div class="ssa-mrow-name">${esc(row.name)}${row.isService ? `<span class="ssa-badge ssa-badge-service">${esc(loc('service'))}</span>` : ''}</div>
                    <div class="ssa-mrow-price">${esc(row.priceDisplay)}</div>
                </div>
                <input type="number" class="ssa-input compact" data-field="mi-stock" data-uuid="${esc(row.uuid)}" value="${row.stock ?? ''}" min="0" placeholder="∞" title="${esc(loc('manage.stockLabel'))}">
                <input type="text" class="ssa-input compact" data-field="mi-price" data-uuid="${esc(row.uuid)}" value="${esc(priceValue)}" placeholder="${esc(loc('manage.pricePlaceholder'))}" title="${esc(loc('manage.priceLabel'))}">
                <button class="ssa-mini-btn danger ${armed ? 'armed' : ''}" data-action="mi-delete" data-uuid="${esc(row.uuid)}"><span>${armed ? esc(loc('manage.confirmAgain')) : '<i class="fas fa-trash"></i>'}</span></button>
                ${itemCatalogSelect}
            </div>`;
        }).join('');

        const body = `
            ${dropHint}
            <div class="ssa-card-block">
                <div class="ssa-block-title"><span>${esc(locf('manage.itemsIn', { name: cat.name }))}</span></div>
                <div class="ssa-mrow-head">
                    <span></span><span></span>
                    <span>${esc(loc('manage.stockLabel'))}</span>
                    <span>${esc(loc('manage.priceLabel'))}</span>
                    <span></span>
                </div>
                ${rows || `<div class="ssa-bal-empty">${esc(loc('manage.noItems'))}</div>`}
            </div>
        `;
        return this._screen(this._titleHtml(cat.name), 'back', body);
    }
}
