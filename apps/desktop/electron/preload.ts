import { contextBridge } from "electron";

const desktopApi = Object.freeze({
  platform: process.platform,
  apiBaseUrl: "http://127.0.0.1:8420/api/v1",
  version: process.env.npm_package_version ?? "0.1.0",
});

contextBridge.exposeInMainWorld("superbot", desktopApi);

export type DesktopApi = typeof desktopApi;
