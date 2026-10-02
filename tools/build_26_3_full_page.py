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
MUSIC_ID = "eag-music"

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
# Payload URLs carry a content hash (?v=), so they are kept in Cache Storage
# after the first visit and later visits load them without the network. Entries
# for URLs this build no longer uses are deleted.
FETCH_DECODER = r"""  const PAYLOAD_CACHE = 'eagler-26.3-payloads';
  function cachedFetch(url) {
    if (typeof caches === 'undefined') return originalFetch(url);
    return caches.open(PAYLOAD_CACHE).then(function (cache) {
      return cache.match(url).then(function (hit) {
        if (hit) { stats.cacheHits = (stats.cacheHits || 0) + 1; return hit; }
        return originalFetch(url).then(function (response) {
          if (response.ok) cache.put(url, response.clone()).catch(function () {});
          return response;
        });
      });
    }).catch(function () { return originalFetch(url); });
  }
  window.__eagCachedFetch = cachedFetch;
  if (typeof caches !== 'undefined') {
    const current = new Set(Object.values(PAYLOADS).map(function (p) { return new URL(p.url, location.href).href; })
      .concat(Object.values(NATIVE_URLS).map(function (u) { return new URL(u, location.href).href; })));
    caches.open(PAYLOAD_CACHE).then(function (cache) {
      return cache.keys().then(function (requests) {
        requests.forEach(function (request) { if (!current.has(request.url)) cache.delete(request); });
      });
    }).catch(function () {});
  }
  function decodePayload(id) {
    if (inflight.has(id)) return inflight.get(id);
    const entry = PAYLOADS[id];
    if (!entry) return Promise.reject(new Error('Missing payload: ' + id));
    window.__eaglerInlinePayloadCacheBytes += entry.size;
    const pending = cachedFetch(entry.url).then(async function (response) {
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
        version = hashlib.sha256(data).hexdigest()[:12]
        payloads[pid] = {"url": base + name + "?v=" + version, "size": size}
        print("%-28s %-24s %10d %s" % (pid, name, size, version))
    html = block.sub("", html)

    def versioned(url, path):
        return url + "?v=" + hashlib.sha256(path.read_bytes()).hexdigest()[:12]

    assets = Path(".") / assets_url.lstrip("/")
    payloads[ASSETS_ID] = {"url": versioned(assets_url, assets), "size": assets.stat().st_size}
    # Optional music pack built by build_music_epk.py, loaded like sounds.epk.
    music = out_dir / "music.epk"
    if music.exists():
        payloads[MUSIC_ID] = {"url": versioned(base + "music.epk", music), "size": music.stat().st_size}
    # vercel.json serves native/<name>.wasm as the Brotli-encoded <name>.wasm.bin.
    native_urls = {}
    for pid, image in (("eag-inline-wasm-br", "classes.wasm"), ("eag-inline-mesh-wasm-br", "mesh-worker.wasm"),
                       ("eag-inline-server-wasm-br", "server-worker.wasm")):
        native_urls[image] = base + "native/" + image + "?v=" + payloads[pid]["url"].rsplit("?v=", 1)[1]

    start = html.index("  function decodePayload(id) {")
    end = html.index("\n  let decoderBytesPromise;")
    html = (html[:start] + "  const PAYLOADS = " + json.dumps(payloads) + ";\n"
            + "  const NATIVE_URLS = " + json.dumps(native_urls) + ";\n  window.__eagNativeURLs = NATIVE_URLS;\n"
            + FETCH_DECODER + html[end:])

    total = sum(p["size"] for p in payloads.values())
    html, n = re.subn(r'var total = Number\("\d+"\)', 'var total = Number("%d")' % total, html)
    assert n == 1
    for zh, en in TRANSLATIONS.items():
        assert zh in html, zh
        html = html.replace(zh, en)
    assert not re.search(r"[一-鿿]", html), "untranslated UI text left"
    html = html.replace("<title>Eaglercraft 26.3 Fixed</title>", "<title>Minecraft 26.3</title>")

    # Home Screen app: icons from the page's grass-block favicon, a web app
    # manifest, and the iOS tags that open it full screen without Safari UI.
    favicon = re.search(r'<link rel="icon" type="image/png" href="data:image/png;base64,([^"]+)"', html)
    (out_dir / "icon-source.png").write_bytes(base64.b64decode(favicon.group(1)))
    for px in (180, 192, 512):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out_dir / "icon-source.png"),
                        "-vf", "scale=%d:%d:flags=lanczos" % (px, px), str(out_dir / ("icon-%d.png" % px))],
                       check=True)
    (out_dir / "icon-source.png").unlink()
    manifest = {
        "name": "Minecraft 26.3",
        "short_name": "Minecraft",
        "start_url": "/",
        "scope": "/",
        "display": "fullscreen",
        "orientation": "landscape",
        "background_color": "#000000",
        "theme_color": "#000000",
        "icons": [{"src": base + "icon-%d.png" % px, "sizes": "%dx%d" % (px, px), "type": "image/png"}
                  for px in (192, 512)],
    }
    (out_dir / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    app_tags = (
        '<link rel="manifest" href="%smanifest.webmanifest">\n'
        '<link rel="apple-touch-icon" href="%sicon-180.png">\n'
        '<meta name="apple-mobile-web-app-capable" content="yes">\n'
        '<meta name="mobile-web-app-capable" content="yes">\n'
        '<meta name="apple-mobile-web-app-title" content="Minecraft">\n'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">\n'
        '<meta name="theme-color" content="#000000">\n' % (base, base))
    if html.count("<title>Minecraft 26.3</title>") != 1:
        raise RuntimeError("title anchor missing")
    html = html.replace("<title>Minecraft 26.3</title>", "<title>Minecraft 26.3</title>\n" + app_tags, 1)


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

    if MUSIC_ID in payloads:
        def swap_music(old, new):
            nonlocal html
            if html.count(old) != 1:
                raise RuntimeError("music anchor missing: " + old[:60])
            html = html.replace(old, new, 1)
        swap_music("      if (name === 'assets.epk' || name === 'sounds.epk') entry.url = payloadPrefix + name;",
                   "      if (name === 'assets.epk' || name === 'sounds.epk' || name === 'music.epk') entry.url = payloadPrefix + name;")
        swap_music("        : name === 'sounds.epk' ? decodePayload('eag-inline-sounds')",
                   "        : name === 'sounds.epk' ? decodePayload('eag-inline-sounds')\n"
                   "        : name === 'music.epk' ? decodePayload('" + MUSIC_ID + "')")
        swap_music('\t\t\t{ url: "sounds.epk?v=49cbfb0a01b2374b", path: "" }\n\t\t];',
                   '\t\t\t{ url: "sounds.epk?v=49cbfb0a01b2374b", path: "" },\n'
                   '\t\t\t{ url: "music.epk?v=' + hashlib.sha256(music.read_bytes()).hexdigest()[:16] + '", path: "" }\n\t\t];')

    # Mobile streams the client image through the native route below, so its
    # download counter only covers the resource packs.
    mobile_initial = (payloads[ASSETS_ID]["size"] + payloads["eag-inline-sounds"]["size"]
                      + payloads.get(MUSIC_ID, {}).get("size", 0))
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
    # Each step is logged and, through __eaglerBoot, written to the crash journal,
    # so a stuck or killed mobile load can be traced to download vs compile.
    swap("                    async function compileImage(name) {\n",
         "                    async function compileImage(name) {\n"
         "                      if (window.__eaglerMobileFastStart) {\n"
         "                        const began = Date.now();\n"
         "                        let phase = 'Downloading game', received = 0;\n"
         "                        const step = function (what) {\n"
         "                          window.__log.push('L:[mobile] ' + name + ': ' + what + ' at '\n"
         "                            + ((Date.now() - began) / 1000).toFixed(1) + 's');\n"
         "                        };\n"
         "                        const show = function () {\n"
         "                          window.__eaglerBoot(62, phase + '... ' + (received ? (received / 1048576).toFixed(1)\n"
         "                            + ' MB, ' : '') + Math.round((Date.now() - began) / 1000) + 's');\n"
         "                        };\n"
         "                        const tick = setInterval(show, 1000);\n"
         "                        show();\n"
         "                        try {\n"
         "                          try {\n"
         "                            step('requesting native image');\n"
         "                            const response = await window.__eagCachedFetch(window.__eagNativeURLs[name]);\n"
         "                            if (!response.ok) throw new Error('HTTP ' + response.status);\n"
         "                            step('response ' + response.headers.get('content-type'));\n"
         "                            const reader = response.body.getReader();\n"
         "                            const counted = new ReadableStream({ async pull(controller) {\n"
         "                              const chunk = await reader.read();\n"
         "                              if (chunk.done) {\n"
         "                                phase = 'Compiling game';\n"
         "                                step('downloaded ' + (received / 1048576).toFixed(1) + ' MB');\n"
         "                                controller.close();\n"
         "                                return;\n"
         "                              }\n"
         "                              received += chunk.value.length;\n"
         "                              controller.enqueue(chunk.value);\n"
         "                            } });\n"
         "                            const compiled = await WebAssembly.compileStreaming(\n"
         "                              new Response(counted, {headers: {'Content-Type': 'application/wasm'}}), {builtins:['js-string']});\n"
         "                            step('compiled');\n"
         "                            return compiled;\n"
         "                          } catch (nativeError) {\n"
         "                            step('native streaming failed (' + nativeError + '); unpacking in page');\n"
         "                            phase = 'Unpacking game'; received = 0;\n"
         "                            let bytes = await window.__eagTakeWasmBytes(name);\n"
         "                            phase = 'Compiling game';\n"
         "                            step('unpacked');\n"
         "                            try {\n"
         "                              const compiled = await WebAssembly.compile(bytes, {builtins:['js-string']});\n"
         "                              step('compiled');\n"
         "                              return compiled;\n"
         "                            } finally { bytes = null; }\n"
         "                          }\n"
         "                        } finally { clearInterval(tick); }\n"
         "                      }\n")

    # iPad Safari compiles the client but then throws "WebAssembly.Module.imports
    # unable to produce import descriptors for the given module" from TeaVM's
    # memory-import check, in the page and in both worker runtimes. That check
    # only asks whether the module imports teavm.memory; none of the 26.3 images
    # does (verified below), so treat a failing Module.imports as "no imports".
    imports_check = "function f(e){return WebAssembly.Module.imports(e).findIndex("
    if html.count(imports_check) != 3:
        raise RuntimeError("expected 3 TeaVM runtime copies, found %d" % html.count(imports_check))
    html = html.replace(imports_check,
                        "function f(e){let i;try{i=WebAssembly.Module.imports(e)}catch(x){i=[]}return i.findIndex(")
    subprocess.run(["node", "-e", """
