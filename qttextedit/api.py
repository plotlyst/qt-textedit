import re
from enum import Enum
from typing import List, Dict, Optional

import qtawesome
from qthandy import vbox, hbox, spacer, vline, btn_popup_menu, margins
from qtpy import QtGui
from qtpy.QtCore import Qt, QMimeData, QSize, QUrl, QBuffer, QIODevice, QPoint
from qtpy.QtGui import QContextMenuEvent, QDesktopServices, QFont, QTextBlockFormat, QTextCursor, QTextList, \
    QTextCharFormat, QTextFormat, QTextBlock
from qtpy.QtWidgets import QMenu, QWidget, QApplication, QFrame, QButtonGroup, QTextEdit, \
    QInputDialog, QToolButton

from qttextedit.ops import TextEditorOperationType, TextEditorOperation, FormatOperation, BoldOperation, \
    ItalicOperation, UnderlineOperation, StrikethroughOperation, ColorOperation, AlignLeftOperation, \
    AlignCenterOperation, AlignRightOperation, InsertListOperation, InsertNumberedListOperation, InsertLinkOperation, \
    ExportPdfOperation, PrintOperation, TextEditorOperationAction, TextEditorOperationMenu, \
    TextEditorOperationWidgetAction, TextEditingSettingsOperation, TextEditorSettingsWidget
from qttextedit.util import select_anchor, select_previous_character, select_next_character, ELLIPSIS, EN_DASH, EM_DASH, \
    is_open_quotation, is_ending_punctuation, has_character_left, LEFT_SINGLE_QUOTATION, RIGHT_SINGLE_QUOTATION, \
    has_character_right, RIGHT_DOUBLE_QUOTATION, LEFT_DOUBLE_QUOTATION, LONG_ARROW_LEFT_RIGHT, HEAVY_ARROW_RIGHT, \
    SHORT_ARROW_LEFT_RIGHT


class DashInsertionMode(Enum):
    NONE = 0
    INSERT_EN_DASH = 1
    INSERT_EM_DASH = 2


class TextBlockState(Enum):
    UNEDITABLE = 10001


class _TextEditionState(Enum):
    ALLOWED = 0
    DEL_BLOCKED = 1
    BACKSPACE_BLOCKED = 2
    REMOVAL_BLOCKED = 3
    DISALLOWED = 4


