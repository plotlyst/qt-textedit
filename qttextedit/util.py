from qtpy.QtGui import QTextCursor


def select_anchor(cursor: QTextCursor) -> QTextCursor:
    pos_cursor = QTextCursor(cursor)
    while pos_cursor.charFormat().anchorHref() == cursor.charFormat().anchorHref() \
            and not pos_cursor.atBlockStart():
        pos_cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter)
    if pos_cursor.charFormat().anchorHref() != cursor.charFormat().anchorHref():
        pos_cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)

    while pos_cursor.charFormat().anchorHref() == cursor.charFormat().anchorHref() \
            and not pos_cursor.atBlockEnd():
        pos_cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
    if pos_cursor.charFormat().anchorHref() != cursor.charFormat().anchorHref():
        pos_cursor.movePosition(QTextCursor.MoveOperation.PreviousCharacter, QTextCursor.MoveMode.KeepAnchor)
    return pos_cursor
