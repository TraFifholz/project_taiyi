/**
 * =======================================================================
 * ★★★ 중요: SmartphoneTime.js 사용 규칙 ★★★
 * =======================================================================
 * * 이 모듈은 파운드리 VTT의 기본 시간과 독립적으로 작동하는 독자적인 게임 세계 시간을 관리합니다.
 * TRPG의 특수한 연표(예: '0064년')를 정확하게 처리하기 위해 만들어졌습니다.
 * * [ 핵심 규칙 ]
 * 이 파일과 이 모듈을 사용하는 다른 파일(예: CalendarApp.js) 내에서
 * 시간 계산이나 날짜 객체 생성 시 절대로 JavaScript의 기본 `new Date()` 생성자를 직접 사용해서는 안 됩니다.
 * * [ 이유 ]
 * 기본 `Date` 객체는 '0064'년과 같이 100 미만의 연도를 '1964'년으로 잘못 해석하는 심각한 문제가 있습니다.
 * 이는 모듈 전체의 시간 계산을 망가뜨리는 원인이 됩니다.
 * * [ 올바른 사용법 ]
 * 1. 현재 시간 가져오기 (숫자): SmartphoneTime.now()
 * 2. 숫자에서 날짜 정보 객체로 변환: SmartphoneTime.getDateObject(timestamp) -> { year, month, day, ... }
 * 3. 날짜 정보 객체에서 숫자로 변환: SmartphoneTime.fromObjectToTimestamp(dateObject)
 * 4. 날짜/시간 표시 (문자열): SmartphoneTime.format(timestamp, 'YYYY-MM-DD HH:mm')
 * * `SmartphoneTime.toDate()` 함수는 달력 UI의 요일(getDay()) 계산 등 극히 제한적인 목적으로만 존재하며,
 * 일반적인 시간 계산 로직에서는 절대 사용해서는 안 됩니다.
 * */
import { SmartphoneWidget } from '../smartphone-widget.js';

export class SmartphoneTime {
    static ID = 'smartphone-widget';
    static SETTING_KEY = 'smartphone-world-time';
    static CONFIG_KEY = 'smartphone-time-config';
    static HOOK_NAME = 'smartphoneTimeChanged';

    static socket = null;
    static _lastKnownExternalTimes = new Map();
    static _warnedUnavailableSources = new Set();

    // 모듈 활성화 상태 실시간 확인
    static get isSimpleCalendarActive() {
        return game.modules.get("foundryvtt-simple-calendar")?.active ?? false;
    }

    static get isSimpleCalendarRebornActive() {
        return game.modules.get("foundryvtt-simple-calendar-reborn")?.active ?? false;
    }

    static get simpleCalendarApi() {
        return globalThis.SimpleCalendar?.api ?? null;
    }

    static isSimpleCalendarSource(source = SmartphoneTime.getTimeSource()) {
        return source === 'simple-calendar' || source === 'simple-calendar-reborn';
    }

    static isSimpleCalendarModuleActive(source = SmartphoneTime.getTimeSource()) {
        switch (source) {
            case 'simple-calendar':
                return SmartphoneTime.isSimpleCalendarActive;
            case 'simple-calendar-reborn':
                return SmartphoneTime.isSimpleCalendarRebornActive;
            default:
                return false;
        }
    }

    static getSimpleCalendarApi(source = SmartphoneTime.getTimeSource()) {
        if (!SmartphoneTime.isSimpleCalendarSource(source)) return null;
        if (!SmartphoneTime.isSimpleCalendarModuleActive(source)) return null;
        return SmartphoneTime.simpleCalendarApi;
    }

    static get isSeasonsAndStarsActive() {
        return game.modules.get("seasons-and-stars")?.active ?? false;
    }

    static get isSimpleTimekeepingActive() {
        return game.modules.get("simple-timekeeping")?.active ?? false;
    }

    static get isCalendariaActive() {
        return game.modules.get("calendaria")?.active ?? false;
    }

