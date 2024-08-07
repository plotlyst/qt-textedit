from qtpy.QtGui import QFont

from qttextedit import EnhancedTextEdit, RichTextEditor, DashInsertionMode
from qttextedit.api import AutoCapitalizationMode
from qttextedit.ops import BoldOperation, ItalicOperation, ColorOperation, UnderlineOperation, StrikethroughOperation
from qttextedit.test.common import type_text, type_enter


def prepare_textedit(qtbot) -> EnhancedTextEdit:
    textedit = EnhancedTextEdit()
    qtbot.addWidget(textedit)
    textedit.show()
    qtbot.waitExposed(textedit)

    return textedit


def prepare_richtext_editor(qtbot) -> RichTextEditor:
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)

    return editor


def test_auto_capitalization(qtbot):
    textedit = prepare_textedit(qtbot)
    assert textedit.autoCapitalizationMode() == AutoCapitalizationMode.NONE

    textedit.setAutoCapitalizationMode(AutoCapitalizationMode.PARAGRAPH)
    type_text(qtbot, textedit, 'test. test')
    assert textedit.toPlainText() == 'Test. test'

    textedit.clear()
    textedit.setAutoCapitalizationMode(AutoCapitalizationMode.SENTENCE)
    type_text(qtbot, textedit, 'test. test')
    assert textedit.toPlainText() == 'Test. Test'

    textedit.clear()
    textedit.setAutoCapitalizationMode(AutoCapitalizationMode.NONE)
    type_text(qtbot, textedit, 'test. test')
    assert textedit.toPlainText() == 'test. test'


# def test_ellipsis(qtbot):
#     textedit = prepare_textedit(qtbot)
#     type_text(qtbot, textedit, '...')
#     assert textedit.toPlainText() == '…'


def test_dashes(qtbot):
    textedit = prepare_textedit(qtbot)
    assert textedit.dashInsertionMode() == DashInsertionMode.NONE
    type_text(qtbot, textedit, '--')
    assert textedit.toPlainText() == '--'

    textedit.clear()
    textedit.setDashInsertionMode(DashInsertionMode.INSERT_EN_DASH)
    type_text(qtbot, textedit, '--')
    assert textedit.toPlainText() == '–'

    textedit.clear()
    textedit.setDashInsertionMode(DashInsertionMode.INSERT_EM_DASH)
    type_text(qtbot, textedit, '--')
    assert textedit.toPlainText() == '—'


def test_quotes(qtbot):
    textedit = prepare_textedit(qtbot)
    type_text(qtbot, textedit, "'")
    assert textedit.toPlainText() == '‘’'

    textedit.clear()
    type_text(qtbot, textedit, "Test'")
    assert textedit.toPlainText() == 'Test’'

    textedit.clear()
    type_text(qtbot, textedit, '"')
    assert textedit.toPlainText() == '“”'

    textedit.clear()
    type_text(qtbot, textedit, 'Test"')
    assert textedit.toPlainText() == 'Test”'

    textedit.clear()
    type_text(qtbot, textedit, 'Test')
    type_enter(qtbot, textedit)
    type_text(qtbot, textedit, '"')
    assert textedit.toPlainText() == 'Test\n“”'


def test_rich_texteditor(qtbot):
    editor = prepare_richtext_editor(qtbot)

    assert editor.toolbar().textEditorOperation(BoldOperation).isVisible()


def test_bold_operation(qtbot):
    editor = prepare_richtext_editor(qtbot)

    editor.toolbar().textEditorOperation(BoldOperation).trigger()
    assert editor.textEdit.fontWeight() == QFont.Bold


def test_italic_operation(qtbot):
    editor = prepare_richtext_editor(qtbot)

    editor.toolbar().textEditorOperation(ItalicOperation).trigger()
    assert editor.textEdit.fontItalic()


def test_underline_operation(qtbot):
    editor = prepare_richtext_editor(qtbot)

    editor.toolbar().textEditorOperation(UnderlineOperation).trigger()
    assert editor.textEdit.fontUnderline()


def test_strikethrough_operation(qtbot):
    editor = prepare_richtext_editor(qtbot)

    editor.toolbar().textEditorOperation(StrikethroughOperation).trigger()
    assert editor.textEdit.currentFont().strikeOut()


def test_foreground_color(qtbot):
    editor = prepare_richtext_editor(qtbot)

    color_op: ColorOperation = editor.toolbar().textEditorOperation(ColorOperation)
    item = color_op.wdgTextStyle.wdgForeground.layout().itemAt(0)
    item.widget().click()

    assert editor.textEdit.textColor().name() == '#da1e37'


def test_background_color(qtbot):
    editor = prepare_richtext_editor(qtbot)

    color_op: ColorOperation = editor.toolbar().textEditorOperation(ColorOperation)
    item = color_op.wdgTextStyle.wdgBackground.layout().itemAt(0)
    item.widget().click()

    assert editor.textEdit.textBackgroundColor().name() == '#da1e37'


def test_width_percentage(qtbot):
    editor = prepare_richtext_editor(qtbot)

    editor.setWidthPercentage(50)
    assert editor.textEdit.viewportMargins().left()
