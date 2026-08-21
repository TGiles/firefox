# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import importlib.util
import sys
from pathlib import Path

import pytest
from buildconfig import topsrcdir
from mozunit import main

import mach
from mach.decorators import Registrar

_registrar_state = copy.deepcopy(vars(Registrar))
Registrar.register_category("misc", "misc", "misc")
_provider_spec = importlib.util.spec_from_file_location(
    "acorn_widget_commands",
    Path(topsrcdir) / "toolkit/content/widgets/mach_commands.py",
)
acorn_widget_commands = importlib.util.module_from_spec(_provider_spec)
_provider_spec.loader.exec_module(acorn_widget_commands)
vars(Registrar).clear()
vars(Registrar).update(_registrar_state)


def acorn_record(path, content, source_tag, component, offset=None):
    if offset is None:
        offset = content.index(f"<{source_tag}")
    return (
        path,
        offset,
        component,
        content.count("\n", 0, offset) + 1,
        offset - content.rfind("\n", 0, offset),
        source_tag.lower(),
    )


def test_find_acorn_label_candidates(tmp_path):
    html = '<label for="field">Field</label><input id="field">'
    xhtml = (
        '<html:root xmlns:html="http://www.w3.org/1999/xhtml">'
        '<html:label for="field">Field</html:label><html:input id="field"/>'
        "</html:root>"
    )
    (tmp_path / "labels.html").write_text(html)
    (tmp_path / "labels.xhtml").write_text(xhtml)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == [
        acorn_record("labels.html", html, "label", 'label is="moz-label"'),
        acorn_record("labels.xhtml", xhtml, "html:label", 'label is="moz-label"'),
    ]


def test_find_acorn_label_candidates_command_output(tmp_path, capsys):
    content = '<label for="field">Field</label><input id="field">'
    (tmp_path / "candidate.html").write_text(content)

    acorn_widget_commands.find_acorn_candidates_command(None, tmp_path)

    assert (
        capsys.readouterr().out
        == 'candidate.html:1:1: candidate <label> for <label is="moz-label">\n'
        "\n"
        "Candidate counts by component:\n"
        '<label is="moz-label">: 1\n'
    )


def test_find_acorn_candidates_command_summarizes_sorted_categories(tmp_path, capsys):
    markup = (
        '<button></button><button></button><label for="field">Field</label>'
        '<input id="field">'
    )
    xul = (
        '<window xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">\n'
        '<radiogroup><radio label="One"/></radiogroup>\n'
        "</window>"
    )
    (tmp_path / "alpha.html").write_text(markup)
    (tmp_path / "groups.xul").write_text(xul)

    acorn_widget_commands.find_acorn_candidates_command(None, tmp_path)

    assert (
        capsys.readouterr().out
        == "alpha.html:1:1: candidate <button> for <moz-button>\n"
        "alpha.html:1:18: candidate <button> for <moz-button>\n"
        'alpha.html:1:35: candidate <label> for <label is="moz-label">\n'
        "groups.xul:2:1: candidate <radiogroup> for <moz-radio-group>\n"
        "\n"
        "Candidate counts by component:\n"
        '<label is="moz-label">: 1\n'
        "<moz-button>: 2\n"
        "<moz-radio-group>: 1\n"
    )


def test_find_acorn_candidates_command_skips_summary_without_candidates(
    tmp_path, capsys
):
    (tmp_path / "empty.html").write_text("<div></div>")

    acorn_widget_commands.find_acorn_candidates_command(None, tmp_path)

    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "suffix, content",
    [
        (".xhtml", '<label for="field"><input id="field">'),
        (".html", '<html:label for="field"><html:input id="field">'),
        (
            ".xhtml",
            '<label xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul" for="field"><input id="field">',
        ),
        (".html", '<xul:label for="field"><xul:input id="field">'),
        (".html", '<unknown:label for="field"><unknown:input id="field">'),
        (".html", '<label><input id="field">'),
        (".html", '<label for=""><input id="field">'),
        (".html", '<label for="field"><div id="field">'),
        (".html", '<label for="field"><input id="field" type="hidden">'),
        (".html", '<label for="${field}"><input id="field">'),
        (".html", '<label for="{{field}}"><input id="field">'),
        (".html", '<label for="<% field %>"><input id="field">'),
        (".html", '<label for="field"><span id="field">'),
        (".html", '<label for="field"><custom-element id="field">'),
        (".html", '<label for="field"><input id="">'),
        (".html", '<label for="field"><input id="${field}">'),
        (".xhtml", '<html:label FOR="field"><html:input id="field">'),
    ],
)
def test_find_acorn_label_candidates_reject_invalid_targets(tmp_path, suffix, content):
    (tmp_path / f"invalid{suffix}").write_text(content)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == []


