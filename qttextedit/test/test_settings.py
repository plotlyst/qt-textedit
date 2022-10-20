from qthandy import vbox
from qtpy.QtWidgets import QWidget

from qttextedit import RichTextEditor, TextEditorSettingsWidget
from qttextedit.ops import TextEditorSettingsSection
from qttextedit.test.common import type_text


def prepare_richtext_editor(qtbot):
    widget = QWidget()
    vbox(widget)
    editor = RichTextEditor()
    widget.layout().addWidget(editor)
    settings = TextEditorSettingsWidget()
    widget.layout().addWidget(settings)
    editor.attachSettingsWidget(settings)
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)

    return widget, editor, settings


def test_page_width(qtbot):
    widget, editor, settings = prepare_richtext_editor(qtbot)
    settings.setSectionVisible(TextEditorSettingsSection.WIDTH, False)

    type_text(qtbot, editor, 'Test text')

    assert editor.widthPercentage() == 0
    wdg = settings.section(TextEditorSettingsSection.WIDTH)
    assert wdg.value() == 100
    wdg.setValue(50)
    assert editor.widthPercentage() == 50