    static initialize(socket) {
        if (socket) {
            SmartphoneTime.socket = socket;
        }

        // 설정 등록
        game.settings.register(SmartphoneTime.ID, SmartphoneTime.SETTING_KEY, {
            name: "Smartphone World Time",
            scope: "world",
            config: false,
            type: Number,
            default: 0, 
        });

        game.settings.register(SmartphoneTime.ID, SmartphoneTime.CONFIG_KEY, {
            name: "Smartphone Time And Calendar Configuration",
            scope: "world",
            config: false,
            type: Object,
            default: SmartphoneTime.getDefaultConfig()
        });

        // 1. Simple Calendar 시간 변경 감지
        Hooks.on("simple-calendar-date-time-change", () => {
            // 현재 설정된 소스가 맞는지 확인
            if (!SmartphoneTime.isSimpleCalendarSource()) return;
            
            const simpleCalendarApi = SmartphoneTime.getSimpleCalendarApi();
            if (simpleCalendarApi) {
                const newTimestamp = simpleCalendarApi.timestamp() * 1000;
                
                // 앱들에게 시간 변경 알림
                Hooks.callAll(SmartphoneTime.HOOK_NAME, newTimestamp);
                
                // GM은 소켓을 통해 다른 클라이언트들의 상단 바 시간도 갱신시킴
                if (game.user.isGM) {
                    SmartphoneWidget.SOCKET?.executeForEveryone('updateStatusBarTime');
                }
            }
        });

        // 2. Calendaria 시간 변경 감지
        Hooks.on("calendaria.dateTimeChange", (data) => {
            if (SmartphoneTime.getTimeSource() !== 'calendaria') return;
            if (SmartphoneTime.isCalendariaActive && globalThis.CALENDARIA?.api) {
                const newTimestamp = data.worldTime * 1000;
                Hooks.callAll(SmartphoneTime.HOOK_NAME, newTimestamp);
                if (game.user.isGM) {
                    SmartphoneWidget.SOCKET?.executeForEveryone('updateStatusBarTime');
                }
            }
        });

        // 3. Foundry Core Time (Simple Timekeeping / Seasons & Stars) 시간 변경 감지
        Hooks.on("updateWorldTime", (worldTime, delta) => {
            const currentSource = SmartphoneTime.getTimeSource();
            
            // Core Time을 사용하는 모듈들인 경우에만 작동
            if (currentSource === 'seasons-and-stars' || currentSource === 'simple-timekeeping') {
                const newTimestamp = worldTime * 1000; // 초 -> 밀리초 변환
                
                // 앱들에게 시간 변경 알림
                Hooks.callAll(SmartphoneTime.HOOK_NAME, newTimestamp);
                
                // 내 위젯 인스턴스가 있다면 즉시 업데이트
                SmartphoneWidget.getInstance().then(instance => instance?.handleTimeUpdate());
            }
        });

        // 3. 디버그 로그 (초기화 확인용)
        Hooks.once('ready', () => {
            console.log(`Smartphone Widget | Time System Initialized. Current Source: ${SmartphoneTime.getTimeSource()}`);
        });
    }
    
