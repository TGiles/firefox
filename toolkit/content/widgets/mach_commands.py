# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import re
import xml.parsers.expat
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

from mach.decorators import Command, CommandArgument
from mach.util import UserError

FIXME_COMMENT = "// FIXME: replace with path to your reusable widget\n"
LICENSE_HEADER = """/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
"""

JS_HEADER = """{license}
import {{ html }} from "../vendor/lit.all.mjs";
import {{ MozLitElement }} from "../lit-utils.mjs";

/**
 * Component description goes here.
 *
 * @tagname {element_name}
 * @property {{string}} variant - Property description goes here
 */
export default class {class_name} extends MozLitElement {{
  static properties = {{
    variant: {{ type: String }},
  }};

  constructor() {{
    super();
    this.variant = "default";
  }}

  render() {{
    return html`
      <link rel="stylesheet" href="chrome://global/content/elements/{element_name}.css" />
      <div>Variant type: ${{this.variant}}</div>
    `;
  }}
}}
customElements.define("{element_name}", {class_name});
"""

STORY_HEADER = """{license}
{html_lit_import}
{fixme_comment}import "{element_path}";

export default {{
  title: "{story_prefix}/{story_name}",
  component: "{element_name}",
  argTypes: {{
    variant: {{
      options: ["default", "other"],
      control: {{ type: "select" }},
    }},
  }},
}};

const Template = ({{ variant }}) => html`
  <{element_name} .variant=${{variant}}></{element_name}>
`;

export const Default = Template.bind({{}});
Default.args = {{
  variant: "default",
}};
"""


def run_mach(command_context, cmd, **kwargs):
    return command_context._mach_context.commands.dispatch(
        cmd, command_context._mach_context, **kwargs
    )


def run_npm(command_context, args):
    return run_mach(
        command_context, "npm", args=[*args, "--prefix=browser/components/storybook"]
    )


def parse_acorn_elements(file_path):
    with open(file_path, newline="\n") as file:
        content = file.read()

    # Regex to extract elements from the acornElements array
    pattern = r'\[\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,?\s*\]'
    matches = re.findall(pattern, content, flags=re.DOTALL)

    # Filter out tags that don't start with "moz-"
    filtered = [match for match in matches if match[0].startswith("moz-")]

    return filtered  # List of (tag, path tuples)


def add_sorted_entry(elements, new_tag, new_path):
    if not any(tag == new_tag for tag, _ in elements):
        elements.append((new_tag, new_path))
        elements.sort(key=lambda x: x[0])
    return elements


def update_acorn_elements_in_file(file_path, updated_elements):
    with open(file_path, newline="\n") as file:
        lines = file.readlines()
    # Locate the start and end of the acornElements array
    start_id = None
    end_id = None
    for i, line in enumerate(lines):
        if "let acornElements = [" in line:
            start_id = i
        if start_id is not None and line.strip() == "];":
            end_id = i
        if start_id is not None and end_id is not None:
            break
    if start_id is None:
        raise ValueError("Could not find 'let acornElements = [' in customElements.js.")
    if end_id is None:
        raise ValueError(
            "Could not find a closing bracket to 'let acornElements = [' in customElements.js."
        )
    # Build updated array block
    array_lines = ["let acornElements = [\n"]
    for tag, path in updated_elements:
        array_lines.append(f'  ["{tag}", "{path}"],\n')
    array_lines.append("];\n")

    # Replace old array block with new one
    new_lines = lines[:start_id] + array_lines + lines[end_id + 1 :]

    with open(file_path, "w", newline="\n") as file:
        file.writelines(new_lines)


