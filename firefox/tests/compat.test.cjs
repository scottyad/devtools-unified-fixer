const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
(async () => {
  let listener, minted = 0;
  const stored = {};
  const context = vm.createContext({console, crypto: {randomUUID: () => {minted++; return 'test-uuid';}}, browser: {
    storage: {local: {get: async key => ({[key]: stored[key]}), set: async value => Object.assign(stored, value)}},
    runtime: {onMessage: {addListener: fn => { listener = fn; }}}, permissions: {},
    devtools: {network: {}, inspectedWindow: {eval: async expression => expression === 'reject' ? Promise.reject(new Error('Access denied')) : expression === 'exception' ? [undefined, {isException: true, value: 'bad expression'}] : [42, undefined]}, panels: {create: async () => ({onShown: {addListener() {}}})}},
  }});
  vm.runInContext(fs.readFileSync(path.join(root, 'src/firefox-compat.js'), 'utf8'), context);
  const api = context.assistantBrowser;
  const evaluate = expression => new Promise(resolve => api.devtools.inspectedWindow.eval(expression, (result, error) => resolve({result, error})));
  assert.equal((await evaluate('ok')).result, 42);
  assert.equal((await evaluate('exception')).error.isException, true);
  assert.match((await evaluate('reject')).error.value, /Access denied/);
  assert(await new Promise(resolve => api.devtools.panels.create('Fix Assistant', '', 'panel.html', resolve)));
  vm.runInContext(fs.readFileSync(path.join(root, 'src/background.js'), 'utf8'), context);
  const identity = () => new Promise(resolve => {assert.equal(listener({type:'getTrialIdentity'}, {}, resolve), true);});
  const keys = await Promise.all(Array.from({length:20}, identity));
  assert.equal(new Set(keys.map(x => x.key)).size, 1); assert.equal(minted, 1);
  console.log('PASS Firefox promise/callback results, exceptions, rejected evaluation, panel creation, and concurrent identity requests');
})().catch(error => {console.error(error);process.exitCode = 1;});
