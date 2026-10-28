import { SmartphoneTime } from "../SmartphoneTime.js";

export class WidgetClock {
    constructor(widgetManager) {
        this.widgetManager = widgetManager;
        this._clockInterval = null;
        this._clockInitialized = false;
        this.updateClockDisplay = this.updateClockDisplay.bind(this);
    }

    async start() {
        if (this._clockInitialized) {
            this.updateClockDisplay();
            return;
        }
        
        this._clockInterval = setInterval(() => {
            if (!game.settings.get("smartphone-widget", "useGameTime")) {
                this.updateClockDisplay();
            }

            if (this.widgetManager.currentApp === 'home') {
                const homeApp = this.widgetManager.apps.get('home');
                if (homeApp && typeof homeApp.checkWidgetAutoSlide === 'function') {
                    homeApp.checkWidgetAutoSlide();
                }
            }
        }, 1000);
        
        Hooks.on("changeSetting", this.updateClockDisplay);
        this._clockInitialized = true;
        this.updateClockDisplay();
    }

    stop() {
        if (this._clockInterval) {
            clearInterval(this._clockInterval);
            this._clockInterval = null;
        }
        
        Hooks.off(SmartphoneTime.HOOK_NAME, this.updateClockDisplay);
        Hooks.off("changeSetting", this.updateClockDisplay);
        
        this._clockInitialized = false;
    }

    updateClockDisplay() {
        if (!this.widgetManager.element) return;
        const timeElement = this.widgetManager.element.querySelector(".time");
        if (!timeElement) return;

        const useGameTime = game.settings.get("smartphone-widget", "useGameTime");
        const clockFormat = game.settings.get("smartphone-widget", "clockFormat");
        let timeString = "";

        if (useGameTime) {
            const now = SmartphoneTime.now();
            if (clockFormat === "12h") {
                const d = SmartphoneTime.getDateObject(now);
                const m = String(d.minute).padStart(2, '0');
                const timeConfig = SmartphoneTime.getConfig();
                const hoursInDay = timeConfig.hoursInDay || 24;
                const minutesInHour = timeConfig.minutesInHour || 60;
                const currentTimeFloat = d.hour + (d.minute / minutesInHour);
                const middayFloat = hoursInDay / 2;
                const a = currentTimeFloat >= middayFloat ? "PM" : "AM";
                let h = d.hour;
                if (h >= middayFloat) {
                    if (h > middayFloat) h = h - middayFloat;
                }
                if (h === 0) h = middayFloat;
                h = Math.floor(h);
                timeString = `${String(h).padStart(2, '0')}:${m} ${a}`;
            } else {
                timeString = SmartphoneTime.format(now, "HH:mm");
            }
        } else {
            const now = new Date();
            timeString = now.toLocaleTimeString(navigator.language, {
                hour: "2-digit", minute: "2-digit", hour12: clockFormat === "12h",
            });
        }
        timeElement.textContent = timeString;
    }

    handleTimeUpdate() {
        if (game.settings.get("smartphone-widget", "useGameTime")) {
            this.updateClockDisplay();
            
            const currentAppInstance = this.widgetManager.apps.get(this.widgetManager.currentApp);
            if (!currentAppInstance) return;

            if (this.widgetManager.currentApp === "messages" && typeof currentAppInstance.updateMessageTimes === "function") {
                currentAppInstance.updateMessageTimes();
            }

            if (this.widgetManager.currentApp === "calendar" && typeof currentAppInstance.render === "function") {
                currentAppInstance.render();
            }

            if (this.widgetManager.currentApp === "home" && typeof currentAppInstance.updateTimeWidgets === "function") {
                currentAppInstance.updateTimeWidgets();
            }
        }
    }
}
