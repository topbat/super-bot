import type { DesktopApi } from "../electron/preload";

declare global {
  interface Window {
    superbot?: DesktopApi;
  }
}

export {};
