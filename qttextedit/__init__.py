import re
from typing import List, Dict

import qtawesome
from qthandy import vbox, hbox, spacer, vline, btn_popup_menu
from qtpy import QtGui
from qtpy.QtCore import Qt, QMimeData, QSize, QUrl, QBuffer, QIODevice, QPoint
from qtpy.QtGui import QContextMenuEvent, QDesktopServices, QFont, QTextBlockFormat, QTextCursor, QTextList, \
    QTextCharFormat, QTextFormat
from qtpy.QtWidgets import QMenu, QWidget, QApplication, QFrame, QButtonGroup, QTextEdit, \
    QInputDialog, QToolButton

from qttextedit.ops import TextEditorOperationType, TextEditorOperation, FormatOperation, BoldOperation, \
    ItalicOperation, UnderlineOperation, StrikethroughOperation, ColorOperation, AlignLeftOperation, \
    AlignCenterOperation, AlignRightOperation, InsertListOperation, InsertNumberedListOperation, InsertLinkOperation, \
    ExportPdfOperation, PrintOperation, TextEditorOperationAction, TextEditorOperationMenu, \
    TextEditorOperationWidgetAction
from qttextedit.util import select_anchor, select_previous_character, select_next_character, is_open_quotation


class EnhancedTextEdit(QTextEdit):

    def __init__(self, parent=None):
        super(EnhancedTextEdit, self).__init__(parent)
        self._pasteAsPlain: bool = False
        self._pasteAsOriginal: bool = False

        self.setTabStopDistance(
            QtGui.QFontMetricsF(self.font()).horizontalAdvance(' ') * 4)

    def createEnhancedContextMenu(self, pos: QPoint) -> QMenu:
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
        action = paste_submenu.addAction('Paste with original style', self.pasteAsOriginalText)
        action.setToolTip('Paste with the original formatting')

        anchor = self.anchorAt(pos)
        if anchor:
            menu.addSeparator()
            menu.addAction(qtawesome.icon('fa5s.link'), 'Edit link',
                           lambda: self._editLink(self.cursorForPosition(pos)))

        return menu

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = self.createEnhancedContextMenu(event.pos())
        menu.exec(event.globalPos())

    def pasteAsPlainText(self):
        previous = self._pasteAsPlain
        self._pasteAsPlain = True
        self.paste()
        self._pasteAsPlain = previous

    def pasteAsOriginalText(self):
        previous = self._pasteAsOriginal
        self._pasteAsOriginal = True
        self.paste()
        self._pasteAsOriginal = previous

    def insertFromMimeData(self, source: QMimeData) -> None:
        if self._pasteAsPlain:
            self.insertPlainText(source.text())
        elif self._pasteAsOriginal:
            super(EnhancedTextEdit, self).insertFromMimeData(source)
        else:
            html = source.html()
            html = re.sub('font-family', '', html)
            self.insertHtml(html)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super(EnhancedTextEdit, self).mouseMoveEvent(event)

        cursor = self.cursorForPosition(event.pos())
        if cursor.atBlockStart() or cursor.atBlockEnd():
            QApplication.restoreOverrideCursor()
            return

        anchor = self.anchorAt(event.pos())
        if anchor:
            if QApplication.overrideCursor() is None:
                QApplication.setOverrideCursor(Qt.PointingHandCursor)
                self._setLinkTooltip(anchor)
        else:
            QApplication.restoreOverrideCursor()
            self.setToolTip('')

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        super(EnhancedTextEdit, self).mouseReleaseEvent(event)

        anchor = self.anchorAt(event.pos())
        if anchor and not self.textCursor().selectedText():
            QDesktopServices.openUrl(QUrl(anchor))

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        cursor: QTextCursor = self.textCursor()
        if event.key() == Qt.Key_Tab:
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
        if event.key() == Qt.Key_Backtab:
            list_: QTextList = cursor.block().textList()
            if list_:
                indent = list_.format().indent()
                if indent > 1:
                    if list_.count() == 1:
                        cursor.beginEditBlock()
                        new_format = list_.format()
                        new_format.setIndent(indent - 1)
                        list_.setFormat(new_format)
                        cursor.endEditBlock()
                    elif list_.count() > 1:
                        cursor.beginEditBlock()
                        new_format = list_.format()
                        new_format.setIndent(indent - 1)
                        list_.remove(cursor.block())
                        new_block_format = cursor.block().blockFormat()
                        new_block_format.setIndent(cursor.block().blockFormat().indent() - 2)
                        cursor.mergeBlockFormat(new_block_format)
                        cursor.createList(new_format)
                        cursor.endEditBlock()
                return
        if event.key() == Qt.Key_I and event.modifiers() & Qt.ControlModifier:
            self.setFontItalic(not self.fontItalic())
        if event.key() == Qt.Key_B and event.modifiers() & Qt.ControlModifier:
            self.setFontWeight(QFont.Bold if self.fontWeight() == QFont.Normal else QFont.Normal)
        if event.key() == Qt.Key_U and event.modifiers() & Qt.ControlModifier:
            self.setFontUnderline(not self.fontUnderline())
        if event.text().isalpha() and self._atSentenceStart(cursor):
            self.textCursor().insertText(event.text().upper())
            return
        if event.key() == Qt.Key_Return:
            self.textCursor().insertBlock(self.textCursor().blockFormat(), QTextCharFormat())
            return
        # if event.key() == Qt.Key_Slash and self.textCursor().atBlockStart():
        #     self._showCommands()
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

    def setStrikethrough(self, strikethrough: bool):
        font = self.currentFont()
        font.setStrikeOut(strikethrough)
        self.setCurrentFont(font)

    def setFontPointSize(self, size: int):
        self.textCursor().select(QTextCursor.Document)
        font = self.document().defaultFont()
        font.setPointSize(size)
        self.document().setDefaultFont(font)
        super(EnhancedTextEdit, self).setFontPointSize(size)
        self.textCursor().clearSelection()

        self.setTabStopDistance(
            QtGui.QFontMetricsF(font).horizontalAdvance(' ') * 4)

    def resetTextColor(self):
        format = QTextCharFormat()
        format.setFontWeight(self.textCursor().charFormat().fontWeight())
        format.setFontItalic(self.textCursor().charFormat().fontItalic())
        format.setFontUnderline(self.textCursor().charFormat().fontUnderline())
        format.setFontStrikeOut(self.textCursor().charFormat().fontStrikeOut())
        self.textCursor().setCharFormat(format)

    def setHeading(self, heading: int):
        cursor: QTextCursor = self.textCursor()
        cursor.beginEditBlock()

        blockFormat: QTextBlockFormat = cursor.blockFormat()
        blockFormat.setHeadingLevel(heading)
        cursor.setBlockFormat(blockFormat)
        sizeAdjustment = 5 - heading if heading else 0

        charFormat = QTextCharFormat()
        charFormat.setFontWeight(QFont.Bold if heading else QFont.Normal)
        charFormat.setProperty(QTextFormat.FontSizeAdjustment, sizeAdjustment)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.mergeBlockCharFormat(charFormat)
        self.mergeCurrentCharFormat(charFormat)

        cursor.endEditBlock()

    def _setLinkTooltip(self, anchor: str):
        icon = qtawesome.icon('fa5s.external-link-alt')
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        pixmap = icon.pixmap(QSize(8, 8))
        pixmap.save(buffer, "PNG", quality=100)
        html = f"<img src='data:image/png;base64, {bytes(buffer.data().toBase64()).decode()}'>{anchor}"
        self.setToolTip(html)

    def _editLink(self, cursor: QTextCursor):
        QApplication.restoreOverrideCursor()
        self.setToolTip('')

        anchor, ok = QInputDialog.getText(self, 'Edit link', 'URL', text=cursor.charFormat().anchorHref())
        if ok:
            pos_cursor = select_anchor(cursor)

            char_format: QTextCharFormat = pos_cursor.charFormat()
            char_format.setAnchorHref(anchor)
            pos_cursor.mergeCharFormat(char_format)

    def _atSentenceStart(self, cursor: QTextCursor) -> bool:
        if cursor.atBlockStart():
            return True
        moved_cursor = select_previous_character(cursor)
        if moved_cursor.selectedText() == '.':
            return True
        if not cursor.atBlockEnd():
            right_moved_cursor = select_next_character(cursor)
            if right_moved_cursor.selectedText().isalpha():
                return False
        if moved_cursor.atBlockStart() and is_open_quotation(moved_cursor.selectedText()):
            return True
        if moved_cursor.positionInBlock() == 1:
            return False
        elif moved_cursor.selectedText() == ' ' or is_open_quotation(moved_cursor.selectedText()):
            moved_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
            if moved_cursor.selectedText().startswith('.'):
                return True

        return False

    # def _showCommands(self, point: QPoint):
    #     def trigger(func):
    #         self.textEditor.textCursor().deletePreviousChar()
    #         func()

    # rect = self.textEditor.cursorRect(self.textEditor.textCursor())
    #
    # menu = QMenu(self.textEditor)
    # menu.addAction(IconRegistry.heading_1_icon(), '', partial(trigger, lambda: self.cbHeading.setCurrentIndex(1)))
    # menu.addAction(IconRegistry.heading_2_icon(), '', partial(trigger, lambda: self.cbHeading.setCurrentIndex(2)))
    #
    # menu.popup(self.textEditor.viewport().mapToGlobal(QPoint(rect.x(), rect.y())))