SUPPORTED_MARKUP_SUFFIXES = {".html", ".xhtml", ".xul"}
XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
INPUT_COMPONENTS = {
    "checkbox": "moz-checkbox",
    "color": "moz-input-color",
    "email": "moz-input-email",
    "number": "moz-input-number",
    "password": "moz-input-password",
    "search": "moz-input-search",
    "tel": "moz-input-tel",
    "text": "moz-input-text",
    "url": "moz-input-url",
}
ELEMENT_COMPONENTS = {
    "button": "moz-button",
    "textarea": "moz-textarea",
    "fieldset": "moz-fieldset",
}
RELEVANT_VALUE_DELIMITERS = ("&", "${", "{{", "<%")
LABELABLE_ELEMENTS = {
    "button",
    "input",
    "meter",
    "output",
    "progress",
    "select",
    "textarea",
}
LABEL_EXCLUDED_ATTRIBUTES = ("is", "control", "value", "crop", "href")

XUL_NAMESPACE = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul"
RADIO_GROUP_COMPONENT = "moz-radio-group"
RADIO_GROUP_ATTRIBUTES = {"value", "name", "orient"}
RADIO_ATTRIBUTES = {
    "label",
    "value",
    "disabled",
    "selected",
    "data-l10n-id",
    "data-l10n-args",
    "data-l10n-attrs",
}
RADIO_BOOLEAN_ATTRIBUTES = {"disabled", "selected"}
LABEL_RELEVANT_ATTRIBUTES = ("for", *LABEL_EXCLUDED_ATTRIBUTES)


@dataclass
class AcornElement:
    name: str
    attributes: list
    offset: int
    namespace: str | None = None
    local_name: str | None = None
    children: list = field(default_factory=list)


def _is_static_relevant_value(value):
    return (
        value is not None
        and value != ""
        and not any(delimiter in value for delimiter in RELEVANT_VALUE_DELIMITERS)
    )


def _coordinates(content, offset):
    return content.count("\n", 0, offset) + 1, offset - content.rfind("\n", 0, offset)


def _line_offsets(content):
    offsets = [0]
    for index, character in enumerate(content):
        if character == "\n":
            offsets.append(index + 1)
    return offsets


def _offset_from_position(line_offsets, line, column):
    return line_offsets[line - 1] + column


def _inert_ranges(content):
    ranges = []
    for opening, closing in (("{{", "}}"), ("<%", "%>"), ("<![CDATA[", "]]>")):
        start = 0
        while (start := content.find(opening, start)) != -1:
            end = content.find(closing, start + len(opening))
            if end == -1:
                ranges.append((start, len(content)))
                break
            ranges.append((start, end + len(closing)))
            start = end + len(closing)
    return ranges


def _is_inert(offset, ranges):
    return any(start <= offset < end for start, end in ranges)


class _HTMLAcornTokenizer(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=False)
        self.content = content
        self.line_offsets = _line_offsets(content)
        self.inert_ranges = _inert_ranges(content)
        self.search_offset = 0
        self.elements = []

    def handle_starttag(self, tag, attrs):
        source = self.get_starttag_text()
        approximate_offset = _offset_from_position(self.line_offsets, *self.getpos())
        offset = self.content.rfind(
            source, self.search_offset, approximate_offset + len(source) + 1
        )
        if offset == -1:
            offset = approximate_offset
        self.search_offset = offset + len(source)
        if "<" not in source[1:] and not _is_inert(offset, self.inert_ranges):
            self.elements.append(AcornElement(tag, attrs, offset, local_name=tag))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def _tokenize_html(content):
    tokenizer = _HTMLAcornTokenizer(content)
    tokenizer.feed(content)
    tokenizer.close()
    return tokenizer.elements


def _split_expanded_name(name):
    parts = name.split("|", 2)
    if len(parts) == 1:
        return None, name
    return parts[0], parts[1]


def _source_tag_name(content, offset):
    end = offset + 1
    while end < len(content) and (content[end].isalnum() or content[end] in "-_:."):
        end += 1
    return content[offset + 1 : end]


def _xml_byte_to_character_offsets(content):
    offsets = {}
    byte_offset = 0
    for character_offset in range(len(content) + 1):
        offsets[byte_offset] = character_offset
        if character_offset < len(content):
            byte_offset += len(content[character_offset].encode("utf-8"))
    return offsets


