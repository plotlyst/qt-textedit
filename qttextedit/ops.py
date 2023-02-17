from abc import abstractmethod
from enum import Enum
from functools import partial
from typing import List, Optional, Dict

import qtawesome
from qthandy import busy, vbox, line, bold, flow
from qtpy.QtCore import Qt, QSize, Signal, QTimer
from qtpy.QtGui import QFont, QKeySequence, QTextListFormat, QColor, QMouseEvent
from qtpy.QtPrintSupport import QPrinter, QPrintDialog
from qtpy.QtWidgets import QMenu, QToolButton, QTextEdit, QSizePolicy, QGridLayout, QWidget, QAction, QWidgetAction, \
    QFileDialog, QLabel, QSlider, QButtonGroup, QPushButton, QRadioButton

from qttextedit.diag import LinkCreationDialog
from qttextedit.util import button, qta_icon


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
    EDITING_SETTINGS = 'editing_settings'


class TextEditorOperation:

    @abstractmethod
    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        pass

    def updateFormat(self, textEdit: QTextEdit):
        pass


class TextEditorOperationAction(QAction, TextEditorOperation):
    def __init__(self, icon: str, text: str = '', tooltip: str = '', shortcut=None, checkable: bool = False,
                 parent=None):
        super(TextEditorOperationAction, self).__init__(parent)
        self.setText(text)
        if not tooltip:
            tooltip = text
        self.setToolTip(tooltip)
        self.setIcon(qta_icon(icon))
        if shortcut:
            self.setShortcut(shortcut)
        self.setCheckable(checkable)

    @abstractmethod
    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        pass


class TextEditorOperationWidgetAction(QWidgetAction, TextEditorOperation):
    def __init__(self, icon: str, tooltip: str = '', parent=None):
        super(TextEditorOperationWidgetAction, self).__init__(parent)
        self.setToolTip(tooltip)
        self.setIcon(qta_icon(icon))

    @abstractmethod
    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        pass


class TextEditorOperationMenu(QMenu, TextEditorOperation):
    def __init__(self, icon: str, tooltip: str = '', parent=None):
        super(TextEditorOperationMenu, self).__init__(parent)
        self.setToolTip(tooltip)
        self.setIcon(qta_icon(icon))

    @abstractmethod
    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        pass


