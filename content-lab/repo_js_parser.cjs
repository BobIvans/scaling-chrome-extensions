/* Trusted syntax-only adapter. Source arrives as data; no project module/config loads. */
'use strict';
const parser = require('./js-parser/babel-parser.cjs');
const { createHash } = require('node:crypto');
const { readSync } = require('node:fs');

const OPTIONS = Object.freeze({ sourceType: 'unambiguous', errorRecovery: false,
  attachComment: false, ranges: false, tokens: false, createImportExpressions: true });

function byteMap(text) {
  const map = new Uint32Array(text.length + 1);
  let bytes = 0;
  for (let i = 0; i < text.length; i++) {
    map[i] = bytes;
    const point = text.codePointAt(i);
    if (point > 0xffff) { map[++i] = 0xffffffff; bytes += 4; }
    else bytes += point <= 0x7f ? 1 : point <= 0x7ff ? 2 : 3;
    map[i + 1] = bytes;
  }
  return map;
}

function extract(raw, extension, outputLimit) {
  // ignoreBOM means preserve U+FEFF, so all AST positions include the original BOM.
  const text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(raw);
  const plugins = [];
  if (['.ts', '.tsx', '.mts', '.cts'].includes(extension))
    plugins.push(['typescript', { dts: false, disallowAmbiguousJSXLike: ['.mts', '.cts'].includes(extension) }]);
  if (['.jsx', '.tsx'].includes(extension)) plugins.push('jsx');
  let ast;
  try { ast = parser.parse(text, { ...OPTIONS, plugins }); }
  catch { return { status: 'PARSER_FAILED', reason: 'PARSER_DIAGNOSTIC', refs: [], symbols: [] }; }
  if (ast.errors?.length) return { status: 'PARSER_FAILED', reason: 'PARSER_DIAGNOSTIC', refs: [], symbols: [] };
  const offsets = byteMap(text);
  const refs = [], symbols = [], exportSpans = new WeakMap();
  let estimatedBytes = 256;
  function span(node) {
    const a = offsets[node.start], b = offsets[node.end];
    if (!Number.isInteger(node.start) || !Number.isInteger(node.end) ||
        a === undefined || b === undefined || a === 0xffffffff || b === 0xffffffff || !(a < b && b <= raw.length))
      throw Error('PARSER_INVALID_RANGE');
    return { byte_start: a, byte_end: b, range_sha256: createHash('sha256').update(raw.subarray(a, b)).digest('hex') };
  }
  function keep(array, record) {
    estimatedBytes += Buffer.byteLength(JSON.stringify(record), 'utf8') + 1;
    if (estimatedBytes > outputLimit - 256) throw Error('PARSER_OUTPUT_BUDGET');
    array.push(record);
  }
  function ref(form, node, kind) {
    if (!node) throw Error('PARSER_INVALID_REFERENCE');
    keep(refs, { syntax_form: form, specifier: node.type === 'StringLiteral' ? node.value : null,
      dependency_kind: kind, ...span(node) });
  }
  const stack = [ast.program];
  while (stack.length) {
    const node = stack.pop();
    switch (node.type) {
      case 'ImportDeclaration': {
        const only = node.importKind === 'type' || (node.specifiers.length > 0 &&
          node.specifiers.every(s => s.importKind === 'type'));
        ref(node.importKind === 'type' ? 'TS_IMPORT_TYPE' : node.specifiers.length ? 'ESM_IMPORT' : 'ESM_SIDE_EFFECT',
          node.source, only ? 'TYPE_ONLY' : 'VALUE_OR_MIXED');
        break;
      }
      case 'ExportNamedDeclaration':
      case 'ExportAllDeclaration':
        if (node.declaration) exportSpans.set(node.declaration, node);
        if (node.source) {
          const only = node.exportKind === 'type' || (node.specifiers?.length > 0 &&
            node.specifiers.every(s => s.exportKind === 'type'));
          ref(node.exportKind === 'type' ? 'TS_EXPORT_TYPE' : 'ESM_REEXPORT', node.source,
            only ? 'TYPE_ONLY' : 'VALUE_OR_MIXED');
        }
        break;
      case 'ExportDefaultDeclaration':
        if (node.declaration) exportSpans.set(node.declaration, node);
        break;
      case 'TSImportEqualsDeclaration':
        if (node.moduleReference.type === 'TSExternalModuleReference')
          ref('IMPORT_EQUALS', node.moduleReference.expression, 'DYNAMIC_OR_UNKNOWN');
        break;
      case 'TSImportType':
        ref('TS_IMPORT_TYPE', node.argument, 'TYPE_ONLY');
        break;
      case 'ImportExpression':
        ref(node.source.type === 'StringLiteral' ? 'DYNAMIC_IMPORT' : 'COMPUTED_IMPORT',
          node.source, 'DYNAMIC_OR_UNKNOWN');
        break;
      case 'CallExpression':
      case 'OptionalCallExpression':
        if (node.callee.type === 'Identifier' && node.callee.name === 'require')
          ref('COMMONJS_REQUIRE', node.arguments.length === 1 ? node.arguments[0] : node, 'DYNAMIC_OR_UNKNOWN');
        break;
      case 'FunctionDeclaration':
      case 'ClassDeclaration':
        // Anonymous declaration names express uncertainty, never semantic ownership.
        keep(symbols, { name: node.id?.name || '<anonymous>',
          kind: node.type === 'FunctionDeclaration' ? 'FUNCTION_DECLARATION' : 'CLASS_DECLARATION',
          ...span(exportSpans.get(node) || node) });
        break;
    }
    for (const [key, value] of Object.entries(node)) {
      if (['loc', 'extra', 'comments', 'leadingComments', 'trailingComments', 'innerComments', 'errors'].includes(key)) continue;
      if (Array.isArray(value)) {
        for (let i = value.length - 1; i >= 0; i--)
          if (value[i] && typeof value[i].type === 'string') stack.push(value[i]);
      } else if (value && typeof value === 'object' && typeof value.type === 'string') stack.push(value);
    }
  }
  const order = (a, b) => a.byte_start - b.byte_start || a.byte_end - b.byte_end;
  refs.sort(order); symbols.sort(order);
  return { status: 'AST_SYNTAX_ONLY', reason: null, refs, symbols };
}

