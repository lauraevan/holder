#!/usr/bin/env python3
"""Build preview/26.3-full from the single-file webmc 26.3 build.

The upstream page embeds every payload as base64 <script> blocks (~90 MB of
HTML). Split them into sibling files that the page fetches, keep the rest of
the proven loader unchanged, use the all-languages assets EPK, and translate
the loader's Chinese UI strings.

usage: build_26_3_full_page.py <webmc/assets/26.3.html> <out_dir> <site base path> <assets.epk site path>

Vercel rewrites / to this page, so payload URLs are absolute site paths.
"""
import base64, hashlib, json, re, sys
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


    # Mobile fast-start: phones boot with the 26.3 client + assets only.
    # Sounds are omitted from the initial resource-pack list and mesh workers
    # are disabled on mobile. The server Wasm remains lazy as before.
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
\t\t\t\t\t|| (window.matchMedia && window.matchMedia("(pointer:coarse)").matches)));
\t\twindow.__eaglerMobileFastStart = mobileFastStart;
\t\tvar startupAssets = [
\t\t\t{ url: "assets.epk?v=49cbfb0a01b2374b", path: "" }
\t\t];
\t\tif (!mobileFastStart) startupAssets.push({ url: "sounds.epk?v=49cbfb0a01b2374b", path: "" });
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

    mobile_initial = (
        payloads["eag-inline-decoder"]["size"]
        + payloads["eag-inline-wasm-br"]["size"]
        + payloads[ASSETS_ID]["size"]
    )
    desktop_initial = mobile_initial + payloads["eag-inline-mesh-wasm-br"]["size"] + payloads["eag-inline-sounds"]["size"]
    html = re.sub(
        r'var total = Number\("\d+"\) \|\| 0;',
        'var total = Number(window.__eaglerMobileFastStart ? "%d" : "%d") || 0;' % (mobile_initial, desktop_initial),
        html,
        count=1
    )

    release_old = '''  window.__eagReleaseInlineWasm = function (name) {
    if (name) wasmCache.delete(name); else wasmCache.clear();
  };

'''
    release_new = '''  window.__eagReleaseInlineWasm = function (name) {
    if (name) wasmCache.delete(name); else wasmCache.clear();
  };
  window.__eaglerWarmMobileSounds = function () {
    if (!window.__eaglerMobileFastStart) return;
    try {
      const c = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      if (c && (c.saveData || /(^|-)2g$/.test(String(c.effectiveType || '')))) return;
      const link = document.createElement('link');
      link.rel = 'prefetch';
      link.as = 'fetch';
      link.href = PAYLOADS['eag-inline-sounds'].url;
      link.fetchPriority = 'low';
      document.head.appendChild(link);
      stats.mobileSoundPrefetch = 1;
    } catch (e) {}
  };

'''
    if release_old not in html:
        raise RuntimeError("mobile sound warm insertion point missing")
    html = html.replace(release_old, release_new, 1)

    ready_anchor = '''\t\t\t\t\t\tdocument.body.style.backgroundColor = "black";
\t\t\t\t\t\treturn;
'''
    ready_start = html.index('if (!eagtekGone && window.__eaglerGameReady === true)')
    ready_at = html.index(ready_anchor, ready_start)
    html = html[:ready_at] + '''\t\t\t\t\t\tif (window.__eaglerMobileFastStart && typeof window.__eaglerWarmMobileSounds === "function") {
\t\t\t\t\t\t\tsetTimeout(window.__eaglerWarmMobileSounds, 8000);
\t\t\t\t\t\t}
''' + html[ready_at:]

    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print("index.html", len(html), "bytes; payload total", total)

if __name__ == "__main__":
    main()
