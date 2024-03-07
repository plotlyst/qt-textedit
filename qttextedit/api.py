from enum import Enum
from typing import Dict, Optional, Any, Type

import qtanim
import qtawesome
from qthandy import vbox, hbox, spacer, vline, btn_popup_menu, margins, translucent, transparent, clear_layout, pointy
from qtpy import QtGui
from qtpy.QtCore import Qt, QMimeData, QSize, QUrl, QBuffer, QIODevice, QPoint, QEvent, Signal, QMargins
from qtpy.QtGui import QContextMenuEvent, QDesktopServices, QFont, QTextBlockFormat, QTextCursor, QTextList, \
    QTextCharFormat, QTextFormat, QTextBlock, QTextTable, QTextTableCell, QTextLength, QTextTableFormat, QKeyEvent, \
    QColor
from qtpy.QtWidgets import QMenu, QWidget, QApplication, QFrame, QButtonGroup, QTextEdit, \
    QInputDialog, QToolButton, QLineEdit

from qttextedit.ops import TextEditorOperation, InsertListOperation, InsertNumberedListOperation, \
    TextEditorOperationAction, TextEditorOperationMenu, \
    TextEditorOperationWidgetAction, TextEditingSettingsOperation, TextEditorSettingsWidget, TextOperation, \
    Heading1Operation, Heading2Operation, Heading3Operation, InsertDividerOperation, InsertRedBannerOperation, \
    InsertBlueBannerOperation, InsertGreenBannerOperation, InsertYellowBannerOperation, InsertPurpleBannerOperation, \
    InsertGrayBannerOperation, InsertTableOperation, AlignmentOperation, FormatOperation, BoldOperation, \
    ItalicOperation, UnderlineOperation, StrikethroughOperation, ColorOperation, AlignLeftOperation, \
    AlignCenterOperation, AlignRightOperation, InsertLinkOperation, ExportPdfOperation, PrintOperation
from qttextedit.util import select_anchor, select_previous_character, select_next_character, ELLIPSIS, EN_DASH, EM_DASH, \
    is_open_quotation, is_ending_punctuation, has_character_left, LEFT_SINGLE_QUOTATION, RIGHT_SINGLE_QUOTATION, \
    has_character_right, RIGHT_DOUBLE_QUOTATION, LEFT_DOUBLE_QUOTATION, LONG_ARROW_LEFT_RIGHT, HEAVY_ARROW_RIGHT, \
    SHORT_ARROW_LEFT_RIGHT, qta_icon, remove_font


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


class _SideBarButton(QToolButton):
    def __init__(self, icon_name: str, tooltip: str = '', icon_color: str = 'black', parent=None):
        super(_SideBarButton, self).__init__(parent)
        self.setIcon(qta_icon(icon_name, icon_color))
        self.setToolTip(tooltip)
        self.setProperty('textedit-sidebar-button', True)
        self.setStyleSheet('''
        
        QToolButton:pressed[textedit-sidebar-button=true] {
            border: 1px solid grey
        }
        
        QToolButton[textedit-sidebar-button] {
            border-radius: 10px;
            border: 1px hidden lightgrey;
            padding: 1px;
        }
        QToolButton::menu-indicator[textedit-sidebar-button] {
            width:0px;
        }
        QToolButton:hover[textedit-sidebar-button] {
            background: lightgrey;
        }
        ''')
        translucent(self)
        self.setIconSize(QSize(18, 18))