const fs = require('fs'), zlib = require('zlib');
for (const file of process.argv.slice(1)) {
  const module = new WebAssembly.Module(zlib.brotliDecompressSync(fs.readFileSync(file)), {builtins: ['js-string']});
  if (WebAssembly.Module.imports(module).some(i => i.kind === 'memory')) {
    throw new Error(file + ' imports memory; the Safari Module.imports fallback would be wrong');
  }
}
"""] + [str(out_dir / PAYLOAD_FILES[p]) for p in ("eag-inline-wasm-br", "eag-inline-mesh-wasm-br",
                                                  "eag-inline-server-wasm-br")], check=True)

    # On short (landscape phone) screens the 100vmin splash image reached the
    # bottom-pinned status line and the two overlapped; leave room for it.
    swap("\t\t\twidth: min(100vmin, 512px);\n\t\t\theight: min(100vmin, 512px);",
         "\t\t\twidth: min(calc(100vmin - 64px), 512px);\n\t\t\theight: min(calc(100vmin - 64px), 512px);")

    # Boot screen: Minecraft's red Mojang Studios screen from the start instead
    # of the eagtek splash image, with the download/status line kept below it.
    html, removed = re.subn(r'\s*<img id="boot_image"[^>]*>', "", html, count=1)
    if removed != 1:
        raise RuntimeError("boot image markup missing")
    swap("\t\t#rotate_device {\n\t\t\tdisplay: none;\n\t\t}",
         "\t\t#loading_screen { background: #ef323d !important; }\n"
         "\t\t#loading_screen #mojang_stage { display: flex; }\n"
         "\t\t#loading_screen #boot_status,\n"
         "\t\t#loading_screen.minecraft-stage #boot_status { display: block; color: rgba(255, 255, 255, 0.9); }\n"
         "\t\t#rotate_device {\n\t\t\tdisplay: none;\n\t\t}")

    # Loader trace, hidden behind a "Logs" toggle in the bottom-right corner
    # (shown open with ?debug=1): the current step, recent loader log lines, page
    # errors, and where the previous attempt stopped if the tab was killed. The
    # toggle turns red when there is an error or a recovered crash. Both are
    # removed once the game is ready.
    swap("</body>",
         """<script>
