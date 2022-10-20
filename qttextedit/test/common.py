from qtpy.QtCore import Qt

from qttextedit import RichTextEditor


def type_text(qtbot, editor, text: str):
    if isinstance(editor, RichTextEditor):
        textedit = editor.textEdit
    else:
        textedit = editor
    for c in text:
        qtbot.keyPress(textedit, c)


def type_enter(qtbot, textedit):
    qtbot.keyPress(textedit, Qt.Key.Key_Enter)
