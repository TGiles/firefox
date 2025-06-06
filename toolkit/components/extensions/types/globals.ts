// Exports for all modules redirected here by a catch-all rule in tsconfig.json.
export var AddonManager,
  AddonManagerPrivate,
  AddonSettings,
  AddonWrapper,
  AsyncShutdown,
  ExtensionMenus,
  ExtensionProcessScript,
  ExtensionScriptingStore,
  ExtensionUserScripts,
  NetUtil,
  E10SUtils,
  LightweightThemeManager,
  ServiceWorkerCleanUp,
  GeckoViewConnection,
  GeckoViewWebExtension,
  IndexedDB,
  JSONFile,
  Log,
  UrlbarUtils,
  WebExtensionDescriptorActor;

/**
 * A stub type for the "class" from EventEmitter.sys.mjs.
 * TODO: Convert EventEmitter.sys.mjs into a proper class.
 */
export declare class EventEmitter {
  emit(event: string, ...args: any[]): void;
  on(event: string, listener: callback): void;
  once(event: string, listener: callback): Promise<any>;
  off(event: string, listener: callback): void;
}
