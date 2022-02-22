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

        # toolbar = StandardTextEditorToolbar()
        # toolbar.setDefaultOperations(Operations.Bold | Operations.Italic)
        #
        # customToolbar = TextEditorToolbar()
        # customToolbar.addStandardOperation(Operations.Bold)
        # customToolbar.addSeparator()
        # customToolbar.addSpacer()
        # customToolbar.addCustomAction(action)
        # customToolbar.addCustomWidget()
        #
        # self.editor.setToolbar(toolbar, ToolbarDisplayMode.OnSelection)
        # self.editor.setTitleEditor(DefaultTitleEditor())


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    app.exec_()