    static getDefaultConfig() {
        return {
            secondsInMinute: 60,
            minutesInHour: 60,
            hoursInDay: 24,
            weekdays: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
            months: [
                { name: 'January', days: 31, isLeap: false, leapOffset: 0 },
                { name: 'February', days: 28, isLeap: true, leapOffset: 1 },
                { name: 'March', days: 31, isLeap: false, leapOffset: 0 },
                { name: 'April', days: 30, isLeap: false, leapOffset: 0 },
                { name: 'May', days: 31, isLeap: false, leapOffset: 0 },
                { name: 'June', days: 30, isLeap: false, leapOffset: 0 },
                { name: 'July', days: 31, isLeap: false, leapOffset: 0 },
                { name: 'August', days: 31, isLeap: false, leapOffset: 0 },
                { name: 'September', days: 30, isLeap: false, leapOffset: 0 },
                { name: 'October', days: 31, isLeap: false, leapOffset: 0 },
                { name: 'November', days: 30, isLeap: false, leapOffset: 0 },
                { name: 'December', days: 31, isLeap: false, leapOffset: 0 }
            ],
            year: 1, month: 1, day: 1, hour: 0, minute: 0, second: 0,
            leapYearRule: { frequency: 4, exception: 100, proleptic: 400 },
            timeShortcuts: {
                morning: "08:00",
                midday: "12:00",
                evening: "18:00",
                midnight: "00:00"
            },
            lightingFX: {
                enabled: true,
                animate: true,
                configs: {
                    dawn: {
                        start: "06:00",
                        darkness: 0.75,
                        daylightColor: "#a56633",
                        daylight: { intensity: 0.3, luminosity: -0.25, saturation: 1, shadows: 0 },
                        darknessColor: "#0d1a2e",
                        darknessEffect: { intensity: 0.5, luminosity: -0.5, saturation: 0, shadows: 0.5 }
                    },
                    day: {
                        start: "08:00",
                        darkness: 0,
                        daylightColor: "#ffffff",
                        daylight: { intensity: 0.5, luminosity: 0, saturation: 1, shadows: 0 },
                        darknessColor: "#0d1a2e",
                        darknessEffect: { intensity: 0.5, luminosity: -0.5, saturation: 0, shadows: 0.5 }
                    },
                    dusk: {
                        start: "18:00",
                        darkness: 0.75,
                        daylightColor: "#ff7b25",
                        daylight: { intensity: 0.3, luminosity: -0.25, saturation: 1, shadows: 0 },
                        darknessColor: "#0d1a2e",
                        darknessEffect: { intensity: 0.5, luminosity: -0.5, saturation: 0, shadows: 0.5 }
                    },
                    night: {
                        start: "20:00",
                        darkness: 1.0,
                        daylightColor: "#ffffff",
                        daylight: { intensity: 0.5, luminosity: 0, saturation: 1, shadows: 0 },
                        darknessColor: "#0d1a2e",
                        darknessEffect: { intensity: 0.5, luminosity: -0.5, saturation: 0, shadows: 0.5 }
                    }
                }
            }
        };
    }

    static getConfig() {
        return game.settings.get(SmartphoneTime.ID, SmartphoneTime.CONFIG_KEY);
    }
    
    static getTimeSource() {
        return game.settings.get(SmartphoneTime.ID, "timeSource") || "internal";
    }    

    static getCalendarConfig() {
        const source = SmartphoneTime.getTimeSource();
        
        try {
            switch (source) {
                case 'simple-calendar':
                case 'simple-calendar-reborn': {
                    const simpleCalendarApi = SmartphoneTime.getSimpleCalendarApi(source);
                    if (simpleCalendarApi) {
                        const scMonths = simpleCalendarApi.getAllMonths();
                        const scWeekdays = simpleCalendarApi.getAllWeekdays();

                        return { 
                            months: scMonths.map(m => ({
                                name: m.name,
                                abbreviation: m.abbreviation,
                                days: m.numberOfDays, 
                                leapDays: m.numberOfLeapYearDays,
                                numericRepresentation: m.numericRepresentation
                            })),
                            weekdays: scWeekdays 
                        };
                    }
                    break;
                }
                case 'simple-timekeeping':
                    if (SmartphoneTime.isSimpleTimekeepingActive && game.time.calendar) {
                        return {
                            months: game.time.calendar.months.values,
                            weekdays: game.time.calendar.days.values
                        };
                    }
                    break;
                case 'calendaria':
                    if (SmartphoneTime.isCalendariaActive && globalThis.CALENDARIA?.api) {
                        const cal = CALENDARIA.api.getActiveCalendar();
                        if (cal) {
                            return {
                                months: cal.monthsArray?.map(m => ({
                                    name: m.name,
                                    days: m.days ?? m.numberOfDays,
                                })) ?? [],
                                weekdays: cal.weekdaysArray?.map(w => w.name) ?? []
                            };
                        }
                    }
                    break;
                case 'seasons-and-stars':
                    if (SmartphoneTime.isSeasonsAndStarsActive && game.seasonsStars?.api) {
                        const cal = game.seasonsStars.api.getActiveCalendar();
                        return { months: cal.months, weekdays: cal.weekdays };
                    }
                    break;
                case 'internal':
                default:
                    return SmartphoneTime.getConfig();
            }
        } catch (e) {
            console.error(`[SmartphoneTime] Error getting calendar config for source '${source}':`, e);
        }
        
        return SmartphoneTime.getDefaultConfig();
    }
        
