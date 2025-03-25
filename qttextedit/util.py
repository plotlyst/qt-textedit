import re
from timeit import default_timer as timer
from typing import Optional

import qtawesome
from qthandy import pointy, transparent
from qtpy.QtCore import QSize, Qt, QEvent, QObject
from qtpy.QtGui import QTextCursor, QIcon, QAction
from qtpy.QtWidgets import QToolButton

ELLIPSIS = u'\u2026'
EN_DASH = u'\u2013'
EM_DASH = u'\u2014'
NBSP = u'\u00A0'

LEFT_SINGLE_QUOTATION = u'\u2018'
RIGHT_SINGLE_QUOTATION = u'\u2019'
LEFT_DOUBLE_QUOTATION = u'\u201C'
RIGHT_DOUBLE_QUOTATION = u'\u201D'

HEAVY_ARROW_RIGHT = u'\u279C'
LONG_ARROW_LEFT_RIGHT = u'\u27F7'
SHORT_ARROW_LEFT_RIGHT = u'\u21C4'

OPEN_QUOTATIONS = ('"', LEFT_DOUBLE_QUOTATION, "«", "‹", "“")
ENDING_PUNCTUATIONS = ('.', '?', '!')

OBJECT_REPLACEMENT_CHARACTER = u'\uFFFC'


def is_open_quotation(char: str) -> bool:
    return char in OPEN_QUOTATIONS


def is_ending_punctuation(char: str) -> bool:
    return char in ENDING_PUNCTUATIONS


def select_anchor(cursor: QTextCursor) -> QTextCursor:
    pos_cursor = QTextCursor(cursor)
    while pos_cursor.charFormat().anchorHref() == cursor.charFormat().anchorHref() \
            and not pos_cursor.atBlockStart():
        pos_cursor.movePosition(QTextCursor.PreviousCharacter)
    if pos_cursor.charFormat().anchorHref() != cursor.charFormat().anchorHref():
        pos_cursor.movePosition(QTextCursor.NextCharacter)

    while pos_cursor.charFormat().anchorHref() == cursor.charFormat().anchorHref() \
            and not pos_cursor.atBlockEnd():
        pos_cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
    if pos_cursor.charFormat().anchorHref() != cursor.charFormat().anchorHref():
        pos_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
    return pos_cursor


def select_previous_character(cursor: QTextCursor, amount: int = 1) -> QTextCursor:
    moved_cursor = QTextCursor(cursor)
    for _ in range(amount):
        moved_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)

    return moved_cursor


def select_next_character(cursor: QTextCursor, amount: int = 1) -> QTextCursor:
    moved_cursor = QTextCursor(cursor)
    for _ in range(amount):
        moved_cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)

    return moved_cursor


def has_character_left(cursor: QTextCursor) -> bool:
    if cursor.atBlockStart():
        return False
    moved_cursor = select_previous_character(cursor)
    if moved_cursor.selectedText() and moved_cursor.selectedText() != ' ':
        return True
    return False


def has_character_right(cursor: QTextCursor) -> bool:
    if cursor.atBlockEnd():
        return False
    moved_cursor = select_next_character(cursor)
    if moved_cursor.selectedText() and moved_cursor.selectedText() != ' ':
        return True
    return False


def button(icon: str, tooltip: str = '', shortcut=None, checkable: bool = True) -> QToolButton:
    btn = QToolButton()
    btn.setToolTip(tooltip)
    btn.setIconSize(QSize(18, 18))
    btn.setCursor(Qt.PointingHandCursor)
    btn.setIcon(qta_icon(icon))
    if shortcut:
        btn.setShortcut(shortcut)
    btn.setCheckable(checkable)

    return btn


def qta_icon(name: str, color: str = 'black') -> QIcon:
    if name.startswith('md') or name.startswith('ri'):
        return qtawesome.icon(name, options=[{'scale_factor': 1.2}], color=color)
    return qtawesome.icon(name, color=color)


def remove_font(html: str) -> str:
    return re.sub(r'font-(family|size):(\'|"|\w|\s|-|,|%|\.|&quot;)*;', '', html)


def q_action(text: str, icon: Optional[QIcon] = None, slot=None, parent=None, checkable: bool = False,
             tooltip: str = '', enabled: bool = True) -> QAction:
    _action = QAction(text)
    if icon:
        _action.setIcon(icon)
    if slot:
        _action.triggered.connect(slot)
    if parent:
        _action.setParent(parent)
    _action.setCheckable(checkable)
    _action.setToolTip(tooltip)
    _action.setEnabled(enabled)

    return _action


class CloseButton(QToolButton):
    def __init__(self, parent=None, colorOff: str = 'grey', colorOn='black', colorHover='darkgrey'):
        super().__init__(parent)
        self._colorOff = colorOff
        self._colorHover = colorHover
        self.setIcon(qta_icon('ei.remove', self._colorOff))
        pointy(self)
        self.installEventFilter(self)
        self.setIconSize(QSize(14, 14))
        transparent(self)

        self.pressed.connect(lambda: self.setIcon(qta_icon('ei.remove', colorOn)))
        self.released.connect(lambda: self.setIcon(qta_icon('ei.remove', colorOff)))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            self.setIcon(qta_icon('ei.remove', self._colorHover))
        elif event.type() == QEvent.Type.Leave:
            self.setIcon(qta_icon('ei.remove', self._colorOff))
        return super().eventFilter(watched, event)


class Timer:
    def __init__(self, prefix: str = 'Elapsed', auto_start: bool = True):
        self._prefix = prefix
        self._elapsed = 0
        self._start = 0

        if auto_start:
            self.start()

    def start(self):
        self._start = timer()

    def end(self, suffix: str = '') -> float:
        end = timer()
        self._elapsed = end - self._start
        if suffix:
            suffix = f'[{suffix}]'
        print(f'{self._prefix}: {self._elapsed} {suffix}')

        return self._elapsed
