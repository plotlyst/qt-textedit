import sys

from qthandy import vbox
from qtpy.QtWidgets import QMainWindow, QApplication, QWidget
from qtpy.QtWidgets import QTextEdit

from qttextedit import RichTextEditor, DashInsertionMode, TextBlockState


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.resize(500, 500)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)

        vbox(self.widget)

        self.editor = RichTextEditor()
        self.editor.setCharacterWidth()
        self.editor.textEdit.setAutoFormatting(QTextEdit.AutoAll)
        self.editor.textEdit.setAutoCapitalizationEnabled(False)
        self.editor.textEdit.setDashInsertionMode(DashInsertionMode.INSERT_EM_DASH)

        self.editor.textEdit.setPlaceholderText('Write text')
        ps = self.editor.textEdit.font().pointSize()
        self.editor.textEdit.zoomIn(ps * 0.47)

        self.insertNonEditableBlock()

        self.sourceViewed = QTextEdit()
        self.sourceViewed.setReadOnly(True)
        self.sourceViewed.setAcceptRichText(False)

        self.widget.layout().addWidget(self.editor)
        self.widget.layout().addWidget(self.sourceViewed)

        self.editor.textEdit.textChanged.connect(lambda: self.sourceViewed.setPlainText(self.editor.textEdit.toHtml()))
        self.editor.textEdit.setFocus()

    def insertNonEditableBlock(self):
        self.editor.textEdit.setUneditableBlocksEnabled(True)
        self.editor.textEdit.textCursor().insertText('First')
        self.editor.textEdit.textCursor().insertBlock()
        self.editor.textEdit.textCursor().insertText('----')
        self.editor.textEdit.textCursor().block().setUserState(TextBlockState.UNEDITABLE.value)
        self.editor.textEdit.textCursor().insertBlock()
        self.editor.textEdit.textCursor().insertText('Second')

    def zoom(self):
        ps = self.editor.textEdit.font().pointSize()
        self.editor.textEdit.zoomIn(ps * 0.1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    app.exec_()