    static _rememberExternalTime(source, timestamp) {
        const numericTimestamp = Number(timestamp);
        if (!Number.isFinite(numericTimestamp)) return null;
        SmartphoneTime._lastKnownExternalTimes.set(source, numericTimestamp);
        return numericTimestamp;
    }

    static _getExternalTimeFallback(source, warn = false, preferLastKnown = false) {
        if (warn && !SmartphoneTime._warnedUnavailableSources.has(source)) {
            SmartphoneTime._warnedUnavailableSources.add(source);
            console.warn(
                `Smartphone Widget | Time source "${source}" is unavailable; using its last known game time or Foundry world time until it returns.`
            );
        }

        const lastKnownTime = SmartphoneTime._lastKnownExternalTimes.get(source);
        if (preferLastKnown && Number.isFinite(lastKnownTime)) {
            return lastKnownTime;
        }

        const coreWorldTime = Number(game.time?.worldTime);
        if (Number.isFinite(coreWorldTime)) {
            const coreTimestamp = coreWorldTime * 1000;
            return preferLastKnown
                ? coreTimestamp
                : SmartphoneTime._rememberExternalTime(source, coreTimestamp);
        }

        if (Number.isFinite(lastKnownTime)) return lastKnownTime;

        const internalTime = Number(
            game.settings.get(SmartphoneTime.ID, SmartphoneTime.SETTING_KEY)
        );
        return Number.isFinite(internalTime) ? internalTime : 0;
    }

    static now() {
        const source = SmartphoneTime.getTimeSource();
        switch (source) {
            case 'simple-calendar':
            case 'simple-calendar-reborn': {
                const simpleCalendarApi = SmartphoneTime.getSimpleCalendarApi(source);
                if (simpleCalendarApi) {
                    const timestamp = SmartphoneTime._rememberExternalTime(
                        source,
                        simpleCalendarApi.timestamp() * 1000
                    );
                    if (timestamp !== null) return timestamp;
                }
                return SmartphoneTime._getExternalTimeFallback(source, true, true);
            }
            case 'calendaria':
                return SmartphoneTime._getExternalTimeFallback(source);
            case 'seasons-and-stars':
            case 'simple-timekeeping':
                return SmartphoneTime._getExternalTimeFallback(source);
            case 'internal':
            default:
                return game.settings.get(SmartphoneTime.ID, SmartphoneTime.SETTING_KEY);
        }
    }

    static isTimeSourceAvailable(source = SmartphoneTime.getTimeSource()) {
        switch (source) {
            case 'simple-calendar':
            case 'simple-calendar-reborn':
                return Boolean(SmartphoneTime.getSimpleCalendarApi(source));
            case 'calendaria':
                return SmartphoneTime.isCalendariaActive && Boolean(globalThis.CALENDARIA?.api);
            case 'seasons-and-stars':
                return SmartphoneTime.isSeasonsAndStarsActive && Boolean(game.seasonsStars?.api);
            case 'simple-timekeeping':
                return SmartphoneTime.isSimpleTimekeepingActive && Boolean(game.time?.calendar);
            case 'internal':
            default:
                return true;
        }
    }

