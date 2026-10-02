#!/usr/bin/env node
// Rewrite the 26.3 build's char-by-char branding strings in classes.wasm.
//
// The 26.3 client builds each branding string in its own lazy getter:
//   i32.const c0 ... i32.const cN-1 ; array.new_fixed <type> N ; struct.new ...
// so the text is invisible to plain string searches. This tool finds a getter
// by its exact current text, re-encodes the char run with the new text, and
// rebuilds the function body and code-section sizes around it.
//
// usage:
//   node patch_26_3_branding.js --inspect <classes.wasm.bin>
//   node patch_26_3_branding.js <in.wasm.bin> <out.wasm.bin> '<old>=<new>' ... [--lower-label=<old>]
// --lower-label moves the title-screen line drawn from <old>'s getter down to
// the bottom line.
// .wasm.bin files are Brotli-compressed Wasm images, as shipped by the page.
'use strict';
const fs = require('fs');
const zlib = require('zlib');

function readU(buf, pos) {
  let result = 0, shift = 0, b;
  do { b = buf[pos++]; result += (b & 0x7f) * 2 ** shift; shift += 7; } while (b & 0x80);
  return [result, pos];
}
function readS32(buf, pos) {
  let result = 0, shift = 0, b;
  do { b = buf[pos++]; result |= (b & 0x7f) << shift; shift += 7; } while (b & 0x80);
  if (shift < 32 && (b & 0x40)) result |= -1 << shift;
  return [result, pos];
}
function encU(n) {
  const out = [];
  do { let b = n & 0x7f; n = Math.floor(n / 128); if (n) b |= 0x80; out.push(b); } while (n);
  return Buffer.from(out);
}
function encS32(n) {
  const out = [];
  for (;;) {
    const b = n & 0x7f; n >>= 7;
    if ((n === 0 && !(b & 0x40)) || (n === -1 && (b & 0x40))) { out.push(b); break; }
    out.push(b | 0x80);
  }
  return Buffer.from(out);
}

function sections(wasm) {
  const out = [];
  let pos = 8;
  while (pos < wasm.length) {
    const id = wasm[pos];
    const [size, body] = readU(wasm, pos + 1);
    out.push({ id, start: pos, body, end: body + size });
    pos = body + size;
  }
  return out;
}

// Every run of >=3 printable i32.const immediates that ends in array.new_fixed.
function findCharRuns(wasm, from, to) {
  const runs = [];
  let chars = [], runStart = -1;
  for (let pos = from; pos < to;) {
    if (wasm[pos] === 0x41) {
      const [v, next] = readS32(wasm, pos + 1);
      if (v >= 32 && v < 0x10000) {
        if (!chars.length) runStart = pos;
        chars.push(v); pos = next; continue;
      }
    }
    if (chars.length >= 3 && wasm[pos] === 0xfb && wasm[pos + 1] === 0x08) {
      const [type, p1] = readU(wasm, pos + 2);
      const [count, p2] = readU(wasm, p1);
      if (count === chars.length) {
        runs.push({ start: runStart, end: p2, type, text: String.fromCharCode(...chars) });
      }
    }
    chars = []; pos++;
  }
  return runs;
}

function countFunctionImports(wasm) {
  const imports = sections(wasm).find(s => s.id === 2);
  if (!imports) return 0;
  let [n, pos] = readU(wasm, imports.body), funcs = 0;
  const skipLimits = () => { const flags = wasm[pos++]; [, pos] = readU(wasm, pos); if (flags & 1) [, pos] = readU(wasm, pos); };
  for (let i = 0; i < n; i++) {
    for (let k = 0; k < 2; k++) { let len; [len, pos] = readU(wasm, pos); pos += len; }
    const kind = wasm[pos++];
    if (kind === 0) { funcs++; [, pos] = readU(wasm, pos); }
    else if (kind === 1) { pos++; skipLimits(); }
    else if (kind === 2) skipLimits();
    else if (kind === 3) pos += 2;
    else if (kind === 4) { pos++; [, pos] = readU(wasm, pos); }
    else throw new Error('unknown import kind ' + kind);
  }
  return funcs;
}

