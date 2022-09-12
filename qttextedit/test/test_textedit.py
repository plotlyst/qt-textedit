from qtpy.QtGui import QFont

from qttextedit import EnhancedTextEdit, RichTextEditor, TextEditorOperationType
from qttextedit.test.common import type_text


def prepare_textedit(qtbot) -> EnhancedTextEdit:
    textedit = EnhancedTextEdit()
    qtbot.addWidget(textedit)
    textedit.show()
    qtbot.waitExposed(textedit)

    return textedit


def test_auto_capitalization(qtbot):
    textedit = prepare_textedit(qtbot)

    type_text(qtbot, textedit, 'test. test')
    assert textedit.toPlainText() == 'Test. test'

    textedit.clear()
    textedit.setSentenceAutoCapitalizationEnabled(True)
    type_text(qtbot, textedit, 'test. test')
    assert textedit.toPlainText() == 'Test. Test'

    textedit.clear()
    textedit.setAutoCapitalizationEnabled(False)
    type_text(qtbot, textedit, 'test. test')
    assert textedit.toPlainText() == 'test. test'


def test_ellipsis(qtbot):
    textedit = prepare_textedit(qtbot)
    type_text(qtbot, textedit, '...')
    assert textedit.toPlainText() == '…'


def test_rich_texteditor(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)

    assert editor.toolbar.standardOperation(TextEditorOperationType.BOLD).isVisible()


def test_bold_operation(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)

    editor.toolbar.standardOperation(TextEditorOperationType.BOLD).trigger()
    assert editor.textEdit.fontWeight() == QFont.Bold


def test_italic_operation(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)

    editor.toolbar.standardOperation(TextEditorOperationType.ITALIC).trigger()
    assert editor.textEdit.fontItalic()


def test_underline_operation(qtbot):
    editor = RichTextEditor()
    editor.show()
    qtbot.addWidget(editor)
    qtbot.waitExposed(editor)

    editor.toolbar.standardOperation(TextEditorOperationType.UNDERLINE).trigger()
    assert editor.textEdit.fontUnderline()


def test_strikethrough_operation(qtbot):
    editor = RichTextEditor()
    editor.show()
    qtbot.addWidget(editor)
    qtbot.waitExposed(editor)

    editor.toolbar.standardOperation(TextEditorOperationType.STRIKETHROUGH).trigger()
    assert editor.textEdit.currentFont().strikeOut()


def test_foreground_color(qtbot):
    editor = RichTextEditor()
    editor.show()
    qtbot.addWidget(editor)
    qtbot.waitExposed(editor)

    color_op = editor.toolbar.standardOperation(TextEditorOperationType.COLOR)
    item = color_op.wdgTextStyle.wdgForeground.layout().itemAt(0)
    item.widget().click()

    assert editor.textEdit.textColor().name() == '#da1e37'


def test_background_color(qtbot):
    editor = RichTextEditor()
    editor.show()
    qtbot.addWidget(editor)
    qtbot.waitExposed(editor)

    color_op = editor.toolbar.standardOperation(TextEditorOperationType.COLOR)
    item = color_op.wdgTextStyle.wdgBackground.layout().itemAt(0)
    item.widget().click()

    assert editor.textEdit.textBackgroundColor().name() == '#da1e37'
