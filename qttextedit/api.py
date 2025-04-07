from enum import Enum
from typing import Dict, Optional, Any, Type, List

import qtanim
import qtawesome
from qthandy import vbox, hbox, spacer, vline, btn_popup_menu, margins, translucent, transparent, clear_layout, pointy, \
    decr_font, italic
from qthandy.filter import DisabledClickEventFilter, OpacityEventFilter
from qtmenu import MenuWidget
from qtpy import QtGui
from qtpy.QtCore import Qt, QMimeData, QSize, QUrl, QBuffer, QIODevice, QPoint, QEvent, Signal, QMargins, QRect
from qtpy.QtGui import QContextMenuEvent, QDesktopServices, QFont, QTextBlockFormat, QTextCursor, QTextList, \
    QTextCharFormat, QTextFormat, QTextBlock, QTextTable, QTextTableCell, QTextLength, QTextTableFormat, QKeyEvent, \
    QColor, QWheelEvent, QTextDocument, QFocusEvent, QKeySequence
from qtpy.QtWidgets import QMenu, QWidget, QApplication, QFrame, QButtonGroup, QTextEdit, \
    QInputDialog, QToolButton, QLineEdit, QPushButton

from qttextedit.ops import TextEditorOperation, InsertListOperation, InsertNumberedListOperation, \
    TextEditorOperationAction, TextEditorOperationMenu, \
    TextEditorOperationWidgetAction, TextEditingSettingsOperation, TextEditorSettingsWidget, TextOperation, \
    Heading1Operation, Heading2Operation, Heading3Operation, InsertDividerOperation, InsertRedBannerOperation, \
    InsertBlueBannerOperation, InsertGreenBannerOperation, InsertYellowBannerOperation, InsertPurpleBannerOperation, \
    InsertGrayBannerOperation, AlignmentOperation, FormatOperation, BoldOperation, \
    ItalicOperation, UnderlineOperation, StrikethroughOperation, ColorOperation, AlignLeftOperation, \
    AlignCenterOperation, AlignRightOperation, InsertLinkOperation, ExportPdfOperation, PrintOperation
from qttextedit.util import select_anchor, select_previous_character, select_next_character, EN_DASH, EM_DASH, \
    is_open_quotation, is_ending_punctuation, has_character_left, LEFT_SINGLE_QUOTATION, RIGHT_SINGLE_QUOTATION, \
    has_character_right, RIGHT_DOUBLE_QUOTATION, LEFT_DOUBLE_QUOTATION, LONG_ARROW_LEFT_RIGHT, HEAVY_ARROW_RIGHT, \
    SHORT_ARROW_LEFT_RIGHT, qta_icon, q_action, CloseButton, ELLIPSIS


class DashInsertionMode(Enum):
    NONE = 'none'
    INSERT_EN_DASH = 'en'
    INSERT_EM_DASH = 'em'


class EllipsisInsertionMode(Enum):
    NONE = 'none'
    INSERT_ELLIPSIS = 'ellipsis'


class AutoCapitalizationMode(Enum):
    NONE = 'none'
    PARAGRAPH = 'paragraph'
    SENTENCE = 'sentence'


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
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)


class PopupBase(QFrame):

    def freeze(self):
        pass

    def unfreeze(self):
        pass

    def isFrozen(self):
        pass

    def beforeShown(self):
        pass

    def afterShown(self):
        pass


