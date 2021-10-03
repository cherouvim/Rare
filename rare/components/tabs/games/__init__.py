from logging import getLogger

from PyQt5.QtCore import pyqtSignal, QSettings
from PyQt5.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from legendary.core import LegendaryCore
from rare.components.dialogs.uninstall_dialog import UninstallDialog
from rare.components.tabs.games.game_info import InfoTabs
from rare.components.tabs.games.game_info.uninstalled_info import UninstalledTabInfo
from rare.components.tabs.games.game_widgets.base_installed_widget import BaseInstalledWidget
from rare.components.tabs.games.game_widgets.base_uninstalled_widget import BaseUninstalledWidget
from rare.components.tabs.games.game_widgets.installed_icon_widget import InstalledIconWidget
from rare.components.tabs.games.game_widgets.installed_list_widget import InstalledListWidget
from rare.components.tabs.games.game_widgets.installing_game_widget import InstallingGameWidget
from rare.components.tabs.games.game_widgets.uninstalled_icon_widget import IconWidgetUninstalled
from rare.components.tabs.games.game_widgets.uninstalled_list_widget import ListWidgetUninstalled
from rare.components.tabs.games.head_bar import GameListHeadBar
from rare.components.tabs.games.import_widget import ImportWidget
from rare.ui.components.tabs.games.games_tab import Ui_GamesTab
from rare.utils import legendary_utils
from rare.utils.extra_widgets import FlowLayout
from rare.utils.models import Signals, ApiResults
from rare.utils.utils import get_pixmap, download_image, get_uninstalled_pixmap

logger = getLogger("GamesTab")