class FormatOperation(TextEditorOperationMenu):
    def __init__(self, parent=None):
        super(FormatOperation, self).__init__('mdi.format-text', 'Format text', parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        for h_clazz in [TextOperation, Heading1Operation, Heading2Operation, Heading3Operation]:
            action = h_clazz(self)
            action.activateOperation(textEdit, editor)
            self.addAction(action)
        self.addSeparator()


class TextOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(TextOperation, self).__init__('mdi.format-text', 'Text', parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: textEdit.setHeading(0))


class HeadingOperation(TextEditorOperationAction):

    def __init__(self, heading: int, parent=None):
        self._heading = heading
        super(HeadingOperation, self).__init__(f'mdi.format-header-{heading}', f'Heading {heading}', parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: textEdit.setHeading(self._heading))


class Heading1Operation(HeadingOperation):

    def __init__(self, parent=None):
        super(Heading1Operation, self).__init__(1, parent)


class Heading2Operation(HeadingOperation):

    def __init__(self, parent=None):
        super(Heading2Operation, self).__init__(2, parent)


class Heading3Operation(HeadingOperation):

    def __init__(self, parent=None):
        super(Heading3Operation, self).__init__(3, parent)


class BoldOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(BoldOperation, self).__init__('fa5s.bold', 'Bold', shortcut=QKeySequence.Bold, checkable=True,
                                            parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda x: textEdit.setFontWeight(QFont.Bold if x else QFont.Normal))

    def updateFormat(self, textEdit: QTextEdit):
        self.setChecked(textEdit.fontWeight() == QFont.Bold)


class ItalicOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(ItalicOperation, self).__init__('fa5s.italic', 'Italic', shortcut=QKeySequence.Italic, checkable=True,
                                              parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda x: textEdit.setFontItalic(x))

    def updateFormat(self, textEdit: QTextEdit):
        self.setChecked(textEdit.fontItalic())


class UnderlineOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(UnderlineOperation, self).__init__('fa5s.underline', 'Underline', shortcut=QKeySequence.Underline,
                                                 checkable=True,
                                                 parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda x: textEdit.setFontUnderline(x))

    def updateFormat(self, textEdit: QTextEdit):
        self.setChecked(textEdit.fontUnderline())


class StrikethroughOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(StrikethroughOperation, self).__init__('fa5s.strikethrough', 'Strikethrough', checkable=True,
                                                     parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(textEdit.setStrikethrough)

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


class ColorOperation(TextEditorOperationWidgetAction):
    def __init__(self, parent=None):
        super(ColorOperation, self).__init__('fa5s.highlighter', 'Text color', parent=parent)
        self.wdgTextStyle = TextColorSelectorWidget(
            ['#da1e37', '#e85d04', '#9c6644', '#ffd500', '#2d6a4f', '#74c69d', '#023e8a', '#219ebc', '#7209b7',
             '#deaaff', '#ff87ab', '#4a4e69', '#ced4da', '#000000'],
            ['#da1e37', '#e85d04', '#9c6644', '#ffd500', '#2d6a4f', '#74c69d', '#023e8a', '#219ebc', '#7209b7',
             '#deaaff', '#ff87ab', '#4a4e69', '#ced4da', '#000000'])
        self.setDefaultWidget(self.wdgTextStyle)
        self.wdgTextStyle.foregroundColorSelected.connect(lambda: self.triggered.emit())
        self.wdgTextStyle.backgroundColorSelected.connect(lambda: self.triggered.emit())
        self.wdgTextStyle.reset.connect(lambda: self.triggered.emit())

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.wdgTextStyle.foregroundColorSelected.connect(lambda x: textEdit.setTextColor(x))
        self.wdgTextStyle.backgroundColorSelected.connect(lambda x: textEdit.setTextBackgroundColor(x))

        self.wdgTextStyle.reset.connect(textEdit.resetTextColor)


class AlignmentOperation(TextEditorOperationAction):

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: textEdit.setAlignment(self.alignment()))

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


class InsertListOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(InsertListOperation, self).__init__('fa5s.list', 'Bulleted list', 'Insert list', parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: textEdit.textCursor().createList(QTextListFormat.ListDisc))


class InsertNumberedListOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(InsertNumberedListOperation, self).__init__('fa5s.list-ol', 'Numbered list', 'Insert numbered list',
                                                          parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: textEdit.textCursor().createList(QTextListFormat.ListDecimal))


class InsertDividerOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(InsertDividerOperation, self).__init__('ri.separator', 'Divider', 'Insert horizontal divider',
                                                     parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: textEdit.textCursor().insertHtml('<hr></hr>'))


class InsertLinkOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(InsertLinkOperation, self).__init__('fa5s.link', 'Insert link', parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: self._insertLink(textEdit))

    def _insertLink(self, textEdit: QTextEdit):
        text = textEdit.textCursor().selectedText()
        result = LinkCreationDialog().display(text)
        if result.accepted:
            textEdit.textCursor().insertHtml(f'<a href="{result.link}">{result.name}</a>')


class ExportPdfOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(ExportPdfOperation, self).__init__('mdi.file-export-outline', 'Export to PDF', parent=parent)
        self._title = 'document'

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: self._exportPdf(textEdit))

    def title(self) -> str:
        return self._title

    def setTitle(self, value: str):
        self._title = value

    def _exportPdf(self, textEdit: QTextEdit):
        filename, _ = QFileDialog.getSaveFileName(textEdit, 'Export PDF', f'{self._title}.pdf',
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


class PrintOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(PrintOperation, self).__init__('mdi.printer', 'Print', parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: self._print(textEdit))

    @busy
    def _getPrinter(self) -> QPrinter:
        return QPrinter(QPrinter.HighResolution)

    def _print(self, textEdit: QTextEdit):
        printer = self._getPrinter()
        dialog = QPrintDialog(printer, textEdit)
        if dialog.exec_() == QPrintDialog.Accepted:
            textEdit.print(printer)


class TextEditorSettingsSection(Enum):
    FONT = 'font'
    FONT_SIZE = 'font_size'
    WIDTH = 'width'
    LINE_SPACE = 'line_space'


class AbstractSettingsSectionWidget(QWidget):
    def __init__(self, name: str, parent=None):
        super(AbstractSettingsSectionWidget, self).__init__(parent)
        self._editor = None

        vbox(self)
        lbl = QLabel(name)
        bold(lbl)
        self.layout().addWidget(lbl, alignment=Qt.AlignLeft)

    def attach(self, editor):
        self._editor = editor
        self._activate()

    def detach(self):
        if self._editor:
            self._deactivate()
        self._editor = None

    @abstractmethod
    def _activate(self):
        pass

    @abstractmethod
    def _deactivate(self):
        pass


class SliderSectionWidget(AbstractSettingsSectionWidget):
    def __init__(self, name: str, min_: int, max_: int, parent=None):
        super(SliderSectionWidget, self).__init__(name, parent)
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setCursor(Qt.PointingHandCursor)
        self._slider.setMinimum(min_)
        self._slider.setMaximum(max_)
        self.layout().addWidget(self._slider)

    def value(self) -> int:
        return self._slider.value()

    def setValue(self, value: int):
        self._slider.setValue(value)

    @abstractmethod
    def _activate(self):
        pass

    def _deactivate(self):
        self._slider.valueChanged.disconnect()


class PageWidthSectionSettingWidget(SliderSectionWidget):
    def __init__(self, parent=None):
        super(PageWidthSectionSettingWidget, self).__init__('Page Width', 20, 100, parent)

    def _activate(self):
        w = self._editor.widthPercentage()
        self._slider.setValue(w if w else 100)
        self._slider.valueChanged.connect(self._valueChanged)

    def _valueChanged(self, value: int):
        if self._editor is None:
            return
        self._editor.setWidthPercentage(value)


DEFAULT_FONT_FAMILIES = ['Times New Roman', 'Helvetica', "Arial", "Courier New"]


class FontSectionSettingWidget(AbstractSettingsSectionWidget):

    def __init__(self, parent=None):
        super().__init__('Font', parent)
        self._fontContainer = QWidget()
        flow(self._fontContainer)

        self._btnGroupFonts = QButtonGroup()
        self._btnGroupFonts.setExclusive(True)

        for f in DEFAULT_FONT_FAMILIES:
            btn = QRadioButton(f, self)
            btn.setCheckable(True)
            self._btnGroupFonts.addButton(btn)
            self._fontContainer.layout().addWidget(btn)

        self.layout().addWidget(self._fontContainer)

        self._btnGroupFonts.buttonToggled.connect(self._changeFont)

    def _activate(self):
        font_: QFont = self._editor.font()
        for btn in self._btnGroupFonts.buttons():
            if btn.text() == font_.family():
                btn.setChecked(True)

    def _deactivate(self):
        pass

    def _changeFont(self, btn: QPushButton, toggled):
        if toggled:
            font_: QFont = self._editor.font()
            font_.setFamily(btn.text())
            self._editor.setFont(font_)


class FontSizeSectionSettingWidget(SliderSectionWidget):
    def __init__(self, parent=None):
        super(FontSizeSectionSettingWidget, self).__init__('Font Size', 7, 32, parent)

    def _activate(self):
        size = self._editor.textEdit.font().pointSize()
        self._slider.setValue(size)
        self._slider.valueChanged.connect(self._valueChanged)

    def _valueChanged(self, value: int):
        if self._editor is None:
            return
        font = self._editor.textEdit.font()
        font.setPointSize(value)
        self._editor.textEdit.setFont(font)


class TextEditorSettingsWidget(QWidget):
    def __init__(self, parent=None):
        super(TextEditorSettingsWidget, self).__init__(parent)
        self._editor = None
        vbox(self)

        self._sections: Dict[TextEditorSettingsSection, AbstractSettingsSectionWidget] = {}
        self._addDefaultSection(TextEditorSettingsSection.FONT)
        self._addDefaultSection(TextEditorSettingsSection.FONT_SIZE)
        self._addDefaultSection(TextEditorSettingsSection.WIDTH)

    def attach(self, editor):
        self._editor = editor
        for wdg in self._sections.values():
            wdg.attach(self._editor)

    def detach(self):
        self._editor = None
        for wdg in self._sections.values():
            wdg.detach()

    def section(self, section: TextEditorSettingsSection) -> AbstractSettingsSectionWidget:
        return self._sections.get(section)

    def setSectionVisible(self, section: TextEditorSettingsSection, visible: bool):
        wdg = self._sections.get(section)
        if wdg:
            wdg.setVisible(visible)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pass

    def _addDefaultSection(self, section: TextEditorSettingsSection):
        if section == TextEditorSettingsSection.FONT_SIZE:
            wdg = FontSizeSectionSettingWidget(self)
        elif section == TextEditorSettingsSection.FONT:
            wdg = FontSectionSettingWidget(self)
        elif section == TextEditorSettingsSection.WIDTH:
            wdg = PageWidthSectionSettingWidget(self)
        else:
            raise ValueError('Unsupported Section type %s', section)
        if self._editor:
            wdg.attach(self._editor)
        self._sections[section] = wdg
        self.layout().addWidget(wdg)


class TextEditingSettingsOperation(TextEditorOperationWidgetAction):
    def __init__(self, parent=None):
        super(TextEditingSettingsOperation, self).__init__('fa5s.bars', 'Text editing settings', parent)
        self._wdgEditor = TextEditorSettingsWidget()
        self.setDefaultWidget(self._wdgEditor)

    def settingsWidget(self) -> TextEditorSettingsWidget:
        return self._wdgEditor

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        if editor is None:
            raise ValueError('RichTextEditor object must be passed to TextEditingSettingsOperation')
        QTimer.singleShot(5, lambda: self._delayedActivation(editor))

    def _delayedActivation(self, editor):
        if editor.settingsWidget() is None:
            editor.attachSettingsWidget(self._wdgEditor)
