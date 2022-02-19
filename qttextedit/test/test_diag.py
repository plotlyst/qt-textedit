from qttextedit import LinkCreationDialog
from qttextedit.test.test_textedit import type_text


def test_link_creation_dialog_when_link_is_copied(qtbot):
    diag = LinkCreationDialog()
    diag.show()
    qtbot.addWidget(diag)

    assert not diag.btnOk.isEnabled()
    type_text(qtbot, diag.lineLink, 'https://')
    assert diag.lineName.text() == 'https://'
    assert diag.btnOk.isEnabled()


def test_link_creation_dialog_when_link_is_not_copied(qtbot):
    diag = LinkCreationDialog()
    diag.show()
    qtbot.addWidget(diag)

    type_text(qtbot, diag.lineName, 'name')
    type_text(qtbot, diag.lineLink, 'https://')
    assert diag.lineName.text() == 'name'
