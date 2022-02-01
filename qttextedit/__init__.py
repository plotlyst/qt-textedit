import qtawesome
from qtpy import QtGui
from qtpy.QtCore import QMimeData
from qtpy.QtCore import Qt
from qtpy.QtGui import QContextMenuEvent, QFont, QTextBlockFormat, QTextCursor
from qtpy.QtWidgets import QMenu, QWidget, QHBoxLayout, QToolButton
from qtpy.QtWidgets import QTextEdit


class TextFormatWidget(QWidget):
    def __init__(self, parent=None):
        super(TextFormatWidget, self).__init__(parent)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(2, 2, 2, 2)
        self.layout().setSpacing(3)

        self.btnBold = QToolButton()
        self.btnBold.setIcon(qtawesome.icon('fa5s.bold'))

        self.btnItalic = QToolButton()
        self.btnItalic.setIcon(qtawesome.icon('fa5s.italic'))

        self.btnUnderline = QToolButton()
        self.btnUnderline.setIcon(qtawesome.icon('fa5s.underline'))

        self.layout().addWidget(self.btnBold)
        self.layout().addWidget(self.btnItalic)
        self.layout().addWidget(self.btnUnderline)


class EnhancedTextEdit(QTextEdit):

    def __init__(self, parent=None):
        super(EnhancedTextEdit, self).__init__(parent)
        self._pasteAsPlain: bool = False
        self._quickFormatPopup = TextFormatWidget(self)
        self._quickFormatPopup.setHidden(True)
        self.selectionChanged.connect(self._toggleQuickFormatPopup)

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = QMenu()
        menu.setToolTipsVisible(True)
        menu.addSeparator()
        selected = bool(self.textCursor().selectedText())
        action = menu.addAction(qtawesome.icon('fa5s.cut'), 'Cut', self.cut)
        action.setEnabled(selected)
        action.setToolTip('Cut selected text')
        action = menu.addAction(qtawesome.icon('fa5s.copy'), 'Copy', self.copy)
        action.setEnabled(selected)
        action.setToolTip('Copy selected text')
        action = menu.addAction(qtawesome.icon('fa5s.paste'), 'Paste', self.paste)
        action.setToolTip('Paste from clipboard and adjust to the current style')

        menu.addSeparator()
        paste_submenu = menu.addMenu('Paste as...')
        action = paste_submenu.addAction('Paste as plain text', self.pasteAsPlainText)
        action.setToolTip('Paste as plain text without any formatting')

        menu.exec(event.globalPos())

    def pasteAsPlainText(self):
        previous = self._pasteAsPlain
        self._pasteAsPlain = True
        self.paste()
        self._pasteAsPlain = previous

    def insertFromMimeData(self, source: QMimeData) -> None:
        # doc = QTextDocument()
        # doc.setDefaultFont(QFont('Helvetica', 16))
        # doc.setHtml(source.html())

        # self.textEditor.textCursor().select(QTextCursor.Document)
        # self.textEditor.setFontPointSize(size)
        # font = self._lblPlaceholder.font()
        # font.setPointSize(size)
        # self._lblPlaceholder.setFont(font)
        # self.textEditor.textCursor().clearSelection()

        if self._pasteAsPlain:
            self.insertPlainText(source.text())
        else:
            # self.insertHtml(doc.toHtml())
            super(EnhancedTextEdit, self).insertFromMimeData(source)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        cursor = self.textCursor()
        if event.key() == Qt.Key.Key_Tab:
            list_ = cursor.block().textList()
            if list_:
                cursor.beginEditBlock()
                block = cursor.block()

                new_format = list_.format()
                new_format.setIndent(list_.format().indent() + 1)
                cursor.insertList(new_format)
                list_.removeItem(list_.itemNumber(block))
                cursor.deletePreviousChar()

                cursor.endEditBlock()
                return
        if event.key() == Qt.Key.Key_Backtab:
            list_ = cursor.block().textList()
            if list_:
                indent = list_.format().indent()
                if indent > 1:
                    cursor.beginEditBlock()
                    new_format = list_.format()
                    new_format.setIndent(indent - 1)
                    list_.setFormat(new_format)
                    cursor.endEditBlock()
                return
        if event.key() == Qt.Key_I and event.modifiers() & Qt.ControlModifier:
            self.setFontItalic(not self.fontItalic())
        if event.key() == Qt.Key_B and event.modifiers() & Qt.ControlModifier:
            self.setFontWeight(QFont.Bold if self.fontWeight() == QFont.Normal else QFont.Normal)
        if event.key() == Qt.Key_U and event.modifiers() & Qt.ControlModifier:
            self.setFontUnderline(not self.fontUnderline())
        super(EnhancedTextEdit, self).keyPressEvent(event)

    # def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
    #     super(EnhancedTextEdit, self).mouseDoubleClickEvent(event)
    #     text = self.textCursor().selectedText()
    #     if text:
    #         x = event.pos().x() - self._quickFormatPopup.width() // 2
    #         if x < 0:
    #             x = 0
    #         y = event.pos().y() + self.fontPointSize()
    #         self._quickFormatPopup.setGeometry(x, y,
    #                                            self._quickFormatPopup.width(),
    #                                            self._quickFormatPopup.height())
    #         qtanim.fade_in(self._quickFormatPopup, duration=150)

    def setFormat(self, lineSpacing: int = 100, textIndent: int = 0):
        blockFmt = QTextBlockFormat()
        blockFmt.setTextIndent(textIndent)
        blockFmt.setLineHeight(lineSpacing, QTextBlockFormat.ProportionalHeight)

        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.select(QTextCursor.Document)
        cursor.mergeBlockFormat(blockFmt)

    def setFontPointSize(self, size: int):
        self.textCursor().select(QTextCursor.Document)
        font = self.document().defaultFont()
        font.setPointSize(size)
        self.document().setDefaultFont(font)
        super(EnhancedTextEdit, self).setFontPointSize(size)
        self.textCursor().clearSelection()

    def _toggleQuickFormatPopup(self):
        if not self.textCursor().hasSelection():
            self._quickFormatPopup.setHidden(True)
