import sys
from abc import abstractmethod
from enum import Enum
from functools import partial
from typing import List, Optional, Dict

import qtawesome
from qthandy import busy, vbox, line, bold, flow, margins, vspacer
from qtpy.QtCore import Qt, QSize, Signal, QTimer
from qtpy.QtGui import QFont, QKeySequence, QTextListFormat, QColor, QMouseEvent, QTextFrameFormat, QTextTableFormat, \
    QTextLength
from qtpy.QtPrintSupport import QPrinter, QPrintDialog
from qtpy.QtWidgets import QMenu, QToolButton, QTextEdit, QSizePolicy, QGridLayout, QWidget, QAction, QWidgetAction, \
    QFileDialog, QLabel, QSlider, QButtonGroup, QRadioButton, QTabWidget

from qttextedit.diag import LinkCreationDialog
from qttextedit.util import button, qta_icon


class TextEditorOperation:

    @abstractmethod
    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        pass

    def updateFormat(self, textEdit: QTextEdit):
        pass


class TextEditorOperationAction(QAction, TextEditorOperation):
    def __init__(self, icon: str, text: str = '', tooltip: str = '', icon_color: str = 'black', shortcut=None,
                 checkable: bool = False,
                 parent=None):
        super(TextEditorOperationAction, self).__init__(parent)
        self.setText(text)
        if not tooltip:
            tooltip = text
        self.setToolTip(tooltip)
        self.setIcon(qta_icon(icon, icon_color))
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


class AlignJustifyOperation(AlignmentOperation):
    def __init__(self, parent=None):
        super(AlignJustifyOperation, self).__init__('fa5s.align-justify', 'Align justify', checkable=True,
                                                    parent=parent)

    def alignment(self):
        return Qt.AlignJustify


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


class InsertTableOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(InsertTableOperation, self).__init__('fa5s.table', 'Table', 'Insert table', parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: self._insertTable(textEdit))

    def _insertTable(self, textEdit: QTextEdit):
        col_number = 3

        format = QTextTableFormat()
        format.setLeftMargin(10)
        format.setBorder(1)
        format.setBorderStyle(QTextTableFormat.BorderStyle_Ridge)
        format.setCellPadding(2)
        format.setCellSpacing(0)
        constraints = []
        for _ in range(col_number):
            constraints.append(QTextLength(QTextLength.PercentageLength, 25))
        format.setColumnWidthConstraints(constraints)

        textEdit.textCursor().insertTable(3, col_number, format)


class InsertDividerOperation(TextEditorOperationAction):
    def __init__(self, parent=None):
        super(InsertDividerOperation, self).__init__('ri.separator', 'Divider', 'Insert horizontal divider',
                                                     parent=parent)

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        self.triggered.connect(lambda: textEdit.textCursor().insertHtml('<hr></hr>'))


class InsertBannerOperation(TextEditorOperationAction):
    def __init__(self, borderColor: str, bgColor: str, title: str, parent=None):
        super(InsertBannerOperation, self).__init__('fa5.bookmark', f'{title} Banner', f'Insert {title.lower()} banner',
                                                    icon_color=borderColor,
                                                    parent=parent)
        self._borderColor = borderColor
        self._bgColor = bgColor

    def activateOperation(self, textEdit: QTextEdit, editor: Optional[QWidget] = None):
        frameFormat = QTextFrameFormat()
        frameFormat.setPadding(10)
        frameFormat.setTopMargin(1)
        frameFormat.setBottomMargin(1)
        frameFormat.setBorder(1)
        frameFormat.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Inset)
        frameFormat.setBorderBrush(QColor(self._borderColor))
        frameFormat.setBackground(QColor(self._bgColor))
        self.triggered.connect(lambda: textEdit.textCursor().insertFrame(frameFormat))


class InsertRedBannerOperation(InsertBannerOperation):
    def __init__(self, parent=None):
        super(InsertRedBannerOperation, self).__init__('#E30040', '#FFEDF0', 'Red', parent)


class InsertGrayBannerOperation(InsertBannerOperation):
    def __init__(self, parent=None):
        super(InsertGrayBannerOperation, self).__init__('#313240', '#EEEFF0', 'Gray', parent)


class InsertBlueBannerOperation(InsertBannerOperation):
    def __init__(self, parent=None):
        super(InsertBlueBannerOperation, self).__init__('#2076DF', '#EBF5FD', 'Blue', parent)


class InsertGreenBannerOperation(InsertBannerOperation):
    def __init__(self, parent=None):
        super(InsertGreenBannerOperation, self).__init__('#009C48', '#E8F8F0', 'Green', parent)


class InsertYellowBannerOperation(InsertBannerOperation):
    def __init__(self, parent=None):
        super(InsertYellowBannerOperation, self).__init__('#FDB80F', '#FDFCEB', 'Yellow', parent)


class InsertPurpleBannerOperation(InsertBannerOperation):
    def __init__(self, parent=None):
        super(InsertPurpleBannerOperation, self).__init__('#8100EC', '#F4EDFE', 'Purple', parent)


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
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
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
        return QPrinter(QPrinter.PrinterMode.HighResolution)

    def _print(self, textEdit: QTextEdit):
        printer = self._getPrinter()
        dialog = QPrintDialog(printer, textEdit)
        if dialog.exec_() == QPrintDialog.Accepted:
            textEdit.print(printer)


