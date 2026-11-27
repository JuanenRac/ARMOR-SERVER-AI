# ARMOR-SERVER-AI - tests/test_cut_answers.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.
"""Answers of the server cut in the middle or that are not HTTP."""
from __future__ import annotations

import _paths  # noqa: F401
import http.client
import io
import unittest
import urllib.error
from unittest import mock

from armor_server_ai import service


class _CutBody(io.BytesIO):
    def read(self, *args):  # noqa: ANN002, ANN201
        raise http.client.IncompleteRead(b"{", 100)


class CutAnswerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = service.HttpServer("http://127.0.0.1:1", "t")

    def test_a_cut_or_garbled_answer_is_unreachable(self) -> None:
        for broken in (http.client.IncompleteRead(b"{", 100), http.client.BadStatusLine("x")):
            with mock.patch.object(service._OPENER, "open", side_effect=broken):
                with self.assertRaises(service.ServerError) as stop:
                    self.server.context()
                self.assertIn("unreachable", str(stop.exception))

    def test_a_refusal_whose_body_is_cut_keeps_its_status(self) -> None:
        refusal = urllib.error.HTTPError("http://127.0.0.1:1", 403, "no", {}, _CutBody())
        with mock.patch.object(service._OPENER, "open", side_effect=refusal):
            with self.assertRaises(service.ServerError) as stop:
                self.server.context()
        self.assertIn("403", f"{stop.exception} {getattr(stop.exception, 'status', '')}")


if __name__ == "__main__":
    unittest.main()
