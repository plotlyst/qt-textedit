def type_text(qtbot, textedit, text: str):
    for c in text:
        qtbot.keyPress(textedit, c)