// The title screen draws the version label at `height - 20` and the (now
// cleared) credit line at `height - 10`, each just before calling its getter.
// Move the label onto the bottom line by changing that one 20 to 10 in place.
function lowerTitleLabel(wasm, labelGetter) {
  const code = sections(wasm).find(s => s.id === 10);
  const call = Buffer.concat([Buffer.from([0x10]), encU(labelGetter)]);
  const upper = Buffer.from([0x41, 0x14, 0x6b, 0x21]);  // i32.const 20; i32.sub; local.set
  const hits = [];
  for (let at = wasm.indexOf(call, code.body); at >= 0 && at < code.end; at = wasm.indexOf(call, at + 1)) {
    const from = Math.max(code.body, at - 300);
    const y = wasm.subarray(from, at).lastIndexOf(upper);
    // The bottom line's `height - 10` must follow in the same draw code.
    const bottom = wasm.subarray(at, at + 2000).indexOf(Buffer.from([0x41, 0x0a, 0x6b, 0x21]));
    if (y >= 0 && bottom >= 0) hits.push(from + y);
  }
  if (hits.length !== 1) throw new Error('expected one title label position, found ' + hits.length);
  wasm[hits[0] + 1] = 0x0a;
  console.error('title label: height - 20 -> height - 10 at %d', hits[0]);
}

// With no worlds saved, the Singleplayer world list's state machine branches
// (br_table 0 1 36) straight to EaglerCreateWorldSelectionScreen ("What would
// you like to do?") instead of listing the NoWorldsEntry. Same function shape
// and fix as the 26.2 build's tools/patch_world_list_wasm.py: br_table 1 1 36.
function showEmptyWorldList(wasm) {
  const code = sections(wasm).find(s => s.id === 10);
  const from = Buffer.from([0x0e, 0x02, 0x00, 0x01, 0x24]);
  const hits = [];
  for (let at = wasm.indexOf(from, code.body); at >= 0 && at < code.end; at = wasm.indexOf(from, at + 1)) hits.push(at);
  if (hits.length !== 1) throw new Error('expected one empty-world-list branch, found ' + hits.length);
  // 0e br_table, 02 two targets, 00 first target (the empty-list case), 01, 24 default.
  wasm[hits[0] + 2] = 0x01;
  if (!wasm.subarray(hits[0], hits[0] + 5).equals(Buffer.from([0x0e, 0x02, 0x01, 0x01, 0x24]))) {
    throw new Error('empty-world-list branch not rewritten');
  }
  console.error('empty world list: br_table 0 1 36 -> 1 1 36 at %d', hits[0]);
}

// Title screen profile button. Indices below are this build's (absolute
// function, type and global numbers as `wasm-tools print` shows them); every
// edit checks the bytes it expects before writing.
const PB = {
  createNormalMenuOptions: 136440,  // TitleScreen.createNormalMenuOptions
  init: 54466,                      // TitleScreen.init
  languageButton: 12394,            // CommonButtons.language(width, onPress, iconOnly)
  addRenderableWidget: 1800,        // Screen.addRenderableWidget(screen, widget)
  profileLambda: 36382, profileLambdaVt: 75502,          // opens EaglerProfileScreen26
  multiplayerLambda: 36383, multiplayerLambdaVt: 75501,  // opens JoinMultiplayerScreen
  accessibilityLambda: 36388,
  titleScreen: 23172, screen: 20319, widthField: 9,
  string: 22, charArray: 21, chars: 1, object: 11,
  vtable: 20576, setX: 274, setY: 273, setterType: 1423, helperType: 111874,
  languageSprite: 153282, languageLabel: 75507, languageTooltip: 153283,
};

const bytes = (...parts) => Buffer.concat(parts.map(p => Buffer.isBuffer(p) ? p : Buffer.from(p)));
const op = (code, ...imms) => bytes([code], ...imms.map(encU));
const gc = (sub, ...imms) => bytes([0xfb, sub], ...imms.map(encU));
const refCast = (type, nullable = true) => bytes([0xfb, nullable ? 0x17 : 0x16], encS32(type));

function replaceAll(body, from, to, expected, what) {
  const parts = [];
  let last = 0, n = 0;
  for (let at = body.indexOf(from); at >= 0; at = body.indexOf(from, at + from.length)) {
    parts.push(body.subarray(last, at), to);
    last = at + from.length;
    n++;
  }
  if (n !== expected) throw new Error(what + ': expected ' + expected + ' matches, found ' + n);
  parts.push(body.subarray(last));
  return Buffer.concat(parts);
}

// A new java.lang.String, built the way TeaVM's own char-run getters build
// one, borrowing the String and char[] vtables from an existing constant.
function newString(text) {
  const g = op(0x23, PB.languageSprite);
  return bytes(
    g, gc(0x02, PB.string, 0), [0xd0, 0x6d],
    g, gc(0x02, PB.string, 2), gc(0x02, PB.charArray, 0), [0xd0, 0x6d],
    ...[...text].map(ch => bytes([0x41], encS32(ch.charCodeAt(0)))),
    gc(0x08, PB.chars, text.length), gc(0x00, PB.charArray),
    [0x41, 0x00], gc(0x00, PB.string));
}