    static async set(timestamp) {
        if (typeof timestamp !== 'number') return;
        const source = SmartphoneTime.getTimeSource();

        switch (source) {
            case 'simple-calendar':
            case 'simple-calendar-reborn': {
                const simpleCalendarApi = SmartphoneTime.getSimpleCalendarApi(source);
                if (simpleCalendarApi) {
                    const dateObject = simpleCalendarApi.timestampToDate(timestamp / 1000);
                    simpleCalendarApi.setDate(dateObject);
                }
                break;
            }
            case 'calendaria':
                if (SmartphoneTime.isCalendariaActive && globalThis.CALENDARIA?.api) {
                    const calDateObj = CALENDARIA.api.timestampToDate(timestamp / 1000);
                    if (calDateObj) {
                        await CALENDARIA.api.setDateTime({
                            year: calDateObj.year,
                            month: calDateObj.month ?? calDateObj.ordinal,
                            day: calDateObj.day,
                            hour: calDateObj.hour,
                            minute: calDateObj.minute
                        });
                    }
                }
                break;
            case 'seasons-and-stars':
            case 'simple-timekeeping':
                if (SmartphoneTime.isSeasonsAndStarsActive || SmartphoneTime.isSimpleTimekeepingActive) {
                    await game.time.set(timestamp / 1000); 
                }
                break;
            case 'internal':
            default:
                await game.settings.set(SmartphoneTime.ID, SmartphoneTime.SETTING_KEY, timestamp);
                Hooks.callAll(SmartphoneTime.HOOK_NAME, timestamp);
                if (game.user.isGM) {
                    SmartphoneWidget.SOCKET?.executeForEveryone('updateStatusBarTime');
                }
                break;
        }
    }

    static async advance(duration) {
        const source = SmartphoneTime.getTimeSource();
        
        try {
            switch (source) {
                case 'simple-calendar':
                case 'simple-calendar-reborn': {
                    const simpleCalendarApi = SmartphoneTime.getSimpleCalendarApi(source);
                    if (simpleCalendarApi) {
                        const scDuration = {
                            year: duration.years || 0,
                            month: duration.months || 0,
                            day: duration.days || 0,
                            hour: duration.hours || 0,
                            minute: duration.minutes || 0,
                            seconds: duration.seconds || 0
                        };
                        simpleCalendarApi.changeDate(scDuration);
                    }
                    break;
                }
                
                case 'calendaria':
                    if (SmartphoneTime.isCalendariaActive && globalThis.CALENDARIA?.api) {
                        await CALENDARIA.api.advanceTime({
                            year: duration.years || 0,
                            month: duration.months || 0,
                            day: duration.days || 0,
                            hour: duration.hours || 0,
                            minute: duration.minutes || 0,
                            second: duration.seconds || 0
                        });
                    }
                    break;

                case 'seasons-and-stars':
                    if (SmartphoneTime.isSeasonsAndStarsActive && game.seasonsStars?.api) {
                        if (duration.years) await game.seasonsStars.api.advanceYears(duration.years);
                        if (duration.months) await game.seasonsStars.api.advanceMonths(duration.months);
                        if (duration.days) await game.seasonsStars.api.advanceDays(duration.days);
                        if (duration.hours) await game.seasonsStars.api.advanceHours(duration.hours);
                        if (duration.minutes) await game.seasonsStars.api.advanceMinutes(duration.minutes);
                        if (duration.seconds) await game.seasonsStars.api.advanceMinutes(duration.seconds / 60);
                    }
                    break;

                case 'simple-timekeeping':
                    if (SmartphoneTime.isSimpleTimekeepingActive) {
                        const calendarConfig = SmartphoneTime.getCalendarConfig();
                        const daysInYear = calendarConfig.months.reduce((acc, m) => acc + m.days, 0);
                        const avgDaysInMonth = daysInYear / calendarConfig.months.length;

                        const seconds = (duration.years || 0) * daysInYear * 86400 + 
                                      (duration.months || 0) * avgDaysInMonth * 86400 + 
                                      (duration.days || 0) * 86400 + 
                                      (duration.hours || 0) * 3600 + 
                                      (duration.minutes || 0) * 60 + 
                                      (duration.seconds || 0);
                        
                        await game.time.advance(seconds);
                    }
                    break;

                case 'internal':
                default:
                    const config = SmartphoneTime.getConfig();
                    let newTimestamp = SmartphoneTime.now();

                    if (duration.years || duration.months) {
                        let currentDateObj = SmartphoneTime.getDateObject(newTimestamp);
                        currentDateObj.year += duration.years || 0;
                        currentDateObj.month += duration.months || 0;
                        while (currentDateObj.month > config.months.length) {
                            currentDateObj.month -= config.months.length;
                            currentDateObj.year += 1;
                        }
                        while (currentDateObj.month < 1) {
                            currentDateObj.month += config.months.length;
                            currentDateObj.year -= 1;
                        }
                        newTimestamp = SmartphoneTime.fromObjectToTimestamp(currentDateObj);
                    }
                    
                    const MS_IN_SECOND = 1000;
                    const MS_IN_MINUTE = MS_IN_SECOND * (config.secondsInMinute || 60);
                    const MS_IN_HOUR = MS_IN_MINUTE * (config.minutesInHour || 60);
                    const MS_IN_DAY = MS_IN_HOUR * (config.hoursInDay || 24);
                    
                    const milliseconds = (duration.days || 0) * MS_IN_DAY +
                                         (duration.hours || 0) * MS_IN_HOUR +
                                         (duration.minutes || 0) * MS_IN_MINUTE +
                                         (duration.seconds || 0) * MS_IN_SECOND;
                    newTimestamp += milliseconds;

                    await SmartphoneTime.set(newTimestamp);
                    break;
            }
        } catch(e) {
            console.error(`[SmartphoneTime] Error during advance for source '${source}':`, e);
        }
    }
    
