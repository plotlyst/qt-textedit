from qtpy.QtGui import QFont

from qttextedit import EnhancedTextEdit, RichTextEditor


def type_text(qtbot, textedit, text: str):
    for c in text:
        qtbot.keyPress(textedit, c)


def test_enhanced_textedit(qtbot):
    textedit = EnhancedTextEdit()
    qtbot.addWidget(textedit)
    textedit.show()
    type_text(qtbot, textedit, 'test. test')

    assert textedit.toPlainText() == 'Test. Test'


def test_rich_texteditor(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()

    assert editor.btnAlignLeft.isChecked()


def test_bold_button(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()

    editor.btnBold.click()
    assert editor.textEdit.fontWeight() == QFont.Bold


def test_italic_button(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()

    editor.btnItalic.click()
    assert editor.textEdit.fontItalic()


def test_underline_button(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()

    editor.btnUnderline.click()
    assert editor.textEdit.fontUnderline()


def test_strikethrough_button(qtbot):
    editor = RichTextEditor()
    qtbot.addWidget(editor)
    editor.show()

    editor.btnStrikethrough.click()
    assert editor.textEdit.currentFont().strikeOut()