def _parse_xml(content):
    byte_offsets = _xml_byte_to_character_offsets(content)
    parser = xml.parsers.expat.ParserCreate(namespace_separator="|")
    parser.namespace_prefixes = True
    elements = []
    roots = []
    stack = []

    def start_element(name, attributes):
        offset = byte_offsets.get(parser.CurrentByteIndex)
        if offset is None:
            raise ValueError("XML parser returned a non-character boundary")
        namespace, local_name = _split_expanded_name(name)
        element = AcornElement(
            _source_tag_name(content, offset),
            [
                (_split_expanded_name(attribute_name), value)
                for attribute_name, value in attributes.items()
            ],
            offset,
            namespace,
            local_name,
        )
        if stack:
            stack[-1].children.append(element)
        else:
            roots.append(element)
        stack.append(element)
        elements.append((element, local_name))

    def character_data(data):
        if stack:
            stack[-1].children.append(("text", data))

    def comment(data):
        if stack:
            stack[-1].children.append(("comment", data))

    def processing_instruction(target, data):
        if stack:
            stack[-1].children.append(("processing-instruction", target, data))

    def start_cdata_section():
        if stack:
            stack[-1].children.append(("cdata-start",))

    def end_cdata_section():
        if stack:
            stack[-1].children.append(("cdata-end",))

    def end_element(name):
        stack.pop()

    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    parser.CharacterDataHandler = character_data
    parser.CommentHandler = comment
    parser.ProcessingInstructionHandler = processing_instruction
    parser.StartCdataSectionHandler = start_cdata_section
    parser.EndCdataSectionHandler = end_cdata_section
    try:
        parser.Parse(content, True)
    except (xml.parsers.expat.ExpatError, ValueError):
        return None
    return roots, elements


def _relevant_attributes(attributes, names, html_case_insensitive):
    values = {}
    for attribute_name, value in attributes:
        if isinstance(attribute_name, tuple):
            namespace, attribute_name = attribute_name
            if namespace is not None:
                continue
        key = attribute_name.lower() if html_case_insensitive else attribute_name
        if key not in names:
            continue
        if key in values:
            return None
        values[key] = value
    return values


def _xul_attributes(element, allowed_attributes):
    attributes = {}
    for attribute_name, value in element.attributes:
        namespace, local_name = attribute_name
        if namespace is not None or local_name not in allowed_attributes:
            return None
        if local_name in attributes or not _is_static_relevant_value(value):
            return None
        attributes[local_name] = value
    return attributes


def _is_xul_radio(element):
    return (
        isinstance(element, AcornElement)
        and element.namespace == XUL_NAMESPACE
        and element.local_name == "radio"
    )


def _radio_group_candidate(group):
    group_attributes = _xul_attributes(group, RADIO_GROUP_ATTRIBUTES)
    if group_attributes is None:
        return False
    if "orient" in group_attributes and group_attributes["orient"] not in {
        "vertical",
        "horizontal",
    }:
        return False

    radios = []
    for child in group.children:
        if _is_xul_radio(child):
            radios.append(child)
        elif isinstance(child, AcornElement):
            return False
        elif child[0] == "comment":
            continue
        elif child[0] == "text" and child[1].isspace():
            continue
        else:
            return False
    if not radios:
        return False

    selected_radio = None
    enabled_radios = []
    for radio in radios:
        attributes = _xul_attributes(radio, RADIO_ATTRIBUTES)
        if attributes is None:
            return False
        if "label" in attributes:
            if any(
                attribute in attributes
                for attribute in (
                    "data-l10n-id",
                    "data-l10n-args",
                    "data-l10n-attrs",
                )
            ):
                return False
        elif "data-l10n-id" not in attributes:
            return False
        elif (
            "data-l10n-attrs" in attributes and attributes["data-l10n-attrs"] != "label"
        ):
            return False
        for attribute in RADIO_BOOLEAN_ATTRIBUTES:
            if attribute in attributes and attributes[attribute] not in {
                "true",
                "false",
            }:
                return False
        if attributes.get("selected") == "true":
            if selected_radio is not None:
                return False
            selected_radio = radio
        if attributes.get("disabled") != "true":
            enabled_radios.append(radio)

    if "value" not in group_attributes:
        return True
    value = group_attributes["value"]
    matching_radios = [
        radio
        for radio in enabled_radios
        if (
            "value" in _xul_attributes(radio, RADIO_ATTRIBUTES)
            and _xul_attributes(radio, RADIO_ATTRIBUTES)["value"] == value
        )
    ]
    return len(matching_radios) == 1 and (
        selected_radio is None or selected_radio is matching_radios[0]
    )


