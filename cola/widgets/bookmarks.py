"""Provides widgets related to bookmarks"""

from __future__ import division, absolute_import, unicode_literals

import os

from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL

from cola import cmds
from cola import core
from cola import git
from cola import gitcfg
from cola import hotkeys
from cola import icons
from cola import qtutils
from cola import utils
from cola.i18n import N_
from cola.models import prefs
from cola.settings import Settings
from cola.widgets import defs
from cola.widgets import standard


BOOKMARKS = 0
RECENT_REPOS = 1


class BookmarksWidget(QtGui.QWidget):

    def __init__(self, style=BOOKMARKS, parent=None):
        QtGui.QWidget.__init__(self, parent)

        self.style = style
        self.settings = Settings()
        self.tree = BookmarksTreeWidget(style, self.settings, parent=self)

        self.add_button = qtutils.create_action_button(
                tooltip=N_('Add'), icon=icons.add())

        self.delete_button = qtutils.create_action_button(tooltip=N_('Delete'),
                                                          icon=icons.remove())

        self.open_button = qtutils.create_action_button(tooltip=N_('Open'),
                                                        icon=icons.repo())

        self.button_group = utils.Group(self.delete_button, self.open_button)
        self.button_group.setEnabled(False)

        self.setFocusProxy(self.tree)
        if style == BOOKMARKS:
            self.setToolTip(N_('Favorite repositories'))
        elif style == RECENT_REPOS:
            self.setToolTip(N_('Recent repositories'))
            self.add_button.hide()

        self.button_layout = qtutils.hbox(defs.no_margin, defs.spacing,
                                          self.open_button, self.add_button,
                                          self.delete_button)

        self.main_layout = qtutils.vbox(defs.no_margin, defs.spacing, self.tree)
        self.setLayout(self.main_layout)

        self.corner_widget = QtGui.QWidget(self)
        self.corner_widget.setLayout(self.button_layout)
        titlebar = parent.titleBarWidget()
        titlebar.add_corner_widget(self.corner_widget)

        qtutils.connect_button(self.add_button, self.tree.add_bookmark)
        qtutils.connect_button(self.delete_button, self.tree.delete_bookmark)
        qtutils.connect_button(self.open_button, self.tree.open_repo)

        self.connect(self.tree, SIGNAL('itemSelectionChanged()'),
                     self.tree_item_selection_changed)

        QtCore.QTimer.singleShot(0, self.reload_bookmarks)

    def reload_bookmarks(self):
        # Called once after the GUI is initialized
        self.settings.load()
        self.tree.refresh()

    def tree_item_selection_changed(self):
        enabled = bool(self.tree.selected_item())
        self.button_group.setEnabled(enabled)


