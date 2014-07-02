# -*- coding: utf-8 -*-

import pep8
import unittest

class TestCodeFormat(unittest.TestCase):

    def test_pep8(self):
        """
        pep8style = pep8.StyleGuide()
        result = pep8style.check_files(['libvirtd.py'])
        self.assertEqual(result.total_errors, 0,
                         "Found code style errors (and warnings).")
        """
        fchecker = pep8.Checker('libvirtd.py', show_source=True)
        file_errors = fchecker.check_all()
        self.assertEqual(file_errors, 0,
                         "Found code style errors (and warnings).")