function readExact(length) {
  const data = Buffer.alloc(length);
  let read = 0;
  while (read < length) {
    const count = readSync(0, data, read, length - read, null);
    if (!count) throw Error('PARSER_INPUT_TRUNCATED');
    read += count;
  }
  return data;
}

if (require.main === module) {
  const inputLimit = Number(process.argv[2]), outputLimit = Number(process.argv[3]);
  let result;
  try {
    const length = readExact(4).readUInt32LE();
    if (!Number.isSafeInteger(inputLimit) || !Number.isSafeInteger(outputLimit) || length > inputLimit)
      throw Error('PARSER_INPUT_BUDGET');
    const frame = JSON.parse(readExact(length).toString('utf8'));
    const raw = Buffer.from(frame.raw_base64, 'base64');
    result = extract(raw, frame.extension, outputLimit);
  } catch (error) {
    result = { status: 'PARSER_FAILED', reason: ['PARSER_OUTPUT_BUDGET', 'PARSER_INPUT_BUDGET'].includes(error.message)
      ? error.message : 'PARSER_ADAPTER_FAILED', refs: [], symbols: [] };
  }
  result.peak_rss_bytes = Math.max(process.memoryUsage().rss, process.resourceUsage().maxRSS * 1024);
  result.parser_version = parser.parse ? require('./js-parser/package.json').version : null;
  let raw = Buffer.from(JSON.stringify(result), 'utf8');
  if (raw.length > outputLimit) raw = Buffer.from(JSON.stringify({ status: 'PARSER_FAILED',
    reason: 'PARSER_OUTPUT_BUDGET', refs: [], symbols: [], parser_version: '7.28.5', peak_rss_bytes: result.peak_rss_bytes }));
  const header = Buffer.alloc(4); header.writeUInt32LE(raw.length);
  process.stdout.write(header); process.stdout.write(raw);
}

module.exports = { extract, byteMap, OPTIONS };
