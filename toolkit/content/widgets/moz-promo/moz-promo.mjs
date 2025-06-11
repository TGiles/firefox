/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { html, ifDefined } from "../vendor/lit.all.mjs";
import MozMessageBar from "../moz-message-bar/moz-message-bar.mjs";

/**
 * A promotional callout element
 *
 * @tagname moz-promo
 * @property {string} type - Can be either "default" or "fun"
 */
export default class MozPromo extends MozMessageBar {
  static properties = {
    type: { type: String },
    iconSrc: { type: String, reflect: true },
    iconAlignment: { type: String },
  };

  constructor() {
    super();
    this.type = "default";
    this.dismissable = false;
  }

  connectedCallback() {
    super.connectedCallback();
    this.removeAttribute("role");
  }

  iconTemplate() {
    // ? How do we handle the localization for this promo icons and illustrations?
    // ? Should they have alt text?
    if (this.iconSrc) {
      return html`
        <div class="icon-container">
          <img
            class="icon"
            src=${this.iconSrc}
          />
        </div>
      `;
    }
  }

  // TODO: simplify and clean up template logic
  contentTemplate() {
    if (this.iconAlignment == "end" || this.iconAlignment == "bottom") {
      return html`<div class="text-container">
            <div class="text-content">
              ${this.headingTemplate()}
              <div>
                <div
                  class="message"
                  data-l10n-id=${ifDefined(this.messageL10nId)}
                  data-l10n-args=${ifDefined(JSON.stringify(this.messageL10nArgs))}
                >
                  ${this.message}
                </div>
                <div class="actions">
                  <slot name="actions" @slotchange=${this.onActionSlotchange}></slot>
                </div>
                <span class="link">
                  <slot
                    name="support-link"
                    @slotchange=${this.onLinkSlotChange}
                  ></slot>
                </span>

              </div>
            </div>
            ${this.iconTemplate()}
          </div>`
    }
    return html`<div class="text-container">
              ${this.iconTemplate()}
              <div class="text-content">
              ${this.headingTemplate()}
              <div>
                <div
                  class="message"
                  data-l10n-id=${ifDefined(this.messageL10nId)}
                  data-l10n-args=${ifDefined(JSON.stringify(this.messageL10nArgs))}
                >
                  ${this.message}
                </div>
                <div class="actions">
                  <slot name="actions" @slotchange=${this.onActionSlotchange}></slot>
                </div>
                <span class="link">
                  <slot
                    name="support-link"
                    @slotchange=${this.onLinkSlotChange}
                  ></slot>
                </span>
              </div>
            </div>
          </div>`
  }

  render() {
    return html`
      <link
        rel="stylesheet"
        href="chrome://global/content/elements/moz-message-bar.css"
      />
      <link rel="stylesheet" href="chrome://global/content/elements/moz-promo.css" />
      <div class="container">
        <div class="content">
        ${this.contentTemplate()}
        </div>
        ${this.closeButtonTemplate()}
      </div>
    `;
  }
}
customElements.define("moz-promo", MozPromo);