def _candidate_elements(content, suffix):
    if suffix == ".html":
        return _tokenize_html(content), True
    parsed = _parse_xml(content)
    if parsed is None:
        return None, False
    return (
        [
            element
            for element, local_name in parsed[1]
            if (
                element.namespace == XHTML_NAMESPACE
                and local_name in (*LABELABLE_ELEMENTS, "label", "fieldset")
            )
            or (
                suffix == ".xul"
                and element.namespace == XUL_NAMESPACE
                and local_name == "radiogroup"
            )
        ],
        False,
    )


def find_acorn_candidates(directory):
    directory = Path(directory)
    if not directory.is_dir():
        raise UserError(f"Not a directory: {directory}")

    candidates = []
    files = sorted(
        (
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_MARKUP_SUFFIXES
        ),
        key=lambda path: path.relative_to(directory).as_posix(),
    )
    for path in files:
        relative_path = path.relative_to(directory).as_posix()
        with path.open(encoding="utf-8", errors="replace", newline="") as markup_file:
            content = markup_file.read()
        suffix = path.suffix.lower()
        elements, html_case_insensitive = _candidate_elements(content, suffix)
        if elements is None:
            continue

        target_ids = {}
        for element in elements:
            element_name = (
                element.name.lower() if html_case_insensitive else element.local_name
            )
            if element_name not in LABELABLE_ELEMENTS:
                continue
            relevant = _relevant_attributes(
                element.attributes, {"id", "type"}, html_case_insensitive
            )
            if relevant is None or "id" not in relevant:
                continue
            target_id = relevant["id"]
            if not _is_static_relevant_value(target_id):
                continue
            if element_name == "input" and "type" in relevant:
                if not _is_static_relevant_value(relevant["type"]):
                    continue
                if relevant["type"].lower() == "hidden":
                    continue
            target_ids.setdefault(target_id, []).append(element)

        for element in elements:
            element_name = (
                element.name.lower() if html_case_insensitive else element.local_name
            )
            if element_name != "label":
                continue
            relevant = _relevant_attributes(
                element.attributes, LABEL_RELEVANT_ATTRIBUTES, html_case_insensitive
            )
            if (
                relevant is None
                or "for" not in relevant
                or not _is_static_relevant_value(relevant["for"])
                or any(attribute in relevant for attribute in LABEL_EXCLUDED_ATTRIBUTES)
                or len(target_ids.get(relevant["for"], [])) != 1
            ):
                continue
            line, column = _coordinates(content, element.offset)
            candidates.append((
                relative_path,
                element.offset,
                'label is="moz-label"',
                line,
                column,
                element.name.lower(),
            ))

        for element in elements:
            if (
                element.namespace != XUL_NAMESPACE
                or element.local_name != "radiogroup"
                or not _radio_group_candidate(element)
            ):
                continue
            line, column = _coordinates(content, element.offset)
            candidates.append((
                relative_path,
                element.offset,
                RADIO_GROUP_COMPONENT,
                line,
                column,
                element.name.lower(),
            ))

        for element in elements:
            element_name = (
                element.name.lower() if html_case_insensitive else element.local_name
            )
            if element_name == "input":
                relevant = _relevant_attributes(
                    element.attributes, {"type"}, html_case_insensitive
                )
                if relevant is None or "type" not in relevant:
                    continue
                input_type = relevant["type"]
                if not _is_static_relevant_value(input_type):
                    continue
                component = INPUT_COMPONENTS.get(input_type.lower())
            else:
                component = ELEMENT_COMPONENTS.get(element_name)
            if not component:
                continue
            line, column = _coordinates(content, element.offset)
            candidates.append((
                relative_path,
                element.offset,
                component,
                line,
                column,
                element.name.lower(),
            ))
    return sorted(candidates, key=lambda candidate: candidate[:3])


