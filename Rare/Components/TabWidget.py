from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QTabWidget, QTabBar, QWidget, QToolButton, QWidgetAction, QMenu
from legendary.core import LegendaryCore

from Rare import style_path
from Rare.Components.Tabs.Account.AccountWidget import MiniWidget
from Rare.Components.Tabs.Downloads.DownloadTab import DownloadTab
from Rare.Components.Tabs.Games.GamesTab import GameTab
from Rare.Components.Tabs.Settings.SettingsTab import SettingsTab


class TabWidget(QTabWidget):
    def __init__(self, core: LegendaryCore):
        super(TabWidget, self).__init__()
        disabled_tab = 2
        self.setTabBar(TabBar(disabled_tab))
        self.settings = SettingsTab(core)
        self.game_list = GameTab(core)
        updates = self.game_list.default_widget.game_list.updates
        self.addTab(self.game_list, self.tr("Games"))
        self.downloadTab = DownloadTab(core, updates)
        self.addTab(self.downloadTab, "Downloads")
        self.downloadTab.finished.connect(self.game_list.default_widget.game_list.update_list)
        self.game_list.default_widget.game_list.install_game.connect(lambda x: self.downloadTab.install_game(x))

        # Commented, because it is not finished
        # self.cloud_saves = SyncSaves(core)
        # self.addTab(self.cloud_saves, "Cloud Saves")

        # Space Tab
        self.addTab(QWidget(), "")
        self.setTabEnabled(disabled_tab, False)

        self.account = QWidget()
        self.addTab(self.account, "")
        self.setTabEnabled(disabled_tab + 1, False)
        # self.settings = SettingsTab(core)

        self.addTab(self.settings, QIcon(style_path + "/Icons/settings.png"), None)
        self.setIconSize(QSize(25, 25))
        self.tabBar().setTabButton(3, self.tabBar().RightSide, TabButtonWidget(core))

    def resizeEvent(self, event):
        self.tabBar().setMinimumWidth(self.width())
        super(TabWidget, self).resizeEvent(event)


class TabBar(QTabBar):
    def __init__(self, expanded):
        super(TabBar, self).__init__()
        self._expanded = expanded
        self.setObjectName("main_tab_bar")
        self.setFont(QFont("Arial", 13))
        # self.setContentsMargins(0,10,0,10)

    def tabSizeHint(self, index):
        size = super(TabBar, self).tabSizeHint(index)
        if index == self._expanded:
            offset = self.width()
            for index in range(self.count()):
                offset -= super(TabBar, self).tabSizeHint(index).width()
            size.setWidth(max(size.width(), size.width() + offset))
        return size


class TabButtonWidget(QToolButton):
    def __init__(self, core):
        super(TabButtonWidget, self).__init__()
        self.setText("Icon")
        self.setPopupMode(QToolButton.InstantPopup)

        self.setIcon(QIcon(style_path + "/Icons/account.png"))
        self.setToolTip("Account")
        self.setIconSize(QSize(25, 25))
        self.setMenu(QMenu())
        action = QWidgetAction(self)
        action.setDefaultWidget(MiniWidget(core))
        self.menu().addAction(action)