(function () {
  var box = document.createElement("div");
  box.id = "eagler_loader_trace";
  box.style.cssText = "position:fixed;left:8px;right:8px;top:8px;z-index:2147483647;max-height:40vh;"
    + "overflow:hidden;background:rgba(0,0,0,.8);color:#9f9;font:11px/1.35 monospace;padding:6px 8px;"
    + "border-radius:4px;white-space:pre-wrap;pointer-events:none";
  var open = new URLSearchParams(location.search).get("debug") === "1";
  box.style.display = open ? "block" : "none";
  var toggle = document.createElement("button");
  toggle.id = "eagler_loader_trace_toggle";
  toggle.type = "button";
  toggle.style.cssText = "position:fixed;right:12px;bottom:12px;z-index:2147483647;padding:6px 12px;"
    + "font:12px/1.2 monospace;color:#fff;background:rgba(0,0,0,.65);border:1px solid #888;border-radius:4px";
  toggle.addEventListener("click", function () { open = !open; box.style.display = open ? "block" : "none"; render(); });
  var started = performance.now(), errors = [];
  window.addEventListener("error", function (e) { errors.push("ERROR " + (e.message || e.error)); });
  window.addEventListener("unhandledrejection", function (e) {
    errors.push("REJECTED " + (e.reason && (e.reason.message || e.reason)));
  });
  var prev = window.__eaglerRecoveredCrash, head = "";
  if (prev) {
    head = "Previous attempt stopped at: " + prev.stage + " (" + (prev.fatalKind || "unknown") + ")\\n"
      + (prev.logTail || []).filter(function (l) { return !/^BOOTSTAGE/.test(l); }).slice(-3).join("\\n") + "\\n---\\n";
  }
  var timer;
  function render() {
    if (window.__eaglerGameReady === true) {
      clearInterval(timer);
      [box, toggle].forEach(function (el) { if (el.parentNode) el.parentNode.removeChild(el); });
      return;
    }
    var alert = !!(prev || errors.length || /^E:/.test(((window.__log || []).filter(function (l) {
      return /^E:\\[shell\\]|^E:SHELL_ERR/.test(l); })[0]) || ""));
    toggle.textContent = (open ? "Hide logs" : "Logs") + (alert ? " !" : "");
    toggle.style.background = alert ? "rgba(170,20,20,.85)" : "rgba(0,0,0,.65)";
    // Stay above the crash screen and the recovered-crash bar.
    var bar = document.getElementById("eagler_recovered_crash");
    toggle.style.bottom = bar ? (bar.offsetHeight + 24) + "px" : "12px";
    if (document.body.lastElementChild !== toggle) { document.body.appendChild(box); document.body.appendChild(toggle); }
    if (!open) return;
    var status = (document.getElementById("boot_status") || {}).textContent || "";
    var lines = (window.__log || []).filter(function (l) { return !/^BOOTSTAGE/.test(l); }).slice(-8);
    box.textContent = head + "[" + Math.round((performance.now() - started) / 1000) + "s] " + status + "\\n"
      + lines.join("\\n") + (errors.length ? "\\n" + errors.slice(-3).join("\\n") : "");
  }
  document.body.appendChild(box);
  document.body.appendChild(toggle);
  timer = setInterval(render, 500);
  render();
})();
</script>
</body>""")

    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print("index.html", len(html), "bytes; payload total", total)

if __name__ == "__main__":
    main()
