import sys

from PyQt5.QtGui import QFont
from qthandy import vbox
from qtpy.QtWidgets import QMainWindow, QApplication, QWidget
from qtpy.QtWidgets import QTextEdit

from qttextedit import RichTextEditor, DashInsertionMode


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.resize(500, 500)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)

        vbox(self.widget)

        self.editor = RichTextEditor()
        self.editor.textEdit.setAutoFormatting(QTextEdit.AutoAll)
        self.editor.textEdit.setAutoCapitalizationEnabled(True)
        self.editor.textEdit.setDashInsertionMode(DashInsertionMode.INSERT_EM_DASH)
        font = QFont('Times New Roman')
        self.editor.textEdit.setFont(font)
        self.editor.textEdit.setPlaceholderText('Write text')
        ps = self.editor.textEdit.font().pointSize()
        self.editor.textEdit.zoomIn(ps * 0.47)

        self.sourceViewed = QTextEdit()
        self.sourceViewed.setReadOnly(True)
        self.sourceViewed.setAcceptRichText(False)

        self.widget.layout().addWidget(self.editor)
        self.widget.layout().addWidget(self.sourceViewed)

        self.editor.textEdit.textChanged.connect(lambda: self.sourceViewed.setPlainText(self.editor.textEdit.toHtml()))
        # self.editor.textEdit.textChanged.connect(lambda: self.zoom())
        self.editor.textEdit.setFocus()

    def zoom(self):
        ps = self.editor.textEdit.font().pointSize()
        self.editor.textEdit.zoomIn(ps * 0.1)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    app.exec_()