    static toDate(timestamp) {
        const dateInfo = SmartphoneTime.getDateObject(timestamp);
        return new Date(dateInfo.year, dateInfo.month - 1, dateInfo.day, dateInfo.hour, dateInfo.minute, dateInfo.second);
    }

    static fromObjectToDate(dateObj) {
        return new Date(dateObj.year, dateObj.month - 1, dateObj.day, dateObj.hour, dateObj.minute, dateObj.second);
    }    

    static fromObjectToTimestamp(dateObj) {
            const source = SmartphoneTime.getTimeSource();
            try {
                switch(source) {
                    case 'simple-calendar':
                    case 'simple-calendar-reborn': {
                        const simpleCalendarApi = SmartphoneTime.getSimpleCalendarApi(source);
                        if (simpleCalendarApi) {
                            const convertedDate = {
                                year: dateObj.year,
                                month: dateObj.month - 1,
                                day: dateObj.day - 1,
                                hour: dateObj.hour,
                                minute: dateObj.minute,
                                seconds: dateObj.second
                            };
                            return simpleCalendarApi.dateToTimestamp(convertedDate) * 1000;
                        }
                        break;
                    }
                    case 'simple-timekeeping':
                        if (SmartphoneTime.isSimpleTimekeepingActive && game.time.calendar) {
                            const calendar = game.time.calendar;
                            let dayOfYear = 0;
                            const isLeap = calendar.isLeapYear(dateObj.year);
                            
                            for (let i = 0; i < dateObj.month - 1; i++) {
                                const m = calendar.months.values[i];
                                dayOfYear += (isLeap && m.leapDays) ? m.leapDays : m.days;
                            }
                            dayOfYear += (dateObj.day - 1);
                            
                            const components = {
                                year: dateObj.year - 1, 
                                day: dayOfYear,         
                                hour: dateObj.hour,
                                minute: dateObj.minute,
                                second: dateObj.second
                            };
                            return game.time.calendar.componentsToTime(components) * 1000;
                        }
                        break;
                    case 'calendaria':
                        if (SmartphoneTime.isCalendariaActive && globalThis.CALENDARIA?.api) {
                            return CALENDARIA.api.dateToTimestamp({
                                year: dateObj.year,
                                month: dateObj.month,
                                day: dateObj.day,
                                hour: dateObj.hour,
                                minute: dateObj.minute,
                                second: dateObj.second
                            }) * 1000;
                        }
                        break;
                    case 'seasons-and-stars':
                        if (SmartphoneTime.isSeasonsAndStarsActive && game.seasonsStars?.api) {
                            const convertedDate = {
                                year: dateObj.year,
                                month: dateObj.month,
                                day: dateObj.day,
                                time: { hour: dateObj.hour, minute: dateObj.minute, second: dateObj.second }
                            };
                            return game.seasonsStars.api.dateToWorldTime(convertedDate) * 1000;
                        }
                        break;
                    case 'internal':
                    default:
                        const config = SmartphoneTime.getConfig();
                        const MS_IN_SECOND = 1000;
                        const MS_IN_MINUTE = MS_IN_SECOND * config.secondsInMinute;
                        const MS_IN_HOUR = MS_IN_MINUTE * config.minutesInHour;
                        const MS_IN_DAY = MS_IN_HOUR * config.hoursInDay;
                        let days = 0;
                        for (let y = 0; y < dateObj.year; y++) {
                            days += SmartphoneTime.getDaysInYear(y);
                        }
                        for (let m = 0; m < dateObj.month - 1; m++) {
                            days += SmartphoneTime.getDaysInMonth(dateObj.year, m + 1);
                        }
                        days += dateObj.day - 1;
                        const msInDay = (dateObj.hour * MS_IN_HOUR) + (dateObj.minute * MS_IN_MINUTE) + (dateObj.second * MS_IN_SECOND);
                        return (days * MS_IN_DAY) + msInDay;
                }
            } catch(e) {
                console.error(`[SmartphoneTime] Error in fromObjectToTimestamp for source '${source}':`, e);
            }
            return 0;
        }