class EnhancedTextEdit(QTextEdit):

    def __init__(self, parent=None):
        super(EnhancedTextEdit, self).__init__(parent)
        self._pasteAsPlain: bool = False
        self._pasteAsOriginal: bool = False
        self._pasteAsOriginalEnabled: bool = True

        self._textIsBeingPasted: bool = False

        self._blockAutoCapitalization: bool = False
        self._sentenceAutoCapitalization: bool = False

        self._uneditableBlocksEnabled: bool = False
        self._sidebarEnabled: bool = True
        self._sidebarMenuEnabled: bool = True
        self._commandsEnabled: bool = True
        self._autoCapitalizationMode: AutoCapitalizationMode = AutoCapitalizationMode.NONE
        self._dashInsertionMode: DashInsertionMode = DashInsertionMode.NONE
        self._ellipsisInsertionMode: EllipsisInsertionMode = EllipsisInsertionMode.NONE
        self._periodInsertionEnabled: bool = True
        self._editionState: _TextEditionState = _TextEditionState.ALLOWED
        self._smartQuotesEnabled: bool = True
        self._blockFormatPosition: int = -1
        self._defaultBlockFormat = QTextBlockFormat()
        self._currentHoveredTable: Optional[QTextTable] = None
        self._currentHoveredTableCell: Optional[QTextTableCell] = None
        self._lastPaintedCursorRect = QRect(0, 0, 0, 0)
        self._placeholderColor = QColor("#5E6C84")
        self._blockPlaceholderEnabled: bool = False
        self._defaultPlaceholder = "Begin writing, or type '/' for commands"

        # self._btnTablePlusAbove = _SideBarButton('fa5s.plus', 'Insert a new row above', parent=self)
        # self._btnTablePlusAbove.setHidden(True)
        # self._btnTablePlusBelow = _SideBarButton('fa5s.plus', 'Insert a new row below', parent=self)
        # self._btnTablePlusBelow.setHidden(True)
        # self._btnTablePlusAbove.clicked.connect(self._insertRowAbove)
        # self._btnTablePlusBelow.clicked.connect(self._insertRowBelow)
        # self._btnTablePlusLeft = _SideBarButton('fa5s.plus', 'Insert a new column to the left', parent=self)
        # self._btnTablePlusLeft.setHidden(True)
        # self._btnTablePlusRight = _SideBarButton('fa5s.plus', 'Insert a new column to the right', parent=self)
        # self._btnTablePlusRight.setHidden(True)
        # self._btnTablePlusLeft.clicked.connect(self._insertColumnLeft)
        # self._btnTablePlusRight.clicked.connect(self._insertColumnRight)

        self._btnPlus = _SideBarButton('ph.plus-light', 'Click to add a block below', parent=self)
        self._btnPlus.setHidden(True)
        self._btnPlus.clicked.connect(lambda: self._insertBlock(self._blockFormatPosition, showCommands=True))
        self._btnBlockFormat = _SideBarButton('ph.dots-six-vertical-bold', 'Click to open menu', parent=self)
        self._btnBlockFormat.setHidden(True)

        self._blockFormatMenu = MenuWidget(self._btnBlockFormat)
        self._blockFormatMenu.aboutToShow.connect(self._showFormatMenu)

        self._commandActions = [Heading1Operation, Heading2Operation, Heading3Operation, InsertListOperation,
                                InsertNumberedListOperation, InsertDividerOperation,
                                InsertGrayBannerOperation,
                                InsertRedBannerOperation,
                                InsertBlueBannerOperation, InsertGreenBannerOperation, InsertYellowBannerOperation,
                                InsertPurpleBannerOperation]
        self._popupWidget: Optional[PopupBase] = None

        self.document().setDocumentMargin(40)

        self._adjustTabDistance()

        self.cursorPositionChanged.connect(self._cursorPositionChanged)
        self.textChanged.connect(self._cursorPositionChanged)
        self.selectionChanged.connect(self._selectionChanged)

    def autoCapitalizationMode(self) -> AutoCapitalizationMode:
        return self._autoCapitalizationMode

    def setAutoCapitalizationMode(self, mode: AutoCapitalizationMode):
        if mode == AutoCapitalizationMode.NONE:
            self._blockAutoCapitalization = False
            self._sentenceAutoCapitalization = False
        elif mode == AutoCapitalizationMode.PARAGRAPH:
            self._blockAutoCapitalization = True
            self._sentenceAutoCapitalization = False
        elif mode == AutoCapitalizationMode.SENTENCE:
            self._blockAutoCapitalization = True
            self._sentenceAutoCapitalization = True

        self._autoCapitalizationMode = mode

    def dashInsertionMode(self) -> DashInsertionMode:
        return self._dashInsertionMode

    def setDashInsertionMode(self, mode: DashInsertionMode):
        self._dashInsertionMode = mode

    def ellipsisInsertionMode(self) -> EllipsisInsertionMode:
        return self._ellipsisInsertionMode

    def setEllipsisInsertionMode(self, mode: EllipsisInsertionMode):
        self._ellipsisInsertionMode = mode

    def uneditableBlocksEnabled(self) -> bool:
        return self._uneditableBlocksEnabled

    def smartQuotesEnabled(self) -> bool:
        return self._smartQuotesEnabled

    def setSmartQuotesEnabled(self, enabled: bool):
        self._smartQuotesEnabled = enabled

    def periodInsertionEnabled(self) -> bool:
        return self._periodInsertionEnabled

    def setPeriodInsertionEnabled(self, enabled: bool):
        self._periodInsertionEnabled = enabled

    def setUneditableBlocksEnabled(self, enabled: bool):
        self._uneditableBlocksEnabled = enabled
        if not enabled:
            self._editionState = _TextEditionState.ALLOWED

    def sidebarEnabled(self) -> bool:
        return self._sidebarEnabled

    def setSidebarEnabled(self, value: bool):
        self._sidebarEnabled = value

    def setSidebarMenuEnabled(self, value: bool):
        self._sidebarMenuEnabled = value

    def setCommandsEnabled(self, value: bool):
        self._commandsEnabled = value

    def setBlockPlaceholderEnabled(self, value: bool):
        self._blockPlaceholderEnabled = value

    def setDocumentMargin(self, value: int):
        self.document().setDocumentMargin(value)

    def setCommandOperations(self, operations: List[Type[TextEditorOperation]]):
        self._commandActions.clear()
        self._commandActions.extend(operations)

    def setPopupWidget(self, widget: QWidget):
        self._popupWidget = widget

    def createEnhancedContextMenu(self, pos: QPoint) -> MenuWidget:
        menu = MenuWidget()
        selected = bool(self.textCursor().selectedText())
        menu.addAction(
            q_action('Cut', qta_icon('fa5s.cut'), self.cut, tooltip='Cut selected text', enabled=selected))
        menu.addAction(
            q_action('Copy', qta_icon('fa5s.copy'), self.copy, tooltip='Copy selected text', enabled=selected))
        menu.addAction(q_action('Paste', qta_icon('fa5s.paste'), self.paste,
                                tooltip='Paste from clipboard and adjust to the current style',
                                enabled=not self.isReadOnly()))

        menu.addSeparator()
        paste_submenu = MenuWidget()
        paste_submenu.setTitle('Paste as...')
        menu.addMenu(paste_submenu)
        paste_submenu.setDisabled(self.isReadOnly())
        paste_submenu.addAction(q_action('Paste as plain text', slot=self.pasteAsPlainText,
                                         tooltip='Paste as plain text without any formatting',
                                         enabled=not self.isReadOnly()))
        if self._pasteAsOriginalEnabled:
            paste_submenu.addAction(q_action('Paste with original style', slot=self.pasteAsOriginalText,
                                             tooltip='Paste with the original formatting',
                                             enabled=not self.isReadOnly()))

        anchor = self.anchorAt(pos)
        if anchor:
            menu.addSeparator()
            menu.addAction(
                q_action('Edit link', qta_icon('fa5s.link'), lambda: self._editLink(self.cursorForPosition(pos))))

        if self._currentHoveredTable is not None:
            menu.addSeparator()
            menu.addAction(q_action('Delete row', qta_icon('mdi.table-row-remove', 'red'), self._removeRow))
            menu.addAction(q_action('Delete column', qta_icon('mdi.table-column-remove', 'red'), self._removeColumn))

        return menu

    def contextMenuEvent(self, event: QContextMenuEvent):
        menu = self.createEnhancedContextMenu(event.pos())
        menu.exec(event.globalPos())

    def isTextBeingPasted(self) -> bool:
        return self._textIsBeingPasted

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
        self._textIsBeingPasted = True
        super(EnhancedTextEdit, self).cut()
        self._textIsBeingPasted = False

    def insertDocument(self, doc: QTextDocument):
        def _preprocessMarkdown(md: str) -> str:
            lines = md.split('\n')
            if len(lines) < 2:
                return md
            for i in range(len(lines)):
                if lines[i].strip() == '***':
                    lines[i] = '<span>***</span>'
                elif lines[i].strip() == '###':
                    lines[i] = '<span>###</span>'
            return '\n'.join(lines)

        cursor: QTextCursor = self.textCursor()

        cursor.beginEditBlock()
        start_pos = cursor.position()

        md = doc.toMarkdown().rstrip('\n')
        md = _preprocessMarkdown(md)
        cursor.insertMarkdown(md)

        end_pos = cursor.position()
        cursor.setPosition(start_pos, QTextCursor.MoveAnchor)
        cursor.setPosition(end_pos, QTextCursor.KeepAnchor)
        cursor.mergeBlockFormat(self._defaultBlockFormat)

        cursor.endEditBlock()

    def insertFromMimeData(self, source: QMimeData) -> None:
        if self._editionState == _TextEditionState.DISALLOWED:
            return

        self._textIsBeingPasted = True

        if self._pasteAsPlain:
            self.insertPlainText(source.text())
        elif self._pasteAsOriginal:
            super(EnhancedTextEdit, self).insertFromMimeData(source)
        else:
            if source.hasHtml():
                doc = QTextDocument()
                html = source.html().replace('<!--StartFragment-->', '')
                html = html.replace('<!--EndFragment-->', '')
                doc.setHtml(html)
                self.insertDocument(doc)
            elif source.hasText():
                self.insertPlainText(source.text())
            else:
                super(EnhancedTextEdit, self).insertFromMimeData(source)

        self._textIsBeingPasted = False

    def wheelEvent(self, event: QWheelEvent):
        super().wheelEvent(event)
        if self.verticalScrollBar().isVisible():
            self._btnPlus.setVisible(False)
            self._btnBlockFormat.setVisible(False)

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

            # self._btnTablePlusAbove.setGeometry(self.viewportMargins().left() + rect.x() - 16, rect.y() - 10, 16, 16)
            # self._btnTablePlusAbove.setVisible(True)
            # beginningCursor.movePosition(QTextCursor.EndOfBlock)
            # self._btnTablePlusBelow.setGeometry(self.viewportMargins().left() + rect.x() - 16,
            #                                     self.cursorRect(beginningCursor).y() + rect.height() - 8,
            #                                     16, 16)
            # self._btnTablePlusBelow.setVisible(True)
            #
            # constraint: QTextLength = self._currentHoveredTable.format().columnWidthConstraints()[
            #     self._currentHoveredTableCell.column()]
            # cell_width = self.document().size().width() * constraint.rawValue() / 100
            #
            # self._btnTablePlusLeft.setGeometry(self.viewportMargins().left() + rect.x() - 8, rect.y() - 18, 16, 16)
            # self._btnTablePlusLeft.setVisible(True)
            #
            # self._btnTablePlusRight.setGeometry(
            #     int(self.viewportMargins().left() + rect.x() + cell_width - self._currentHoveredTable.format().leftMargin() - 20),
            #     int(rect.y() - 18), 16, 16)
            # self._btnTablePlusRight.setVisible(True)

        else:
            # self._btnTablePlusAbove.setHidden(True)
            # self._btnTablePlusBelow.setHidden(True)
            # self._btnTablePlusLeft.setHidden(True)
            # self._btnTablePlusRight.setHidden(True)
            if self._sidebarEnabled and self._blockFormatPosition != cursor.blockNumber():
                self._blockFormatPosition = cursor.blockNumber()

                y_diff = (rect.height() - 20) // 2 + self.viewportMargins().top()
                first_x = 40 if self._sidebarMenuEnabled else 20
                doc_margin = int(self.document().documentMargin())
                self._btnPlus.setGeometry(self.viewportMargins().left() - first_x + doc_margin, rect.y() + y_diff, 20,
                                          20)
                self._btnPlus.setVisible(True)
                if self._sidebarMenuEnabled:
                    self._btnBlockFormat.setGeometry(self.viewportMargins().left() - first_x + 20 + doc_margin,
                                                     rect.y() + y_diff, 20, 20)
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

        if self._popupWidget:
            if self.textCursor().selectedText():
                if self._popupWidget.parent() is None:
                    self._popupWidget.setParent(QApplication.activeWindow())
                self._popup(self._popupWidget, event.pos())
            elif self._popupWidget.isVisible():
                self._popupWidget.hide()

        anchor = self.anchorAt(event.pos())
        if anchor and not self.textCursor().selectedText():
            QDesktopServices.openUrl(QUrl(anchor))

    def enterEvent(self, event: QEvent) -> None:
        super(EnhancedTextEdit, self).enterEvent(event)
        if self._blockFormatPosition >= 0:
            self._btnPlus.setVisible(self._sidebarEnabled)
            self._btnBlockFormat.setVisible(self._sidebarMenuEnabled)

    def leaveEvent(self, event: QEvent) -> None:
        super(EnhancedTextEdit, self).leaveEvent(event)
        self._btnPlus.setHidden(True)
        self._btnBlockFormat.setHidden(True)
        # self._btnTablePlusAbove.setHidden(True)
        # self._btnTablePlusBelow.setHidden(True)
        # self._btnTablePlusLeft.setHidden(True)
        # self._btnTablePlusRight.setHidden(True)

    def focusOutEvent(self, event: QFocusEvent):
        super().focusOutEvent(event)
        if self._popupWidget and self._popupWidget.isVisible() and not self._popupWidget.isFrozen():
            self._popupWidget.hide()

    def setPlaceholderText(self, placeholderText: str) -> None:
        self._defaultPlaceholder = placeholderText

    def paintEvent(self, e: QtGui.QPaintEvent) -> None:
        if ((self._blockPlaceholderEnabled or self.textCursor().blockNumber() == 0)
                and self._lastPaintedCursorRect != self.cursorRect(self.textCursor())):
            self._lastPaintedCursorRect = self.cursorRect(self.textCursor())
            self.viewport().update()
        super().paintEvent(e)

        if not self._blockPlaceholderEnabled and self.textCursor().blockNumber() > 0:
            return

        block = self.textCursor().block()
        if block.text() != "":
            return

        placeholderFont = self.font()
        if block.textList():
            placeholder = 'List'
        elif block.blockFormat().headingLevel():
            heading = block.blockFormat().headingLevel()
            placeholder = f'Heading {heading}'
            if heading == 1:
                placeholderFont.setPointSizeF(placeholderFont.pointSize() * 2)
            elif heading == 2:
                placeholderFont.setPointSizeF(placeholderFont.pointSize() * 1.5)
            elif heading == 3:
                placeholderFont.setPointSizeF(placeholderFont.pointSize() * 1.2)
            placeholderFont.setWeight(QtGui.QFont.Weight.Bold)
        else:
            alignment = self.alignment()
            if alignment & Qt.AlignmentFlag.AlignCenter:
                placeholder = "Centered"
            elif alignment & Qt.AlignmentFlag.AlignRight:
                return
            else:
                placeholder = self._defaultPlaceholder

        painter = QtGui.QPainter(self.viewport())
        painter.setPen(self._placeholderColor)
        painter.setFont(placeholderFont)
        font_metrics = QtGui.QFontMetrics(placeholderFont)

        text_rect = QRect(self._lastPaintedCursorRect.bottomLeft(), self.viewport().rect().bottomRight())
        text_rect.setTop(text_rect.top() - font_metrics.ascent())

        painter.drawText(text_rect, Qt.TextFlag.TextWordWrap, placeholder)

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
        if event.matches(QKeySequence.Cut):
            self._textIsBeingPasted = True
            super().keyPressEvent(event)
            self._textIsBeingPasted = False
            return
        if event.key() == Qt.Key_I and event.modifiers() & Qt.ControlModifier:
            self.setFontItalic(not self.fontItalic())
        if event.key() == Qt.Key_B and event.modifiers() & Qt.ControlModifier:
            self.setFontWeight(QFont.Bold if self.fontWeight() == QFont.Normal else QFont.Normal)
        if event.key() == Qt.Key_U and event.modifiers() & Qt.ControlModifier:
            self.setFontUnderline(not self.fontUnderline())
        if event.key() == Qt.Key.Key_V and event.modifiers() & Qt.ControlModifier and event.modifiers() & Qt.ShiftModifier:
            self.pasteAsPlainText()
        if event.key() == Qt.Key_D and event.modifiers() & Qt.ControlModifier:
            self._duplicateBlock(self.textCursor().blockNumber())
            return
        if event.text().isalpha():
            if (self._blockAutoCapitalization and cursor.atBlockStart() and not cursor.block().text()) or (
                    self._sentenceAutoCapitalization and self._atSentenceStart(cursor)):
                self.textCursor().insertText(event.text().upper())
                return
        if event.key() == Qt.Key_Return and not event.modifiers():
            self._insertNewBlock(cursor)
            return
        if cursor.atBlockEnd() and event.key() == Qt.Key.Key_Space and self._periodInsertionEnabled:
            moved_cursor = select_previous_character(cursor)
            if moved_cursor.selectedText() == ' ':
                self.textCursor().deletePreviousChar()
                self.textCursor().insertText('.')
        if event.key() == Qt.Key_Period and self._ellipsisInsertionMode != EllipsisInsertionMode.NONE:
            moved_cursor = select_previous_character(cursor, amount=2)
            if moved_cursor.selectedText() == '..':
                moved_cursor.removeSelectedText()
                cursor.insertText(ELLIPSIS)
                # cursor.insertText(f'.{NBSP}.{NBSP}.')
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
            elif moved_cursor.selectedText() == EN_DASH and self._dashInsertionMode == DashInsertionMode.INSERT_EN_DASH:
                cursor.deletePreviousChar()
                cursor.insertText(EM_DASH)
                return
            elif moved_cursor.selectedText() == EM_DASH and self._dashInsertionMode == DashInsertionMode.INSERT_EM_DASH:
                cursor.deletePreviousChar()
                cursor.insertText(EN_DASH)
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
        if event.key() == Qt.Key_Apostrophe and self._smartQuotesEnabled:
            self._insertQuote(cursor, LEFT_SINGLE_QUOTATION, RIGHT_SINGLE_QUOTATION)
            return
        if event.key() == Qt.Key_QuoteDbl and self._smartQuotesEnabled:
            self._insertQuote(cursor, LEFT_DOUBLE_QUOTATION, RIGHT_DOUBLE_QUOTATION)
            return
        if event.key() == Qt.Key_Delete and (
                self._editionState == _TextEditionState.DEL_BLOCKED or
                self._editionState == _TextEditionState.REMOVAL_BLOCKED):
            return
        if event.key() == Qt.Key_Backspace and (
                self._editionState == _TextEditionState.BACKSPACE_BLOCKED or
                self._editionState == _TextEditionState.REMOVAL_BLOCKED):
            return
        if event.key() == Qt.Key_Backspace and cursor.currentFrame() and isinstance(cursor.currentFrame(),
                                                                                    QTextTable):
            frame: QTextTable = cursor.currentFrame()
            if not cursor.block().text() and frame.columns() == 1 and frame.rows() == 1:
                cursor.setPosition(frame.firstCursorPosition().position() - 1, QTextCursor.MoveAnchor)
                cursor.setPosition(frame.lastCursorPosition().position() + 1, QTextCursor.KeepAnchor)
                if len(cursor.selectedText()) <= 2:
                    cursor.removeSelectedText()
                    return
        if self._commandsEnabled and event.key() == Qt.Key_Slash and self.textCursor().atBlockStart():
            self._showCommands()
        super(EnhancedTextEdit, self).keyPressEvent(event)

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
        cursor.mergeBlockFormat(blockFmt)

    def applyBlockFormat(self):
        block = self.document().begin()
        first_parag_block_format = QTextBlockFormat(self._defaultBlockFormat)
        first_parag_block_format.setTextIndent(0)
        while block.isValid():
            cursor = QTextCursor(block)
            if block.blockNumber() == 0:
                cursor.mergeBlockFormat(first_parag_block_format)
            else:
                cursor.mergeBlockFormat(self._defaultBlockFormat)

            block = block.next()

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
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
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

    def _showFormatMenu(self):
        block = self.document().findBlockByNumber(self._blockFormatPosition)
        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

        if not self._blockFormatMenu.actions():
            self._blockFormatMenu.addAction(
                q_action('Duplicate', qta_icon('fa5.copy'), lambda: self._duplicateBlock(self._blockFormatPosition)))
            self._convertIntoMenu = MenuWidget()
            self._convertIntoMenu.setTitle('Convert into')
            self._convertIntoMenu.setIcon(qta_icon('ph.arrows-clockwise-fill'))
            for op_clazz in [TextOperation, Heading1Operation, Heading2Operation, Heading3Operation,
                             InsertListOperation,
                             InsertNumberedListOperation]:
                action = op_clazz(self._convertIntoMenu)
                self._convertIntoMenu.addAction(action)
                action.activateOperation(self)
            self._blockFormatMenu.addMenu(self._convertIntoMenu)
            self._blockFormatMenu.addSeparator()
            self._blockFormatMenu.addAction(
                q_action('Delete', qta_icon('fa5s.trash-alt'), lambda: self._deleteBlock(self._blockFormatPosition)))

    def _adjustTabDistance(self):
        self.setTabStopDistance(QtGui.QFontMetricsF(self.font()).horizontalAdvance(' ') * 4)

    def _cursorPositionChanged(self):
        if self._popupWidget and self._popupWidget.isVisible():
            self._popupWidget.hide()
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
            if cursor.block().text():
                return False
            return True
        moved_cursor = select_previous_character(cursor)
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
            if not showCommands and not cursor.atBlockEnd() and cursor.blockFormat().headingLevel():
                heading = cursor.blockFormat().headingLevel()
                self.setHeading(0)
                prevCursor = QTextCursor(cursor)
                cursor.insertBlock(self._defaultBlockFormat)
                self.setHeading(heading)
                self.setTextCursor(prevCursor)
            elif not self.alignment() & Qt.AlignmentFlag.AlignLeft:
                if cursor.block().text():
                    cursor.insertBlock(cursor.blockFormat(), cursor.charFormat())
                else:
                    self.setAlignment(Qt.AlignmentFlag.AlignLeft)
            else:
                cursor.insertBlock(self._defaultBlockFormat, QTextCharFormat())

            if showCommands:
                self._showCommands(self._btnPlus)
        self.ensureCursorVisible()

    def _duplicateBlock(self, blockNumber: int):
        block: QTextBlock = self.document().findBlockByNumber(blockNumber)
        cursor = QTextCursor(block)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        fragment = cursor.selection()

        cursor.beginEditBlock()
        self._insertBlock(blockNumber)
        self.textCursor().insertMarkdown(fragment.toMarkdown())
        heading = block.blockFormat().headingLevel()
        if heading > 0:
            self.setHeading(heading)
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

    def _insertQuote(self, cursor: QTextCursor, left: str, right: str):
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            cursor.insertText(left + selected_text + right)
        elif has_character_left(cursor):
            self.textCursor().insertText(right)
        elif has_character_right(cursor):
            self.textCursor().insertText(left)
        else:
            self.textCursor().insertText(left)
            self.textCursor().insertText(right)
            cursor.movePosition(QTextCursor.PreviousCharacter)
            self.setTextCursor(cursor)

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

    def _showCommands(self, parent=None):
        def cleanUp():
            if not self.textCursor().atBlockStart():
                self.textCursor().deletePreviousChar()

        rect = self.cursorRect()

        menu = MenuWidget()
        for op_clazz in self._commandActions:
            action = op_clazz(menu)
            action.activateOperation(self)
            menu.addAction(action)
        menu.aboutToHide.connect(cleanUp)
        menu.setKeyNavigationEnabled(True)

        if parent:
            menu.exec(self.viewport().mapToGlobal(parent.pos()))
        else:
            menu.exec(self.viewport().mapToGlobal(QPoint(rect.x(), rect.y())))

    def _popup(self, wdg: PopupBase, pos: QPoint):
        ml = self.viewportMargins().left()
        tl = self.viewportMargins().top()
        cursor: QTextCursor = self.cursorForPosition(pos)
        rect = self.cursorRect(cursor)
        pos = QPoint(pos.x(), rect.y())
        global_pos: QPoint = self.mapToGlobal(pos) - QPoint(-ml,
                                                            wdg.sizeHint().height() + 40 - tl) - QApplication.activeWindow().pos()
        wdg.setGeometry(global_pos.x(), global_pos.y(), wdg.sizeHint().width(),
                        wdg.sizeHint().height())
        wdg.beforeShown()
        qtanim.fade_in(wdg, teardown=wdg.afterShown)


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
            self.op.iconChanged.connect(self.setIcon)
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

    def addTextEditorOperation(self, operationType: Type[TextEditorOperation]) -> TextEditorOperationButton:
        operation, btn = self._initOperation(operationType)
        if self._linkedTextEdit:
            operation.activateOperation(self._linkedTextEdit, self._linkedTextEditor)
        self.layout().addWidget(btn)

        return btn

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
        self.btnGroupAlignment.setExclusive(False)
        for btn in self._textEditorOperations.values():
            btn.op.updateFormat(textEdit)
        self.btnGroupAlignment.setExclusive(True)

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
        # self.addSeparator()
        # self.addTextEditorOperation(InsertTableOperation)
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
    replace = Signal(str)
    replaceAll = Signal(str)
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self)
        self.wdgFind = QWidget()
        hbox(self.wdgFind, 0)
        self._icon = QToolButton()
        transparent(self._icon)
        self._icon.setIcon(qta_icon('mdi.magnify'))
        self._lineText = QLineEdit()
        self._lineText.setPlaceholderText('Find...')
        self._lineText.setClearButtonEnabled(True)
        self._lineText.setMaximumWidth(150)
        self._btnFindNext = QPushButton('Find next')
        self._btnFindNext.clicked.connect(self._findNext)
        self._btnFindNext.setDisabled(True)
        self._btnFindNext.installEventFilter(
            DisabledClickEventFilter(self._btnFindNext, lambda: qtanim.shake(self._lineText)))

        self._btnClose = CloseButton()
        self._btnClose.clicked.connect(self.closed)

        self.wdgFind.layout().addWidget(self._icon)
        self.wdgFind.layout().addWidget(self._lineText)
        self.wdgFind.layout().addWidget(self._btnFindNext)
        self.wdgFind.layout().addWidget(spacer())
        self.wdgFind.layout().addWidget(self._btnClose, alignment=Qt.AlignmentFlag.AlignTop)

        self.wdgReplace = QWidget()
        self._lineTextReplace = QLineEdit()
        self._lineTextReplace.setPlaceholderText('Replace...')
        self._lineTextReplace.setClearButtonEnabled(True)
        self._lineTextReplace.setMaximumWidth(150)
        hbox(self.wdgReplace, 0)
        self._iconReplace = QToolButton()
        transparent(self._iconReplace)
        self._iconReplace.setIcon(qta_icon('mdi.find-replace'))
        self._btnReplace = QPushButton('Replace')
        self._btnReplace.setDisabled(True)
        self._btnReplaceAll = QPushButton('Replace all')
        self._btnReplaceAll.setDisabled(True)
        self._btnReplace.installEventFilter(
            DisabledClickEventFilter(self._btnReplace, lambda: qtanim.shake(self._lineText)))
        self._btnReplaceAll.installEventFilter(
            DisabledClickEventFilter(self._btnReplace, lambda: qtanim.shake(self._lineText)))
        self.wdgReplace.layout().addWidget(self._iconReplace)
        self.wdgReplace.layout().addWidget(self._lineTextReplace)
        self.wdgReplace.layout().addWidget(self._btnReplace)
        self.wdgReplace.layout().addWidget(self._btnReplaceAll)
        self.wdgReplace.layout().addWidget(spacer())

        self._btnActivateReplace = QPushButton('Replace...')
        self._btnActivateReplace.setToolTip('Show Replace field (Ctrl+R)')
        pointy(self._btnActivateReplace)
        self._btnActivateReplace.installEventFilter(OpacityEventFilter(self._btnActivateReplace))
        decr_font(self._btnActivateReplace, 2)
        transparent(self._btnActivateReplace)
        italic(self._btnActivateReplace)

        margins(self, left=15)
        self.layout().addWidget(self.wdgFind)
        self.layout().addWidget(self.wdgReplace)
        self.layout().addWidget(self._btnActivateReplace, alignment=Qt.AlignmentFlag.AlignLeft)

        self._lineText.textChanged.connect(self._termChanged)
        self._btnReplace.clicked.connect(self._replace)
        self._btnReplaceAll.clicked.connect(self._replaceAll)
        self._btnActivateReplace.clicked.connect(self._activateReplace)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Return and self._lineText.text():
            self.findNext.emit(self._lineText.text())
        elif event.key() == Qt.Key_Escape:
            self.closed.emit()

    def lineEditSearch(self) -> QLineEdit:
        return self._lineText

    def lineEditReplace(self) -> QLineEdit:
        return self._lineTextReplace

    def buttonNext(self) -> QPushButton:
        return self._btnFindNext

    def buttonReplace(self) -> QPushButton:
        return self._btnReplace

    def buttonReplaceAll(self) -> QPushButton:
        return self._btnReplaceAll

    def activate(self, replace: bool = False):
        self._lineText.setFocus()
        if replace:
            self._activateReplace()
        else:
            self._resetReplace()

    def showZeroFind(self):
        qtanim.glow(self._lineText, duration=300)
        qtanim.glow(self._icon, duration=300)

    def showFindOver(self):
        qtanim.glow(self._lineText, color=QColor('#ffb703'))
        qtanim.glow(self._icon, color=QColor('#ffb703'))

    def _activateReplace(self):
        self.wdgReplace.setVisible(True)
        self._btnActivateReplace.setHidden(True)

    def _resetReplace(self):
        self.wdgReplace.setHidden(True)
        self._lineTextReplace.clear()
        self._btnActivateReplace.setVisible(True)

    def _termChanged(self, term: str):
        self._btnFindNext.setEnabled(len(term) > 0)
        self._btnReplace.setEnabled(len(term) > 0)
        self._btnReplaceAll.setEnabled(len(term) > 0)
        self.find.emit(term)

    def _findNext(self):
        self.findNext.emit(self._lineText.text())

    def _replace(self):
        self.replace.emit(self._lineTextReplace.text())

    def _replaceAll(self):
        self.replaceAll.emit(self._lineTextReplace.text())


