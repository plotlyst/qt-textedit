from qtpy.QtGui import QTextCursor


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


def select_previous_character(cursor: QTextCursor) -> QTextCursor:
    moved_cursor = QTextCursor(cursor)
    moved_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)

    return moved_cursor


def select_next_character(cursor: QTextCursor) -> QTextCursor:
    moved_cursor = QTextCursor(cursor)
    moved_cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)

    return moved_cursor


OPEN_QUOTATIONS = ('"', '"', '“', "«", "‹", "“")


def is_open_quotation(char: str) -> bool:
    return char in OPEN_QUOTATIONS
