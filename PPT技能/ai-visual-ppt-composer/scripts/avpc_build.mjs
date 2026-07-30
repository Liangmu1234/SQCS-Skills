#!/usr/bin/env node
/*
 * AI Visual PPT Composer builder
 *
 * Reads deck.json and writes:
 * - output/deck.pptx with editable PPT text/shapes/tables/charts where possible
 * - output/deck_preview.html for inspection
 * - optional output/slide-XX.png screenshots if Playwright is installed
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const pptxgen = require('pptxgenjs');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function die(message) {
  console.error(`ERROR: ${message}`);
  process.exit(1);
}

function readJson(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (err) {
    die(`Could not read JSON ${filePath}: ${err.message}`);
  }
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function cleanHex(color, fallback = 'FFFFFF') {
  if (!color) return fallback;
  const s = String(color).replace('#', '').trim();
  return /^[0-9a-fA-F]{6}$/.test(s) ? s.toUpperCase() : fallback;
}

function resolveAsset(baseDir, assetPath) {
  if (!assetPath) return null;
  if (/^data:/.test(assetPath)) return assetPath;
  if (/^https?:\/\//.test(assetPath)) return assetPath;
  return path.resolve(baseDir, assetPath);
}

function readSvgAsDataUri(filePath) {
  const raw = fs.readFileSync(filePath, 'utf8');
  const b64 = Buffer.from(raw, 'utf8').toString('base64');
  return `data:image/svg+xml;base64,${b64}`;
}

function svgStringAsDataUri(svg) {
  const b64 = Buffer.from(svg, 'utf8').toString('base64');
  return `data:image/svg+xml;base64,${b64}`;
}

function opacityToTransparency(opacity) {
  if (opacity === undefined || opacity === null) return undefined;
  const n = Number(opacity);
  if (Number.isNaN(n)) return undefined;
  // Deck JSON uses 0..1 opacity. PPTX uses 0..100 transparency.
  if (n >= 0 && n <= 1) return Math.round((1 - n) * 100);
  return Math.max(0, Math.min(100, 100 - n));
}

function normalizeFill(fill, fallbackColor = 'FFFFFF') {
  if (!fill) return undefined;
  if (typeof fill === 'string') return { color: cleanHex(fill, fallbackColor) };
  const out = { ...fill };
  if (out.color) out.color = cleanHex(out.color, fallbackColor);
  if (out.opacity !== undefined && out.transparency === undefined) {
    out.transparency = opacityToTransparency(out.opacity);
  }
  return out;
}

function normalizeLine(line, fallbackColor = 'FFFFFF') {
  if (!line) return undefined;
  if (typeof line === 'string') return { color: cleanHex(line, fallbackColor), width: 1 };
  const out = { ...line };
  if (out.color) out.color = cleanHex(out.color, fallbackColor);
  if (out.opacity !== undefined && out.transparency === undefined) {
    out.transparency = opacityToTransparency(out.opacity);
  }
  return out;
}

function normalizeShadow(shadow) {
  if (!shadow) return undefined;
  const out = { ...shadow };
  if (out.color) out.color = cleanHex(out.color, '000000');
  return out;
}

function shapeTypeFromName(pptx, name, radius) {
  const n = String(name || '').toLowerCase();
  if (n === 'ellipse' || n === 'circle') return pptx.ShapeType.ellipse;
  if (n === 'triangle') return pptx.ShapeType.triangle;
  if (n === 'diamond') return pptx.ShapeType.diamond;
  if (n === 'arc') return pptx.ShapeType.arc;
  if (n === 'chevron') return pptx.ShapeType.chevron;
  if (n === 'pentagon') return pptx.ShapeType.pentagon;
  if (n === 'hexagon') return pptx.ShapeType.hexagon;
  if (radius || n === 'roundrect' || n === 'roundedrect' || n === 'rounded-rect') return pptx.ShapeType.roundRect;
  return pptx.ShapeType.rect;
}

function addBackground(slide, pptx, deckSlide, baseDir, W, H, theme) {
  const bg = deckSlide.background || {};
  const color = bg.color || theme.backgroundColor || '0B1020';
  slide.background = { color: cleanHex(color, '0B1020') };
  if (bg.image) {
    const p = resolveAsset(baseDir, bg.image);
    if (p && fs.existsSync(p)) {
      slide.addImage({ path: p, x: 0, y: 0, w: W, h: H, transparency: opacityToTransparency(bg.opacity) });
    } else {
      console.warn(`WARN: background image not found: ${bg.image}`);
    }
  }
}

function addText(slide, el, theme) {
  const opts = {
    x: Number(el.x),
    y: Number(el.y),
    w: Number(el.w),
    h: Number(el.h),
    fontFace: el.fontFace || theme.fontFace || 'Microsoft YaHei',
    fontSize: Number(el.fontSize || 16),
    bold: Boolean(el.bold),
    italic: Boolean(el.italic),
    color: cleanHex(el.color || theme.color || 'FFFFFF'),
    align: el.align || 'left',
    valign: el.valign || 'top',
    margin: el.margin === undefined ? 0.04 : Number(el.margin),
    rotate: el.rotate ? Number(el.rotate) : undefined,
    fit: el.fit || 'shrink',
    breakLine: Boolean(el.breakLine),
    isTextBox: true,
    transparency: opacityToTransparency(el.opacity),
    shadow: normalizeShadow(el.shadow),
  };
  if (el.fill) opts.fill = normalizeFill(el.fill);
  if (el.line) opts.line = normalizeLine(el.line);
  slide.addText(String(el.text ?? ''), opts);
}

function addShape(slide, pptx, el) {
  const opts = {
    x: Number(el.x),
    y: Number(el.y),
    w: Number(el.w),
    h: Number(el.h),
    rotate: el.rotate ? Number(el.rotate) : undefined,
    fill: normalizeFill(el.fill || { color: 'FFFFFF', transparency: 100 }),
    line: normalizeLine(el.line || { color: 'FFFFFF', transparency: 100 }),
    shadow: normalizeShadow(el.shadow),
    transparency: opacityToTransparency(el.opacity),
  };
  slide.addShape(shapeTypeFromName(pptx, el.shape || el.name, el.radius), opts);
}

function addLine(slide, el) {
  slide.addShape('line', {
    x: Number(el.x),
    y: Number(el.y),
    w: Number(el.w),
    h: Number(el.h),
    line: normalizeLine(el.line || { color: 'FFFFFF', width: 1 }),
    rotate: el.rotate ? Number(el.rotate) : undefined,
  });
}

function addImage(slide, el, baseDir) {
  const p = resolveAsset(baseDir, el.path);
  if (!p) return;
  const opts = {
    x: Number(el.x),
    y: Number(el.y),
    w: Number(el.w),
    h: Number(el.h),
    rotate: el.rotate ? Number(el.rotate) : undefined,
    transparency: opacityToTransparency(el.opacity),
  };
  if (/^data:/.test(p)) {
    slide.addImage({ data: p, ...opts });
  } else if (fs.existsSync(p)) {
    if (p.toLowerCase().endsWith('.svg')) {
      slide.addImage({ data: readSvgAsDataUri(p), ...opts });
    } else {
      slide.addImage({ path: p, ...opts });
    }
  } else {
    console.warn(`WARN: image not found: ${el.path}`);
  }
}

function addSvg(slide, el, baseDir) {
  const opts = {
    x: Number(el.x),
    y: Number(el.y),
    w: Number(el.w),
    h: Number(el.h),
    rotate: el.rotate ? Number(el.rotate) : undefined,
    transparency: opacityToTransparency(el.opacity),
  };
  if (el.svg) {
    slide.addImage({ data: svgStringAsDataUri(String(el.svg)), ...opts });
    return;
  }
  const p = resolveAsset(baseDir, el.path);
  if (p && fs.existsSync(p)) {
    slide.addImage({ data: readSvgAsDataUri(p), ...opts });
  } else {
    console.warn(`WARN: svg not found: ${el.path}`);
  }
}

function addTable(slide, el, theme) {
  const rows = Array.isArray(el.rows) ? el.rows : [];
  if (!rows.length) return;
  const opts = {
    x: Number(el.x),
    y: Number(el.y),
    w: Number(el.w),
    h: Number(el.h),
    fontFace: el.fontFace || theme.fontFace || 'Microsoft YaHei',
    fontSize: Number(el.fontSize || 10),
    color: cleanHex(el.color || theme.color || 'FFFFFF'),
    border: normalizeLine(el.line || { color: 'FFFFFF', transparency: 70, width: 0.5 }),
    fill: normalizeFill(el.fill || { color: 'FFFFFF', transparency: 100 }),
    margin: el.margin === undefined ? 0.04 : Number(el.margin),
    ...el.options,
  };
  slide.addTable(rows, opts);
}

function addChart(slide, pptx, el, theme) {
  const chartTypeMap = {
    bar: pptx.ChartType.bar,
    col: pptx.ChartType.bar,
    column: pptx.ChartType.bar,
    line: pptx.ChartType.line,
    pie: pptx.ChartType.pie,
    doughnut: pptx.ChartType.doughnut,
    area: pptx.ChartType.area,
    scatter: pptx.ChartType.scatter,
  };
  const type = chartTypeMap[String(el.chartType || 'bar').toLowerCase()] || pptx.ChartType.bar;
  const data = Array.isArray(el.data) ? el.data : [];
  if (!data.length) return;
  const opts = {
    x: Number(el.x),
    y: Number(el.y),
    w: Number(el.w),
    h: Number(el.h),
    showLegend: false,
    showTitle: false,
    showValue: true,
    catAxisLabelFontFace: theme.fontFace || 'Microsoft YaHei',
    valAxisLabelFontFace: theme.fontFace || 'Microsoft YaHei',
    catAxisLabelColor: cleanHex(el.color || theme.color || 'FFFFFF'),
    valAxisLabelColor: cleanHex(el.color || theme.color || 'FFFFFF'),
    ...el.options,
  };
  slide.addChart(type, data, opts);
}

function buildPptx(deck, deckPath, outDir) {
  const baseDir = path.dirname(deckPath);
  const meta = deck.meta || {};
  const size = meta.slideSize || {};
  const W = Number(size.width || 13.333);
  const H = Number(size.height || 7.5);
  const theme = meta.theme || {};

  const pptx = new pptxgen();
  pptx.author = meta.author || 'AI Visual PPT Composer';
  pptx.subject = meta.title || 'AI Visual PPT';
  pptx.title = meta.title || 'AI Visual PPT';
  pptx.company = meta.company || '';
  pptx.lang = 'zh-CN';
  pptx.layout = 'LAYOUT_WIDE';
  pptx.defineLayout({ name: 'AVPC_WIDE', width: W, height: H });
  pptx.layout = 'AVPC_WIDE';
  pptx.theme = {
    headFontFace: theme.titleFontFace || theme.fontFace || 'Microsoft YaHei',
    bodyFontFace: theme.fontFace || 'Microsoft YaHei',
    lang: 'zh-CN',
  };

  for (const deckSlide of deck.slides || []) {
    const slide = pptx.addSlide();
    addBackground(slide, pptx, deckSlide, baseDir, W, H, theme);

    for (const el of deckSlide.elements || []) {
      try {
        if (el.type === 'text') addText(slide, el, theme);
        else if (el.type === 'shape') addShape(slide, pptx, el);
        else if (el.type === 'line') addLine(slide, el);
        else if (el.type === 'image') addImage(slide, el, baseDir);
        else if (el.type === 'svg') addSvg(slide, el, baseDir);
        else if (el.type === 'table') addTable(slide, el, theme);
        else if (el.type === 'chart') addChart(slide, pptx, el, theme);
      } catch (err) {
        console.warn(`WARN: failed element ${el.name || el.type}: ${err.message}`);
      }
    }

    if (deckSlide.notes) {
      slide.addNotes(String(deckSlide.notes));
    }
  }

  const pptxPath = path.join(outDir, 'deck.pptx');
  return pptx.writeFile({ fileName: pptxPath }).then(() => pptxPath);
}

function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function cssColor(hex, fallback = 'FFFFFF') {
  return `#${cleanHex(hex, fallback)}`;
}

function cssRgba(hex, opacity = 1, fallback = 'FFFFFF') {
  const c = cleanHex(hex, fallback);
  const r = parseInt(c.slice(0, 2), 16);
  const g = parseInt(c.slice(2, 4), 16);
  const b = parseInt(c.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

function elementStyle(el, W, H, previewW, previewH) {
  const px = (n, axis) => `${(Number(n) / (axis === 'x' ? W : H)) * (axis === 'x' ? previewW : previewH)}px`;
  const base = [
    'position:absolute',
    `left:${px(el.x, 'x')}`,
    `top:${px(el.y, 'y')}`,
    `width:${px(el.w, 'x')}`,
    `height:${px(el.h, 'y')}`,
    el.rotate ? `transform:rotate(${Number(el.rotate)}deg)` : '',
    el.opacity !== undefined ? `opacity:${Number(el.opacity)}` : '',
    'box-sizing:border-box',
  ].filter(Boolean);
  return base.join(';');
}

function renderTextHtml(el, theme, W, H, previewW, previewH) {
  const fontSizePx = Math.round((Number(el.fontSize || 16) / 72) * 96 * (previewW / 1280));
  const fill = el.fill ? normalizeFill(el.fill) : null;
  const line = el.line ? normalizeLine(el.line) : null;
  const styles = [
    elementStyle(el, W, H, previewW, previewH),
    `font-family:${esc(el.fontFace || theme.fontFace || 'Microsoft YaHei')}, sans-serif`,
    `font-size:${fontSizePx}px`,
    `font-weight:${el.bold ? 800 : 400}`,
    `font-style:${el.italic ? 'italic' : 'normal'}`,
    `color:${cssColor(el.color || theme.color || 'FFFFFF')}`,
    `text-align:${el.align || 'left'}`,
    `display:flex`,
    `align-items:${el.valign === 'mid' ? 'center' : el.valign === 'bottom' ? 'flex-end' : 'flex-start'}`,
    `justify-content:${el.align === 'center' ? 'center' : el.align === 'right' ? 'flex-end' : 'flex-start'}`,
    `padding:${Math.max(0, Number(el.margin === undefined ? 0.04 : el.margin) * 96)}px`,
    `line-height:${el.lineHeight || 1.18}`,
    `white-space:pre-wrap`,
    `overflow:hidden`,
    fill ? `background:${cssRgba(fill.color || 'FFFFFF', fill.transparency !== undefined ? 1 - fill.transparency / 100 : 1)}` : '',
    line ? `border:${line.width || 1}px solid ${cssRgba(line.color || 'FFFFFF', line.transparency !== undefined ? 1 - line.transparency / 100 : 1)}` : '',
    el.radius ? `border-radius:${Number(el.radius) * 96}px` : '',
    el.shadow ? `filter:drop-shadow(0 8px 16px rgba(0,0,0,.25))` : '',
  ].filter(Boolean).join(';');
  return `<div class="el text" data-name="${esc(el.name || '')}" style="${styles}"><span>${esc(el.text)}</span></div>`;
}

function renderShapeHtml(el, W, H, previewW, previewH) {
  const fill = normalizeFill(el.fill || { color: 'FFFFFF', transparency: 100 });
  const line = normalizeLine(el.line || { color: 'FFFFFF', transparency: 100 });
  const shapeName = String(el.shape || el.name || '').toLowerCase();
  const radius = el.radius || shapeName.includes('round') ? (Number(el.radius || 0.12) * 96) : 0;
  const styles = [
    elementStyle(el, W, H, previewW, previewH),
    `background:${cssRgba(fill?.color || 'FFFFFF', fill?.transparency !== undefined ? 1 - fill.transparency / 100 : 1)}`,
    `border:${line?.width || 0}px solid ${cssRgba(line?.color || 'FFFFFF', line?.transparency !== undefined ? 1 - line.transparency / 100 : 0)}`,
    `border-radius:${shapeName.includes('ellipse') || shapeName.includes('circle') ? '50%' : `${radius}px`}`,
    el.shadow ? `filter:drop-shadow(0 10px 22px rgba(0,0,0,.28))` : '',
  ].filter(Boolean).join(';');
  return `<div class="el shape" data-name="${esc(el.name || '')}" style="${styles}"></div>`;
}

function renderLineHtml(el, W, H, previewW, previewH) {
  const line = normalizeLine(el.line || { color: 'FFFFFF', width: 1 });
  const x1 = Number(el.x) / W * previewW;
  const y1 = Number(el.y) / H * previewH;
  const x2 = (Number(el.x) + Number(el.w)) / W * previewW;
  const y2 = (Number(el.y) + Number(el.h)) / H * previewH;
  const len = Math.hypot(x2 - x1, y2 - y1);
  const angle = Math.atan2(y2 - y1, x2 - x1) * 180 / Math.PI;
  const styles = [
    'position:absolute',
    `left:${x1}px`,
    `top:${y1}px`,
    `width:${len}px`,
    `height:0`,
    `border-top:${line.width || 1}px solid ${cssRgba(line.color || 'FFFFFF', line.transparency !== undefined ? 1 - line.transparency / 100 : 1)}`,
    `transform-origin:left top`,
    `transform:rotate(${angle}deg)`,
  ].join(';');
  return `<div class="el line" data-name="${esc(el.name || '')}" style="${styles}"></div>`;
}

function renderImageHtml(el, baseDir, W, H, previewW, previewH) {
  const p = resolveAsset(baseDir, el.path);
  if (!p || !fs.existsSync(p)) return '';
  const url = pathToFileURL(p).href;
  const styles = [
    elementStyle(el, W, H, previewW, previewH),
    'object-fit:cover',
  ].join(';');
  return `<img class="el image" data-name="${esc(el.name || '')}" src="${url}" style="${styles}" />`;
}

function renderSvgHtml(el, baseDir, W, H, previewW, previewH) {
  let inner = '';
  if (el.svg) inner = String(el.svg);
  else {
    const p = resolveAsset(baseDir, el.path);
    if (p && fs.existsSync(p)) inner = fs.readFileSync(p, 'utf8');
  }
  if (!inner) return '';
  const styles = elementStyle(el, W, H, previewW, previewH);
  return `<div class="el svg" data-name="${esc(el.name || '')}" style="${styles}">${inner}</div>`;
}

function renderTableHtml(el, theme, W, H, previewW, previewH) {
  const rows = Array.isArray(el.rows) ? el.rows : [];
  const styles = [
    elementStyle(el, W, H, previewW, previewH),
    `font-family:${esc(el.fontFace || theme.fontFace || 'Microsoft YaHei')}, sans-serif`,
    `font-size:${Math.round((Number(el.fontSize || 10) / 72) * 96 * (previewW / 1280))}px`,
    `color:${cssColor(el.color || theme.color || 'FFFFFF')}`,
  ].join(';');
  const body = rows.map(row => `<tr>${row.map(cell => `<td>${esc(cell)}</td>`).join('')}</tr>`).join('');
  return `<table class="el table" data-name="${esc(el.name || '')}" style="${styles}">${body}</table>`;
}

function buildPreviewHtml(deck, deckPath, outDir) {
  const baseDir = path.dirname(deckPath);
  const meta = deck.meta || {};
  const size = meta.slideSize || {};
  const W = Number(size.width || 13.333);
  const H = Number(size.height || 7.5);
  const previewW = Number(size.previewWidth || 1920);
  const previewH = Number(size.previewHeight || 1080);
  const theme = meta.theme || {};

  const slideHtml = (deck.slides || []).map((s, idx) => {
    const bg = s.background || {};
    const bgColor = cssColor(bg.color || theme.backgroundColor || '0B1020', '0B1020');
    let bgStyle = `background:${bgColor};`;
    if (bg.image) {
      const p = resolveAsset(baseDir, bg.image);
      if (p && fs.existsSync(p)) {
        bgStyle += `background-image:url('${pathToFileURL(p).href}');background-size:cover;background-position:center;`;
      }
    }
    const elements = (s.elements || []).map(el => {
      if (el.type === 'text') return renderTextHtml(el, theme, W, H, previewW, previewH);
      if (el.type === 'shape') return renderShapeHtml(el, W, H, previewW, previewH);
      if (el.type === 'line') return renderLineHtml(el, W, H, previewW, previewH);
      if (el.type === 'image') return renderImageHtml(el, baseDir, W, H, previewW, previewH);
      if (el.type === 'svg') return renderSvgHtml(el, baseDir, W, H, previewW, previewH);
      if (el.type === 'table') return renderTableHtml(el, theme, W, H, previewW, previewH);
      return '';
    }).join('\n');
    return `<section class="slide" id="slide-${idx + 1}" style="${bgStyle}">${elements}</section>`;
  }).join('\n');

  const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>${esc(meta.title || 'AI Visual PPT Preview')}</title>
<style>
  body{margin:0;background:#111;color:white;font-family:Microsoft YaHei,Arial,sans-serif;}
  .deck{display:flex;flex-direction:column;gap:32px;padding:32px;align-items:center;}
  .slide{position:relative;width:${previewW}px;height:${previewH}px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.45);}
  .el{box-sizing:border-box;}
  table{border-collapse:collapse;}
  td{border:1px solid rgba(255,255,255,.25);padding:8px;}
</style>
</head>
<body>
<div class="deck">
${slideHtml}
</div>
</body>
</html>`;

  const previewPath = path.join(outDir, 'deck_preview.html');
  fs.writeFileSync(previewPath, html, 'utf8');
  return { previewPath, previewW, previewH, slideCount: (deck.slides || []).length };
}

async function maybeScreenshots(previewPath, outDir, previewW, previewH, slideCount, noScreenshots) {
  if (noScreenshots) return false;
  let chromium;
  try {
    const playwright = await import('playwright');
    chromium = playwright.chromium;
  } catch (err) {
    console.warn('WARN: Playwright not installed; skipped PNG screenshots. Run `npm install` including devDependencies to enable screenshots.');
    return false;
  }
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: previewW, height: previewH } });
  await page.goto(pathToFileURL(previewPath).href);
  for (let i = 1; i <= slideCount; i++) {
    const selector = `#slide-${i}`;
    const el = page.locator(selector);
    await el.screenshot({ path: path.join(outDir, `slide-${String(i).padStart(2, '0')}.png`) });
  }
  await browser.close();
  return true;
}

async function main() {
  const args = process.argv.slice(2);
  const deckArg = args[0] || 'deck.json';
  const outArg = args[1] || 'output';
  const noScreenshots = args.includes('--no-screenshots');

  const deckPath = path.resolve(process.cwd(), deckArg);
  const outDir = path.resolve(process.cwd(), outArg);
  ensureDir(outDir);

  const deck = readJson(deckPath);
  const { previewPath, previewW, previewH, slideCount } = buildPreviewHtml(deck, deckPath, outDir);
  const pptxPath = await buildPptx(deck, deckPath, outDir);
  const didScreenshots = await maybeScreenshots(previewPath, outDir, previewW, previewH, slideCount, noScreenshots);

  console.log('DONE');
  console.log(`PPTX: ${pptxPath}`);
  console.log(`HTML preview: ${previewPath}`);
  if (didScreenshots) console.log(`PNG screenshots: ${path.join(outDir, 'slide-XX.png')}`);
}

main().catch(err => die(err.stack || err.message));