class EnhancedTextEdit(QTextEdit):

    def __init__(self, parent=None):
        super(EnhancedTextEdit, self).__init__(parent)
        self._pasteAsPlain: bool = False
        self._pasteAsOriginal: bool = False
        self._blockAutoCapitalization: bool = True
        self._sentenceAutoCapitalization: bool = False
        self._uneditableBlocksEnabled: bool = False
        self._sidebarEnabled: bool = True
        self._commandsEnabled: bool = True
        self._dashInsertionMode: DashInsertionMode = DashInsertionMode.NONE
        self._editionState: _TextEditionState = _TextEditionState.ALLOWED
        self._blockFormatPosition: int = -1
        self._defaultBlockFormat = QTextBlockFormat()
        self._currentHoveredTable: Optional[QTextTable] = None
        self._currentHoveredTableCell: Optional[QTextTableCell] = None

        self._btnTablePlusAbove = _SideBarButton('fa5s.plus', 'Insert a new row above', parent=self)
        self._btnTablePlusAbove.setHidden(True)
        self._btnTablePlusBelow = _SideBarButton('fa5s.plus', 'Insert a new row below', parent=self)
        self._btnTablePlusBelow.setHidden(True)
        self._btnTablePlusAbove.clicked.connect(self._insertRowAbove)
        self._btnTablePlusBelow.clicked.connect(self._insertRowBelow)
        self._btnTablePlusLeft = _SideBarButton('fa5s.plus', 'Insert a new column to the left', parent=self)
        self._btnTablePlusLeft.setHidden(True)
        self._btnTablePlusRight = _SideBarButton('fa5s.plus', 'Insert a new column to the right', parent=self)
        self._btnTablePlusRight.setHidden(True)
        self._btnTablePlusLeft.clicked.connect(self._insertColumnLeft)
        self._btnTablePlusRight.clicked.connect(self._insertColumnRight)

        self._btnPlus = _SideBarButton('fa5s.plus', 'Click to add a block below', parent=self)
        self._btnPlus.setHidden(True)
        self._btnPlus.clicked.connect(lambda: self._insertBlock(self._blockFormatPosition, showCommands=True))

        self._blockFormatMenu = QMenu()
        self._blockFormatMenu.setToolTipsVisible(True)
        self._blockFormatMenu.addAction(qta_icon('fa5.copy'), 'Duplicate',
                                        lambda: self._duplicateBlock(self._blockFormatPosition))
        self._convertIntoMenu = QMenu('Convert into')
        for op_clazz in [TextOperation, Heading1Operation, Heading2Operation, Heading3Operation, InsertListOperation,
                         InsertNumberedListOperation]:
            action = op_clazz(self._convertIntoMenu)
            self._convertIntoMenu.addAction(action)
            action.activateOperation(self)

        self._blockFormatMenu.addMenu(self._convertIntoMenu)
        self._blockFormatMenu.addSeparator()
        self._blockFormatMenu.addAction(qta_icon('fa5s.trash-alt'), 'Delete',
                                        lambda: self._deleteBlock(self._blockFormatPosition))

        self._btnBlockFormat = _SideBarButton('ph.dots-six-vertical-bold', 'Click to open menu', parent=self)
        self._btnBlockFormat.setHidden(True)
        btn_popup_menu(self._btnBlockFormat, self._blockFormatMenu)

        self.document().setDocumentMargin(40)

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

    def sidebarEnabled(self) -> bool:
        return self._sidebarEnabled

    def setSidebarEnabled(self, value: bool):
        self._sidebarEnabled = value

    def setCommandsEnabled(self, value: bool):
        self._commandsEnabled = value

    def setDocumentMargin(self, value: int):
        self.document().setDocumentMargin(value)

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
        action.setDisabled(self.isReadOnly())

        menu.addSeparator()
        paste_submenu = menu.addMenu('Paste as...')
        paste_submenu.setToolTipsVisible(True)
        paste_submenu.setDisabled(self.isReadOnly())
        action = paste_submenu.addAction('Paste as plain text', self.pasteAsPlainText)
        action.setToolTip('Paste as plain text without any formatting')
        action.setDisabled(self.isReadOnly())
        action = paste_submenu.addAction('Paste with original style', self.pasteAsOriginalText)
        action.setToolTip('Paste with the original formatting')
        action.setDisabled(self.isReadOnly())

        anchor = self.anchorAt(pos)
        if anchor:
            menu.addSeparator()
            menu.addAction(qta_icon('fa5s.link'), 'Edit link',
                           lambda: self._editLink(self.cursorForPosition(pos)))

        if self._currentHoveredTable is not None:
            menu.addSeparator()
            menu.addAction(qta_icon('mdi.table-row-remove', 'red'), 'Delete row', self._removeRow)
            menu.addAction(qta_icon('mdi.table-column-remove', 'red'), 'Delete column', self._removeColumn)

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
            if source.hasHtml():
                self.insertHtml(remove_font(source.html()))
            elif source.hasText():
                self.insertPlainText(source.text())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        super(EnhancedTextEdit, self).mouseMoveEvent(event)

        cursor: QTextCursor = self.cursorForPosition(event.pos())
        beginningCursor = QTextCursor(cursor.block())
        rect = self.cursorRect(beginningCursor)
        self._currentHoveredTable = cursor.currentTable()
        if self._currentHoveredTable:
            self._currentHoveredTableCell = self._currentHoveredTable.cellAt(cursor)
            self._btnPlus.setHidden(True)
            self._btnBlockFormat.setHidden(True)

            self._btnTablePlusAbove.setGeometry(self.viewportMargins().left() + rect.x() - 16, rect.y() - 10, 16, 16)
            self._btnTablePlusAbove.setVisible(True)
            beginningCursor.movePosition(QTextCursor.EndOfBlock)
            self._btnTablePlusBelow.setGeometry(self.viewportMargins().left() + rect.x() - 16,
                                                self.cursorRect(beginningCursor).y() + rect.height() - 8,
                                                16, 16)
            self._btnTablePlusBelow.setVisible(True)

            constraint: QTextLength = self._currentHoveredTable.format().columnWidthConstraints()[
                self._currentHoveredTableCell.column()]
            cell_width = self.document().size().width() * constraint.rawValue() / 100

            self._btnTablePlusLeft.setGeometry(self.viewportMargins().left() + rect.x() - 8, rect.y() - 18, 16, 16)
            self._btnTablePlusLeft.setVisible(True)

            self._btnTablePlusRight.setGeometry(
                int(self.viewportMargins().left() + rect.x() + cell_width - self._currentHoveredTable.format().leftMargin() - 20),
                int(rect.y() - 18), 16, 16)
            self._btnTablePlusRight.setVisible(True)

        else:
            self._btnTablePlusAbove.setHidden(True)
            self._btnTablePlusBelow.setHidden(True)
            self._btnTablePlusLeft.setHidden(True)
            self._btnTablePlusRight.setHidden(True)
            if self._sidebarEnabled and self._blockFormatPosition != cursor.blockNumber():
                self._blockFormatPosition = cursor.blockNumber()

                y_diff = (rect.height() - 20) // 2 + self.viewportMargins().top()
                self._btnPlus.setGeometry(self.viewportMargins().left(), rect.y() + y_diff, 20, 20)
                self._btnBlockFormat.setGeometry(self.viewportMargins().left() + 20, rect.y() + y_diff, 20, 20)
                self._btnPlus.setVisible(True)
                self._btnBlockFormat.setVisible(True)

        if cursor.atBlockStart() or cursor.atBlockEnd():
            QApplication.restoreOverrideCursor()
        else:
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

    def enterEvent(self, event: QEvent) -> None:
        super(EnhancedTextEdit, self).enterEvent(event)
        if self._blockFormatPosition >= 0:
            self._btnPlus.setVisible(True)
            self._btnBlockFormat.setVisible(True)

    def leaveEvent(self, event: QEvent) -> None:
        super(EnhancedTextEdit, self).leaveEvent(event)
        self._btnPlus.setHidden(True)
        self._btnBlockFormat.setHidden(True)
        self._btnTablePlusAbove.setHidden(True)
        self._btnTablePlusBelow.setHidden(True)
        self._btnTablePlusLeft.setHidden(True)
        self._btnTablePlusRight.setHidden(True)

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
        if event.key() == Qt.Key_Return and not event.modifiers():
            self._insertNewBlock(cursor)
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
        if self._commandsEnabled and event.key() == Qt.Key_Slash and self.textCursor().atBlockStart():
            self._showCommands()
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

    def setBlockFormat(self, lineSpacing: int = 100, textIndent: int = 0, margin_left: int = 0, margin_top: int = 0,
                       margin_right: int = 0, margin_bottom: int = 0):
        blockFmt = QTextBlockFormat()
        blockFmt.setTextIndent(textIndent)
        blockFmt.setLineHeight(lineSpacing, 1)
        blockFmt.setLeftMargin(margin_left)
        blockFmt.setTopMargin(margin_top)
        blockFmt.setRightMargin(margin_right)
        blockFmt.setBottomMargin(margin_bottom)

        self._defaultBlockFormat = blockFmt

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
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        self.setTextCursor(cursor)

        blockFormat: QTextBlockFormat = cursor.blockFormat()
        blockFormat.setHeadingLevel(heading)
        cursor.setBlockFormat(blockFormat)
        sizeAdjustment = 4 - heading if heading else 0

        charFormat = QTextCharFormat()
        charFormat.setFontWeight(QFont.Bold if heading else QFont.Normal)
        charFormat.setProperty(QTextFormat.FontSizeAdjustment, sizeAdjustment)
        cursor.mergeBlockCharFormat(charFormat)
        self.mergeCurrentCharFormat(charFormat)

        cursor.clearSelection()
        self.setTextCursor(cursor)
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

    def _insertBlock(self, blockNumber: int, showCommands: bool = False):
        block: QTextBlock = self.document().findBlockByNumber(blockNumber)
        cursor = QTextCursor(block)
        if cursor.currentTable():
            self._insertRowBelow()
            return
        else:
            cursor.movePosition(QTextCursor.EndOfBlock)
        self._insertNewBlock(cursor, showCommands)
        self.setTextCursor(cursor)

    def _insertNewBlock(self, cursor: QTextCursor, showCommands: bool = False):
        if cursor.block().textList() and not cursor.block().text():
            list_ = cursor.block().textList()
            list_.remove(cursor.block())
            cursor.deletePreviousChar()
            cursor.insertBlock(self._defaultBlockFormat, QTextCharFormat())
        elif cursor.block().textList():
            cursor.insertBlock(cursor.blockFormat(), QTextCharFormat())
        else:
            cursor.insertBlock(self._defaultBlockFormat, QTextCharFormat())
            if showCommands:
                self._showCommands()
        self.ensureCursorVisible()

    def _duplicateBlock(self, blockNumber: int):
        block: QTextBlock = self.document().findBlockByNumber(blockNumber)
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        fragment = cursor.selection()

        cursor.beginEditBlock()
        self._insertBlock(blockNumber)
        self.textCursor().insertFragment(fragment)
        cursor.endEditBlock()

    def _deleteBlock(self, blockNumber: int, force: bool = False):
        block: QTextBlock = self.document().findBlockByNumber(blockNumber)
        if self.__blockUneditable(block) and not force:
            return
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
        if self.__blockUneditable(cursor.block()) and not force:
            return

        cursor = QTextCursor(block)
        cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        if block.isValid():
            cursor.deleteChar()
        cursor.endEditBlock()

    def _insertRowAbove(self):
        if self._currentHoveredTableCell is None:
            return
        self._currentHoveredTable.insertRows(self._currentHoveredTableCell.row(), 1)

    def _insertRowBelow(self):
        if self._currentHoveredTableCell is None:
            return
        self._currentHoveredTable.insertRows(self._currentHoveredTableCell.row() + 1, 1)

    def _insertColumnLeft(self):
        if self._currentHoveredTableCell is None:
            return
        self._currentHoveredTable.insertColumns(self._currentHoveredTableCell.column(), 1)
        self._resizeTableColumns(self._currentHoveredTable)

    def _insertColumnRight(self):
        if self._currentHoveredTableCell is None:
            return
        self._currentHoveredTable.insertColumns(self._currentHoveredTableCell.column() + 1, 1)
        self._resizeTableColumns(self._currentHoveredTable)

    def _removeRow(self):
        if self._currentHoveredTableCell is None:
            return
        self._currentHoveredTable.removeRows(self._currentHoveredTableCell.row(), 1)
        self._resizeTableColumns(self._currentHoveredTable)

    def _removeColumn(self):
        if self._currentHoveredTableCell is None:
            return
        self._currentHoveredTable.removeColumns(self._currentHoveredTableCell.column(), 1)
        self._resizeTableColumns(self._currentHoveredTable)

    def _resizeTableColumns(self, table: QTextTable):
        format: QTextTableFormat = table.format()
        format.clearColumnWidthConstraints()

        constraints = []
        if table.columns() > 3:
            percent = 100 // table.columns()
        else:
            percent = 25
        for _ in range(table.columns()):
            constraints.append(QTextLength(QTextLength.PercentageLength, percent))
        format.setColumnWidthConstraints(constraints)
        table.setFormat(format)

    def _showCommands(self):
        def cleanUp():
            if not self.textCursor().atBlockStart():
                self.textCursor().deletePreviousChar()

        rect = self.cursorRect()

        menu = QMenu(self)
        menu.setToolTipsVisible(True)
        for op_clazz in [Heading1Operation, Heading2Operation, Heading3Operation, InsertListOperation,
                         InsertNumberedListOperation, InsertTableOperation, InsertDividerOperation,
                         InsertGrayBannerOperation,
                         InsertRedBannerOperation,
                         InsertBlueBannerOperation, InsertGreenBannerOperation, InsertYellowBannerOperation,
                         InsertPurpleBannerOperation]:
            action = op_clazz(menu)
            action.activateOperation(self)
            menu.addAction(action)
        menu.aboutToHide.connect(cleanUp)

        menu.popup(self.viewport().mapToGlobal(QPoint(rect.x(), rect.y())))


