// |reftest| shell-option(--enable-iterator-helpers) skip-if(!this.hasOwnProperty('Iterator')||!xulRuntime.shell) -- iterator-helpers is not enabled unconditionally, requires shell-options
// Copyright (C) 2024 Mozilla Corporation. All rights reserved.
// This code is governed by the BSD license found in the LICENSE file.

/*---
description: |
  The `length` property of Iterator.prototype.find.
info: |
  ES7 section 17: Unless otherwise specified, the length property of a built-in
  Function object has the attributes { [[Writable]]: false, [[Enumerable]]:
  false, [[Configurable]]: true }.

  Iterator is not enabled unconditionally
includes: [sm/non262.js, sm/non262-shell.js]
flags:
  - noStrict
features:
  - iterator-helpers
esid: pending
---*/
const propDesc = Reflect.getOwnPropertyDescriptor(Iterator.prototype.find, 'length');
assert.sameValue(propDesc.value, 1);
assert.sameValue(propDesc.writable, false);
assert.sameValue(propDesc.enumerable, false);
assert.sameValue(propDesc.configurable, true);


reportCompare(0, 0);
