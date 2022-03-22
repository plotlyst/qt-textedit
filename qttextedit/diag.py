from dataclasses import dataclass

import qtawesome
from qthandy import vbox, hbox, transparent
from qtpy.QtWidgets import QDialog, QSizePolicy, QWidget, QToolButton, QLineEdit, QDialogButtonBox


@dataclass
class LinkCreationResult:
    accepted: bool
    link: str
    name: str


class LinkCreationDialog(QDialog):
    def __init__(self, parent=None):
        super(LinkCreationDialog, self).__init__(parent)
        self.setWindowTitle('Insert link')
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        vbox(self)

        self._wdgLink = QWidget()
        hbox(self._wdgLink)
        self._btnLinkIcon = QToolButton()
        self._btnLinkIcon.setIcon(qtawesome.icon('fa5s.link'))
        transparent(self._btnLinkIcon)
        self.lineLink = QLineEdit()
        self.lineLink.setPlaceholderText('https://...')
        self.lineLink.textChanged.connect(self._linkChanged)
        self._wdgLink.layout().addWidget(self._btnLinkIcon)
        self._wdgLink.layout().addWidget(self.lineLink)

        self._wdgName = QWidget()
        hbox(self._wdgName)
        self._btnNameIcon = QToolButton()
        transparent(self._btnNameIcon)
        self._btnNameIcon.setIcon(qtawesome.icon('mdi6.format-text-variant', options=[{'scale_factor': 1.2}]))
        self.lineName = QLineEdit()
        self.lineName.setPlaceholderText('Displayed text')
        self.lineName.textEdited.connect(self._nameEdited)
        self._nameManuallyEdited: bool = False
        self._wdgName.layout().addWidget(self._btnNameIcon)
        self._wdgName.layout().addWidget(self.lineName)

        self._btnBox = QDialogButtonBox()
        self._btnBox.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btnOk = self._btnBox.button(QDialogButtonBox.Ok)
        self.btnOk.setEnabled(False)
        self.btnCancel = self._btnBox.button(QDialogButtonBox.Cancel)
        self.btnOk.clicked.connect(lambda: self.accept())
        self.btnCancel.clicked.connect(lambda: self.reject())

        self.layout().addWidget(self._wdgLink)
        self.layout().addWidget(self._wdgName)
        self.layout().addWidget(self._btnBox)

    def display(self, name: str = '') -> LinkCreationResult:
        if name:
            self.lineName.setText(name)
            self._nameManuallyEdited = True

        self.lineLink.setFocus()
        result = self.exec()
        if result == QDialog.Accepted:
            name = self.lineName.text() if self.lineName.text() else self.lineLink.text()
            return LinkCreationResult(True, self.lineLink.text(), name)
        return LinkCreationResult(False, '', '')

    def _linkChanged(self, text: str):
        self.btnOk.setEnabled(len(text) > 0)
        if not self._nameManuallyEdited:
            self.lineName.setText(text)

    def _nameEdited(self):
        self._nameManuallyEdited = len(self.lineName.text()) > 0