    static format(timestamp, formatString) {
        const d = SmartphoneTime.getDateObject(timestamp);

        return formatString
            .replace('YYYY', String(d.year).padStart(4, '0'))
            .replace('MM', String(d.month).padStart(2, '0'))
            .replace('DD', String(d.day).padStart(2, '0'))
            .replace('HH', String(d.hour).padStart(2, '0'))
            .replace('mm', String(d.minute).padStart(2, '0'))
            .replace('ss', String(d.second).padStart(2, '0'));
    }

    static isLeapYear(year) {
        const rule = SmartphoneTime.getConfig().leapYearRule;
        if (rule.exception > 0 && year % rule.exception === 0) {
            return (rule.proleptic > 0 && year % rule.proleptic === 0);
        }
        return rule.frequency > 0 && year % rule.frequency === 0;
    }
    
    static getDaysInYear(year) {
        const config = SmartphoneTime.getConfig();
        const isLeap = SmartphoneTime.isLeapYear(year);
        return config.months.reduce((acc, month, index) => {
            let days = month.days;
            if (isLeap && month.isLeap) {
                days += month.leapOffset;
            }
            return acc + days;
        }, 0);
    }
    
    static getDaysInMonth(year, month) {
        const config = SmartphoneTime.getConfig();
        const monthData = config.months[month - 1];
        if (!monthData) return 30;
        let days = monthData.days;
        if (SmartphoneTime.isLeapYear(year) && monthData.isLeap) {
            days += monthData.leapOffset;
        }
        return days;
    }

