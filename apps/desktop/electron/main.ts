import { join, relative, resolve } from "node:path";
import { pathToFileURL } from "node:url";

import { app, BrowserWindow, net, protocol, shell } from "electron";

const isDevelopment = !app.isPackaged;

protocol.registerSchemesAsPrivileged([
  {
    scheme: "superbot",
    privileges: { standard: true, secure: true, supportFetchAPI: true },
  },
]);

function registerRendererProtocol(): void {
  const rendererRoot = resolve(__dirname, "../renderer");
  protocol.handle("superbot", (request) => {
    const pathname = decodeURIComponent(new URL(request.url).pathname);
    const target = resolve(rendererRoot, pathname === "/" ? "index.html" : pathname.slice(1));
    const relativeTarget = relative(rendererRoot, target);
    if (relativeTarget.startsWith("..") || relativeTarget.includes(":")) {
      return new Response("Not found", { status: 404 });
    }
    return net.fetch(pathToFileURL(target).toString());
  });
}

function createWindow(): void {
  const window = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1040,
    minHeight: 680,
    show: false,
    title: "Super Bot",
    backgroundColor: "#f5f5f5",
    webPreferences: {
      preload: join(__dirname, "../preload/index.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  window.once("ready-to-show", () => window.show());
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith("https://")) void shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDevelopment && process.env.ELECTRON_RENDERER_URL) {
    void window.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    void window.loadURL("superbot://app/");
  }
}

app.whenReady().then(() => {
  registerRendererProtocol();
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
