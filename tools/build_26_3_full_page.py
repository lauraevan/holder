#!/usr/bin/env python3
"""Build preview/26.3-full from the single-file webmc 26.3 build.

The upstream page embeds every payload as base64 <script> blocks (~90 MB of
HTML). Split them into sibling files that the page fetches, keep the rest of
the proven loader unchanged, use the all-languages assets EPK, and translate
the loader's Chinese UI strings.

usage: build_26_3_full_page.py <webmc/assets/26.3.html> <out_dir> <site base path> <assets.epk site path>

Vercel rewrites / to this page, so payload URLs are absolute site paths.
"""
import base64, hashlib, json, re, subprocess, sys
from pathlib import Path

PAYLOAD_FILES = {
    "eag-inline-decoder": "decoder.wasm",
    "eag-inline-wasm-br": "classes.wasm.bin",
    "eag-inline-mesh-wasm-br": "mesh-worker.wasm.bin",
    "eag-inline-server-wasm-br": "server-worker.wasm.bin",
    "eag-inline-sounds": "sounds.epk",
}
ASSETS_ID = "eag-inline-assets"

TRANSLATIONS = {
    "之前的渲染器没有干净地完成页面导航就停止了。": "The previous renderer stopped without finishing page navigation cleanly.",
    " 它的最后心跳和遥测数据被找回了。": " Its last heartbeat and telemetry were recovered.",
    "上一个游戏停止响应或其渲染器已被终止。其最后一次卡顿和内存统计信息已恢复。":
        "The previous game stopped responding or its renderer was terminated. Its last stall and memory statistics were recovered.",
    "上一次游戏会话意外结束。它的崩溃和内存信息已被恢复。":
        "The previous game session ended unexpectedly. Its crash and memory information was recovered.",
    "下载崩溃报告": "Download crash report",
    "关闭": "Close",
    "正在下载资源... ": "Downloading resources... ",
    "正在加载 Eaglercraft 26.3 运行时...": "Loading Eaglercraft 26.3 runtime...",
    "旋转你的设备": "Rotate your device",
    "Eaglercraft 在移动设备需要横屏模式": "Eaglercraft requires landscape mode on mobile devices.",
}

# Joey-JM's credit moves from the title screen to the Credits page: the version
# label reads "Minecraft 26.3" and moves down to the bottom line, where the
# title's "Made by Joey-JM" line (now cleared) used to be. The Credits page keeps "26.3-JM Credits" and "Made by Joey-JM |
# Based on Eaglercraft 26.2", which are separate strings.
BRANDING_EDITS = {
    "26.3-JM": "Minecraft 26.3",
    "Made by Joey-JM": "",
}

# Replaces the base64 <script> decoder: same contract (Promise<Uint8Array>, one
# in-flight request per id), but streams the payload from a sibling file.
FETCH_DECODER = r"""  function decodePayload(id) {
    if (inflight.has(id)) return inflight.get(id);
    const entry = PAYLOADS[id];
    if (!entry) return Promise.reject(new Error('Missing payload: ' + id));
    window.__eaglerInlinePayloadCacheBytes += entry.size;
    const pending = originalFetch(entry.url).then(async function (response) {
      if (!response.ok) throw new Error('Failed to load ' + entry.url + ': ' + response.status);
      const out = new Uint8Array(entry.size);
      let offset = 0;
      const reader = response.body.getReader();
      for (;;) {
        const chunk = await reader.read();
        if (chunk.done) break;
        if (offset + chunk.value.length > entry.size) throw new Error('Payload too large: ' + id);
        out.set(chunk.value, offset);
        offset += chunk.value.length;
        stats.chunks++;
        if (window.__eaglerAssetDownloadProgress) window.__eaglerAssetDownloadProgress(entry.url, offset);
      }
      if (offset !== entry.size) throw new Error('Payload size mismatch: ' + id);
      return out;
    }).finally(function () {
      inflight.delete(id);
      window.__eaglerInlinePayloadCacheBytes -= entry.size;
    });
    inflight.set(id, pending);
    return pending;
  }
"""

