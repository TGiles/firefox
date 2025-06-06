/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

"use strict";

/**
 * Bug 1774005 - Generic window.InstallTrigger shim
 *
 * This interventions shims window.InstallTrigger to a string, which evaluates
 * as `true` in web developers browser sniffing code. This intervention will
 * be applied to multiple domains, see bug 1774005 for more information.
 */

/* globals exportFunction */

console.info(
  "The InstallTrigger has been shimmed for compatibility reasons. See https://bugzilla.mozilla.org/show_bug.cgi?id=1774005 for details."
);

window.wrappedJSObject.InstallTrigger =
  "This property has been shimmed for Web Compatibility reasons.";
