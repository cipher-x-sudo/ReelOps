import { bundle } from "@remotion/bundler"
import { renderMedia, selectComposition } from "@remotion/renderer"
import fs from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"

type Args = {
  manifest: string
  out: string
}

function parseArgs(): Args {
  const args = process.argv.slice(2)
  const get = (name: string) => {
    const index = args.indexOf(name)
    return index >= 0 ? args[index + 1] : ""
  }
  const manifest = get("--manifest")
  const out = get("--out")
  if (!manifest || !out) {
    throw new Error("Usage: npm run render -- --manifest <manifest.json> --out <reel.mp4>")
  }
  return { manifest, out }
}

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const args = parseArgs()
const manifest = JSON.parse(await fs.readFile(args.manifest, "utf-8"))
const entryPoint = path.join(__dirname, "Root.tsx")
const serveUrl = await bundle({ entryPoint })
const composition = await selectComposition({
  serveUrl,
  id: "ReelOpsReel",
  inputProps: { manifest }
})

await renderMedia({
  composition,
  serveUrl,
  codec: "h264",
  outputLocation: args.out,
  inputProps: { manifest },
  chromiumOptions: {
    ignoreCertificateErrors: true
  }
})

console.log(`Rendered ${args.out}`)