class TextEditorSettingsSection(Enum):
    FONT = 'font'
    FONT_SIZE = 'font_size'
    PAGE_WIDTH = 'page_width'
    TEXT_WIDTH = 'text_width'
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
        self._slider.setMaximumWidth(200)
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
        super().__init__('Page Width', 20, 100, parent)

    def _activate(self):
        w = self._editor.widthPercentage()
        self._slider.setValue(w if w else 100)
        self._slider.valueChanged.connect(self._valueChanged)

    def _valueChanged(self, value: int):
        if self._editor is None:
            return
        self._editor.setWidthPercentage(value)


class TextWidthSectionSettingWidget(SliderSectionWidget):
    def __init__(self, parent=None):
        super().__init__('Text Width', 40, 80, parent)

    def _activate(self):
        self._slider.setValue(self._editor.characterWidth())
        self._slider.valueChanged.connect(self._valueChanged)

    def _valueChanged(self, value: int):
        if self._editor is None:
            return
        self._editor.setCharacterWidth(value)


DEFAULT_FONT_FAMILIES = []
if sys.platform in ('win32', 'cygwin'):
    DEFAULT_FONT_FAMILIES = [
        'Segoe UI',  # sans-serif
        'Verdana',  # sans-serif
        'Times New Roman',  # serif
        'Georgia',  # serif
        'Garamond',  # serif
        'Courier New',  # mono
        'Segoe Print',  # cursive
        'Segoe Script',  # cursive
        'Comic Sans MS',  # cursive
    ]
elif sys.platform == 'darwin':
    DEFAULT_FONT_FAMILIES = [
        'Helvetica',  # sans-serif
        'Times New Roman',  # serif
        'Courier New',  # mono
        'Apple Chancery',  # cursive
        'Papyrus',  # fantasy
    ]
elif sys.platform.startswith('linux'):
    DEFAULT_FONT_FAMILIES = ['Sans-serif', 'Serif', 'Monospace', 'Cursive']


class FontRadioButton(QRadioButton):
    def __init__(self, family: str, parent=None):
        super(FontRadioButton, self).__init__(family, parent)
        self._family = family
        self.setCheckable(True)
        font = self.font()
        font.setFamily(family)
        self.setFont(font)

    def family(self) -> str:
        return self._family


class FontSectionSettingWidget(AbstractSettingsSectionWidget):
    fontSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__('Font', parent)
        self._fontContainer = QWidget()
        self._fontContainer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        flow(self._fontContainer)
        margins(self._fontContainer, left=10)

        self._btnGroupFonts = QButtonGroup()
        self._btnGroupFonts.setExclusive(True)

        for family in DEFAULT_FONT_FAMILIES:
            btn = FontRadioButton(family, self)
            self._btnGroupFonts.addButton(btn)
            self._fontContainer.layout().addWidget(btn)

        self.layout().addWidget(self._fontContainer)

        self._btnGroupFonts.buttonToggled.connect(self._changeFont)
        self._btnGroupFonts.buttonClicked.connect(self._fontClicked)

    def _activate(self):
        font_: QFont = self._editor.textEdit.font()
        for btn in self._btnGroupFonts.buttons():
            if btn.family() == font_.family():
                btn.setChecked(True)

    def _deactivate(self):
        pass

    def _changeFont(self, btn: FontRadioButton, toggled):
        if toggled:
            font_: QFont = self._editor.textEdit.font()
            font_.setFamily(btn.family())
            self._editor.textEdit.setFont(font_)

    def _fontClicked(self, btn: FontRadioButton):
        self.fontSelected.emit(btn.family())
        if self._editor.characterWidth():
            self._editor.setCharacterWidth(self._editor.characterWidth())


class FontSizeSectionSettingWidget(SliderSectionWidget):
    def __init__(self, parent=None):
        super(FontSizeSectionSettingWidget, self).__init__('Font Size', 10, 20, parent)

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
        if self._editor.characterWidth():
            self._editor.setCharacterWidth(self._editor.characterWidth())


class TextEditorSettingsWidget(QTabWidget):
    def __init__(self, parent=None):
        super(TextEditorSettingsWidget, self).__init__(parent)
        self._editor = None
        self._defaultTab = QWidget(self)
        self.addTab(self._defaultTab, qta_icon('mdi.format-text'), '')
        vbox(self._defaultTab)

        self._sections: Dict[TextEditorSettingsSection, AbstractSettingsSectionWidget] = {}
        self._addDefaultSection(TextEditorSettingsSection.FONT)
        self._addDefaultSection(TextEditorSettingsSection.FONT_SIZE)
        self._addDefaultSection(TextEditorSettingsSection.PAGE_WIDTH)
        self._addDefaultSection(TextEditorSettingsSection.TEXT_WIDTH)
        self.setSectionVisible(TextEditorSettingsSection.TEXT_WIDTH, False)
        self._defaultTab.layout().addWidget(vspacer())

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
        elif section == TextEditorSettingsSection.PAGE_WIDTH:
            wdg = PageWidthSectionSettingWidget(self)
        elif section == TextEditorSettingsSection.TEXT_WIDTH:
            wdg = TextWidthSectionSettingWidget(self)
        else:
            raise ValueError('Unsupported Section type %s', section)
        if self._editor:
            wdg.attach(self._editor)
        self._sections[section] = wdg
        self._defaultTab.layout().addWidget(wdg)


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
