#!/usr/bin/python3
# Copyright 2013-2020 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

import unittest
from guibot.config import GlobalConfig, TemporaryConfig


class ConfigTest(unittest.TestCase):

    def test_retake_settings(self) -> None:
        """Retaking is opt-in and its settings support temporary configuration."""
        self.assertFalse(GlobalConfig.retake_images)
        self.assertEqual(GlobalConfig.retake_similarity, 0.69)
        self.assertEqual(GlobalConfig.retake_similarity_step, 0.033)
        with TemporaryConfig() as cfg:
            cfg.retake_images = True
            cfg.retake_similarity = 0.6
            cfg.retake_similarity_step = 0.05
            self.assertTrue(GlobalConfig.retake_images)
            self.assertEqual(GlobalConfig.retake_similarity, 0.6)
            self.assertEqual(GlobalConfig.retake_similarity_step, 0.05)
            for value in (0, 1, 'yes'):
                with self.subTest(flag=value):
                    with self.assertRaises(ValueError):
                        cfg.retake_images = value
            for value in (-0.1, 1.1, float('nan'), float('inf')):
                with self.subTest(similarity=value):
                    with self.assertRaises(ValueError):
                        cfg.retake_similarity = value
            for value in (0, -0.1, 1.1, 1e-100, float('nan'), float('inf')):
                with self.subTest(step=value):
                    with self.assertRaises(ValueError):
                        cfg.retake_similarity_step = value
        self.assertFalse(GlobalConfig.retake_images)
        self.assertEqual(GlobalConfig.retake_similarity, 0.69)
        self.assertEqual(GlobalConfig.retake_similarity_step, 0.033)

    def test_temporary_config(self) -> None:
        """Check that using a temporary config has a temporary effect."""
        original_value = GlobalConfig.delay_before_drop
        new_value = original_value * 10

        with TemporaryConfig() as cfg:
            cfg.delay_before_drop = new_value
            self.assertEqual(cfg.delay_before_drop, new_value)
            # changing TemporaryConfig inside the context
            # should affect GlobalConfig
            self.assertEqual(GlobalConfig.delay_before_drop, new_value)

        # value should be restored once we exit the context
        self.assertEqual(GlobalConfig.delay_before_drop, original_value)

if __name__ == '__main__':
    unittest.main()