def main():
    src, out_dir, base, assets_url = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    html = Path(src).read_text(encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)

    block = re.compile(r'<script type="application/octet-stream" id="([^"]+)" data-size="(\d+)">(.*?)</script>\n?', re.S)
    payloads = {}
    for m in block.finditer(html):
        pid, size = m.group(1), int(m.group(2))
        data = base64.b64decode("".join(m.group(3).split()))
        assert len(data) == size, (pid, len(data), size)
        if pid == ASSETS_ID:
            continue
        name = PAYLOAD_FILES[pid]
        (out_dir / name).write_bytes(data)
        if pid == "eag-inline-wasm-br":
            patcher = Path(__file__).with_name("patch_26_3_branding.js")
            subprocess.run(["node", str(patcher), str(out_dir / name), str(out_dir / name)]
                           + ["%s=%s" % kv for kv in BRANDING_EDITS.items()]
                           + ["--lower-label=26.3-JM"], check=True)
            data = (out_dir / name).read_bytes()
            size = len(data)
        payloads[pid] = {"url": base + name, "size": size}
        print("%-28s %-24s %10d %s" % (pid, name, size, hashlib.sha256(data).hexdigest()[:12]))
    html = block.sub("", html)

    assets = Path(".") / assets_url.lstrip("/")
    payloads[ASSETS_ID] = {"url": assets_url, "size": assets.stat().st_size}

    start = html.index("  function decodePayload(id) {")
    end = html.index("\n  let decoderBytesPromise;")
    html = (html[:start] + "  const PAYLOADS = " + json.dumps(payloads) + ";\n" + FETCH_DECODER + html[end:])

    total = sum(p["size"] for p in payloads.values())
    html, n = re.subn(r'var total = Number\("\d+"\)', 'var total = Number("%d")' % total, html)
    assert n == 1
    for zh, en in TRANSLATIONS.items():
        assert zh in html, zh
        html = html.replace(zh, en)
    assert not re.search(r"[一-鿿]", html), "untranslated UI text left"
    html = html.replace("<title>Eaglercraft 26.3 Fixed</title>", "<title>Minecraft 26.3</title>")


    # iPadOS Safari reports a Macintosh UA, so also treat multi-touch Macs as mobile.
    # Mobile fast-start keeps all required resource packs present so Java boot
    # cannot stall during resource initialization. Mobile still skips the eager
    # mesh-worker compile; the integrated-server Wasm remains lazy as before.
    opts_old = '''\t\twindow.eaglercraftXOpts = {
\t\t\tcontainer: "game_frame",
\t\t\tassetsURI: [
\t\t\t\t{ url: "assets.epk?v=49cbfb0a01b2374b", path: "" },
\t\t\t\t{ url: "sounds.epk?v=49cbfb0a01b2374b", path: "" }
\t\t\t],
'''
    opts_new = '''\t\tvar mobileFastStart = /[?&]mobilefast=1(?:&|$)/.test(window.location.search)
\t\t\t|| (!/[?&]fullboot=1(?:&|$)/.test(window.location.search)
\t\t\t\t&& (/(Android|iPhone|iPad|iPod|Mobile)/i.test(navigator.userAgent)
\t\t\t\t\t|| (/Macintosh/.test(navigator.userAgent) && navigator.maxTouchPoints > 1)
\t\t\t\t\t|| (window.matchMedia && window.matchMedia("(pointer:coarse)").matches)));
\t\twindow.__eaglerMobileFastStart = mobileFastStart;
\t\tvar startupAssets = [
\t\t\t{ url: "assets.epk?v=49cbfb0a01b2374b", path: "" },
\t\t\t{ url: "sounds.epk?v=49cbfb0a01b2374b", path: "" }
\t\t];
\t\twindow.eaglercraftXOpts = {
\t\t\tcontainer: "game_frame",
\t\t\tassetsURI: startupAssets,
'''
    if opts_old not in html:
        raise RuntimeError("mobile opts insertion point missing")
    html = html.replace(opts_old, opts_new, 1)
    html = html.replace(
        '''\t\t\t\tmeshWorkers: window.location.search.indexOf("singlethread") < 0
\t\t\t\t\t&& window.location.search.indexOf("nomesh") < 0,''',
        '''\t\t\t\tmeshWorkers: !mobileFastStart
\t\t\t\t\t&& window.location.search.indexOf("singlethread") < 0
\t\t\t\t\t&& window.location.search.indexOf("nomesh") < 0,''',
        1
    )

    # Mobile streams the client image through the native route below, so its
    # download counter only covers the resource packs.
    mobile_initial = payloads[ASSETS_ID]["size"] + payloads["eag-inline-sounds"]["size"]
    desktop_initial = (mobile_initial + payloads["eag-inline-decoder"]["size"]
                       + payloads["eag-inline-wasm-br"]["size"]
                       + payloads["eag-inline-mesh-wasm-br"]["size"])
    html = re.sub(
        r'var total = Number\("\d+"\) \|\| 0;',
        'var total = Number(window.__eaglerMobileFastStart ? "%d" : "%d") || 0;' % (mobile_initial, desktop_initial),
        html,
        count=1
    )

    # iPad Safari stalled right after the client download ("18 MB") while the
    # page-side Wasm Brotli decoder unpacked the 102 MB image. vercel.json serves
    # the same .wasm.bin files under native/ with Content-Encoding: br, so on
    # mobile the browser decodes natively and compiles while streaming. If that
    # route fails, fall back to unpacking in the page, releasing the decoder as
    # soon as it finishes and compiling straight from the bytes.
    def swap(old, new):
        nonlocal html
        if html.count(old) != 1:
            raise RuntimeError("mobile compile anchor missing: " + old[:60])
        html = html.replace(old, new, 1)

    swap("          if (!jobs.size) idleTimer = setTimeout(stopDecoder, 250);",
         "          if (!jobs.size) {\n"
         "            if (window.__eaglerMobileFastStart) stopDecoder();\n"
         "            else idleTimer = setTimeout(stopDecoder, 250);\n"
         "          }")
    swap("  window.__eagReleaseInlineWasm = function (name) {",
         "  window.__eagNativeFetch = originalFetch;\n"
         "  // Hand the decompressed image to the compiler without a Response copy.\n"
         "  window.__eagTakeWasmBytes = function (name) {\n"
         "    const bytes = wasmCache.get(name) || decodePayload(wasmIds[name]).then(decompress);\n"
         "    wasmCache.delete(name);\n"
         "    return bytes;\n"
         "  };\n"
         "  window.__eagReleaseInlineWasm = function (name) {")
    swap("                    async function compileImage(name) {\n",
         "                    async function compileImage(name) {\n"
         "                      if (window.__eaglerMobileFastStart) {\n"
         "                        const began = Date.now();\n"
         "                        const tick = setInterval(function () {\n"
         "                          window.__eaglerBoot(62, 'Loading game... (' + Math.round((Date.now() - began) / 1000) + 's)');\n"
         "                        }, 1000);\n"
         "                        window.__eaglerBoot(62, 'Loading game...');\n"
         "                        try {\n"
         "                          try {\n"
         "                            return await WebAssembly.compileStreaming(\n"
         "                              window.__eagNativeFetch(" + json.dumps(base + "native/") + " + name), {builtins:['js-string']});\n"
         "                          } catch (nativeError) {\n"
         "                            window.__log.push('W:[mobile] native streaming compile failed (' + nativeError + '); unpacking in page');\n"
         "                            let bytes = await window.__eagTakeWasmBytes(name);\n"
         "                            try { return await WebAssembly.compile(bytes, {builtins:['js-string']}); }\n"
         "                            finally { bytes = null; }\n"
         "                          }\n"
         "                        } finally { clearInterval(tick); }\n"
         "                      }\n")

    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print("index.html", len(html), "bytes; payload total", total)

if __name__ == "__main__":
    main()
