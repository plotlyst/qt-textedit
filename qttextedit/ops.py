from abc import abstractmethod
from enum import Enum
from functools import partial
from typing import List

import qtawesome
from qthandy import btn_popup_menu, btn_popup, busy, vbox, line
from qtpy.QtCore import Qt, QSize, Signal
from qtpy.QtGui import QFont, QKeySequence, QTextListFormat, QColor
from qtpy.QtPrintSupport import QPrinter, QPrintDialog
from qtpy.QtWidgets import QFileDialog
from qtpy.QtWidgets import QMenu, QToolButton, QTextEdit, QSizePolicy, QGridLayout, QWidget

from qttextedit.diag import LinkCreationDialog
from qttextedit.util import button


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


class TextColorSelectorWidget(QWidget):
    foregroundColorSelected = Signal(QColor)
    backgroundColorSelected = Signal(QColor)
    reset = Signal()

    def __init__(self, foregroundColors: List[str], backgroundColors: List[str], parent=None):
        super(TextColorSelectorWidget, self).__init__(parent)

        vbox(self)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

        self.btnReset = button('mdi.format-color-marker-cancel', tooltip='Reset current color', checkable=False)
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
