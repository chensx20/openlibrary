import json
from unittest.mock import patch

import web

from openlibrary.plugins.openlibrary import lists
from openlibrary.plugins.openlibrary.lists import ListRecord


def test_process_seeds():
    process_seeds = lists.lists_json().process_seeds

    def f(s):
        return process_seeds([s])[0]

    assert f("/books/OL1M") == {"key": "/books/OL1M"}
    assert f({"key": "/books/OL1M"}) == {"key": "/books/OL1M"}
    assert f("/subjects/love") == "subject:love"
    assert f("subject:love") == "subject:love"


class TestListRecord:
    def test_from_input_request_uses_body_instead_of_query(self):
        class InputHandler:
            def POST(self):
                record = ListRecord.from_input()
                return json.dumps(record.__dict__)

        app = web.application(('/input', 'InputHandler'), locals())
        response = app.request(
            '/input?name=query&seeds--0--key=/books/query',
            method='POST',
            data='name=body&seeds--0--key=/books/body',
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
        )

        assert json.loads(response.data) == {
            'key': None,
            'name': 'body',
            'description': '',
            'seeds': [{'key': '/books/body'}],
        }

    def test_from_input_body_overrides_conflicting_query_including_indexed_seeds(self):
        with (
            patch('web.ctx.env', {'CONTENT_TYPE': ''}, create=True),
            patch(
                'web.data',
                return_value=b'key=/lists/body&name=body&description=body+description&seeds--0--key=/books/body1&seeds--1--key=/books/body2',
            ),
            patch(
                'web.input',
                return_value={
                    'key': '/lists/query',
                    'name': 'query',
                    'description': 'query description',
                    'seeds': [{'key': '/books/query'}],
                },
            ) as mock_input,
        ):
            assert ListRecord.from_input() == ListRecord(
                key='/lists/body',
                name='body',
                description='body description',
                seeds=[{'key': '/books/body1'}, {'key': '/books/body2'}],
            )
            mock_input.assert_not_called()

    def test_from_input_body_preserves_repeated_and_comma_separated_seeds(self):
        with (
            patch('web.ctx.env', {'CONTENT_TYPE': ''}, create=True),
            patch(
                'web.data',
                return_value=b'seeds=OL1M&seeds=OL2M%2COL3M',
            ),
            patch('web.input') as mock_input,
        ):
            assert ListRecord.from_input().seeds == [
                {'key': '/books/OL1M'},
                {'key': '/books/OL2M'},
                {'key': '/books/OL3M'},
            ]
            mock_input.assert_not_called()

    def test_from_input_accepts_scalar_seed_from_json_body(self):
        with (
            patch('web.ctx.env', {'CONTENT_TYPE': 'application/json'}, create=True),
            patch('web.data', return_value=b'{"seeds":"OL1M"}'),
            patch('web.input') as mock_input,
        ):
            assert ListRecord.from_input().seeds == [{'key': '/books/OL1M'}]
            mock_input.assert_not_called()

    def test_from_input_uses_query_when_body_is_empty(self):
        with (
            patch('web.data', return_value=b''),
            patch('web.ctx.env', {'CONTENT_TYPE': ''}, create=True),
            patch(
                'web.input',
                return_value={
                    'name': 'query',
                    'seeds--0--key': '/books/query1',
                    'seeds--1--key': '/books/query2',
                },
            ),
        ):
            assert ListRecord.from_input() == ListRecord(
                key=None,
                name='query',
                description='',
                seeds=[{'key': '/books/query1'}, {'key': '/books/query2'}],
            )