class TextEditorOperationButton(QToolButton):
    def __init__(self, op: TextEditorOperation, parent=None):
        super(TextEditorOperationButton, self).__init__(parent)
        self.op: TextEditorOperation = op
        pointy(self)

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
        self._linkedTextEdit: Optional[QTextEdit] = None
        self._linkedTextEditor: Optional['RichTextEditor'] = None
        self._textEditorOperations: Dict[Any, TextEditorOperationButton] = {}
        self.btnGroupAlignment = QButtonGroup(self)
        self.btnGroupAlignment.setExclusive(True)

    def addTextEditorOperation(self, operationType: Type[TextEditorOperation]):
        operation, btn = self._initOperation(operationType)
        if self._linkedTextEdit:
            operation.activateOperation(self._linkedTextEdit, self._linkedTextEditor)
        self.layout().addWidget(btn)

    def insertTextEditorOperationBefore(self, reference: Type[TextEditorOperation],
                                        operationType: Type[TextEditorOperation]):
        refBtn = self._getOperationButtonOrFail(reference)
        i = self.layout().indexOf(refBtn)
        _, btn = self._initOperation(operationType)
        self.layout().insertWidget(i, btn)

    def insertTextEditorOperationAfter(self, reference: Type[TextEditorOperation],
                                       operationType: Type[TextEditorOperation]):
        refBtn = self._getOperationButtonOrFail(reference)
        i = self.layout().indexOf(refBtn)
        _, btn = self._initOperation(operationType)
        self.layout().insertWidget(i + 1, btn)

    def addWidget(self, widget):
        self.layout().addWidget(widget)

    def addSeparator(self):
        self.layout().addWidget(vline())

    def addSpacer(self):
        self.layout().addWidget(spacer())

    def setTextEditorOperationVisible(self, operationType: Type[TextEditorOperation], visible: bool):
        op = self._getOperationButtonOrFail(operationType)
        op.setVisible(visible)

    def textEditorOperation(self, operationType: Type[TextEditorOperation]) -> TextEditorOperation:
        return self._getOperationButtonOrFail(operationType).op

    def clear(self):
        self._textEditorOperations.clear()
        clear_layout(self)

    def activate(self, textEdit: QTextEdit, editor: Optional['RichTextEditor'] = None):
        self._linkedTextEdit = textEdit
        self._linkedTextEditor = editor
        for btn in self._textEditorOperations.values():
            btn.op.activateOperation(textEdit, editor)

    def updateFormat(self, textEdit: QTextEdit):
        for btn in self._textEditorOperations.values():
            btn.op.updateFormat(textEdit)

    def _initOperation(self, operationType: Type[TextEditorOperation]):
        operation = operationType()
        btn = TextEditorOperationButton(operation)
        self._textEditorOperations[operationType] = btn

        if isinstance(operation, AlignmentOperation):
            self.btnGroupAlignment.addButton(btn)

        return operation, btn

    def _getOperationButtonOrFail(self, operationType: Type[TextEditorOperation]) -> TextEditorOperationButton:
        if operationType in self._textEditorOperations:
            return self._textEditorOperations[operationType]
        raise ValueError('Operation type is not present in the toolbar: %s', operationType)


