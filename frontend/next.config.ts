import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Build Docker enxuto: .next/standalone com server.js próprio
  // (node_modules completo fica fora da imagem final).
  output: "standalone",
  turbopack: {
    // O package-lock.json da raiz do repo (CLI do shadcn) faz o Next inferir a
    // raiz errada e aninhar o standalone em standalone/frontend/. O app é este
    // diretório, não um workspace.
    root: __dirname,
  },
};

export default nextConfig;