// Point "Minecraft Realms" at the Multiplayer screen, and add a small sprite
// button that opens the profile screen, left of the language button.
function addProfileButton(wasm, sprite, label) {
  const secs = sections(wasm);
  const funcSec = secs.find(s => s.id === 3), code = secs.find(s => s.id === 10);
  const imports = countFunctionImports(wasm);
  let [nTypes, p] = readU(wasm, funcSec.body);
  const types = [];
  for (let i = 0; i < nTypes; i++) { let t; [t, p] = readU(wasm, p); types.push(t); }
  let [count, pos] = readU(wasm, code.body);
  const bodies = [];
  for (let i = 0; i < count; i++) {
    const [size, start] = readU(wasm, pos);
    bodies.push(wasm.subarray(start, start + size));
    pos = start + size;
  }
  const idx = fn => fn - imports;
  const clone = imports + count, helper = clone + 1;

  // 1. The Realms button's onPress lambda becomes the Multiplayer one (same
  //    struct shape: vtable, monitor, TitleScreen), including the local that
  //    holds it and the cast that restores that local on coroutine resume.
  let body = bodies[idx(PB.createNormalMenuOptions)];
  for (const [prefix, n] of [[[0xfb, 0x01], 1], [[0xfb, 0x05], 2], [[0xfb, 0x17], 2], [[0x63], 1]]) {
    const enc = prefix[0] === 0xfb && prefix[1] !== 0x17 ? encU : encS32;
    body = replaceAll(body, bytes(prefix, enc(PB.profileLambda)),
                      bytes(prefix, enc(PB.multiplayerLambda)), n, 'realms lambda ' + prefix);
  }
  body = replaceAll(body, op(0x23, PB.profileLambdaVt), op(0x23, PB.multiplayerLambdaVt), 1, 'realms vtable');
  bodies[idx(PB.createNormalMenuOptions)] = body;

  // 2. Shift the language and accessibility buttons (x = width/2 - 22 + 0|24)
  //    right by 12 so the three small buttons stay centered, then add ours.
  body = bodies[idx(PB.init)];
  const x = off => bytes(gc(0x02, PB.titleScreen, PB.widthField), [0x41, 0x02, 0x6d, 0x41, 22, 0x6b, 0x41, off, 0x6a]);
  for (const off of [0, 24]) {
    const to = Buffer.from(x(off)); to[to.length - 5] = 10;
    body = replaceAll(body, x(off), to, 1, 'small button x ' + off);
  }
  const before = gc(0x01, PB.accessibilityLambda);
  body = replaceAll(body, before, bytes([0x20, 0x00, 0x20, 0x09], op(0x10, helper), before), 1,
                    'helper call site');  // helper(this, y)
  bodies[idx(PB.init)] = body;

  // 3. A copy of the language button factory with our sprite and label.
  body = bodies[idx(PB.languageButton)];
  body = replaceAll(body, op(0x23, PB.languageSprite), newString(sprite), 1, 'sprite');
  body = replaceAll(body, op(0x23, PB.languageLabel), newString(label), 1, 'label');
  body = replaceAll(body, op(0x23, PB.languageTooltip), newString(label), 1, 'tooltip');
  bodies.push(body);
  types.push(types[idx(PB.languageButton)]);

  // 4. helper(TitleScreen this, int y): builds the profile lambda, the button,
  //    adds it and places it at (width/2 - 34, y).
  const setter = slot => bytes([0x20, 0x02], gc(0x02, PB.object, 0), refCast(PB.vtable, false),
                               gc(0x02, PB.vtable, slot), op(0x14, PB.setterType));
  const helperCode = bytes(
    [0x01, 0x01, 0x63], encS32(PB.object),                 // local 2: (ref null 11)
    gc(0x01, PB.profileLambda), [0x21, 0x02],
    [0x20, 0x02], refCast(PB.profileLambda), op(0x23, PB.profileLambdaVt), gc(0x05, PB.profileLambda, 0),
    [0x20, 0x02], refCast(PB.profileLambda), [0x20, 0x00], gc(0x05, PB.profileLambda, 2),
    [0x41, 20, 0x20, 0x02, 0x41, 1], op(0x10, clone), [0x21, 0x02],
    [0x20, 0x00], refCast(PB.screen), [0x20, 0x02], op(0x10, PB.addRenderableWidget), [0x1a],
    [0x20, 0x02, 0x20, 0x00], gc(0x02, PB.titleScreen, PB.widthField),
    [0x41, 0x02, 0x6d, 0x41, 34, 0x6b], setter(PB.setX),
    [0x20, 0x02, 0x20, 0x01], setter(PB.setY),
    [0x0b]);
  bodies.push(helperCode);
  types.push(PB.helperType);

  const funcContent = Buffer.concat([encU(types.length), ...types.map(encU)]);
  const codeContent = Buffer.concat([encU(bodies.length), ...bodies.flatMap(b => [encU(b.length), b])]);
  console.error('profile button: realms -> multiplayer, clone #%d, helper #%d', clone, helper);
  return bytes(wasm.subarray(0, funcSec.start), [3], encU(funcContent.length), funcContent,
               wasm.subarray(funcSec.end, code.start), [10], encU(codeContent.length), codeContent,
               wasm.subarray(code.end));
}