class StandardTextEditorToolbar(TextEditorToolbar):
    def __init__(self, parent=None):
        super(StandardTextEditorToolbar, self).__init__(parent)
        self.addTextEditorOperation(FormatOperation)
        self.addSeparator()
        self.addTextEditorOperation(BoldOperation)
        self.addTextEditorOperation(ItalicOperation)
        self.addTextEditorOperation(UnderlineOperation)
        self.addTextEditorOperation(StrikethroughOperation)
        self.addSeparator()
        self.addTextEditorOperation(ColorOperation)
        self.addSeparator()
        self.addTextEditorOperation(AlignLeftOperation)
        self.addTextEditorOperation(AlignCenterOperation)
        self.addTextEditorOperation(AlignRightOperation)
        self.addSeparator()
        self.addTextEditorOperation(InsertListOperation)
        self.addTextEditorOperation(InsertNumberedListOperation)
        self.addSeparator()
        self.addTextEditorOperation(InsertTableOperation)
        self.addSeparator()
        self.addTextEditorOperation(InsertLinkOperation)
        self.addSpacer()
        self.addTextEditorOperation(ExportPdfOperation)
        self.addTextEditorOperation(PrintOperation)
        self.addSeparator()
        self.addTextEditorOperation(TextEditingSettingsOperation)


