import re
from abc import abstractmethod
from enum import Enum
from functools import partial
from typing import List, Dict

import qtawesome
from PyQt5.QtCore import QPoint
from qthandy import vbox, hbox, spacer, vline, btn_popup_menu, line, btn_popup, busy
from qtpy import QtGui
from qtpy.QtCore import Qt, QMimeData, QSize, QUrl, QBuffer, QIODevice, Signal
from qtpy.QtGui import QContextMenuEvent, QDesktopServices, QFont, QTextBlockFormat, QTextCursor, QTextList, \
    QKeySequence, QTextListFormat, QTextCharFormat, QTextFormat, QColor
from qtpy.QtPrintSupport import QPrinter, QPrintDialog
from qtpy.QtWidgets import QFileDialog
from qtpy.QtWidgets import QMenu, QWidget, QApplication, QToolButton, QFrame, QButtonGroup, QTextEdit, \
    QInputDialog, QSizePolicy, QGridLayout

from qttextedit.diag import LinkCreationDialog
from qttextedit.util import select_anchor, select_previous_character, select_next_character, is_open_quotation


class TextColorSelectorWidget(QWidget):
    foregroundColorSelected = Signal(QColor)
    backgroundColorSelected = Signal(QColor)
    reset = Signal()

    def __init__(self, foregroundColors: List[str], backgroundColors: List[str], parent=None):
        super(TextColorSelectorWidget, self).__init__(parent)

        vbox(self)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        self.btnReset = _button('mdi.format-color-marker-cancel', tooltip='Reset current color', checkable=False)
        self.btnReset.clicked.connect(lambda: self.reset.emit())

        self.wdgForeground = QWidget()
        self.wdgForeground.setLayout(QGridLayout())
        self.wdgForeground.layout().setSpacing(2)
        self.wdgForeground.layout().setContentsMargins(2, 2, 2, 2)

        for i, color in enumerate(foregroundColors):
            btn = self._addBtn('mdi.alpha-a', i, color, self.wdgForeground)
            btn.clicked.connect(partial(self.foregroundColorSelected.emit, QColor(color)))

        self.wdgBackground = QWidget()
        self.wdgBackground.setLayout(QGridLayout())

        for i, color in enumerate(backgroundColors):
            btn = self._addBtn('mdi.alpha-a-box', i, color, self.wdgBackground)
            btn.clicked.connect(partial(self.backgroundColorSelected.emit, QColor(color)))

        self.layout().addWidget(self.btnReset, alignment=Qt.AlignRight)
        self.layout().addWidget(self.wdgForeground)
        self.layout().addWidget(line())
        self.layout().addWidget(self.wdgBackground)

    def _addBtn(self, icon: str, i: int, color: str, parent: QWidget) -> QToolButton:
        btn = QToolButton()
        btn.setIconSize(QSize(24, 24))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setIcon(qtawesome.icon(icon, color=color, options=[{'scale_factor': 1.2}]))

        parent.layout().addWidget(btn, i // 6, i % 6)

        return btn


def _button(icon: str, tooltip: str = '', shortcut=None, checkable: bool = True) -> QToolButton:
    btn = QToolButton()
    btn.setToolTip(tooltip)
    btn.setIconSize(QSize(18, 18))
    btn.setCursor(Qt.PointingHandCursor)
    if icon.startswith('md') or icon.startswith('ri'):
        btn.setIcon(qtawesome.icon(icon, options=[{'scale_factor': 1.2}]))
    else:
        btn.setIcon(qtawesome.icon(icon))
    if shortcut:
        btn.setShortcut(shortcut)
    btn.setCheckable(checkable)

    return btn


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
            self.resetTextColor()
            # self.resetTextBackgroundColor()
            level = self.textCursor().blockFormat().headingLevel()
            if level > 0:  # heading
                self.textCursor().insertBlock()
                self.textCursor().insertText('')
                self.setHeading(0)
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
        self.setTextColor(Qt.black)

    def resetTextBackgroundColor(self):
        self.setTextBackgroundColor(Qt.white)

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


class TextEditorOperationType(Enum):
    BOLD = 'bold'
    ITALIC = 'italic'
    UNDERLINE = 'underline'
    STRIKETHROUGH = 'strikethrough'
    FORMAT = 'format'
    ALIGNMENT_LEFT = 'alignment_left'
    ALIGNMENT_CENTER = 'alignment_center'
    ALIGNMENT_RIGHT = 'alignment_right'
    INSERT_LIST = 'insert_list'
    INSERT_NUMBERED_LIST = 'insert_numbered_list'
    INSERT_LINK = 'insert_link'
    COLOR = 'color'
    EXPORT_PDF = 'export_pdf'
    PRINT = 'print'


class TextEditorOperation(QToolButton):
    def __init__(self, icon: str, tooltip: str = '', shortcut=None, checkable: bool = False, parent=None):
        super(TextEditorOperation, self).__init__(parent)
        self.setToolTip(tooltip)
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.PointingHandCursor)
        if icon.startswith('md') or icon.startswith('ri'):
            self.setIcon(qtawesome.icon(icon, options=[{'scale_factor': 1.2}]))
        else:
            self.setIcon(qtawesome.icon(icon))
        if shortcut:
            self.setShortcut(shortcut)
        self.setCheckable(checkable)

    @abstractmethod
    def activate(self, textEdit: QTextEdit):
        pass

    def updateFormat(self, textEdit: QTextEdit):
        pass


class FormatOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(FormatOperation, self).__init__('mdi.format-text', 'Format text', parent=parent)

    def activate(self, textEdit: QTextEdit):
        formatMenu = QMenu(self)
        formatMenu.addAction(qtawesome.icon('mdi.format-header-1', options=[{'scale_factor': 1.4}]), '',
                             lambda: textEdit.setHeading(1))
        formatMenu.addAction(qtawesome.icon('mdi.format-header-2', options=[{'scale_factor': 1.3}]), '',
                             lambda: textEdit.setHeading(2))
        formatMenu.addAction(qtawesome.icon('mdi.format-header-3', options=[{'scale_factor': 1.2}]), '',
                             lambda: textEdit.setHeading(3))
        formatMenu.addSeparator()
        formatMenu.addAction(qtawesome.icon('mdi.format-clear', options=[{'scale_factor': 1.2}]), '',
                             lambda: textEdit.setHeading(0))
        btn_popup_menu(self, formatMenu)


class BoldOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(BoldOperation, self).__init__('fa5s.bold', 'Bold', shortcut=QKeySequence.Bold, checkable=True,
                                            parent=parent)

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(lambda x: textEdit.setFontWeight(QFont.Bold if x else QFont.Normal))

    def updateFormat(self, textEdit: QTextEdit):
        self.setChecked(textEdit.fontWeight() == QFont.Bold)


class ItalicOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(ItalicOperation, self).__init__('fa5s.italic', 'Italic', shortcut=QKeySequence.Italic, checkable=True,
                                              parent=parent)

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(lambda x: textEdit.setFontItalic(x))

    def updateFormat(self, textEdit: QTextEdit):
        self.setChecked(textEdit.fontItalic())


class UnderlineOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(UnderlineOperation, self).__init__('fa5s.underline', 'Underline', shortcut=QKeySequence.Underline,
                                                 checkable=True,
                                                 parent=parent)

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(lambda x: textEdit.setFontUnderline(x))

    def updateFormat(self, textEdit: QTextEdit):
        self.setChecked(textEdit.fontUnderline())


class StrikethroughOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(StrikethroughOperation, self).__init__('fa5s.strikethrough', 'Strikethrough', checkable=True,
                                                     parent=parent)

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(textEdit.setStrikethrough)

    def updateFormat(self, textEdit: QTextEdit):
        self.setChecked(textEdit.currentFont().strikeOut())


class ColorOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(ColorOperation, self).__init__('fa5s.highlighter', 'Text color', parent=parent)
        self.wdgTextStyle = TextColorSelectorWidget(
            ['#da1e37', '#e85d04', '#9c6644', '#ffd500', '#2d6a4f', '#74c69d', '#023e8a', '#219ebc', '#7209b7',
             '#deaaff', '#ff87ab', '#4a4e69', '#ced4da', '#000000'],
            ['#da1e37', '#e85d04', '#9c6644', '#ffd500', '#2d6a4f', '#74c69d', '#023e8a', '#219ebc', '#7209b7',
             '#deaaff', '#ff87ab', '#4a4e69', '#ced4da', '#000000'])
        btn_popup(self, self.wdgTextStyle)
        self.wdgTextStyle.foregroundColorSelected.connect(self.menu().hide)
        self.wdgTextStyle.backgroundColorSelected.connect(self.menu().hide)
        self.wdgTextStyle.reset.connect(self.menu().hide)

    def activate(self, textEdit: QTextEdit):
        self.wdgTextStyle.foregroundColorSelected.connect(lambda x: textEdit.setTextColor(x))
        self.wdgTextStyle.backgroundColorSelected.connect(lambda x: textEdit.setTextBackgroundColor(x))

        self.wdgTextStyle.reset.connect(textEdit.resetTextColor)
        self.wdgTextStyle.reset.connect(textEdit.resetTextBackgroundColor)