class BookmarksTreeWidget(standard.TreeWidget):

    def __init__(self, style, settings, parent=None):
        standard.TreeWidget.__init__(self, parent=parent)
        self.style = style
        self.settings = settings

        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setHeaderHidden(True)

        self.open_action = qtutils.add_action(self,
                N_('Open'), self.open_repo, hotkeys.OPEN, *hotkeys.ACCEPT)

        self.open_new_action = qtutils.add_action(self,
                N_('Open in New Window'), self.open_new_repo, hotkeys.NEW)

        self.set_default_repo_action = qtutils.add_action(self,
                N_('Set Default Repository'), self.set_default_repo)

        self.clear_default_repo_action = qtutils.add_action(self,
                N_('Clear Default Repository'), self.clear_default_repo)

        self.open_default_action = qtutils.add_action(self,
                cmds.OpenDefaultApp.name(), self.open_default,
                hotkeys.PRIMARY_ACTION)

        self.launch_editor_action = qtutils.add_action(self,
                cmds.Edit.name(), self.launch_editor, hotkeys.EDIT)

        self.launch_terminal_action = qtutils.add_action(self,
                cmds.LaunchTerminal.name(), self.launch_terminal,
                hotkeys.TERMINAL)

        self.copy_action = qtutils.add_action(self,
                N_('Copy'), self.copy, hotkeys.COPY)

        self.connect(self, SIGNAL('itemSelectionChanged()'),
                     self.item_selection_changed)

        self.connect(self, SIGNAL('itemDoubleClicked(QTreeWidgetItem*,int)'),
                     self.tree_double_clicked)

        self.action_group = utils.Group(self.open_action,
                                        self.open_new_action,
                                        self.copy_action,
                                        self.launch_editor_action,
                                        self.launch_terminal_action,
                                        self.open_default_action)
        self.action_group.setEnabled(False)
        self.set_default_repo_action.setEnabled(False)
        self.clear_default_repo_action.setEnabled(False)

    def refresh(self):
        settings = self.settings
        builder = BuildItem(self.style)

        # bookmarks
        if self.style == BOOKMARKS:
            items = [builder.get(path) for path in settings.bookmarks]

            if prefs.sort_bookmarks():
                items.sort()
        elif self.style == RECENT_REPOS:
            # recent items
            items = [builder.get(path) for path in settings.recent]
        else:
            items = []
        self.clear()
        self.addTopLevelItems(items)

    def contextMenuEvent(self, event):
        menu = QtGui.QMenu(self)
        menu.addAction(self.open_action)
        menu.addAction(self.open_new_action)
        menu.addAction(self.open_default_action)
        menu.addSeparator()
        menu.addAction(self.copy_action)
        menu.addAction(self.launch_editor_action)
        menu.addAction(self.launch_terminal_action)
        menu.addSeparator()
        item = self.selected_item()
        is_default = bool(item and item.is_default)
        if is_default:
            menu.addAction(self.clear_default_repo_action)
        else:
            menu.addAction(self.set_default_repo_action)
        menu.exec_(self.mapToGlobal(event.pos()))

    def apply_fn(self, fn, *args, **kwargs):
        item = self.selected_item()
        if item:
            fn(item, *args, **kwargs)

    def copy(self):
        self.apply_fn(lambda item: qtutils.set_clipboard(item.path))

    def open_default(self):
        self.apply_fn(lambda item: cmds.do(cmds.OpenDefaultApp, [item.path]))

    def set_default_repo(self):
        self.apply_fn(self.set_default_item)

    def set_default_item(self, item):
        cmds.do(cmds.SetDefaultRepo, item.path)
        self.refresh()

    def clear_default_repo(self):
        self.apply_fn(self.clear_default_item)

    def clear_default_item(self, item):
        cmds.do(cmds.SetDefaultRepo, None)
        self.refresh()

    def open_repo(self):
        self.apply_fn(lambda item: cmds.do(cmds.OpenRepo, item.path))

    def open_new_repo(self):
        self.apply_fn(lambda item: cmds.do(cmds.OpenNewRepo, item.path))

    def launch_editor(self):
        self.apply_fn(lambda item: cmds.do(cmds.Edit, [item.path]))

    def launch_terminal(self):
        self.apply_fn(lambda item: cmds.do(cmds.LaunchTerminal, item.path))

    def item_selection_changed(self):
        item = self.selected_item()
        enabled = bool(item)
        self.action_group.setEnabled(enabled)

        is_default = bool(item and item.is_default)
        self.set_default_repo_action.setEnabled(not is_default)
        self.clear_default_repo_action.setEnabled(is_default)

    def tree_double_clicked(self, item, column):
        cmds.do(cmds.OpenRepo, item.path)

    def add_bookmark(self):
        path, ok = qtutils.prompt(N_('Path to git repository'),
                                  title=N_('Enter Git Repository'),
                                  text=core.getcwd())
        if not ok:
            return
        normpath = utils.expandpath(path)
        if git.is_git_worktree(normpath):
            self.settings.add_bookmark(normpath)
            self.settings.save()
            self.refresh()
        else:
            qtutils.critical(N_('Error'),
                             N_('%s is not a Git repository.') % path)

    def delete_bookmark(self):
        """Removes a bookmark from the bookmarks list"""
        item = self.selected_item()
        if not item:
            return
        if self.style == BOOKMARKS:
            cmd = cmds.RemoveBookmark
        elif self.style == RECENT_REPOS:
            cmd = cmds.RemoveRecent
        else:
            return
        ok, status, out, err = cmds.do(cmd, self.settings, item.path,
                                       icon=icons.discard())
        if ok:
            self.refresh()


class BuildItem(object):

    def __init__(self, style):
        self.star_icon = icons.star()
        self.folder_icon = icons.folder()
        self.default_repo = gitcfg.current().get('cola.defaultrepo')

    def get(self, path):
        is_default = self.default_repo == path
        if is_default:
            icon = self.star_icon
        else:
            icon = self.folder_icon
        return BookmarksTreeWidgetItem(path, icon, is_default)


class BookmarksTreeWidgetItem(QtGui.QTreeWidgetItem):

    def __init__(self, path, icon, is_default):
        QtGui.QTreeWidgetItem.__init__(self)
        self.path = path
        self.is_default = is_default

        self.setIcon(0, icon)
        normpath = os.path.normpath(path)
        basename = os.path.basename(normpath)
        self.setText(0, basename)
        self.setToolTip(0, path)
