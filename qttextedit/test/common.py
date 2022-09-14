from qtpy.QtCore import Qt


def type_text(qtbot, textedit, text: str):
    for c in text:
        qtbot.keyPress(textedit, c)


def type_enter(qtbot, textedit):
    qtbot.keyPress(textedit, Qt.Key.Key_Enter)