@Command(
    "find-acorn-candidates",
    category="misc",
    description="Find markup elements that are candidates for Acorn components.",
)
@CommandArgument(
    "directory",
    type=Path,
    help="Directory containing .html, .xhtml, or .xul files to inspect.",
)
def find_acorn_candidates_command(command_context, directory):
    for relative_path, _, component, line, column, source_tag in find_acorn_candidates(
        directory
    ):
        print(
            f"{relative_path}:{line}:{column}: candidate <{source_tag}> "
            f"for <{component}>"
        )


@Command(
    "addwidget",
    category="misc",
    description="Scaffold a front-end component.",
)
@CommandArgument(
    "names",
    nargs="+",
    help="Component names to create in kebab-case, eg. my-card.",
)
def addwidget(command_context, names):
    story_prefix = "UI Widgets"
    html_lit_import = 'import { html } from "../vendor/lit.all.mjs";'
    for name in names:
        component_dir = f"toolkit/content/widgets/{name}"

        try:
            os.mkdir(component_dir)
        except FileExistsError:
            pass

        with open(f"{component_dir}/{name}.mjs", "w", newline="\n") as f:
            class_name = "".join(p.capitalize() for p in name.split("-"))
            f.write(
                JS_HEADER.format(
                    license=LICENSE_HEADER,
                    element_name=name,
                    class_name=class_name,
                )
            )

        with open(f"{component_dir}/{name}.css", "w", newline="\n") as f:
            f.write(LICENSE_HEADER)

        test_name = name.replace("-", "_")
        test_path = f"toolkit/content/tests/widgets/test_{test_name}.html"
        jar_path = "toolkit/content/jar.mn"
        jar_lines = None
        with open(jar_path) as f:
            jar_lines = f.readlines()
        elements_startswith = "   content/global/elements/"
        new_css_line = (
            f"{elements_startswith}{name}.css    (widgets/{name}/{name}.css)\n"
        )
        new_js_line = (
            f"{elements_startswith}{name}.mjs    (widgets/{name}/{name}.mjs)\n"
        )
        new_jar_lines = []
        found_elements_section = False
        added_widget = False
        for line in jar_lines:
            if line.startswith(elements_startswith):
                found_elements_section = True
            if found_elements_section and not added_widget and line > new_css_line:
                added_widget = True
                new_jar_lines.append(new_css_line)
                new_jar_lines.append(new_js_line)
            new_jar_lines.append(line)

        with open(jar_path, "w", newline="\n") as f:
            f.write("".join(new_jar_lines))

        custom_elements = parse_acorn_elements("toolkit/content/customElements.js")
        custom_elements = add_sorted_entry(
            custom_elements, f"{name}", f"chrome://global/content/elements/{name}.mjs"
        )
        update_acorn_elements_in_file(
            "toolkit/content/customElements.js", custom_elements
        )

        # Run prettier to fix the formatting generated by adding a new
        # entry to the Acorn elements array
        run_mach(
            command_context, "lint", argv=["--fix", "toolkit/content/customElements.js"]
        )

        story_path = f"{component_dir}/{name}.stories.mjs"
        element_path = f"./{name}.mjs"
        with open(story_path, "w", newline="\n") as f:
            story_name = " ".join(
                name for name in re.findall(r"[A-Z][a-z]+", class_name) if name != "Moz"
            )
            f.write(
                STORY_HEADER.format(
                    license=LICENSE_HEADER,
                    element_name=name,
                    story_name=story_name,
                    story_prefix=story_prefix,
                    fixme_comment="",
                    element_path=element_path,
                    html_lit_import=html_lit_import,
                )
            )

        run_mach(
            command_context, "addtest", argv=[test_path, "--suite", "mochitest-chrome"]
        )