@pytest.mark.parametrize("attribute", ("is", "control", "value", "crop", "href"))
def test_find_acorn_label_candidates_reject_excluded_attributes(tmp_path, attribute):
    content = f'<label for="field" {attribute}="static"><input id="field">'
    (tmp_path / "excluded.html").write_text(content)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == []


@pytest.mark.parametrize(
    "content",
    [
        '<label for="field" for="field"><input id="field">',
        '<label for="field"><input id="field"><input id="field">',
        '<label for="field" control="one" control="two"><input id="field">',
        '<label for="a&amp;b"><input id="a&amp;b">',
        '<label for="a&#38;b"><input id="a&#38;b">',
        '<label for="a&#x26;b"><input id="a&#x26;b">',
    ],
)
def test_find_acorn_label_candidates_reject_ambiguous_or_entity_values(
    tmp_path, content
):
    (tmp_path / "ambiguous.html").write_text(content)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == []


def test_find_acorn_label_candidates_preserve_identity_and_html_attribute_case(
    tmp_path,
):
    matching = '<LABEL FOR=" Field "><INPUT ID=" Field ">'
    nonmatching = '<label for="field"><input id=" Field ">'
    (tmp_path / "matching.html").write_text(matching)
    (tmp_path / "nonmatching.html").write_text(nonmatching)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == [
        acorn_record("matching.html", matching, "LABEL", 'label is="moz-label"'),
    ]


def test_find_acorn_candidates_preserves_inputs_and_tuple_order(tmp_path):
    first = '<input type="text">'
    second = "<button></button><textarea></textarea>"
    nested = tmp_path / "nested"
    nested.mkdir()
    (tmp_path / "z.html").write_text(second)
    (nested / "a.html").write_text(first)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == [
        acorn_record("nested/a.html", first, "input", "moz-input-text"),
        acorn_record("z.html", second, "button", "moz-button"),
        acorn_record("z.html", second, "textarea", "moz-textarea"),
    ]


@pytest.mark.parametrize(
    "suffix, content, source_tag",
    [
        (
            ".xhtml",
            '<root xmlns="http://www.w3.org/1999/xhtml"><button></button></root>',
            "button",
        ),
        (
            ".xhtml",
            '<root xmlns="urn:not-html"><button></button>'
            '<html:button xmlns:html="http://www.w3.org/1999/xhtml"/>'
            "</root>",
            "html:button",
        ),
        (
            ".xul",
            '<window xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">'
            '<html:button xmlns:html="http://www.w3.org/1999/xhtml"/>'
            "</window>",
            "html:button",
        ),
    ],
)
def test_find_acorn_candidates_uses_xml_namespaces(
    tmp_path, suffix, content, source_tag
):
    path = f"namespaces{suffix}"
    (tmp_path / path).write_text(content)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == [
        acorn_record(path, content, source_tag, "moz-button"),
    ]


@pytest.mark.parametrize(
    "suffix, content",
    [
        (
            ".xhtml",
            '<root xmlns="http://www.w3.org/1999/xhtml">'
            "<button></button><bad:button/></root>",
        ),
        (
            ".xhtml",
            '<root xmlns="http://www.w3.org/1999/xhtml">'
            "<button></button><broken></root>",
        ),
        (
            ".xul",
            '<window xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">'
            '<html:button xmlns:html="http://www.w3.org/1999/xhtml"/>'
            "<broken></window>",
        ),
    ],
)
def test_find_acorn_candidates_discards_malformed_xml_files(tmp_path, suffix, content):
    (tmp_path / f"invalid{suffix}").write_text(content)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == []


def test_find_acorn_candidates_preserves_xml_case_rules(tmp_path):
    content = (
        '<root xmlns="http://www.w3.org/1999/xhtml">'
        "<button></button><BUTTON></BUTTON></root>"
    )
    (tmp_path / "case.xhtml").write_text(content)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == [
        acorn_record("case.xhtml", content, "button", "moz-button"),
    ]


def test_find_acorn_candidates_preserves_decoded_coordinates_and_inert_regions(
    tmp_path,
):
    html = (
        "😀\r\n<!-- <button> --><script><button></script><style><button></style>"
        "{{ <button> }}<% <button> %><![CDATA[<button>]]>"
        "<button></button><textarea></textarea>"
    )
    xhtml = (
        '<?xml version="1.0"?><!DOCTYPE root [<!ENTITY ignored "text">]>'
        '<root xmlns="http://www.w3.org/1999/xhtml">&ignored;<![CDATA[<button>]]>'
        "😀\r\n<button></button><textarea></textarea></root>"
    )
    with (tmp_path / "inert.html").open("w", newline="") as html_file:
        html_file.write(html)
    with (tmp_path / "inert.xhtml").open("w", newline="") as xhtml_file:
        xhtml_file.write(xhtml)
    invalid_utf8 = tmp_path / "replacement.html"
    invalid_utf8.write_bytes(b"\xff<button></button>")

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == [
        acorn_record(
            "inert.html",
            html,
            "button",
            "moz-button",
            html.rindex("<button"),
        ),
        acorn_record("inert.html", html, "textarea", "moz-textarea"),
        acorn_record(
            "inert.xhtml",
            xhtml,
            "button",
            "moz-button",
            xhtml.rindex("<button"),
        ),
        acorn_record("inert.xhtml", xhtml, "textarea", "moz-textarea"),
        acorn_record("replacement.html", "�<button></button>", "button", "moz-button"),
    ]


def test_find_acorn_candidates_recovers_html_after_malformed_markup(tmp_path):
    content = '<button broken=<><input type="text"><!-- <textarea> -->'
    (tmp_path / "recovery.html").write_text(content)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == [
        acorn_record("recovery.html", content, "input", "moz-input-text"),
    ]


def test_find_acorn_radio_group_candidates(tmp_path):
    xul = (
        '<window xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">'
        '<radiogroup name="choices" orient="vertical">'
        "\n<!-- permitted -->\n"
        '<radio label="One" value="one"/>'
        '<radio label="Two" value="two" selected="true"/>'
        "</radiogroup>"
        '<radiogroup orient="horizontal" value="two"><radio data-l10n-id="one" value="one"/>'
        '<radio data-l10n-id="two" data-l10n-args="{}" value="two"/>'
        '<radio data-l10n-id="three" data-l10n-attrs="label" value="three"/>'
        "</radiogroup>"
        "</window>"
    )
    with (tmp_path / "groups.xul").open("w", newline="") as xul_file:
        xul_file.write(xul)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == [
        acorn_record("groups.xul", xul, "radiogroup", "moz-radio-group"),
        acorn_record(
            "groups.xul",
            xul,
            "radiogroup",
            "moz-radio-group",
            xul.rindex("<radiogroup"),
        ),
    ]


