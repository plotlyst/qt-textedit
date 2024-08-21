from qthandy import vbox
from qtpy.QtWidgets import QWidget

from qttextedit import RichTextEditor, TextEditorSettingsButton
from qttextedit.ops import TextEditorSettingsSection, TextEditingSettingsOperation
from qttextedit.test.common import type_text


def prepare_richtext_editor(qtbot):
    widget = QWidget()
    vbox(widget)
    editor = RichTextEditor()
    widget.layout().addWidget(editor)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)

    qtbot.wait(15)

    op: TextEditingSettingsOperation = editor.toolbar().textEditorOperation(TextEditingSettingsOperation)
    return widget, editor, op.settingsWidget()


def test_page_width(qtbot):
    widget, editor, settings = prepare_richtext_editor(qtbot)
    settings.setSectionVisible(TextEditorSettingsSection.PAGE_WIDTH, False)
    type_text(qtbot, editor, 'Test text')

    assert editor.widthPercentage() == 0
    wdg = settings.section(TextEditorSettingsSection.PAGE_WIDTH)
    assert wdg.value() == 100
    wdg.setValue(50)
    assert editor.widthPercentage() == 50


def test_font_size(qtbot):
    widget, editor, settings = prepare_richtext_editor(qtbot)
    type_text(qtbot, editor, 'Test text')

    wdg = settings.section(TextEditorSettingsSection.FONT_SIZE)
    assert wdg.value() != 18
    wdg.setValue(18)
    assert editor.textEdit.font().pointSize() == 18


def test_separate_settings_btn(qtbot):
    widget, editor, settings = prepare_richtext_editor(qtbot)
    type_text(qtbot, editor, 'Test text')

    editor.toolbar().setTextEditorOperationVisible(TextEditingSettingsOperation, False)

    btn = TextEditorSettingsButton(widget)
    widget.layout().addWidget(btn)
    editor.attachSettingsWidget(btn.settingsWidget())

    wdg = btn.settingsWidget().section(TextEditorSettingsSection.PAGE_WIDTH)
    assert wdg.value() == 100
    wdg.setValue(50)
    assert editor.widthPercentage() == 50
