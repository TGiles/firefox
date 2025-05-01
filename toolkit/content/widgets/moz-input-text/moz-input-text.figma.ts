import figma, { html } from "@figma/code-connect/html";

// Desktop Components v3 (newest)

/* 
Variants do not work as expected with the following error message:
Validation failed for undefined (https://www.figma.com/design/3WoKOSGtaSjhUHKldHCXbc/Desktop-Compone
nts-3?node-id=33-302&m=dev): 
The property "Text Input Show icon" does not exist on the Figma component
*/
figma.connect(
  "https://www.figma.com/design/3WoKOSGtaSjhUHKldHCXbc/Desktop-Components-3?node-id=33-302&m=dev",
  {
    props: {
      labelProps: figma.nestedProps("Label", {
        description: figma.boolean("Show description", {
          true: figma.string("Description"),
        }),
        label: figma.string("Label"),
        supportPage: figma.boolean("Show support link", {
          true: "sumo-slug",
        }),
        iconSrc: figma.boolean("Show icon", {
          true: "chrome://example.svg",
        }),
      }),
      textInputProps: figma.nestedProps("Text Input", {
        text: figma.string("Text"),
        showIcon: figma.boolean("Show icon"),
        showAction: figma.boolean("Show action"),
        disabled: figma.enum("State", { Disabled: true }),
      }),
    },
    variant: { "Text Input Show icon": true, "Text Input Show action": true },
    example: props =>
      html`<moz-input-search
        disabled=${props.textInputProps.disabled}
        description=${props.labelProps.description}
        label=${props.labelProps.label}
        support-page=${props.labelProps.supportPage}
      ></moz-input-search>`,
  }
);

/*
Variants do not work as expected with the following error message:
Validation failed for undefined (https://www.figma.com/design/3WoKOSGtaSjhUHKldHCXbc/Desktop-Compone
nts-3?node-id=33-302&m=dev): 
The property "textInputProps.showIcon" does not exist on the Figma component
*/

figma.connect(
  "https://www.figma.com/design/3WoKOSGtaSjhUHKldHCXbc/Desktop-Components-3?node-id=33-302&m=dev",
  {
    props: {
      labelProps: figma.nestedProps("Label", {
        description: figma.boolean("Show description", {
          true: figma.string("Description"),
        }),
        label: figma.string("Label"),
        supportPage: figma.boolean("Show support link", {
          true: "sumo-slug",
        }),
        iconSrc: figma.boolean("Show icon", {
          true: "chrome://example.svg",
        }),
      }),
      textInputProps: figma.nestedProps("Text Input", {
        text: figma.string("Text"),
        showIcon: figma.boolean("Show icon"),
        showAction: figma.boolean("Show action"),
        disabled: figma.enum("State", { Disabled: true }),
      }),
    },
    variant: {
      "textInputProps.showIcon": false,
      "textInputProps.showAction": false,
    },
    example: props =>
      html`<moz-input-text
        disabled=${props.textInputProps.disabled}
        description=${props.labelProps.description}
        label=${props.labelProps.label}
        support-page=${props.labelProps.supportPage}
      ></moz-input-text>`,
  }
);

// Desktop Components v3 base element, no label
/*
Variants work as expected but we are unable to pass in the label props because
no label exists in this component
*/
figma.connect(
  "https://www.figma.com/design/3WoKOSGtaSjhUHKldHCXbc/Desktop-Components-3?node-id=33-125&t=7etC85GJjsyfMHnn-4",
  {
    props: {
      showIcon: figma.boolean("Show icon"),
      text: figma.string("Text"),
      showAction: figma.boolean("Show action"),
      icon: figma.instance("Icon"),
      disabled: figma.enum("State", { Disabled: true }),
    },
    variant: {"Show icon": true, "Show action": true },
    example: props =>
      html`<moz-input-search
        disabled=${props.disabled}
      ></moz-input-search>`,
  },
)

/*
Variants work as expected but we are unable to pass in the label props because
no label exists in this component
*/
figma.connect(
  "https://www.figma.com/design/3WoKOSGtaSjhUHKldHCXbc/Desktop-Components-3?node-id=33-125&t=7etC85GJjsyfMHnn-4",
  {
    props: {
      showIcon: figma.boolean("Show icon"),
      text: figma.string("Text"),
      showAction: figma.boolean("Show action"),
      icon: figma.instance("Icon"),
      disabled: figma.enum("State", { Disabled: true }),
    },
    variant: {"Show icon": false, "Show action": false },
    example: props =>
      html`<moz-input-text
        disabled=${props.disabled}
      ></moz-input-text>`,
  },
)

// Desktop Components (deprecated)
figma.connect(
  "https://www.figma.com/design/2ruSnPauajQGprFy6K333u/%E2%9A%A0%EF%B8%8F-DEPRECATED---Desktop-Components?node-id=800-7517&m=dev",
  {
    props: {
      disabled: figma.enum("State", { Disabled: true }),
      value: figma.textContent("✏️ Input text"),
    },
    variant: { Type: "Default" },
    example: props =>
      html`<moz-input-text
        disabled=${props.disabled}
        value=${props.value}
      ></moz-input-text>`,
  }
);
figma.connect(
  "https://www.figma.com/design/2ruSnPauajQGprFy6K333u/%E2%9A%A0%EF%B8%8F-DEPRECATED---Desktop-Components?node-id=800-7517&m=dev",
  {
    props: {
      disabled: figma.enum("State", { Disabled: true }),
      value: figma.textContent("✏️ Input text"),
    },
    variant: { Type: "Search" },
    example: props =>
      html`<moz-input-search
        disabled=${props.disabled}
        value=${props.value}
      ></moz-input-search>`,
  }
);
