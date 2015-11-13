#!/usr/bin/env python
"""Tests basic git operations: commit, log, config"""
from __future__ import unicode_literals

import unittest

from cola import core
from cola.models.main import MainModel

from test import helper


class ColaBasicGitTestCase(helper.GitRepositoryTestCase):

    def setUp(self):
        helper.GitRepositoryTestCase.setUp(self, commit=False)

    def test_git_commit(self):
        """Test running 'git commit' via cola.git"""
        self.write_file('A', 'A')
        self.write_file('B', 'B')
        self.git('add', 'A', 'B')

        model = MainModel(cwd=core.getcwd())
        model.git.commit(m='commit test')
        log = self.git('log', '--pretty=oneline')

        self.assertEqual(len(log.splitlines()), 1)

    def test_git_config(self):
        """Test cola.git.config()"""
        self.git('config', 'section.key', 'value')
        model = MainModel(cwd=core.getcwd())
        value = model.git.config('section.key', get=True)

        self.assertEqual(value, (0, 'value', ''))

        #  Test config_set
        model.config_set('section.bool', True)
        value = model.git.config('section.bool', get=True)

        self.assertEqual(value, (0, 'true', ''))
        model.config_set('section.bool', False)

        # Test config_dict
        config_dict = model.config_dict(local=True)

        self.assertEqual(config_dict['section_key'], 'value')
        self.assertEqual(config_dict['section_bool'], False)

        # Test config_dict --global
        global_dict = model.config_dict(local=False)

        self.assertEqual(type(global_dict), dict)


if __name__ == '__main__':
    unittest.main()
