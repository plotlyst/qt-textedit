import qtawesome
from PyQt5.QtGui import QKeySequence, QTextListFormat
from PyQt5.QtWidgets import QButtonGroup
from qthandy import vbox, hbox, spacer, vline
from qtpy import QtGui
from qtpy.QtCore import Qt, QMimeData, QSize
from qtpy.QtGui import QContextMenuEvent, QFont, QTextBlockFormat, QTextCursor
from qtpy.QtWidgets import QMenu, QWidget, QHBoxLayout, QToolButton, QFrame
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


def _button(icon: str, shortcut=None, checkable: bool = True) -> QToolButton:
    btn = QToolButton()
    btn.setIconSize(QSize(18, 18))
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setIcon(qtawesome.icon(icon))
    if shortcut:
        btn.setShortcut(shortcut)
    btn.setCheckable(checkable)

    return btn


class EnhancedTextEdit(QTextEdit):

    def __init__(self, parent=None):
        super(EnhancedTextEdit, self).__init__(parent)
        self._pasteAsPlain: bool = False
        self._quickFormatPopup = TextFormatWidget(self)
        self._quickFormatPopup.setHidden(True)
        self.selectionChanged.connect(self._toggleQuickFormatPopup)

        self.setTabStopDistance(
            QtGui.QFontMetricsF(self.font()).horizontalAdvance(' ') * 4)

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
        if event.key() == Qt.Key.Key_I and event.modifiers() & Qt.KeyboardModifiers.ControlModifier:
            self.setFontItalic(not self.fontItalic())
        if event.key() == Qt.Key.Key_B and event.modifiers() & Qt.KeyboardModifiers.ControlModifier:
            self.setFontWeight(QFont.Bold if self.fontWeight() == QFont.Normal else QFont.Normal)
        if event.key() == Qt.Key.Key_U and event.modifiers() & Qt.KeyboardModifiers.ControlModifier:
            self.setFontUnderline(not self.fontUnderline())
        if event.text().isalpha() and self._atSentenceStart(cursor):
            self.textCursor().insertText(event.text().upper())
            return
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

        self.setTabStopDistance(
            QtGui.QFontMetricsF(font).horizontalAdvance(' ') * 4)

    def _toggleQuickFormatPopup(self):
        if not self.textCursor().hasSelection():
            self._quickFormatPopup.setHidden(True)

    def _atSentenceStart(self, cursor: QTextCursor) -> bool:
        if cursor.atBlockStart():
            return True

        cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
        if cursor.selectedText() == '.':
            return True
        if cursor.atBlockStart() and cursor.selectedText() == '"':
            return True
        if cursor.positionInBlock() == 1:
            return False
        elif cursor.selectedText() == ' ' or cursor.selectedText() == '"':
            cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
            if cursor.selectedText().startswith('.'):
                return True

        return False


class RichTextEditor(QWidget):
    def __init__(self, parent=None):
        super(RichTextEditor, self).__init__(parent)
        vbox(self, 0, 0)

        self.toolbar = QFrame(self)
        self.toolbar.setStyleSheet('''
            QFrame {
                background-color: white;
            }
            
            QToolButton {
                border: 1px hidden black;
            }
            QToolButton:checked {
                background-color: #ced4da;
            }
            QToolButton:hover:!checked {
                background-color: #e5e5e5;
            }
        ''')
        hbox(self.toolbar)
        self.textEdit = EnhancedTextEdit(self)

        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.textEdit)

        self.btnBold = _button('fa5s.bold', shortcut=QKeySequence.Bold)
        self.btnBold.clicked.connect(lambda x: self.textEdit.setFontWeight(QFont.Bold if x else QFont.Normal))
        self.btnItalic = _button('fa5s.italic', shortcut=QKeySequence.Italic)
        self.btnItalic.clicked.connect(self.textEdit.setFontItalic)
        self.btnUnderline = _button('fa5s.underline', shortcut=QKeySequence.Underline)
        self.btnUnderline.clicked.connect(self.textEdit.setFontUnderline)

        self.btnAlignLeft = _button('fa5s.align-left')
        self.btnAlignLeft.clicked.connect(lambda: self.textEdit.setAlignment(Qt.AlignmentFlag.AlignLeft))
        self.btnAlignLeft.setChecked(True)
        self.btnAlignCenter = _button('fa5s.align-center')
        self.btnAlignCenter.clicked.connect(lambda: self.textEdit.setAlignment(Qt.AlignmentFlag.AlignCenter))
        self.btnAlignRight = _button('fa5s.align-right')
        self.btnAlignRight.clicked.connect(lambda: self.textEdit.setAlignment(Qt.AlignmentFlag.AlignRight))

        self.btnGroupAlignment = QButtonGroup(self.toolbar)
        self.btnGroupAlignment.setExclusive(True)
        self.btnGroupAlignment.addButton(self.btnAlignLeft)
        self.btnGroupAlignment.addButton(self.btnAlignCenter)
        self.btnGroupAlignment.addButton(self.btnAlignRight)

        self.btnInsertList = _button('fa5s.list')
        self.btnInsertList.clicked.connect(lambda: self.textEdit.textCursor().insertList(QTextListFormat.ListDisc))
        self.btnInsertNumberedList = _button('fa5s.list-ol')
        self.btnInsertNumberedList.clicked.connect(
            lambda: self.textEdit.textCursor().insertList(QTextListFormat.ListDecimal))

        self.toolbar.layout().addWidget(self.btnBold)
        self.toolbar.layout().addWidget(self.btnItalic)
        self.toolbar.layout().addWidget(self.btnUnderline)
        self.toolbar.layout().addWidget(vline())
        self.toolbar.layout().addWidget(self.btnAlignLeft)
        self.toolbar.layout().addWidget(self.btnAlignCenter)
        self.toolbar.layout().addWidget(self.btnAlignRight)
        self.toolbar.layout().addWidget(vline())
        self.toolbar.layout().addWidget(self.btnInsertList)
        self.toolbar.layout().addWidget(self.btnInsertNumberedList)
        self.toolbar.layout().addWidget(spacer())

        self.textEdit.cursorPositionChanged.connect(self._updateFormat)

    def _updateFormat(self):
        self.btnBold.setChecked(self.textEdit.fontWeight() == QFont.Bold)
        self.btnItalic.setChecked(self.textEdit.fontItalic())
        self.btnUnderline.setChecked(self.textEdit.fontUnderline())

        self.btnAlignLeft.setChecked(self.textEdit.alignment() == Qt.AlignmentFlag.AlignLeft)
        self.btnAlignCenter.setChecked(self.textEdit.alignment() == Qt.AlignmentFlag.AlignCenter)
        self.btnAlignRight.setChecked(self.textEdit.alignment() == Qt.AlignmentFlag.AlignRight)

        # self.cbHeading.blockSignals(True)
        # cursor = self.textEditor.textCursor()
        # level = cursor.blockFormat().headingLevel()
        # self.cbHeading.setCurrentIndex(level)
        # self.cbHeading.blockSignals(False)