class TextEditorSettingsButton(TextEditorOperationButton):
    def __init__(self, parent=None):
        self._settingsOp = TextEditingSettingsOperation()
        super(TextEditorSettingsButton, self).__init__(self._settingsOp, parent)

    def settingsWidget(self) -> TextEditorSettingsWidget:
        return self._settingsOp.settingsWidget()


class TextFindWidget(QFrame):
    find = Signal(str)
    findNext = Signal(str)
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self)
        self._icon = QToolButton()
        transparent(self._icon)
        self._icon.setIcon(qta_icon('mdi.magnify'))
        self._lineText = QLineEdit()
        self._lineText.setPlaceholderText('Find...')
        self._lineText.setClearButtonEnabled(True)
        self._lineText.setMaximumWidth(150)
        self.layout().addWidget(spacer())
        self.layout().addWidget(self._icon)
        self.layout().addWidget(self._lineText)
        margins(self, right=10)
        self.setStyleSheet('''TextFindWidget {
                                background-color: white;
                            }''')

        self._lineText.textChanged.connect(self.find.emit)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and self._lineText.text():
            self.findNext.emit(self._lineText.text())
        elif event.key() == Qt.Key_Escape:
            self.closed.emit()

    def activate(self):
        self._lineText.setFocus()

    def showZeroFind(self):
        qtanim.glow(self._lineText, duration=300)
        qtanim.glow(self._icon, duration=300)

    def showFindOver(self):
        qtanim.glow(self._lineText, color=QColor('#ffb703'))
        qtanim.glow(self._icon, color=QColor('#ffb703'))


