import re
from functools import partial
from typing import List

import qtawesome
from qthandy import vbox, hbox, spacer, vline, btn_popup_menu, btn_popup, line
from qtpy import QtGui
from qtpy.QtCore import Qt, QMimeData, QSize, QUrl, QBuffer, QIODevice, Signal
from qtpy.QtGui import QContextMenuEvent, QDesktopServices, QFont, QTextBlockFormat, QTextCursor, QTextList, \
    QKeySequence, QTextListFormat, QTextCharFormat, QTextFormat, QColor
from qtpy.QtPrintSupport import QPrinter, QPrintDialog
from qtpy.QtWidgets import QMenu, QWidget, QApplication, QHBoxLayout, QToolButton, QFrame, QButtonGroup, QTextEdit, \
    QFileDialog, QInputDialog, QSizePolicy, QGridLayout

from qttextedit.diag import LinkCreationDialog
from qttextedit.util import select_anchor


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
        action = paste_submenu.addAction('Paste with original style', self.pasteAsOriginalText)
        action.setToolTip('Paste with the original formatting')

        anchor = self.anchorAt(event.pos())
        if anchor:
            menu.addSeparator()
            menu.addAction(qtawesome.icon('fa5s.link'), 'Edit link',
                           lambda: self._editLink(self.cursorForPosition(event.pos())))

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
        if event.text().isalpha() and self._atSentenceStart(cursor) and cursor.atBlockEnd():
            self.textCursor().insertText(event.text().upper())
            return
        if event.key() == Qt.Key_Return:
            self.resetTextColor()
            self.resetTextBackgroundColor()
            level = self.textCursor().blockFormat().headingLevel()
            if level > 0:  # heading
                self.textCursor().insertBlock()
                self.textCursor().insertText('')
                self.setHeading(0)
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

    def _toggleQuickFormatPopup(self):
        if not self.textCursor().hasSelection():
            self._quickFormatPopup.setHidden(True)

    def _atSentenceStart(self, cursor: QTextCursor) -> bool:
        if cursor.atBlockStart():
            return True
        moved_cursor = QTextCursor(cursor)
        moved_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
        if moved_cursor.selectedText() == '.':
            return True
        if moved_cursor.atBlockStart() and moved_cursor.selectedText() == '"':
            return True
        if moved_cursor.positionInBlock() == 1:
            return False
        elif moved_cursor.selectedText() == ' ' or moved_cursor.selectedText() == '"':
            moved_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
            if moved_cursor.selectedText().startswith('.'):
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
        self.textEdit = self._initTextEdit()

        self.layout().addWidget(self.toolbar)
        self.layout().addWidget(self.textEdit)

        self.btnFormat = _button('mdi.format-text', 'Format text', checkable=False)
        formatMenu = QMenu(self.btnFormat)
        formatMenu.addAction(qtawesome.icon('mdi.format-header-1', options=[{'scale_factor': 1.4}]), '',
                             lambda: self.textEdit.setHeading(1))
        formatMenu.addAction(qtawesome.icon('mdi.format-header-2', options=[{'scale_factor': 1.3}]), '',
                             lambda: self.textEdit.setHeading(2))
        formatMenu.addAction(qtawesome.icon('mdi.format-header-3', options=[{'scale_factor': 1.2}]), '',
                             lambda: self.textEdit.setHeading(3))
        formatMenu.addSeparator()
        formatMenu.addAction(qtawesome.icon('mdi.format-clear', options=[{'scale_factor': 1.2}]), '',
                             lambda: self.textEdit.setHeading(0))
        btn_popup_menu(self.btnFormat, formatMenu)

        self.btnBold = _button('fa5s.bold', 'Bold', shortcut=QKeySequence.Bold)
        self.btnBold.clicked.connect(lambda x: self.textEdit.setFontWeight(QFont.Bold if x else QFont.Normal))
        self.btnItalic = _button('fa5s.italic', 'Italic', shortcut=QKeySequence.Italic)
        self.btnItalic.clicked.connect(lambda x: self.textEdit.setFontItalic(x))
        self.btnUnderline = _button('fa5s.underline', 'Underline', shortcut=QKeySequence.Underline)
        self.btnUnderline.clicked.connect(lambda x: self.textEdit.setFontUnderline(x))
        self.btnStrikethrough = _button('fa5s.strikethrough', 'Strikethrough')
        self.btnStrikethrough.clicked.connect(self.textEdit.setStrikethrough)

        self.btnTextStyle = _button('fa5s.highlighter', 'Text color', checkable=False)
        self.wdgTextStyle = TextColorSelectorWidget(
            ['#da1e37', '#e85d04', '#9c6644', '#ffd500', '#2d6a4f', '#74c69d', '#023e8a', '#219ebc', '#7209b7',
             '#deaaff', '#ff87ab', '#4a4e69', '#ced4da', '#000000'],
            ['#da1e37', '#e85d04', '#9c6644', '#ffd500', '#2d6a4f', '#74c69d', '#023e8a', '#219ebc', '#7209b7',
             '#deaaff', '#ff87ab', '#4a4e69', '#ced4da', '#000000'])
        btn_popup(self.btnTextStyle, self.wdgTextStyle)
        self.wdgTextStyle.foregroundColorSelected.connect(lambda x: self.textEdit.setTextColor(x))
        self.wdgTextStyle.backgroundColorSelected.connect(lambda x: self.textEdit.setTextBackgroundColor(x))
        self.wdgTextStyle.foregroundColorSelected.connect(self.btnTextStyle.menu().hide)
        self.wdgTextStyle.backgroundColorSelected.connect(self.btnTextStyle.menu().hide)
        self.wdgTextStyle.reset.connect(self.textEdit.resetTextColor)
        self.wdgTextStyle.reset.connect(self.textEdit.resetTextBackgroundColor)
        self.wdgTextStyle.reset.connect(self.btnTextStyle.menu().hide)

        self.btnAlignLeft = _button('fa5s.align-left', 'Align left')
        self.btnAlignLeft.clicked.connect(lambda: self.textEdit.setAlignment(Qt.AlignLeft))
        self.btnAlignLeft.setChecked(True)
        self.btnAlignCenter = _button('fa5s.align-center', 'Align center')
        self.btnAlignCenter.clicked.connect(lambda: self.textEdit.setAlignment(Qt.AlignCenter))
        self.btnAlignRight = _button('fa5s.align-right', 'Align right')
        self.btnAlignRight.clicked.connect(lambda: self.textEdit.setAlignment(Qt.AlignRight))

        self.btnGroupAlignment = QButtonGroup(self.toolbar)
        self.btnGroupAlignment.setExclusive(True)
        self.btnGroupAlignment.addButton(self.btnAlignLeft)
        self.btnGroupAlignment.addButton(self.btnAlignCenter)
        self.btnGroupAlignment.addButton(self.btnAlignRight)

        self.btnInsertList = _button('fa5s.list', 'Insert list', checkable=False)
        self.btnInsertList.clicked.connect(lambda: self.textEdit.textCursor().insertList(QTextListFormat.ListDisc))
        self.btnInsertNumberedList = _button('fa5s.list-ol', 'Insert numbered list', checkable=False)
        self.btnInsertNumberedList.clicked.connect(
            lambda: self.textEdit.textCursor().insertList(QTextListFormat.ListDecimal))

        self.btnInsertLink = _button('fa5s.link', 'Insert link', checkable=False)
        self.btnInsertLink.clicked.connect(lambda: self._insertLink())

        self.btnExportToPdf = _button('mdi.file-export-outline', 'Export to PDF', checkable=False)
        self.btnExportToPdf.clicked.connect(lambda: self._exportPdf())
        self.btnPrint = _button('mdi.printer', 'Print', checkable=False)
        self.btnPrint.clicked.connect(lambda: self._print())

        self.toolbar.layout().addWidget(self.btnFormat)
        self.toolbar.layout().addWidget(vline())
        self.toolbar.layout().addWidget(self.btnBold)
        self.toolbar.layout().addWidget(self.btnItalic)
        self.toolbar.layout().addWidget(self.btnUnderline)
        self.toolbar.layout().addWidget(self.btnStrikethrough)
        self.toolbar.layout().addWidget(vline())
        self.toolbar.layout().addWidget(self.btnTextStyle)
        self.toolbar.layout().addWidget(vline())
        self.toolbar.layout().addWidget(self.btnAlignLeft)
        self.toolbar.layout().addWidget(self.btnAlignCenter)
        self.toolbar.layout().addWidget(self.btnAlignRight)
        self.toolbar.layout().addWidget(vline())
        self.toolbar.layout().addWidget(self.btnInsertList)
        self.toolbar.layout().addWidget(self.btnInsertNumberedList)
        self.toolbar.layout().addWidget(vline())
        self.toolbar.layout().addWidget(self.btnInsertLink)
        self.toolbar.layout().addWidget(spacer())
        self.toolbar.layout().addWidget(self.btnExportToPdf)
        self.toolbar.layout().addWidget(self.btnPrint)

        self.textEdit.cursorPositionChanged.connect(self._updateFormat)

    def _initTextEdit(self) -> EnhancedTextEdit:
        return EnhancedTextEdit(self)

    def _updateFormat(self):
        self.btnBold.setChecked(self.textEdit.fontWeight() == QFont.Bold)
        self.btnItalic.setChecked(self.textEdit.fontItalic())
        self.btnUnderline.setChecked(self.textEdit.fontUnderline())
        self.btnStrikethrough.setChecked(self.textEdit.currentFont().strikeOut())

        self.btnAlignLeft.setChecked(self.textEdit.alignment() == Qt.AlignLeft)
        self.btnAlignCenter.setChecked(self.textEdit.alignment() == Qt.AlignCenter)
        self.btnAlignRight.setChecked(self.textEdit.alignment() == Qt.AlignRight)

    def _insertLink(self):
        result = LinkCreationDialog().display()
        if result.accepted:
            self.textEdit.textCursor().insertHtml(f'<a href="{result.link}">{result.name}</a>')

    def _exportPdf(self):
        title = self._exportedDocumentTitle()
        fn, _ = QFileDialog.getSaveFileName(self, 'Export PDF', f'{title}.pdf',
                                            'PDF files (*.pdf);;All Files()')
        if fn:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(fn)
            printer.setDocName(title)
            self.__printHtml(printer)

    def _exportedDocumentTitle(self) -> str:
        return 'document'

    def _print(self):
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec_() == QPrintDialog.Accepted:
            self.__printHtml(printer)

    def __printHtml(self, printer: QPrinter):
        textedit = EnhancedTextEdit()  # create a new instance without the highlighters associated to it
        textedit.setFormat()
        textedit.setHtml(self.textEdit.toHtml())
        textedit.print(printer)
