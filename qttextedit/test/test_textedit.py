from qtpy.QtGui import QFont

from qttextedit import EnhancedTextEdit, RichTextEditor
from .common import type_text


def test_enhanced_textedit(qtbot):
    textedit = EnhancedTextEdit()
    qtbot.addWidget(textedit)
    textedit.show()
    qtbot.waitExposed(textedit)

    type_text(qtbot, textedit, 'test. test')

    assert textedit.toPlainText() == 'Test. Test'


def test_rich_texteditor(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)

    assert editor.btnAlignLeft.isChecked()


def test_bold_button(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)

    editor.btnBold.click()
    assert editor.textEdit.fontWeight() == QFont.Bold


def test_italic_button(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)

    editor.btnItalic.click()
    assert editor.textEdit.fontItalic()


def test_underline_button(qtbot):
    editor = RichTextEditor()
    editor.show()
    qtbot.addWidget(editor)
    qtbot.waitExposed(editor)

    editor.btnUnderline.click()
    assert editor.textEdit.fontUnderline()


def test_strikethrough_button(qtbot):
    editor = RichTextEditor()
    editor.show()
    qtbot.addWidget(editor)
    qtbot.waitExposed(editor)

    editor.btnStrikethrough.click()
    assert editor.textEdit.currentFont().strikeOut()


def test_foreground_color(qtbot):
    editor = RichTextEditor()
    editor.show()
    qtbot.addWidget(editor)
    qtbot.waitExposed(editor)

    item = editor.wdgTextStyle.wdgForeground.layout().itemAt(0)
    item.widget().click()

    assert editor.textEdit.textColor().name() == '#da1e37'


def test_background_color(qtbot):
    editor = RichTextEditor()
    editor.show()
    qtbot.addWidget(editor)
    qtbot.waitExposed(editor)

    item = editor.wdgTextStyle.wdgBackground.layout().itemAt(0)
    item.widget().click()

    assert editor.textEdit.textBackgroundColor().name() == '#da1e37'