class RichTextEditor(QWidget):
    settingsAttached = Signal()

    def __init__(self, parent=None):
        super(RichTextEditor, self).__init__(parent)
        vbox(self, 0, 0)
        self._widthPercentage: int = 0
        self._maxContentWidth: int = -1
        self._characterWidth: int = 0
        self._settings: Optional[TextEditorSettingsWidget] = None

        self._toolbar = self._initToolbar()
        self._wdgFind = TextFindWidget(self)
        self._wdgFind.setHidden(True)
        self._findCursor: Optional[QTextCursor] = None
        self._findTerm: str = ''

        self._textedit = self._initTextEdit()
        self._wdgFind.find.connect(self._find)
        self._wdgFind.findNext.connect(self._findNext)
        self._wdgFind.replace.connect(self._replace)
        self._wdgFind.replaceAll.connect(self._replaceAll)
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
        elif event.key() == Qt.Key_R and event.modifiers() & Qt.ControlModifier:
            self._wdgFind.setVisible(True)
            self._wdgFind.activate(replace=True)
        elif event.key() == Qt.Key_Escape and self._wdgFind.isVisible():
            self._wdgFind.setHidden(True)
        else:
            super(RichTextEditor, self).keyPressEvent(event)

    def toolbar(self) -> TextEditorToolbar:
        return self._toolbar

    # def setToolbar(self, toolbar: TextEditorToolbar):
    #     self._toolbar = toolbar

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

    def characterWidth(self) -> int:
        return self._characterWidth

    def setCharacterWidth(self, count: int = 80):
        self._characterWidth = count
        metrics = QtGui.QFontMetricsF(self._textedit.font())
        self._maxContentWidth = metrics.boundingRect('M' * self._characterWidth).width()
        self._resize()

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
        # margins(self._toolbar, left=margin)

    def _initToolbar(self) -> TextEditorToolbar:
        return StandardTextEditorToolbar(self)

    def _initTextEdit(self) -> EnhancedTextEdit:
        return EnhancedTextEdit(self)

    def _find(self, text: str):
        self._findTerm = text
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

    def _replace(self, replacedWith: str):
        if self._findCursor and self._findCursor.selectedText():
            self._findCursor.insertText(replacedWith)
            self._findNext(self._findTerm)

    def _replaceAll(self, replacedWith: str):
        while self._findCursor and self._findCursor.selectedText():
            self._replace(replacedWith)