class AlignmentOperation(TextEditorOperation):

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(lambda: textEdit.setAlignment(self.alignment()))

    def updateFormat(self, textEdit: QTextEdit):
        self.setChecked(textEdit.alignment() == self.alignment())

    @abstractmethod
    def alignment(self):
        pass


class AlignLeftOperation(AlignmentOperation):
    def __init__(self, parent=None):
        super(AlignLeftOperation, self).__init__('fa5s.align-left', 'Align left', checkable=True, parent=parent)

    def alignment(self):
        return Qt.AlignLeft


class AlignCenterOperation(AlignmentOperation):
    def __init__(self, parent=None):
        super(AlignCenterOperation, self).__init__('fa5s.align-center', 'Align center', checkable=True, parent=parent)

    def alignment(self):
        return Qt.AlignCenter


class AlignRightOperation(AlignmentOperation):
    def __init__(self, parent=None):
        super(AlignRightOperation, self).__init__('fa5s.align-right', 'Align right', checkable=True, parent=parent)

    def alignment(self):
        return Qt.AlignRight


class InsertListOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(InsertListOperation, self).__init__('fa5s.list', 'Insert list', parent=parent)

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(lambda: textEdit.textCursor().createList(QTextListFormat.ListDisc))


class InsertNumberedListOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(InsertNumberedListOperation, self).__init__('fa5s.list-ol', 'Insert numbered list', parent=parent)

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(lambda: textEdit.textCursor().createList(QTextListFormat.ListDecimal))


class InsertLinkOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(InsertLinkOperation, self).__init__('fa5s.link', 'Insert link', parent=parent)

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(lambda: self._insertLink(textEdit))

    def _insertLink(self, textEdit: QTextEdit):
        text = textEdit.textCursor().selectedText()
        result = LinkCreationDialog().display(text)
        if result.accepted:
            textEdit.textCursor().insertHtml(f'<a href="{result.link}">{result.name}</a>')


class ExportPdfOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(ExportPdfOperation, self).__init__('mdi.file-export-outline', 'Export to PDF', parent=parent)
        self._title = 'document'

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(lambda: self._exportPdf(textEdit))

    def title(self) -> str:
        return self._title

    def setTitle(self, value: str):
        self._title = value

    def _exportPdf(self, textEdit: QTextEdit):
        filename, _ = QFileDialog.getSaveFileName(self, 'Export PDF', f'{self._title}.pdf',
                                                  'PDF files (*.pdf);;All Files()')
        if filename:
            self._print(filename, textEdit)

    @busy
    def _print(self, filename: str, textEdit: QTextEdit):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(filename)
        printer.setDocName(self._title)
        textEdit.print(printer)


class PrintOperation(TextEditorOperation):
    def __init__(self, parent=None):
        super(PrintOperation, self).__init__('mdi.printer', 'Print', parent=parent)

    def activate(self, textEdit: QTextEdit):
        self.clicked.connect(lambda: self._print(textEdit))

    @busy
    def _getPrinter(self) -> QPrinter:
        return QPrinter(QPrinter.HighResolution)

    def _print(self, textEdit: QTextEdit):
        printer = self._getPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            textEdit.print(printer)


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
        self._standardOperations: Dict[TextEditorOperationType, TextEditorOperation] = {}
        self.btnGroupAlignment = QButtonGroup(self)
        self.btnGroupAlignment.setExclusive(True)

    def addStandardOperation(self, operationType: TextEditorOperationType):
        opBtn = self._newOperation(operationType)
        if opBtn:
            self._standardOperations[operationType] = opBtn
            self.layout().addWidget(opBtn)
            if operationType.value.startswith('alignment'):
                self.btnGroupAlignment.addButton(opBtn)

    def addSeparator(self):
        self.layout().addWidget(vline())

    def addSpacer(self):
        self.layout().addWidget(spacer())

    def setStandardOperationVisible(self, operationType: TextEditorOperationType, visible: bool):
        op = self._getOperationOrFail(operationType)
        op.setVisible(visible)

    def standardOperation(self, operationType: TextEditorOperationType) -> TextEditorOperation:
        return self._getOperationOrFail(operationType)

    def activate(self, textEdit: QTextEdit):
        for op in self._standardOperations.values():
            op.activate(textEdit)

    def updateFormat(self, textEdit: QTextEdit):
        for op in self._standardOperations.values():
            op.updateFormat(textEdit)

    def _getOperationOrFail(self, operationType: TextEditorOperationType) -> TextEditorOperation:
        if operationType in self._standardOperations:
            return self._standardOperations[operationType]
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


# class ToolbarDisplayMode(Enum):
#     DOCKED = 'docked'
#     ON_SELECTION = 'on_selection'


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
