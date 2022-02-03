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