class EnhancedTextEdit(QTextEdit):

    def __init__(self, parent=None):
        super(EnhancedTextEdit, self).__init__(parent)
        self._pasteAsPlain: bool = False
        self._pasteAsOriginal: bool = False
        self._blockAutoCapitalization: bool = True
        self._sentenceAutoCapitalization: bool = False
        self._uneditableBlocksEnabled: bool = False
        self._dashInsertionMode: DashInsertionMode = DashInsertionMode.NONE
        self._editionState: _TextEditionState = _TextEditionState.ALLOWED

        self._adjustTabDistance()

        self.cursorPositionChanged.connect(self._cursorPositionChanged)
        self.textChanged.connect(self._cursorPositionChanged)
        self.selectionChanged.connect(self._selectionChanged)

    def blockAutoCapitalizationEnabled(self) -> bool:
        return self._blockAutoCapitalization

    def setBlockAutoCapitalizationEnabled(self, enabled: bool):
        self._blockAutoCapitalization = enabled

    def sentenceAutoCapitalizationEnabled(self) -> bool:
        return self._sentenceAutoCapitalization

    def setSentenceAutoCapitalizationEnabled(self, enabled: bool):
        self._sentenceAutoCapitalization = enabled

    def setAutoCapitalizationEnabled(self, enabled: bool):
        self._blockAutoCapitalization = enabled
        self._sentenceAutoCapitalization = enabled

    def dashInsertionMode(self) -> DashInsertionMode:
        return self._dashInsertionMode

    def setDashInsertionMode(self, mode: DashInsertionMode):
        self._dashInsertionMode = mode

    def uneditableBlocksEnabled(self) -> bool:
        return self._uneditableBlocksEnabled

    def setUneditableBlocksEnabled(self, enabled: bool):
        self._uneditableBlocksEnabled = enabled
        if not enabled:
            self._editionState = _TextEditionState.ALLOWED

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

    def selectAll(self):
        if self.__blocksUneditable(end=self.document().blockCount()):
            self._editionState = _TextEditionState.DISALLOWED
        super(EnhancedTextEdit, self).selectAll()

    def cut(self):
        if self._editionState == _TextEditionState.DISALLOWED:
            return
        super(EnhancedTextEdit, self).cut()

    def insertFromMimeData(self, source: QMimeData) -> None:
        if self._editionState == _TextEditionState.DISALLOWED:
            return
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
        if self._editionState == _TextEditionState.DISALLOWED:
            if event.key() not in (Qt.Key_Up, Qt.Key_Down):
                return

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
        if event.text().isalpha():
            if (self._blockAutoCapitalization and cursor.atBlockStart()) or (
                    self._sentenceAutoCapitalization and self._atSentenceStart(cursor)):
                self.textCursor().insertText(event.text().upper())
                return
        if event.key() == Qt.Key_Return:
            if cursor.block().textList() and not cursor.block().text():
                list_ = cursor.block().textList()
                list_.remove(cursor.block())
                cursor.deletePreviousChar()
                self.textCursor().insertBlock(QTextBlockFormat(), QTextCharFormat())
                return
            self.textCursor().insertBlock(self.textCursor().blockFormat(), QTextCharFormat())
            self.ensureCursorVisible()
            return
        if event.key() == Qt.Key_Period:
            moved_cursor = select_previous_character(cursor, amount=2)
            if moved_cursor.selectedText() == '..':
                moved_cursor.removeSelectedText()
                cursor.insertText(ELLIPSIS)
                return
        if event.key() == Qt.Key_Minus and self._dashInsertionMode != DashInsertionMode.NONE:
            moved_cursor = select_previous_character(cursor)
            if moved_cursor.selectedText() == '-':
                cursor.deletePreviousChar()
                if self._dashInsertionMode == DashInsertionMode.INSERT_EN_DASH:
                    cursor.insertText(EN_DASH)
                elif self._dashInsertionMode == DashInsertionMode.INSERT_EM_DASH:
                    cursor.insertText(EM_DASH)
                return
        if event.key() == Qt.Key_Greater:
            moved_cursor = select_previous_character(cursor, 2)
            if moved_cursor.selectedText() == '<-':
                cursor.deletePreviousChar()
                cursor.deletePreviousChar()
                cursor.insertText(LONG_ARROW_LEFT_RIGHT)
                return
            moved_cursor = select_previous_character(cursor)
            if moved_cursor.selectedText() == '-':
                cursor.deletePreviousChar()
                cursor.insertText(HEAVY_ARROW_RIGHT)
                return
            if moved_cursor.selectedText() == '<':
                cursor.deletePreviousChar()
                cursor.insertText(SHORT_ARROW_LEFT_RIGHT)
                return
        if event.key() == Qt.Key_Apostrophe:
            if has_character_left(cursor):
                self.textCursor().insertText(RIGHT_SINGLE_QUOTATION)
            elif has_character_right(cursor):
                self.textCursor().insertText(LEFT_SINGLE_QUOTATION)
            else:
                self.textCursor().insertText(LEFT_SINGLE_QUOTATION)
                self.textCursor().insertText(RIGHT_SINGLE_QUOTATION)
                cursor.movePosition(QTextCursor.PreviousCharacter)
                self.setTextCursor(cursor)
            return
        if event.key() == Qt.Key_QuoteDbl:
            if has_character_left(cursor):
                self.textCursor().insertText(RIGHT_DOUBLE_QUOTATION)
            elif has_character_right(cursor):
                self.textCursor().insertText(LEFT_DOUBLE_QUOTATION)
            else:
                self.textCursor().insertText(LEFT_DOUBLE_QUOTATION)
                self.textCursor().insertText(RIGHT_DOUBLE_QUOTATION)
                cursor.movePosition(QTextCursor.PreviousCharacter)
                self.setTextCursor(cursor)
            return
        if event.key() == Qt.Key_Delete and (
                self._editionState == _TextEditionState.DEL_BLOCKED or
                self._editionState == _TextEditionState.REMOVAL_BLOCKED):
            return
        if event.key() == Qt.Key_Backspace and (
                self._editionState == _TextEditionState.BACKSPACE_BLOCKED or
                self._editionState == _TextEditionState.REMOVAL_BLOCKED):
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
        blockFmt.setLineHeight(lineSpacing, 1)

        cursor = self.textCursor()
        cursor.clearSelection()
        cursor.select(QTextCursor.Document)
        cursor.mergeBlockFormat(blockFmt)

    def setStrikethrough(self, strikethrough: bool):
        font = self.currentFont()
        font.setStrikeOut(strikethrough)
        self.setCurrentFont(font)

    def zoomIn(self, range: int = ...) -> None:
        super(EnhancedTextEdit, self).zoomIn(range)
        self._adjustTabDistance()

    def zoomOut(self, range: int = ...) -> None:
        super(EnhancedTextEdit, self).zoomOut(range)
        self._adjustTabDistance()

    def resetTextColor(self):
        format = self.textCursor().charFormat()
        format.clearBackground()
        format.clearForeground()
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

    def _adjustTabDistance(self):
        self.setTabStopDistance(QtGui.QFontMetricsF(self.font()).horizontalAdvance(' ') * 4)

    def _cursorPositionChanged(self):
        if not self._uneditableBlocksEnabled:
            return
        if self.textCursor().block().userState() == TextBlockState.UNEDITABLE.value:
            cursor = self.textCursor()
            self._editionState = _TextEditionState.DISALLOWED
            cursor.movePosition(QTextCursor.StartOfBlock)
            self.setTextCursor(cursor)
            return
        if self.textCursor().atBlockEnd():
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
            if cursor.block().userState() == TextBlockState.UNEDITABLE.value:
                self._editionState = _TextEditionState.DEL_BLOCKED
        if self.textCursor().atBlockStart():
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock)
            if cursor.block().userState() == TextBlockState.UNEDITABLE.value:
                if self._editionState == _TextEditionState.DEL_BLOCKED:
                    self._editionState = _TextEditionState.REMOVAL_BLOCKED
                else:
                    self._editionState = _TextEditionState.BACKSPACE_BLOCKED
                return

        self._editionState = _TextEditionState.ALLOWED

    def _selectionChanged(self):
        if not self.textCursor().hasSelection():
            self._editionState = _TextEditionState.ALLOWED
            return
        if not self._uneditableBlocksEnabled:
            return
        first_block = self.document().findBlock(self.textCursor().selectionStart())
        last_block = self.document().findBlock(self.textCursor().selectionEnd())

        if self.__blocksUneditable(first_block, last_block):
            self._editionState = _TextEditionState.DISALLOWED
            return

    def __blocksUneditable(self, firstBlock: QTextBlock, lastBlock: QTextBlock) -> bool:
        if not self._uneditableBlocksEnabled:
            return False
        block = firstBlock
        while block.isValid() and block.blockNumber() <= lastBlock.blockNumber():
            if self.__blockUneditable(block):
                return True
            block = block.next()
        return False

    def __blockUneditable(self, block: QTextBlock) -> bool:
        return self._uneditableBlocksEnabled and block.userState() == TextBlockState.UNEDITABLE.value

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
            if is_ending_punctuation(moved_cursor.selectedText()[0]):
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

    def activate(self, textEdit: QTextEdit, editor: Optional['RichTextEditor'] = None):
        for btn in self._standardOperationButtons.values():
            btn.op.activateOperation(textEdit, editor)

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
        if operationType == TextEditorOperationType.EDITING_SETTINGS:
            return TextEditingSettingsOperation()


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
        self.addSeparator()
        self.addStandardOperation(TextEditorOperationType.EDITING_SETTINGS)

    def setStandardOperations(self, operations: List[TextEditorOperationType]):
        for op in TextEditorOperationType:
            self.setStandardOperationVisible(op, False)
        for op in operations:
            self.setStandardOperationVisible(op, True)


