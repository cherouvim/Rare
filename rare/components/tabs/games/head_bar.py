import platform as pf

from PyQt5.QtCore import QSettings, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import (
    QLabel,
    QPushButton,
    QWidget,
    QHBoxLayout,
    QComboBox, QToolButton, QMenu, QAction,
)
from qtawesome import IconWidget

from rare.shared import RareCore
from rare.utils.extra_widgets import SelectViewWidget, ButtonLineEdit
from rare.utils.misc import icon


class GameListHeadBar(QWidget):
    filterChanged: pyqtSignal = pyqtSignal(str)
    goto_import: pyqtSignal = pyqtSignal()
    goto_egl_sync: pyqtSignal = pyqtSignal()
    goto_eos_ubisoft: pyqtSignal = pyqtSignal()

    def __init__(self, parent=None):
        super(GameListHeadBar, self).__init__(parent=parent)
        self.rcore = RareCore.instance()
        self.settings = QSettings(self)

        self.filter = QComboBox(self)
        self.filter.addItem(self.tr("All games"), "all")
        self.filter.addItem(self.tr("Installed only"), "installed")
        self.filter.addItem(self.tr("Offline Games"), "offline")
        # self.filter.addItem(self.tr("Hidden"), "hidden")
        if self.rcore.bit32_games:
            self.filter.addItem(self.tr("32 Bit Games"), "32bit")
        if self.rcore.mac_games:
            self.filter.addItem(self.tr("Mac games"), "mac")
        if self.rcore.origin_games:
            self.filter.addItem(self.tr("Exclude Origin"), "installable")
        self.filter.addItem(self.tr("Include Unreal Engine"), "include_ue")

        filter_default = "mac" if pf.system() == "Darwin" else "all"
        filter_index = i if (i := self.filter.findData(filter_default, Qt.UserRole)) >= 0 else 0
        try:
            self.filter.setCurrentIndex(self.settings.value("library_filter", filter_index, int))
        except TypeError:
            self.settings.setValue("library_filter", filter_index)
            self.filter.setCurrentIndex(filter_index)
        self.filter.currentIndexChanged.connect(self.filter_changed)

        integrations_menu = QMenu(self)
        import_action = QAction(icon("mdi.import", "fa.arrow-down"), self.tr("Import Game"), integrations_menu)

        import_action.triggered.connect(self.goto_import)
        egl_sync_action = QAction(icon("mdi.sync", "fa.refresh"), self.tr("Sync with EGL"), integrations_menu)
        egl_sync_action.triggered.connect(self.goto_egl_sync)

        eos_ubisoft_action = QAction(icon("mdi.rocket", "fa.rocket"), self.tr("Epic Overlay and Ubisoft"),
                                     integrations_menu)
        eos_ubisoft_action.triggered.connect(self.goto_eos_ubisoft)

        integrations_menu.addAction(import_action)
        integrations_menu.addAction(egl_sync_action)
        integrations_menu.addAction(eos_ubisoft_action)

        integrations = QToolButton(self)
        integrations.setText(self.tr("Integrations"))
        integrations.setMenu(integrations_menu)
        integrations.setPopupMode(QToolButton.InstantPopup)

        self.search_bar = ButtonLineEdit("fa.search", placeholder_text=self.tr("Search Game"))
        self.search_bar.setObjectName("SearchBar")
        self.search_bar.setFrame(False)
        self.search_bar.setMinimumWidth(200)

        checked = QSettings().value("icon_view", True, bool)

        installed_tooltip = self.tr("Installed games")
        self.installed_icon = IconWidget(parent=self)
        self.installed_icon.setIcon(icon("ph.floppy-disk-back-fill"))
        self.installed_icon.setToolTip(installed_tooltip)
        self.installed_label = QLabel(parent=self)
        font = self.installed_label.font()
        font.setBold(True)
        self.installed_label.setFont(font)
        self.installed_label.setToolTip(installed_tooltip)
        available_tooltip = self.tr("Available games")
        self.available_icon = IconWidget(parent=self)
        self.available_icon.setIcon(icon("ph.floppy-disk-back-light"))
        self.available_icon.setToolTip(available_tooltip)
        self.available_label = QLabel(parent=self)
        self.available_label.setToolTip(available_tooltip)

        self.view = SelectViewWidget(checked)

        self.refresh_list = QPushButton()
        self.refresh_list.setIcon(icon("fa.refresh"))  # Reload icon
        self.refresh_list.clicked.connect(self.refresh_clicked)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 5, 0, 5)
        layout.addWidget(self.filter)
        layout.addStretch(0)
        layout.addWidget(integrations)
        layout.addStretch(5)
        layout.addWidget(self.search_bar)
        layout.addStretch(2)
        layout.addWidget(self.installed_icon)
        layout.addWidget(self.installed_label)
        layout.addWidget(self.available_icon)
        layout.addWidget(self.available_label)
        layout.addStretch(2)
        layout.addWidget(self.view)
        layout.addStretch(2)
        layout.addWidget(self.refresh_list)
        self.setLayout(layout)

    def set_games_count(self, inst: int, avail: int) -> None:
        self.installed_label.setText(str(inst))
        self.available_label.setText(str(avail))

    @pyqtSlot()
    def refresh_clicked(self):
        self.rcore.fetch()

    @pyqtSlot(int)
    def filter_changed(self, index: int):
        self.filterChanged.emit(self.filter.itemData(index, Qt.UserRole))
        self.settings.setValue("library_filter", index)