function patch(wasm, edits, options = {}) {
  const code = sections(wasm).find(s => s.id === 10);
  const [count, first] = readU(wasm, code.body);
  const pending = new Map(Object.entries(edits));
  const getters = {};
  const bodies = [];
  let pos = first, changed = 0;
  for (let i = 0; i < count; i++) {
    const [size, start] = readU(wasm, pos);
    let body = wasm.subarray(start, start + size);
    pos = start + size;
    // Branding getters are tiny; skip scanning large bodies.
    if (size < 4096) {
      const runs = findCharRuns(body, 0, body.length).filter(r => pending.has(r.text));
      if (runs.length) {
        const parts = [];
        let last = 0;
        for (const run of runs) {
          const text = pending.get(run.text);
          const consts = [...text].map(ch => Buffer.concat([Buffer.from([0x41]), encS32(ch.charCodeAt(0))]));
          parts.push(body.subarray(last, run.start), ...consts,
                     Buffer.from([0xfb, 0x08]), encU(run.type), encU(text.length));
          last = run.end;
          console.error('function #%d: %j -> %j', i, run.text, text);
          getters[run.text] = i;
          changed++;
        }
        parts.push(body.subarray(last));
        body = Buffer.concat(parts);
      }
    }
    bodies.push(encU(body.length), body);
  }
  if (changed !== pending.size) {
    throw new Error('expected ' + pending.size + ' edits, applied ' + changed);
  }
  const content = Buffer.concat([encU(count), ...bodies]);
  const out = Buffer.concat([wasm.subarray(0, code.start), Buffer.from([10]), encU(content.length),
                             content, wasm.subarray(code.end)]);
  if (options.lowerLabel) {
    if (!(options.lowerLabel in getters)) throw new Error('label getter not edited: ' + options.lowerLabel);
    lowerTitleLabel(out, countFunctionImports(out) + getters[options.lowerLabel]);
  }
  if (options.emptyWorldList) showEmptyWorldList(out);
  if (options.profileButton) return addProfileButton(out, 'icon/profile', 'eagler.menu.editProfile');
  return out;
}

const args = process.argv.slice(2);
if (args[0] === '--inspect') {
  const wasm = zlib.brotliDecompressSync(fs.readFileSync(args[1]));
  const code = sections(wasm).find(s => s.id === 10);
  for (const run of findCharRuns(wasm, code.body, code.end)) {
    if (/JM|Joey|o_xer|Made by|Credits/.test(run.text)) console.log(run.start, JSON.stringify(run.text));
  }
} else {
  const [input, output, ...rest] = args;
  const edits = {}, options = {};
  for (const arg of rest) {
    if (arg.startsWith('--lower-label=')) { options.lowerLabel = arg.slice('--lower-label='.length); continue; }
    if (arg === '--empty-world-list') { options.emptyWorldList = true; continue; }
    if (arg === '--profile-button') { options.profileButton = true; continue; }
    const i = arg.indexOf('=');
    edits[arg.slice(0, i)] = arg.slice(i + 1);
  }
  const wasm = patch(zlib.brotliDecompressSync(fs.readFileSync(input)), edits, options);
  if (!WebAssembly.validate(wasm, { builtins: ['js-string'] })) {
    throw new Error('patched module does not validate');
  }
  fs.writeFileSync(output, zlib.brotliCompressSync(wasm, { params: {
    [zlib.constants.BROTLI_PARAM_QUALITY]: 9,
    [zlib.constants.BROTLI_PARAM_LGWIN]: 24,
    [zlib.constants.BROTLI_PARAM_SIZE_HINT]: wasm.length,
  } }));
}
