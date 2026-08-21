# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import re
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
LABEL_RELEVANT_ATTRIBUTES = ("for", *LABEL_EXCLUDED_ATTRIBUTES)


def _is_static_relevant_value(value):
    return (
        value is not None
        and value != ""
        and not any(delimiter in value for delimiter in RELEVANT_VALUE_DELIMITERS)
    )


def _parse_start_tag(content, offset):
    """Return a start tag's spelling and attributes, or None if malformed."""
    length = len(content)
    position = offset + 1
    name_start = position
    while position < length and (
        content[position].isalnum() or content[position] in "-_:"
    ):
        position += 1
    if position == name_start:
        return None

    tag_name = content[name_start:position]
    attributes = []
    while position < length:
        while position < length and content[position].isspace():
            position += 1
        if content.startswith("/>", position):
            return tag_name, attributes, position + 2
        if position < length and content[position] == ">":
            return tag_name, attributes, position + 1
        if position >= length or content[position] in "<>":
            return None

        attribute_start = position
        while position < length and (
            content[position].isalnum() or content[position] in "-_:."
        ):
            position += 1
        if position == attribute_start:
            return None
        attribute_name = content[attribute_start:position]

        while position < length and content[position].isspace():
            position += 1
        value = None
        if position < length and content[position] == "=":
            position += 1
            while position < length and content[position].isspace():
                position += 1
            if position >= length:
                return None
            if content[position] in "\"'":
                quote = content[position]
                position += 1
                value_start = position
                while position < length and content[position] != quote:
                    if content[position] == "<":
                        return None
                    position += 1
                if position >= length:
                    return None
                value = content[value_start:position]
                position += 1
            else:
                value_start = position
                while (
                    position < length
                    and not content[position].isspace()
                    and content[position] not in "'\"=<>`"
                ):
                    position += 1
                if position == value_start:
                    return None
                value = content[value_start:position]
        attributes.append((attribute_name, value))
    return None


def _iter_start_tags(content):
    """Yield lexical start tags outside comments, raw-text, and template regions."""
    offset = 0
    raw_text_tag = None
    while offset < len(content):
        if content.startswith("<!--", offset):
            end = content.find("-->", offset + 4)
            offset = len(content) if end == -1 else end + 3
            continue
        if content.startswith("<%", offset) or content.startswith("{{", offset):
            closing = "%>" if content.startswith("<%", offset) else "}}"
            end = content.find(closing, offset + len(closing))
            offset = len(content) if end == -1 else end + len(closing)
            continue
        if content[offset] != "<":
            offset += 1
            continue
        if content.startswith("</", offset):
            close = content.find(">", offset + 2)
            if close == -1:
                return
            name = content[offset + 2 : close].strip().lower()
            if name == raw_text_tag:
                raw_text_tag = None
            offset = close + 1
            continue
        if content.startswith("<!", offset) or content.startswith("<?", offset):
            close = content.find(">", offset + 2)
            offset = len(content) if close == -1 else close + 1
            continue
        parsed = _parse_start_tag(content, offset)
        if not parsed:
            offset += 1
            continue
        tag_name, attributes, end = parsed
        lower_name = tag_name.lower()
        if raw_text_tag is None:
            yield offset, tag_name, attributes
            if lower_name in {"script", "style"}:
                raw_text_tag = lower_name
        offset = end


def _relevant_attributes(attributes, names, html_case_insensitive):
    values = {}
    for attribute_name, value in attributes:
        key = attribute_name.lower() if html_case_insensitive else attribute_name
        if key not in names:
            continue
        if key in values:
            return None
        values[key] = value
    return values


def _is_html_tag(tag_name, element_name, suffix):
    if suffix == ".html":
        return tag_name.lower() == element_name
    return tag_name == f"html:{element_name}"


def _coordinates(content, offset):
    return content.count("\n", 0, offset) + 1, offset - content.rfind("\n", 0, offset)


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
        content = path.read_text(encoding="utf-8", errors="replace")
        suffix = path.suffix.lower()
        html_case_insensitive = suffix != ".xhtml"
        tags = list(_iter_start_tags(content))
        target_ids = {}
        for offset, tag_name, attributes in tags:
            element_name = tag_name.lower() if html_case_insensitive else tag_name
            if not any(
                _is_html_tag(tag_name, labelable_element, suffix)
                for labelable_element in LABELABLE_ELEMENTS
            ):
                continue
            relevant = _relevant_attributes(
                attributes, {"id", "type"}, html_case_insensitive
            )
            if relevant is None or "id" not in relevant:
                continue
            target_id = relevant["id"]
            if not _is_static_relevant_value(target_id):
                continue
            if element_name.removeprefix("html:") == "input" and "type" in relevant:
                if not _is_static_relevant_value(relevant["type"]):
                    continue
                if relevant["type"].lower() == "hidden":
                    continue
            target_ids.setdefault(target_id, []).append((offset, tag_name))

        for offset, tag_name, attributes in tags:
            if not _is_html_tag(tag_name, "label", suffix):
                continue
            relevant = _relevant_attributes(
                attributes, LABEL_RELEVANT_ATTRIBUTES, html_case_insensitive
            )
            if (
                relevant is None
                or "for" not in relevant
                or not _is_static_relevant_value(relevant["for"])
                or any(attribute in relevant for attribute in LABEL_EXCLUDED_ATTRIBUTES)
            ):
                continue
            targets = target_ids.get(relevant["for"], [])
            if len(targets) != 1:
                continue
            line, column = _coordinates(content, offset)
            candidates.append((
                relative_path,
                offset,
                'label is="moz-label"',
                line,
                column,
                tag_name.lower(),
            ))

        for offset, tag_name, attributes in tags:
            source_tag = tag_name.lower()
            element_name = source_tag.removeprefix("html:")
            if element_name == "input":
                relevant = _relevant_attributes(
                    attributes, {"type"}, html_case_insensitive
                )
                if relevant is None or "type" not in relevant:
                    continue
                input_type = relevant["type"]
                if not _is_static_relevant_value(input_type):
                    continue
                component = INPUT_COMPONENTS.get(input_type.lower())
            elif element_name in ELEMENT_COMPONENTS:
                component = ELEMENT_COMPONENTS[element_name]
            else:
                continue
            if not component:
                continue
            line, column = _coordinates(content, offset)
            candidates.append((
                relative_path,
                offset,
                component,
                line,
                column,
                source_tag,
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