class TextEditorOperationButton(QToolButton):
    def __init__(self, op: TextEditorOperation, parent=None):
        super(TextEditorOperationButton, self).__init__(parent)
        self.op: TextEditorOperation = op

        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.PointingHandCursor)

        if isinstance(self.op, TextEditorOperationAction):
            self.setDefaultAction(self.op)
        elif isinstance(self.op, TextEditorOperationMenu):
            btn_popup_menu(self, self.op)
            self.setIcon(self.op.icon())
            self.setToolTip(self.op.toolTip())
        elif isinstance(self.op, TextEditorOperationWidgetAction):
            menu = QMenu(self)
            menu.addAction(self.op)
            self.setIcon(self.op.icon())
            self.setToolTip(self.op.toolTip())
            btn_popup_menu(self, menu)
            self.op.triggered.connect(self.menu().hide)


class TextEditorToolbar(QFrame):
    def __init__(self, parent=None):
        super(TextEditorToolbar, self).__init__(parent)
        self.setStyleSheet('''
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
        hbox(self)
        self._standardOperationButtons: Dict[TextEditorOperationType, TextEditorOperationButton] = {}
        self.btnGroupAlignment = QButtonGroup(self)
        self.btnGroupAlignment.setExclusive(True)

    def addStandardOperation(self, operationType: TextEditorOperationType):
        opAction = self._newOperation(operationType)
        if opAction:
            btn = TextEditorOperationButton(opAction)
            self._standardOperationButtons[operationType] = btn
            self.layout().addWidget(btn)
            if operationType.value.startswith('alignment'):
                self.btnGroupAlignment.addButton(btn)

    def addSeparator(self):
        self.layout().addWidget(vline())

    def addSpacer(self):
        self.layout().addWidget(spacer())

    def setStandardOperationVisible(self, operationType: TextEditorOperationType, visible: bool):
        op = self._getOperationButtonOrFail(operationType)
        op.setVisible(visible)

    def standardOperation(self, operationType: TextEditorOperationType) -> TextEditorOperation:
        return self._getOperationButtonOrFail(operationType).op

    def activate(self, textEdit: QTextEdit):
        for btn in self._standardOperationButtons.values():
            btn.op.activate(textEdit)

    def updateFormat(self, textEdit: QTextEdit):
        for btn in self._standardOperationButtons.values():
            btn.op.updateFormat(textEdit)

    def _getOperationButtonOrFail(self, operationType: TextEditorOperationType) -> TextEditorOperationButton:
        if operationType in self._standardOperationButtons:
            return self._standardOperationButtons[operationType]
        raise ValueError('Operation type is not present in the toolbar: %s', operationType)

    def _newOperation(self, operationType: TextEditorOperationType) -> TextEditorOperation:
        if operationType == TextEditorOperationType.FORMAT:
            return FormatOperation()
        if operationType == TextEditorOperationType.BOLD:
            return BoldOperation()
        if operationType == TextEditorOperationType.ITALIC:
            return ItalicOperation()
        if operationType == TextEditorOperationType.UNDERLINE:
            return UnderlineOperation()
        if operationType == TextEditorOperationType.STRIKETHROUGH:
            return StrikethroughOperation()
        if operationType == TextEditorOperationType.COLOR:
            return ColorOperation()
        if operationType == TextEditorOperationType.ALIGNMENT_LEFT:
            return AlignLeftOperation()
        if operationType == TextEditorOperationType.ALIGNMENT_CENTER:
            return AlignCenterOperation()
        if operationType == TextEditorOperationType.ALIGNMENT_RIGHT:
            return AlignRightOperation()
        if operationType == TextEditorOperationType.INSERT_LIST:
            return InsertListOperation()
        if operationType == TextEditorOperationType.INSERT_NUMBERED_LIST:
            return InsertNumberedListOperation()
        if operationType == TextEditorOperationType.INSERT_LINK:
            return InsertLinkOperation()
        if operationType == TextEditorOperationType.EXPORT_PDF:
            return ExportPdfOperation()
        if operationType == TextEditorOperationType.PRINT:
            return PrintOperation()


class StandardTextEditorToolbar(TextEditorToolbar):
    def __init__(self, parent=None):
        super(StandardTextEditorToolbar, self).__init__(parent)
        self.addStandardOperation(TextEditorOperationType.FORMAT)
        self.addSeparator()
        self.addStandardOperation(TextEditorOperationType.BOLD)
        self.addStandardOperation(TextEditorOperationType.ITALIC)
        self.addStandardOperation(TextEditorOperationType.UNDERLINE)
        self.addStandardOperation(TextEditorOperationType.STRIKETHROUGH)
        self.addSeparator()
        self.addStandardOperation(TextEditorOperationType.COLOR)
        self.addSeparator()
        self.addStandardOperation(TextEditorOperationType.ALIGNMENT_LEFT)
        self.addStandardOperation(TextEditorOperationType.ALIGNMENT_CENTER)
        self.addStandardOperation(TextEditorOperationType.ALIGNMENT_RIGHT)
        self.addSeparator()
        self.addStandardOperation(TextEditorOperationType.INSERT_LIST)
        self.addStandardOperation(TextEditorOperationType.INSERT_NUMBERED_LIST)
        self.addSeparator()
        self.addStandardOperation(TextEditorOperationType.INSERT_LINK)
        self.addSpacer()
        self.addStandardOperation(TextEditorOperationType.EXPORT_PDF)
        self.addStandardOperation(TextEditorOperationType.PRINT)

    def setStandardOperations(self, operations: List[TextEditorOperationType]):
        for op in TextEditorOperationType:
            self.setStandardOperationVisible(op, False)
        for op in operations:
            self.setStandardOperationVisible(op, True)


class RichTextEditor(QWidget):
    def __init__(self, parent=None):
        super(RichTextEditor, self).__init__(parent)
        vbox(self, 0, 0)

        self.toolbar = StandardTextEditorToolbar(self)
        self.textEdit = self._initTextEdit()
        self.toolbar.activate(self.textEdit)

        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.textEdit)

        self.textEdit.cursorPositionChanged.connect(lambda: self.toolbar.updateFormat(self.textEdit))

    def setToolbar(self, toolbar: TextEditorToolbar):
        self.toolbar = toolbar

    def _initTextEdit(self) -> EnhancedTextEdit:
        return EnhancedTextEdit(self)
