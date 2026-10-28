const appId = "smartphone-browser-app";

import { BaseApp } from '../../../smartphone-widget/scripts/apps/BaseApp.js';
import { SmartphoneWidget } from '../../../smartphone-widget/scripts/smartphone-widget.js';
import { SignalManager } from '../../../smartphone-widget/scripts/core/SignalManager.js';

export class BrowserApp extends BaseApp {
    static socket = null;

    constructor(widget) {
        super(widget);
        this.address = null;
        this.lastAddress= null;
    }

    static initialize(socket) { this.socket = socket; }

    async render() {
        if (!SignalManager.hasSignal() && 
            !SignalManager.isWeakSignal() && 
            game.settings.get(appId, "useSignalSystem")) {
                this.noSignal();
            return;
        }

        const journal = game.journal.getName(game.settings.get(appId, "journalName"));
        if (journal) {
            let page;
            if (this.address === null) {
                page = journal.pages.contents[0];
                this.address = journal.pages.contents[0].name;
            } else page = journal.pages.getName(this.address);
            
            if (page) this.fetchWebpage(page)
            else this.notFound();
        }
        return;
    }

    renderAppHeader() {
        return `<div class="app-header" style="border-bottom: 1px solid var(--ba-bg-color)!important;">
            <button id="browser-app-home"><i class="fas fa-home"></i></button>
            <button id="browser-app-back"><i class="fas fa-backward-step"></i></button>
            <input type="text" id="browser-app-address" value="${this.address}" />
            <button id="browser-app-go"><i class="fas fa-right-long"></i></button>
            <button id="browser-app-refresh"><i class="fas fa-arrows-rotate"></i></button>
        </div>`;
        return;
    }

    async fetchWebpage(page) {
        const theme = game.settings.get(appId, 'theme');
        const body = (page.type === "text" ? page.text.content:`<div class="centered"><img src="${page.src}" width="100%"/></div>`)
            .replace(`<div id="browser-app-search"></div>`,`<input type="text" id="browser-app-search" placeholder="${game.i18n.localize("BROWSERAPP.ui.placeholder.search")}" />`).trim();
        const content = `
            <div class="browser-app" data-theme="${theme}">
                ${this.renderAppHeader()}
                <div class="app-content" id="browser-page">
                    ${body}
                </div>
            </div>
        `;
        this.updateContent(content);
        return;
    }

    async notFound() {
        const theme = game.settings.get(appId, 'theme');
        const content = `
            <div class="browser-app" data-theme="${theme}">
                ${this.renderAppHeader()}
                <div class="app-content">
                    <h3 style="text-align: center">${game.i18n.localize("BROWSERAPP.ui.error.404.header")}</h3>
                    <p>${game.i18n.format("BROWSERAPP.ui.error.404.text", { address: this.address})}</p>
                </div>
            </div>
        `;
        this.updateContent(content);
        return;
    }

    async noSignal() {
        const theme = game.settings.get(appId, 'theme');
        const content = `
            <div class="browser-app" data-theme="${theme}">
                ${this.renderAppHeader()}
                <div class="app-content">
                    <h3 style="text-align: center">${game.i18n.localize("BROWSERAPP.ui.error.signal.header")}</h3>
                    <p>${game.i18n.localize("BROWSERAPP.ui.error.signal.text")}</p>
                </div>
            </div>
        `;
        this.updateContent(content);
        return;
    }

    navigateTo(address) {
        this.lastAddress = this.address;
        this.address = address;
        this.render();
        return;
    }

    setupListeners() {
        super.removeAllListeners();
        if (!this.element) return;

        const homeButton = this.element.querySelector("#browser-app-home");
        if (homeButton) {
            this.addListener(homeButton, "click", (event) => {
                this.navigateTo(null);
            });
        }
        const refreshButton = this.element.querySelector("#browser-app-refresh");
        if (refreshButton) {
            this.addListener(refreshButton, "click", (event) => {
                this.navigateTo(this.address);
            });
        }
        const backButton = this.element.querySelector("#browser-app-back");
        if (backButton) {
            this.addListener(backButton, "click", (event) => {
                this.navigateTo(this.lastAddress);
            });
        }
        const inputBar = this.element.querySelector("#browser-app-address");
        const goButton = this.element.querySelector("#browser-app-go");
        if (goButton && inputBar) {
            this.addListener(goButton, "click", (event) => {
                this.navigateTo(inputBar.value);
            });
        }

        if (inputBar) {
            this.addListener(inputBar, "keydown", (event) => {
                if (event.keyCode == 13) {
                    goButton.click();
                }
            })
        }

        const searchEngine = this.element.querySelector("#browser-app-search");
        if (searchEngine) {
            this.addListener(searchEngine, "keydown", (event) => {
                const searchFor = searchEngine.value;
                const regex = new RegExp(searchFor, "gi");
                const results = [];

                this.element.querySelector("#browser-app-search-results").innerHTML = "";

                const journal = game.journal.getName(game.settings.get(appId, "journalName"));
                if (journal) {
                    journal.pages.forEach(page => {
                        if ((page.text && regex.test(new DOMParser().parseFromString(page.text.content, 'text/html').body.textContent)) || 
                            (page.text && regex.test(page.name))) {
                                if (!String(page.text.content).includes("browser-app-no-index")) results.push(page);
                        }
                    });
                }

                if (results.length > 0) {
                    results.forEach(result => {
                        const description = new DOMParser().parseFromString(result.text.content, 'text/html').getElementById("browser-app-description")?.textContent || game.i18n.localize("BROWSERAPP.ui.error.results.description");
                        this.element.querySelector("#browser-app-search-results").insertAdjacentHTML("beforeend", `<div class="card"><span class="link" data-target="${result.name}">${result.name}</span><br /><small>${description}</small></div>`)
                    });
                } else this.element.querySelector("#browser-app-search-results").innerHTML = game.i18n.localize("BROWSERAPP.ui.error.results.none");
            });
        }

        const links = this.element.querySelectorAll(".link");
        if (links) {
            this.addListener(this.element.querySelector("#browser-page"), "click", (event) => {
                event.preventDefault();
                event.stopPropagation();
                if (event.target.matches(".link")) {
                    const address = event.target.getAttribute("data-target");
                    if (address) {
                        this.navigateTo(address);
                    }
                }

                if (event.target.tagName.toLowerCase() === 'a') {
                    if (event.target.href) {
                        this.navigateTo(String(event.target.href).replace(/https?:/, '').replace(/\/+$/, '').trim());
                    }
                }
            }, { passive: false });
        }
    }
}