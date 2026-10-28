import { SmartphoneWidget } from "./core/SmartphoneWidget.js";
import { exposeModuleAPI } from "./core/SmartphoneAPI.js";
import { registerHandlebarsHelpers } from "./core/HandlebarsHelpers.js";
import {
  registerInitHooks,
  registerReadyHooks,
  registerRuntimeHooks,
} from "./core/SmartphoneHooks.js";
import { onInit, onReady } from "./core/SmartphoneInitializer.js";
import { BatteryChargingBehavior } from "./core/BatteryChargingBehavior.js";
import { SignalBlockBehavior } from "./core/SignalBlockBehavior.js";

export { SmartphoneWidget };

Hooks.once("init", () => {
  console.log("Smartphone Widget | Init Hook Fired");

  exposeModuleAPI();
  registerHandlebarsHelpers();
  registerInitHooks();
  registerRuntimeHooks();

  if (BatteryChargingBehavior) {
    BatteryChargingBehavior.register();
  }
  if (SignalBlockBehavior) {
    SignalBlockBehavior.register();
  }

  onInit();
});

Hooks.once("ready", async () => {
  console.log("Smartphone Widget | Ready Hook Fired");

  warnIfLibInactive();

  // Hooks that require the world + DOM to exist
  registerReadyHooks();

  // Keep a single deterministic ready pipeline
  await onReady();
});

function warnIfLibInactive() {
  const lib = game.modules.get("glitchsmith-lib");
  if (lib?.active && lib.api?.currency) return;
  ui.notifications?.error(game.i18n.localize("SMARTPHONE.errors.libRequired"), { permanent: true });
  console.error("Smartphone Widget | glitchsmith-lib is required but not active or its API is missing.");
}