class TextEditorSettingsButton(TextEditorOperationButton):
    def __init__(self, parent=None):
        self._settingsOp = TextEditingSettingsOperation()
        super(TextEditorSettingsButton, self).__init__(self._settingsOp, parent)

    def settingsWidget(self) -> TextEditorSettingsWidget:
        return self._settingsOp.settingsWidget()


class RichTextEditor(QWidget):
    def __init__(self, parent=None):
        super(RichTextEditor, self).__init__(parent)
        vbox(self, 0, 0)
        self._widthPercentage: int = 0
        self._settings: Optional[TextEditorSettingsWidget] = None

        self._toolbar = StandardTextEditorToolbar(self)
        self.textEdit = self._initTextEdit()

        self.layout().addWidget(self._toolbar)
        self.layout().addWidget(self.textEdit)

        self._toolbar.activate(self.textEdit, self)
        self.textEdit.cursorPositionChanged.connect(lambda: self._toolbar.updateFormat(self.textEdit))

    def toolbar(self) -> TextEditorToolbar:
        return self._toolbar

    def setToolbar(self, toolbar: TextEditorToolbar):
        self._toolbar = toolbar

    def settingsWidget(self) -> Optional[TextEditorSettingsWidget]:
        return self._settings

    def attachSettingsWidget(self, widget: TextEditorSettingsWidget):
        if self._settings:
            self._settings.detach()
        self._settings = widget
        widget.attach(self)

    def widthPercentage(self) -> int:
        return self._widthPercentage

    def setWidthPercentage(self, percentage: int):
        if 0 < percentage <= 100:
            self._widthPercentage = percentage
            self._resize()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        if self._widthPercentage:
            self._resize()

    def _resize(self):
        margin = self.width() * (100 - self._widthPercentage) // 100
        margin = margin // 2
        self.textEdit.setViewportMargins(margin, 0, margin, 0)
        margins(self._toolbar, left=margin)

    def _initTextEdit(self) -> EnhancedTextEdit:
        return EnhancedTextEdit(self)
