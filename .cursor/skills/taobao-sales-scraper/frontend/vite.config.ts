import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const mediaRoot = path.resolve(__dirname, "../data/product_media");

/** 开发时把 Skill 包内 product_media 挂到 /product_media（后端未启时兜底） */
function serveProductMedia(): Plugin {
  return {
    name: "serve-product-media",
    configureServer(server) {
      server.middlewares.use("/product_media", (req, res, next) => {
        try {
          const rel = decodeURIComponent((req.url || "/").split("?")[0] || "/");
          const file = path.normalize(path.join(mediaRoot, rel.replace(/^\/+/, "")));
          if (!file.startsWith(mediaRoot)) {
            res.statusCode = 403;
            res.end("Forbidden");
            return;
          }
          if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
            next();
            return;
          }
          const ext = path.extname(file).toLowerCase();
          const type =
            ext === ".png"
              ? "image/png"
              : ext === ".webp"
                ? "image/webp"
                : "image/jpeg";
          res.setHeader("Content-Type", type);
          fs.createReadStream(file).pipe(res);
        } catch {
          next();
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), serveProductMedia()],
  server: {
    host: "127.0.0.1",
    port: 5174,
    open: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8787",
        changeOrigin: true,
        timeout: 0,
        proxyTimeout: 0,
      },
    },
  },
});
