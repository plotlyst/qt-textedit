from qttextedit import EnhancedTextEdit


def type_text(qtbot, textedit, text: str):
    for c in text:
        qtbot.keyPress(textedit, c)


def test_enhanced_textedit(qtbot):
    textedit = EnhancedTextEdit()
    qtbot.addWidget(textedit)
    textedit.show()
    type_text(qtbot, textedit, 'test')

    assert textedit.toPlainText() == 'test'
