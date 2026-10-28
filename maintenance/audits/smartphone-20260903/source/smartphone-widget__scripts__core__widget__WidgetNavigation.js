export class WidgetNavigation {
    constructor(widgetManager) {
        this.widgetManager = widgetManager;
    }

    setupKeypad(container) {
        const razrKeypad = container.querySelector('.feature-phone-keypad.razr-keypad');
        if (razrKeypad) this._attachKeypadListeners(razrKeypad);

        const monolithKeypad = container.querySelector('.feature-phone-keypad.monolith-keypad');
        if (monolithKeypad) this._attachKeypadListeners(monolithKeypad);
    }

    _attachKeypadListeners(keypadElement) {
        keypadElement.querySelectorAll('.keypad-button').forEach(button => {
            const clickHandler = async () => {
                const phoneApp = this.widgetManager.apps.get('phone');
                
                if (button.classList.contains('number')) {
                    const value = button.textContent.match(/^\d/)[0];
                    if (phoneApp && this.widgetManager.currentApp === 'phone' && phoneApp.currentView === 'keypad') {
                        phoneApp.appendToDialInput(value);
                    }
                } else if (button.classList.contains('symbol')) {
                    const value = button.textContent;
                    if (phoneApp && this.widgetManager.currentApp === 'phone' && phoneApp.currentView === 'keypad') {
                        phoneApp.appendToDialInput(value);
                    }
                } else if (button.classList.contains('call')) {
                    if (phoneApp) await phoneApp.initiateCall();
                } else if (button.classList.contains('end-call')) {
                    if (phoneApp && phoneApp.activeCall) phoneApp.endCall();
                } else if (button.classList.contains('contacts') || button.classList.contains('soft-right')) {
                    this.widgetManager.switchApp('contacts');
                } else if (button.classList.contains('messages')) {
                    this.widgetManager.switchApp('messages');
                } else if (button.classList.contains('soft-left')) {
                    this.widgetManager.switchApp('settings');
                } else if (button.classList.contains('clear-back')) {
                    if (phoneApp && this.widgetManager.currentApp === 'phone' && phoneApp.currentView === 'keypad') {
                        if (phoneApp.dialedNumber && phoneApp.dialedNumber.length > 0) {
                            phoneApp.handleBackspace();
                        } else {
                            this.widgetManager.handleBackNavigation();
                        }
                    } else {
                        this.widgetManager.handleBackNavigation();
                    }
                }
            };
            this.widgetManager.addListener(button, 'click', clickHandler);
        });
    }

    setupNavigationHandlers(container) {
        const backBtn = container.querySelector(".back-btn");
        const homeBtn = container.querySelector(".home-btn");
        const menuBtn = container.querySelector(".menu-btn");
        const persistentHomeBtn = container.querySelector(".persistent-home-btn");

        if (persistentHomeBtn) {
            this.widgetManager.addListener(persistentHomeBtn, "click", () => this.widgetManager.navigateToHome());
        }
        if (backBtn) {
            this.widgetManager.addListener(backBtn, "click", () => this.widgetManager.handleBackNavigation());
        }
        if (homeBtn) {
            this.widgetManager.addListener(homeBtn, "click", () => this.widgetManager.navigateToHome());
        }
        if (menuBtn) {
            this.widgetManager.addListener(menuBtn, "click", () => this.widgetManager.toggleMenu());
        }

        this._setupSwipeGesture(container);
    }

    _setupSwipeGesture(container) {
        const smartphoneScreen = container.querySelector(".smartphone-screen");
        const navigationBar = container.querySelector(".navigation-bar");
        
        let isGestureStarted = false;
        let startY = 0;
        let navHideTimer;

        const handleGestureStart = (e) => {
            const rect = smartphoneScreen.getBoundingClientRect();
            const eventY = e.touches ? e.touches[0].clientY : e.clientY;
            if (eventY - rect.top > rect.height - 25) {
                isGestureStarted = true;
                startY = eventY;
            }
        };

        const handleGestureMove = (e) => {
            if (!isGestureStarted) return;
            const currentY = e.touches ? e.touches[0].clientY : e.clientY;
            if (startY - currentY > 30) {
                navigationBar.classList.add("visible");
                isGestureStarted = false;
                this.widgetManager._dismissGestureHint("bottom");
                clearTimeout(navHideTimer);
                navHideTimer = setTimeout(() => { navigationBar.classList.remove("visible"); }, 1500);
            }
        };

        const handleGestureEnd = () => { isGestureStarted = false; };

        const doc = container.ownerDocument;
        this.widgetManager.addListener(smartphoneScreen, "mousedown", handleGestureStart);
        this.widgetManager.addListener(doc, "mousemove", handleGestureMove);
        this.widgetManager.addListener(doc, "mouseup", handleGestureEnd);
        this.widgetManager.addListener(smartphoneScreen, "touchstart", handleGestureStart, { passive: true });
        this.widgetManager.addListener(doc, "touchmove", handleGestureMove);
        this.widgetManager.addListener(doc, "touchend", handleGestureEnd);

        this.widgetManager.addListener(navigationBar, "mouseenter", () => clearTimeout(navHideTimer));
        this.widgetManager.addListener(navigationBar, "mouseleave", () => {
            clearTimeout(navHideTimer);
            navHideTimer = setTimeout(() => { navigationBar.classList.remove("visible"); }, 2000);
        });
    }
}
