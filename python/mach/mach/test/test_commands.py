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


def acorn_record(path, content, source_tag, component):
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
    xhtml = '<html:label for="field">Field</html:label><html:input id="field">'
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
    )


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