    static getDateObject(timestamp) {
        const source = SmartphoneTime.getTimeSource();
        try {
            switch (source) {
                case 'simple-calendar':
                case 'simple-calendar-reborn': {
                    const simpleCalendarApi = SmartphoneTime.getSimpleCalendarApi(source);
                    if (simpleCalendarApi) {
                        const scDate = simpleCalendarApi.timestampToDate(timestamp / 1000);
                        if(scDate){
                            return {
                                year: scDate.year,
                                month: scDate.month + 1,
                                day: scDate.day + 1,
                                hour: scDate.hour,
                                minute: scDate.minute,
                                second: scDate.second ?? scDate.seconds ?? 0,
                                weekday: scDate.dayOfTheWeek 
                            };
                        }
                    }
                    break;
                }
                case 'simple-timekeeping':
                    if (SmartphoneTime.isSimpleTimekeepingActive && game.time.calendar) {
                        const components = game.time.calendar.timeToComponents(timestamp / 1000);
                        return {
                            year: components.year + 1,
                            month: components.month + 1,
                            day: components.dayOfMonth + 1,
                            hour: components.hour,
                            minute: components.minute,
                            second: components.second,
                            weekday: components.dayOfWeek
                        };
                    }
                    break;
                case 'calendaria':
                    if (SmartphoneTime.isCalendariaActive && globalThis.CALENDARIA?.api) {
                        const calDate = CALENDARIA.api.timestampToDate(timestamp / 1000);
                        if (calDate) {
                            const weekday = calDate.weekday ?? CALENDARIA.api.dayOfWeek?.({
                                year: calDate.year,
                                month: calDate.month ?? calDate.ordinal,
                                day: calDate.day
                            }) ?? 0;

                            return {
                                year: calDate.year,
                                month: calDate.month ?? calDate.ordinal,
                                day: calDate.day,
                                hour: calDate.hour ?? 0,
                                minute: calDate.minute ?? 0,
                                second: calDate.second ?? 0,
                                weekday
                            };
                        }
                    }
                    break;
                case 'seasons-and-stars':
                    if (SmartphoneTime.isSeasonsAndStarsActive && game.seasonsStars?.api) {
                        const snsDate = game.seasonsStars.api.worldTimeToDate(timestamp / 1000);
                        if (snsDate) {
                            return {
                                year: snsDate.year,
                                month: snsDate.month,
                                day: snsDate.day,
                                hour: snsDate.time?.hour ?? 0,
                                minute: snsDate.time?.minute ?? 0,
                                second: snsDate.time?.second ?? 0,
                                weekday: snsDate.weekday
                            };
                        }
                    }
                    break;
                case 'internal':
                default:
                    const config = SmartphoneTime.getConfig();
                    const MS_IN_SECOND = 1000;
                    const MS_IN_MINUTE = MS_IN_SECOND * (config.secondsInMinute || 60);
                    const MS_IN_HOUR = MS_IN_MINUTE * (config.minutesInHour || 60);
                    const MS_IN_DAY = MS_IN_HOUR * (config.hoursInDay || 24);
                    if (MS_IN_DAY <= 0) return SmartphoneTime.getDefaultConfig();
                    let days = Math.floor(timestamp / MS_IN_DAY);
                    let msRemaining = timestamp % MS_IN_DAY;
                    let year = 0;
                    while (days >= SmartphoneTime.getDaysInYear(year)) {
                        days -= SmartphoneTime.getDaysInYear(year);
                        year++;
                    }
                    let month = 1;
                    while (days >= SmartphoneTime.getDaysInMonth(year, month)) {
                        days -= SmartphoneTime.getDaysInMonth(year, month);
                        month++;
                    }
                    let day = days + 1;
                    let hour = Math.floor(msRemaining / MS_IN_HOUR);
                    msRemaining %= MS_IN_HOUR;
                    let minute = Math.floor(msRemaining / MS_IN_MINUTE);
                    msRemaining %= MS_IN_MINUTE;
                    let second = Math.floor(msRemaining / MS_IN_SECOND);
                    
                    const tempDate = SmartphoneTime.fromObjectToDate({ year, month, day, hour, minute, second });

                    return { year, month, day, hour, minute, second, weekday: tempDate.getDay() };
            }
        } catch (e) {
            console.error(`[SmartphoneTime] Error in getDateObject for source '${source}':`, e);
        }
        return { year: 1, month: 1, day: 1, hour: 0, minute: 0, second: 0, weekday: 0 };
    }
    
    static fromObject(dateObj) {
        return new Date(dateObj.year, dateObj.month - 1, dateObj.day, dateObj.hour, dateObj.minute, dateObj.second);
    }

    static async setTimeToShortcut(shortcutKey) {
        const config = SmartphoneTime.getConfig();
        const timeString = config.timeShortcuts?.[shortcutKey];
        if (!timeString) {
            console.warn(`[SmartphoneTime] Unknown shortcut key: ${shortcutKey}`);
            return;
        }

        const [hour, minute] = timeString.split(':').map(Number);
        const currentDateObj = SmartphoneTime.getDateObject(SmartphoneTime.now());
        
        currentDateObj.hour = hour;
        currentDateObj.minute = minute;
        currentDateObj.second = 0;
        
        const newTimestamp = SmartphoneTime.fromObjectToTimestamp(currentDateObj);
        await SmartphoneTime.set(newTimestamp);
    }    
}
