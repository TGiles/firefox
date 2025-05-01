import figma, { html } from "@figma/code-connect/html";

// Desktop Components v3
figma.connect(
  "https://www.figma.com/design/3WoKOSGtaSjhUHKldHCXbc/Desktop-Components-3?node-id=442-2086&m=dev",
  {
    props: {
      label: figma.string("Label"),
    },
    example: props => html` <label is="moz-label">${props.label}</label>`,
  }
);

figma.connect(
  "https://www.figma.com/design/3WoKOSGtaSjhUHKldHCXbc/Desktop-Components-3?node-id=442-2086&m=dev",
  {
    props: {
      label: figma.string("Label"),
      supportLink: figma.string("Support link"),
    },
    variant: { "Show support link": true },
    example: props =>
      html` <label is="moz-label">${props.label}</label>
        <a is="moz-support-link">${props.supportLink}</a>`,
  }
);

// Desktop Components (deprecated)
figma.connect(
  "https://www.figma.com/design/2ruSnPauajQGprFy6K333u/%E2%9A%A0%EF%B8%8F-DEPRECATED---Desktop-Components?node-id=891-7665&m=dev",
  {
    props: {
      label: figma.textContent("✏️ Label"),
    },
    example: props => html` <label is="moz-label">${props.label}</label>`,
  }
);
