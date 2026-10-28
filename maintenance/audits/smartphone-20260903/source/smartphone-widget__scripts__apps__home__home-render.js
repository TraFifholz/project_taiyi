/**
 * Rendering methods for HomeApp
 */

import { SmartphoneWidget } from "../../smartphone-widget.js";

/**
 * Create render-related methods
 * @param {HomeApp} HomeApp - The HomeApp class
 * @returns {Object} Methods to assign to prototype
 */
export const createRenderMethods = (HomeApp) => ({
  /**
   * Main render function
   */
  async render() {
    await this.loadLayout();
    const allPossibleApps = this.getAllAppDefinitions();

    const pagesHtml = await Promise.all(this.pages.map(async (pageApps, pageIndex) => {
      const slotsHtmlPromises = pageApps.map(async (appId, slotIndex) => {
        if (appId === '__occupied__') {
          return `<div class="app-slot occupied" style="display: none;" data-page="${pageIndex}" data-slot="${slotIndex}"></div>`;
        }
        if (!appId) {
          return `<div class="app-slot empty" data-page="${pageIndex}" data-slot="${slotIndex}"></div>`;
        }
        if (appId.startsWith('widget-')) {
          const widgetDef = this.widgets[appId];
          if (widgetDef) {
            const content = await widgetDef.class.render(this, widgetDef.variant);
            const { w, h } = widgetDef.size;
            return `
                <div class="app-slot widget-container" 
                        draggable="true"
                        style="grid-column: span ${w}; grid-row: span ${h};" 
                        data-page="${pageIndex}" 
                        data-slot="${slotIndex}"
                        data-widget="${appId}">
                    <div class="widget-content-wrapper">
                        ${content}
                    </div>
                </div>
            `;
          }
          return `<div class="app-slot empty" data-page="${pageIndex}" data-slot="${slotIndex}"></div>`;
        }
        
        const app = allPossibleApps.find(a => a.id === appId);
        if (!app) return `<div class="app-slot empty" data-page="${pageIndex}" data-slot="${slotIndex}"></div>`;

        const isImagePath = app.icon.includes('/') || app.icon.includes('.');
        const isGradient = app.color && app.color.includes("gradient");

        const iconColor = isGradient ? "#ffffff" : app.color;
        
        let bgStyle = "";
        if (!app.isTransparent) {
            bgStyle = isGradient ? `background: ${app.color};` : `background: ${app.color}20;`;
        }

        const iconHtml = isImagePath 
            ? `<img src="${app.icon}">` 
            : `<i class="${app.icon}" style="color: ${iconColor}"></i>`;
            
        const wrapperClass = app.isTransparent ? 'app-icon-wrapper no-bubble' : 'app-icon-wrapper';

        return `
            <div class="app-slot" data-page="${pageIndex}" data-slot="${slotIndex}">
                <div class="app-icon" data-app="${app.id}" draggable="true">
                    <div class="${wrapperClass}" style="${bgStyle}">
                        ${iconHtml}
                    </div>
                    <span class="app-name">${app.name}</span>
                </div>
            </div>
        `;
      });
      const slotsHtml = (await Promise.all(slotsHtmlPromises)).join("");
      return `<div class="home-page" style="width: ${100 / this.pages.length}%"><div class="app-grid">${slotsHtml}</div></div>`;
    }));

    const content = `
        <div class="home-screen-wrapper">
            <div class="home-screen">
                <div class="edge-glow left"></div><div class="edge-glow right"></div>
                <div class="home-pages-container" style="--current-page: ${this.currentPage}; --page-count: ${this.pages.length}; width: ${this.pages.length * 100}%;">
                    ${pagesHtml.join("")}
                </div>
            </div>
            <div class="home-pagination">
                ${this.pages.map((_, index) => `<span class="dot ${index === this.currentPage ? 'active' : ''}" data-page="${index}"></span>`).join("")}
            </div>
        </div>
    `;

    const styles = `
           <style>
                .smartphone-frame .home-screen { 
                    padding: 10px 8px; 
                    height: 100%; 
                    overflow-y: hidden;
                    overflow-x: hidden;                       
                    scrollbar-width: none; 
                }
                .smartphone-frame .home-screen::-webkit-scrollbar { 
                    display: none; 
                }

                .smartphone-frame .app-grid { 
                    display: grid; 
                    grid-template-columns: repeat(4, minmax(0, 1fr)); 
                    grid-template-rows: repeat(6, minmax(0, 1fr));    
                    gap: 10px 4px;
                    padding: 0;
                    width: 100%;
                    height: 100%; 
                }

                .smartphone-frame .app-slot {
                    width: 100%;
                    height: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: start; 
                    position: relative;
                    min-height: 60px; 
                    overflow: visible; 
                }
                
                .smartphone-frame .app-slot.drag-over {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 10px;
                }

                .smartphone-frame .app-icon { 
                    display: flex; 
                    flex-direction: column; 
                    align-items: center; 
                    gap: 4px; 
                    cursor: pointer; 
                    transition: transform 0.2s; 
                    padding: 4px; 
                    border-radius: 8px; 
                    width: 100%;
                    box-sizing: border-box;
                    overflow: visible; 
                }

                .smartphone-frame .app-icon:hover { 
                    transform: scale(1.05); 
                    background-color: rgba(255, 255, 255, 0.1); 
                }
                
                .smartphone-frame .app-icon:active { 
                    transform: scale(0.95); 
                }

                .smartphone-frame .app-icon-wrapper { 
                    width: 42px; 
                    height: 42px; 
                    border-radius: 10px; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    flex-shrink: 0; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2); 
                    position: relative;
                    transition: all 0.2s;
                    text-shadow: 1px 1px 1px black;
                }

                .smartphone-frame .app-icon-wrapper i { 
                    font-size: 20px; 
                    transition: color 0.2s; 
                }
                
                .smartphone-frame .app-icon-wrapper img {
                    width: 26px; 
                    height: 26px;
                    object-fit: contain;
                    pointer-events: none;
                }

                .smartphone-frame .app-icon-wrapper.no-bubble img {
                    width: 100%;
                    height: 100%;
                }                

                .smartphone-frame .app-icon-wrapper.no-bubble {
                    background: transparent !important; 
                    box-shadow: none; 
                    border-radius: 0; 
                }                

                .smartphone-frame .app-name { 
                    font-size: 10px; 
                    color: white !important; 
                    text-align: center; 
                    text-shadow: 0 1px 2px rgba(0,0,0,0.8); 
                    width: 100%; 
                    display: block;
                    white-space: nowrap;       
                    overflow: hidden;          
                    text-overflow: ellipsis;   
                    padding: 0 1px;
                    box-sizing: border-box; 
                    line-height: 1.2;
                    letter-spacing: -0.3px; 
                }

                @keyframes app-launch { 
                    0% { 
                        transform: scale(1); 
                        opacity: 1; 
                    } 
                    100% { 
                        transform: scale(1.15); 
                        opacity: 0; 
                    } 
                }
                
                .smartphone-frame .app-launch { 
                    animation: app-launch 0.2s ease-out forwards; 
                    z-index: 10; 
                    pointer-events: none;
                }
           </style>
       `;

    this.updateContent(styles + content);

    // Update badges and setup hooks
    SmartphoneWidget.updateBadge();
    this.setupActorHooks(); 
  },

  /**
   * Update pagination dots only
   */
  updatePaginationDots() {
    const dots = this.element.querySelectorAll('.home-pagination .dot');
    dots.forEach((dot, index) => {
      dot.classList.toggle('active', index === this.currentPage);
    });
  },

  /**
   * Update time-sensitive widgets only
   */
  async updateTimeWidgets() {
    if (!this.element) return;

    const timeSensitiveWidgets = [
        'widget-clock', 'widget-clock-wide', 
        'widget-weather', 'widget-weather-wide',
        'widget-bio-monitor', 'widget-bio-monitor-wide',
        'widget-photo-frame', 'widget-photo-frame-wide' 
    ];

    const widgetSlots = this.element.querySelectorAll('.app-slot.widget-container');
    
    for (const slot of widgetSlots) {
        const widgetId = slot.dataset.widget;
        if (timeSensitiveWidgets.includes(widgetId)) {
            const widgetDef = this.widgets[widgetId];
            if (widgetDef) {
                const content = await widgetDef.class.render(this, widgetDef.variant);
                const wrapper = slot.querySelector('.widget-content-wrapper');
                if (wrapper) wrapper.innerHTML = content;
            }
        }
    }

    this._attachWidgetListeners();
  }
});