@Command(
    "addstory",
    category="misc",
    description="Scaffold a front-end Storybook story.",
)
@CommandArgument(
    "name",
    help="Story to create in kebab-case, eg. my-card.",
)
@CommandArgument(
    "project_name",
    type=str,
    help='Name of the project or team for the new component to keep stories organized. Eg. "Credential Management"',
)
@CommandArgument(
    "--path",
    help="Path to the widget source, eg. /browser/components/my-module.mjs or chrome://browser/content/my-module.mjs",
)
def addstory(command_context, name, project_name, path):
    html_lit_import = 'import { html } from "lit.all.mjs";'
    story_path = f"browser/components/storybook/stories/{name}.stories.mjs"
    project_name = project_name.split()
    project_name = " ".join(p.capitalize() for p in project_name)
    story_prefix = f"Domain-specific UI Widgets/{project_name}"
    with open(story_path, "w", newline="\n") as f:
        print(f"Creating new story {name} in {story_path}")
        story_name = " ".join(p.capitalize() for p in name.split("-"))
        f.write(
            STORY_HEADER.format(
                license=LICENSE_HEADER,
                element_name=name,
                story_name=story_name,
                element_path=path,
                fixme_comment="" if path else FIXME_COMMENT,
                project_name=project_name,
                story_prefix=story_prefix,
                html_lit_import=html_lit_import,
            )
        )


@Command(
    "buildtokens",
    category="misc",
    description="Build the design tokens CSS files",
)
@CommandArgument(
    "--import-figma",
    action="store_true",
    dest="import_figma",
    help="Import Nova design tokens from the committed figma-variables-all.json "
    "(no network or token needed), then build. Add --remote to fetch a fresh "
    "export from Figma first.",
)
@CommandArgument(
    "--remote",
    action="store_true",
    help="With --import-figma, fetch a fresh export from the Figma API before "
    "importing. Requires a valid FIGMA_ACCESS_TOKEN in your environment.",
)
@CommandArgument(
    "--fetch-figma",
    action="store_true",
    help="Alias for `--import-figma --remote`.",
)
@CommandArgument(
    "--match",
    action="append",
    dest="match",
    default=None,
    metavar="SUBSTRING",
    help="Only import changed tokens whose path contains SUBSTRING. May be "
    "passed multiple times. Requires --import-figma.",
)
@CommandArgument(
    "--all",
    action="store_true",
    dest="import_all",
    help="Import every changed token without prompting for a selection. "
    "Requires --import-figma.",
)
def buildtokens(command_context, import_figma, remote, fetch_figma, match, import_all):
    # `--fetch-figma` is an alias for `--import-figma --remote`.
    do_import = import_figma or fetch_figma
    do_remote = remote or fetch_figma
    if (match or import_all or remote) and not do_import:
        raise UserError("--match, --all, and --remote require --import-figma.")
    if run_mach(
        command_context,
        "npm",
        args=["ls", "--prefix=toolkit/themes/shared/design-system"],
    ):
        run_mach(
            command_context,
            "npm",
            args=["ci", "--prefix=toolkit/themes/shared/design-system"],
        )
    if do_import:
        fetch_args = [
            "run",
            "import-figma-nova",
            "--prefix=toolkit/themes/shared/design-system",
            "--",
        ]
        if do_remote:
            fetch_args.append("--remote")
        for substring in match or []:
            fetch_args.append(f"--match={substring}")
        if import_all:
            fetch_args.append("--all")
        failed = run_mach(command_context, "npm", args=fetch_args)
        if failed:
            if do_remote:
                raise UserError(
                    "Failed to access Figma API, is FIGMA_ACCESS_TOKEN set and valid?"
                )
            raise UserError("Failed to import tokens from figma-variables-all.json.")
    run_mach(
        command_context,
        "npm",
        args=[
            "run",
            "build-figma-nova",
            "--prefix=toolkit/themes/shared/design-system",
        ],
    )
    run_mach(
        command_context,
        "npm",
        args=["run", "build", "--prefix=toolkit/themes/shared/design-system"],
    )
    run_mach(command_context, "newtab", subcommand="install")
    run_mach(command_context, "newtab", subcommand="bundle")