class RichTextEditor(QWidget):
    settingsAttached = Signal()

    def __init__(self, parent=None):
        super(RichTextEditor, self).__init__(parent)
        vbox(self, 0, 0)
        self._widthPercentage: int = 0
        self._maxContentWidth: int = -1
        self._settings: Optional[TextEditorSettingsWidget] = None

        self._toolbar = StandardTextEditorToolbar(self)
        self._wdgFind = TextFindWidget(self)
        self._wdgFind.setHidden(True)
        self._findCursor: Optional[QTextCursor] = None

        self._textedit = self._initTextEdit()
        self._wdgFind.find.connect(self._find)
        self._wdgFind.findNext.connect(self._findNext)
        self._wdgFind.closed.connect(lambda: self._wdgFind.setHidden(True))

        self.layout().addWidget(self._toolbar)
        self.layout().addWidget(self._wdgFind)
        self.layout().addWidget(self._textedit)

        self._toolbar.activate(self._textedit, self)
        self._textedit.cursorPositionChanged.connect(lambda: self._toolbar.updateFormat(self._textedit))

    @property
    def textEdit(self):
        return self._textedit

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self._wdgFind.setVisible(True)
            self._wdgFind.activate()
        elif event.key() == Qt.Key_Escape and self._wdgFind.isVisible():
            self._wdgFind.setHidden(True)
        else:
            super(RichTextEditor, self).keyPressEvent(event)

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
        self.settingsAttached.emit()

    def widthPercentage(self) -> int:
        return self._widthPercentage

    def setCharacterWidth(self, count: int = 80):
        metrics = QtGui.QFontMetricsF(self._textedit.font())
        self._maxContentWidth = metrics.boundingRect('M' * count).width()
        self._resize()

    def characterWidth(self) -> int:
        return self._maxContentWidth

    def setWidthPercentage(self, percentage: int):
        if 0 < percentage <= 100:
            self._widthPercentage = percentage
            self._resize()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        if self._widthPercentage > 0 or self._maxContentWidth > 0:
            self._resize()

    def _resize(self):
        if 0 < self._maxContentWidth < self.width():
            margin = self.width() - self._maxContentWidth
        elif self._widthPercentage > 0:
            margin = self.width() * (100 - self._widthPercentage) // 100
        else:
            margin = 0

        margin = int(margin // 2)
        current_margins: QMargins = self._textedit.viewportMargins()
        self._textedit.setViewportMargins(margin, current_margins.top(), margin, current_margins.bottom())
        margins(self._toolbar, left=margin)

    def _initTextEdit(self) -> EnhancedTextEdit:
        return EnhancedTextEdit(self)

    def _find(self, text: str):
        if not text:
            self._findCursor = None
            return
        match: QTextCursor = self._textedit.document().find(text)
        if match.isNull():
            self._wdgFind.showZeroFind()
        else:
            self._findCursor = match
            self._textedit.setTextCursor(self._findCursor)
            self._textedit.ensureCursorVisible()

    def _findNext(self, text: str):
        if self._findCursor is None:
            match: QTextCursor = self._textedit.document().find(text)
        else:
            match = self._textedit.document().find(text, position=self._findCursor.position())

        if match.isNull():
            if self._findCursor is None:
                self._wdgFind.showZeroFind()
            else:
                self._wdgFind.showFindOver()
                self._findCursor = QTextCursor(self._textedit.document())
        else:
            self._findCursor = match
            self._textedit.setTextCursor(self._findCursor)
            self._textedit.ensureCursorVisible()
