import sys

from PyQt5.QtWidgets import QTextEdit
from qthandy import hbox
from qtpy.QtWidgets import QMainWindow, QApplication, QWidget

from qttextedit import EnhancedTextEdit


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)

        self.resize(500, 500)

        self.widget = QWidget(self)
        self.setCentralWidget(self.widget)

        hbox(self.widget)

        self.enhancedTextEdit = EnhancedTextEdit()
        self.enhancedTextEdit.setAutoFormatting(QTextEdit.AutoAll)
        self.enhancedTextEdit.setFontPointSize(16)
        self.widget.layout().addWidget(self.enhancedTextEdit)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    window.show()

    app.exec()