@pytest.mark.parametrize(
    "group",
    [
        '<radiogroup><radio label="One" selected="true"/>'
        '<radio label="Two" selected="true"/></radiogroup>',
        '<radiogroup value="missing"><radio label="One" value="one"/></radiogroup>',
        '<radiogroup value="one"><radio label="One" value="one"/>'
        '<radio label="Again" value="one"/></radiogroup>',
        '<radiogroup value="one"><radio label="One" value="one" disabled="true"/>'
        "</radiogroup>",
        '<radiogroup value="one"><radio label="One" value="one" selected="false"/>'
        '<radio label="Two" value="two" selected="true"/></radiogroup>',
        '<radiogroup hidden="true"><radio label="One"/></radiogroup>',
        '<radiogroup orient="diagonal"><radio label="One"/></radiogroup>',
        '<radiogroup orient="${orient}"><radio label="One"/></radiogroup>',
        '<radiogroup><radio label="One" form="settings"/></radiogroup>',
        '<radiogroup><radio hidden="true" label="One"/></radiogroup>',
        '<radiogroup><radio label="One" required="true"/></radiogroup>',
        '<radiogroup><radio label="One" name="choice"/></radiogroup>',
        '<radiogroup><radio label="${label}"/></radiogroup>',
        '<radiogroup><radio data-l10n-args="{}"/></radiogroup>',
        '<radiogroup><radio data-l10n-id="one" data-l10n-id="two"/></radiogroup>',
        '<radiogroup><radio data-l10n-id="${id}"/></radiogroup>',
        '<radiogroup><radio data-l10n-id="one" data-l10n-args="${args}"/></radiogroup>',
        '<radiogroup><radio data-l10n-id="one" data-l10n-attrs="title"/></radiogroup>',
        '<radiogroup><radio data-l10n-id="one" data-l10n-name="label"/></radiogroup>',
        '<radiogroup><radio data-l10n-id="one" data-l10n-attrs="${attrs}"/></radiogroup>',
        '<radiogroup><radio label="One" disabled="maybe"/></radiogroup>',
        '<radiogroup><radio label="One" selected="${selected}"/></radiogroup>',
        '<radiogroup preference="pref"><radio label="One"/></radiogroup>',
        '<radiogroup group="legacy"><radio label="One"/></radiogroup>',
        '<radiogroup><radio label="One" observes="binding"/></radiogroup>',
        '<radiogroup><template><radio label="One"/></template></radiogroup>',
        '<radiogroup><radio label="One" oncommand="run()"/></radiogroup>',
        '<radiogroup><radio label="One" flex="1"/></radiogroup>',
        '<radiogroup>text<radio label="One"/></radiogroup>',
        '<radiogroup><![CDATA[text]]><radio label="One"/></radiogroup>',
        '<radiogroup><?pi value?><radio label="One"/></radiogroup>',
        '<radiogroup><box><radio label="One"/></box></radiogroup>',
        '<radiogroup><button/><radio label="One"/></radiogroup>',
    ],
)
def test_find_acorn_radio_groups_reject_unapproved_source(tmp_path, group):
    content = (
        '<window xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">'
        f"{group}</window>"
    )
    (tmp_path / "invalid.xul").write_text(content)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == []


def test_find_acorn_radio_groups_reject_lone_radio_and_malformed_xml(tmp_path):
    lone_radio = (
        '<window xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">'
        '<radio label="One"/></window>'
    )
    malformed = (
        '<window xmlns="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">'
        '<radiogroup><radio label="One"/></radiogroup><broken></window>'
    )
    (tmp_path / "lone.xul").write_text(lone_radio)
    (tmp_path / "malformed.xul").write_text(malformed)

    assert acorn_widget_commands.find_acorn_candidates(tmp_path) == []


ALL_COMMANDS = [
    "cmd_bar",
    "cmd_foo",
    "cmd_foobar",
    "mach-commands",
    "mach-completion",
    "mach-debug-commands",
]


@pytest.fixture
def run_completion(run_mach):
    def inner(args=[]):
        mach_dir = Path(mach.__file__).parent
        providers = [
            Path("commands.py"),
            mach_dir / "commands" / "commandinfo.py",
        ]

        def context_handler(key):
            if key == "topdir":
                return topsrcdir

        args = ["mach-completion"] + args
        return run_mach(args, providers, context_handler=context_handler)

    return inner


def format(targets):
    return "\n".join(targets) + "\n"


def test_mach_completion(run_completion):
    result, stdout, stderr = run_completion()
    assert result == 0
    assert stdout == format(ALL_COMMANDS)

    result, stdout, stderr = run_completion(["cmd_f"])
    assert result == 0
    # While it seems like this should return only commands that have
    # 'cmd_f' as a prefix, the completion script will handle this case
    # properly.
    assert stdout == format(ALL_COMMANDS)

    result, stdout, stderr = run_completion(["cmd_foo"])
    assert result == 0
    assert stdout == format(["help", "--arg"])


@pytest.mark.parametrize("shell", ("bash", "fish", "zsh"))
def test_generate_mach_completion_script(run_completion, shell):
    rv, out, err = run_completion([shell])
    print(out)
    print(err, file=sys.stderr)
    assert rv == 0
    assert err == ""

    assert "cmd_foo" in out
    assert "arg" in out
    assert "cmd_foobar" in out
    assert "cmd_bar" in out


if __name__ == "__main__":
    main()