class GamesTab(QStackedWidget, Ui_GamesTab):
    updates = []
    widgets = {}
    running_games = []
    game_exited = pyqtSignal(str)
    game_started = pyqtSignal(str)

    def __init__(self, core: LegendaryCore, offline, signals: Signals, api_results: ApiResults):
        super(GamesTab, self).__init__()
        self.setupUi(self)
        self.core = core
        self.offline = offline
        self.signals = signals
        self.signals.games_tab.connect(lambda x: self.signal_received(*x))
        self.settings = QSettings()

        self.head_bar = GameListHeadBar()
        self.games.layout().insertWidget(0, self.head_bar)

        self.game_info = InfoTabs(self.core, self.signals, self)
        self.addWidget(self.game_info)

        self.import_widget = ImportWidget(core, self)
        self.addWidget(self.import_widget)

        self.uninstalled_info_widget = UninstalledTabInfo(core, self.signals, self.offline, self)
        self.layout().addWidget(self.uninstalled_info_widget)

        # navigation
        self.head_bar.import_game.clicked.connect(lambda: self.setCurrentIndex(2))
        self.import_widget.back_button.clicked.connect(lambda: self.setCurrentIndex(0))
        self.uninstalled_info_widget.tabBarClicked.connect(lambda x: self.setCurrentIndex(0) if x == 0 else None)

        self.game_list = api_results.game_list
        self.dlcs = api_results.dlcs
        self.bit32 = api_results.bit32_games
        self.mac_games = api_results.mac_games
        self.no_assets = api_results.no_asset_games
        self.no_asset_names = []
        if not self.offline:
            for game in self.no_assets:
                self.no_asset_names.append(game.app_name)
        else:
            self.no_assets = []

        self.setup_game_list()

        if not self.settings.value("icon_view", True, bool):
            self.scroll_widget.layout().insertWidget(1, self.list_view)
            self.head_bar.view.list()
        else:
            self.scroll_widget.layout().insertWidget(1, self.icon_view)

        self.head_bar.search_bar.textChanged.connect(self.search)
        self.head_bar.filter_changed_signal.connect(self.filter)
        self.head_bar.refresh_list.clicked.connect(self.update_list)
        self.head_bar.view.toggled.connect(self.toggle_view)

        self.filter(self.head_bar.available_filters[self.settings.value("filter", 0, int)])

    def signal_received(self, action, data):
        if action == self.signals.actions.dl_status:
            self.installing_widget.set_status(data)
        elif action == self.signals.actions.set_index:
            self.setCurrentIndex(data)
        elif action == self.signals.actions.start_installation:
            self.installing_widget.set_game(data)
            self.installing_widget.setVisible(True)
        elif action == self.signals.actions.installation_finished:
            self.update_list(data)
            self.installing_widget.setVisible(False)
        elif action == self.signals.actions.uninstall:
            infos = UninstallDialog(data).get_information()
            if infos == 0:
                return
            legendary_utils.uninstall(data.app_name, self.core, infos)
            self.setCurrentIndex(0)
            self.update_list(data.app_name)

    def show_game_info(self, game):
        self.game_info.update_game(game, self.dlcs)
        self.setCurrentIndex(1)

    def show_uninstalled_info(self, game):
        self.uninstalled_info_widget.update_game(game)
        self.setCurrentIndex(3)

    def setup_game_list(self):

        self.icon_view = QWidget()
        self.icon_view.setLayout(FlowLayout())
        self.list_view = QWidget()
        self.list_view.setLayout(QVBoxLayout())

        self.installed = sorted(self.core.get_installed_list(), key=lambda x: x.title)
        installed_names = [i.app_name for i in self.installed]
        self.update_count_games_label()

        # add installing game widget for icon view: List view not supported
        self.installing_widget = InstallingGameWidget()
        self.icon_view.layout().addWidget(self.installing_widget)
        self.installing_widget.setVisible(False)

        # add installed games
        for igame in self.installed:
            icon_widget, list_widget = self.add_installed_widget(self.core.get_game(igame.app_name))
            self.icon_view.layout().addWidget(icon_widget)
            self.list_view.layout().addWidget(list_widget)

        for game in self.no_assets:
            icon_widget, list_widget = self.add_installed_widget(game, is_origin=True)
            self.icon_view.layout().addWidget(icon_widget)
            self.list_view.layout().addWidget(list_widget)

        self.uninstalled_games = []
        for game in sorted(self.game_list, key=lambda x: x.app_title):
            if game.app_name not in [i.app_name for i in self.installed]:
                self.uninstalled_games.append(game)
                icon_widget, list_widget = self.add_uninstalled_widget(game)
                self.icon_view.layout().addWidget(icon_widget)
                self.list_view.layout().addWidget(list_widget)

    def update_count_games_label(self):
        self.count_games_label.setText(self.tr("Installed Games: {}    Available Games: {}").format(
            len(self.core.get_installed_list()),
            len(self.game_list)))

    def add_installed_widget(self, game, is_origin=False):
        pixmap = get_pixmap(game.app_name)
        if pixmap.isNull():
            logger.info(game.app_title + " has a corrupt image.")
            download_image(self.core.get_game(game.app_name), force=True)
            pixmap = get_pixmap(game.app_name)

        if game.app_name in self.no_asset_names:
            igame = None
        else:
            igame = self.core.get_installed_game(game.app_name)

        icon_widget = InstalledIconWidget(igame, self.core, pixmap, self.offline, is_origin, game)

        list_widget = InstalledListWidget(igame, self.core, pixmap, self.offline, is_origin, game)

        self.widgets[game.app_name] = (icon_widget, list_widget)

        icon_widget.show_info.connect(self.show_game_info)
        list_widget.show_info.connect(self.show_game_info)

        icon_widget.launch_signal.connect(self.launch)
        icon_widget.finish_signal.connect(self.finished)
        icon_widget.update_list.connect(self.update_list)

        list_widget.launch_signal.connect(self.launch)
        list_widget.finish_signal.connect(self.finished)
        list_widget.update_list.connect(self.update_list)

        if icon_widget.update_available:
            self.updates.append(igame)

        return icon_widget, list_widget

    def add_uninstalled_widget(self, game):
        pixmap = get_uninstalled_pixmap(game.app_name)
        if pixmap.isNull():
            logger.info(game.app_title + " has a corrupt image. Reloading...")
            download_image(game, force=True)
            pixmap = get_uninstalled_pixmap(game.app_name)

        icon_widget = IconWidgetUninstalled(game, self.core, pixmap)
        icon_widget.show_uninstalled_info.connect(self.show_uninstalled_info)

        list_widget = ListWidgetUninstalled(self.core, game, pixmap)
        list_widget.show_uninstalled_info.connect(self.show_uninstalled_info)

        self.widgets[game.app_name] = (icon_widget, list_widget)

        return icon_widget, list_widget

    def finished(self, app_name):
        self.running_games.remove(app_name)
        self.widgets[app_name][0].info_text = ""
        self.widgets[app_name][0].info_label.setText("")
        self.widgets[app_name][1].launch_button.setDisabled(False)
        self.widgets[app_name][1].launch_button.setText(self.tr("Launch"))
        if self.widgets[app_name][0].game.supports_cloud_saves:
            if not self.settings.value(f"{app_name}/auto_sync_cloud", True, bool) \
                    and not self.settings.value("auto_sync_cloud", True, bool):
                logger.info("Auto saves disabled")
                return

            self.widgets[app_name][0].info_text = self.tr("Sync CLoud saves")
            self.widgets[app_name][0].info_label.setText(self.tr("Sync CLoud saves"))
            self.widgets[app_name][1].info_label.setText(self.tr("Sync CLoud saves"))
        self.game_exited.emit(app_name)

    def launch(self, app_name):
        self.running_games.append(app_name)
        self.game_started.emit(app_name)
        self.widgets[app_name][0].info_text = self.tr("Game running")
        self.widgets[app_name][0].info_label.setText(self.tr("Game running"))
        self.widgets[app_name][1].launch_button.setDisabled(True)
        self.widgets[app_name][1].launch_button.setText(self.tr("Game running"))

    def search(self, text: str):
        for t in self.widgets.values():
            for w in t:
                if text.lower() in w.game.app_title.lower() + w.game.app_name.lower():
                    w.setVisible(True)
                else:
                    w.setVisible(False)

    def filter(self, filter_name="installed"):
        for t in self.widgets.values():
            # icon and list widget
            for w in t:
                if filter_name == "installed":
                    w.setVisible(self.core.is_installed(w.game.app_name))
                elif filter_name == "offline":
                    if self.core.is_installed(w.game.app_name):
                        w.setVisible(w.igame.can_run_offline)
                    else:
                        w.setVisible(False)
                elif filter_name == "32bit" and self.bit32:
                    w.setVisible(w.game.app_name in self.bit32)
                elif filter_name == "mac":
                    w.setVisible(w.game.app_name in self.mac_games)
                elif filter_name == "installable":
                    w.setVisible(w.game.app_name not in self.no_asset_names)
                else:
                    # All visible
                    w.setVisible(True)

    def update_list(self, app_name=None):
        if app_name:
            if widgets := self.widgets.get(app_name):

                # from update
                if self.core.is_installed(widgets[0].game.app_name) and isinstance(widgets[0], BaseInstalledWidget):
                    igame = self.core.get_installed_game(app_name)
                    for w in widgets:
                        w.igame = igame
                        w.update_available = self.core.get_asset(w.game.app_name, True).build_version != igame.version
                    widgets[0].info_label.setText("")
                    widgets[0].info_text = ""
                # new installed
                elif self.core.is_installed(app_name) and isinstance(widgets[0], BaseUninstalledWidget):
                    logger.debug("Update Gamelist: New installed " + app_name)
                    self.widgets[app_name][0].deleteLater()
                    self.widgets[app_name][1].deleteLater()
                    self.widgets.pop(app_name)

                    igame = self.core.get_installed_game(app_name)
                    self.add_installed_widget(self.core.get_game(igame.app_name))

                    self._update_games()

                # uninstalled
                elif not self.core.is_installed(widgets[0].game.app_name) and isinstance(widgets[0],
                                                                                         BaseInstalledWidget):
                    logger.debug("Update list: uninstall")
                    self.widgets[app_name][0].deleteLater()
                    self.widgets[app_name][1].deleteLater()

                    self.widgets.pop(app_name)

                    game = self.core.get_game(app_name, False)
                    self.add_uninstalled_widget(game)

                    self._update_games()

        else:
            installed_names = [i.app_name for i in self.core.get_installed_list()]
            # get Uninstalled games
            uninstalled_names = []
            games = self.core.get_game_list(True)
            for game in sorted(games, key=lambda x: x.app_title):
                if not game.app_name in installed_names:
                    uninstalled_names.append(game.app_name)

            new_installed_games = list(set(installed_names) - set([i.app_name for i in self.installed]))
            new_uninstalled_games = list(set(uninstalled_names) - set([i.app_name for i in self.uninstalled_games]))

            if (not new_uninstalled_games) and (not new_installed_games):
                return

            if new_installed_games:
                for name in new_installed_games:
                    self.icon_view.layout().removeWidget(self.widgets[name][0])
                    self.list_view.layout().removeWidget(self.widgets[name][1])

                    self.widgets[name][0].deleteLater()
                    self.widgets[name][1].deleteLater()
                    self.widgets.pop(name)

                    igame = self.core.get_installed_game(name)
                    self.add_installed_widget(self.core.get_game(igame.app_name))

                for name in new_uninstalled_games:
                    self.icon_view.layout().removeWidget(self.widgets[app_name][0])
                    self.list_view.layout().removeWidget(self.widgets[app_name][1])

                    self.widgets[name][0].deleteLater()
                    self.widgets[name][1].deleteLater()

                    self.widgets.pop(name)

                    game = self.core.get_game(name, True)
                    self.add_uninstalled_widget(game)

                for igame in sorted(self.core.get_installed_list(), key=lambda x: x.title):
                    i_widget, list_widget = self.widgets[igame.app_name]

                    self.icon_view.layout().addWidget(i_widget)
                    self.list_view.layout().addWidget(list_widget)

                # get Uninstalled games
                games, self.dlcs = self.core.get_game_and_dlc_list()
                for game in sorted(games, key=lambda x: x.app_title):
                    if not game.app_name in installed_names:
                        self.uninstalled_names.append(game)
                for name in uninstalled_names:
                    i_widget, list_widget = self.widgets[name]
                    self.icon_view.layout().addWidget(i_widget)
                    self.list_view.layout().addWidget(list_widget)
        self.installing_widget.setVisible(False)
        self.update_count_games_label()

    def _update_games(self):
        icon_layout = FlowLayout()
        list_layout = QVBoxLayout()

        icon_layout.addWidget(self.installing_widget)
        for igame in sorted(self.core.get_installed_list(), key=lambda x: x.title):
            i_widget, l_widget = self.widgets[igame.app_name]
            icon_layout.addWidget(i_widget)
            list_layout.addWidget(l_widget)

        for game in self.no_assets:
            i_widget, l_widget = self.widgets[game.app_name]
            icon_layout.addWidget(i_widget)
            list_layout.addWidget(l_widget)

        self.uninstalled_names = []
        installed_names = [i.app_name for i in self.core.get_installed_list()]
        # get Uninstalled games
        games, self.dlcs = self.core.get_game_and_dlc_list(update_assets=False)
        # add uninstalled games
        for game in sorted(games, key=lambda x: x.app_title):
            if game.app_name not in installed_names:
                self.uninstalled_names.append(game.app_name)
        for game in self.uninstalled_names:
            i_widget, list_widget = self.widgets[game.app_name]
            icon_layout.addWidget(i_widget)
            list_layout.addWidget(list_widget)

        QWidget().setLayout(self.icon_view.layout())
        QWidget().setLayout(self.list_view.layout())
        # self.icon_view.layout().deleteLater()
        # self.list_view.layout().deleteLater()

        self.icon_view.setLayout(icon_layout)
        self.list_view.setLayout(list_layout)

        self.icon_view.setParent(None)
        self.list_view.setParent(None)

        # insert widget in layout
        self.scroll_widget.layout().insertWidget(1,
                                                 self.icon_view if self.head_bar.view.isChecked() else self.list_view)

    def toggle_view(self):
        self.settings.setValue("icon_view", not self.head_bar.view.isChecked())

        if not self.head_bar.view.isChecked():
            self.scroll_widget.layout().replaceWidget(self.list_view, self.icon_view)
            self.list_view.setParent(None)
        else:
            self.scroll_widget.layout().replaceWidget(self.icon_view, self.list_view)
            self.icon_view.setParent(None)
