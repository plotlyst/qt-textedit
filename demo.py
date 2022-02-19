import sys

from qthandy import vbox
from qtpy.QtWidgets import QMainWindow, QApplication, QWidget
from qtpy.QtWidgets import QTextEdit

from qttextedit import RichTextEditor


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.resize(500, 500)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)

        vbox(self.widget)

        self.editor = RichTextEditor()
        self.editor.textEdit.setAutoFormatting(QTextEdit.AutoAll)
        self.editor.textEdit.setFontPointSize(16)

        self.sourceViewed = QTextEdit()
        self.sourceViewed.setReadOnly(True)
        self.sourceViewed.setAcceptRichText(False)

        self.widget.layout().addWidget(self.editor)
        self.widget.layout().addWidget(self.sourceViewed)

        self.editor.textEdit.textChanged.connect(lambda: self.sourceViewed.setPlainText(self.editor.textEdit.toHtml()))

        self.editor.textEdit.insertHtml(
            '<a href="https://github.com/zkovari">zkovari</a> opened this issue 3 days ago · 0 comments')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    app.exec_()
