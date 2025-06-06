/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

"use strict";

const {
  Component,
} = require("resource://devtools/client/shared/vendor/react.mjs");
const dom = require("resource://devtools/client/shared/vendor/react-dom-factories.js");
const PropTypes = require("resource://devtools/client/shared/vendor/react-prop-types.mjs");
const {
  L10N,
} = require("resource://devtools/client/netmonitor/src/utils/l10n.js");
const {
  propertiesEqual,
} = require("resource://devtools/client/netmonitor/src/utils/request-utils.js");

const { div, span } = dom;

const UPDATED_STATUS_PROPS = [
  "earlyHintsStatus",
  "fromCache",
  "fromServiceWorker",
  "status",
  "statusText",
];

/**
 * Status code component
 * Displays HTTP status code icon
 * Used in RequestListColumnStatus and HeadersPanel
 */
class StatusCode extends Component {
  static get propTypes() {
    return {
      item: PropTypes.object.isRequired,
    };
  }

  shouldComponentUpdate(nextProps) {
    return !propertiesEqual(
      UPDATED_STATUS_PROPS,
      this.props.item,
      nextProps.item
    );
  }

  render() {
    const { item } = this.props;
    const {
      fromCache,
      fromServiceWorker,
      status,
      statusText,
      earlyHintsStatus,
      blockedReason,
    } = item;
    let code;

    if (status) {
      if (fromCache) {
        code = "cached";
      } else if (fromServiceWorker) {
        code = "service worker";
      } else {
        code = status;
      }
    }

    if (blockedReason) {
      return div(
        {
          className:
            "requests-list-status-code status-code status-code-blocked",
          title: L10N.getStr("networkMenu.blockedTooltip"),
        },
        div({
          className: "status-code-blocked-icon",
        })
      );
    }

    const statusInfo = [
      {
        status,
        statusText,
        code,
      },
    ];
    if (earlyHintsStatus) {
      statusInfo.unshift({
        status: earlyHintsStatus,
        statusText: "",
        code: earlyHintsStatus,
      });
    }

    // `data-code` refers to the status-code
    // `data-status-code` can be one of "cached", "service worker"
    // or the status-code itself
    // For example - if a resource is cached, `data-code` would be 200
    // and the `data-status-code` would be "cached"
    return div(
      {},
      statusInfo.map(info => {
        if (!info.status) {
          return null;
        }
        return span(
          {
            className: "requests-list-status-code status-code",
            onMouseOver({ target }) {
              if (info.status && info.statusText && !target.title) {
                target.title = getStatusTooltip(item);
              }
            },
            "data-status-code": info.code,
            "data-code": info.status,
          },
          info.status
        );
      })
    );
  }
}

function getStatusTooltip(item) {
  const { fromCache, fromServiceWorker, status, statusText } = item;
  let title;
  if (fromCache && fromServiceWorker) {
    title = L10N.getFormatStr(
      "netmonitor.status.tooltip.cachedworker",
      status,
      statusText
    );
  } else if (fromCache) {
    title = L10N.getFormatStr(
      "netmonitor.status.tooltip.cached",
      status,
      statusText
    );
  } else if (fromServiceWorker) {
    title = L10N.getFormatStr(
      "netmonitor.status.tooltip.worker",
      status,
      statusText
    );
  } else {
    title = L10N.getFormatStr(
      "netmonitor.status.tooltip.simple",
      status,
      statusText
    );
  }
  return title;
}

module.exports = StatusCode;
