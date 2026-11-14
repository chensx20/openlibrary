import pytest
from lxml import etree
from pymarc import Field, Record, record_to_xml

from openlibrary.catalog.marc.marc_binary import MarcBinary
from openlibrary.catalog.marc.marc_xml import MarcXml
from openlibrary.catalog.marc.parse import read_author_person, read_publisher, read_title


@pytest.fixture(params=['xml', 'binary'])
def make_record(request):
    def build(fields):
        record = Record(force_utf8=True)
        for tag, subfields in fields:
            record.add_field(Field(tag=tag, indicators=[' ', ' '], subfields=subfields))
        if request.param == 'xml':
            rec = MarcXml(etree.fromstring(record_to_xml(record, namespace=True)))
        else:
            rec = MarcBinary(record.as_marc())
        rec.build_fields(['100', '245', '260', '264'])
        return rec

    return build


def test_linked_title_and_author(make_record):
    rec = make_record([
        ('100', ['6', '880-02', 'a', 'Roman Name']),
        ('245', ['6', '880-01/$1', 'a', 'Roman Title']),
        ('880', ['a', 'Unlinked']),
        ('880', ['6', '245-02', 'a', 'Wrong occurrence']),
        ('880', ['6', '100-01', 'a', 'Wrong tag']),
        ('880', ['6', '245-01/$1', 'a', 'Alternate Title']),
        ('880', ['6', '100-02/(3/r', 'a', 'Alternate Name']),
    ])
    assert read_title(rec) == {'title': 'Alternate Title', 'other_titles': ['Roman Title']}
    assert read_author_person(rec.get_fields('100')[0])['alternate_names'] == ['Alternate Name']


@pytest.mark.parametrize('link', ['', '880', '880-0', '880-010', '880-01extra', '245-01'])
def test_malformed_source_linkage(make_record, link):
    rec = make_record([('880', ['6', '245-01', 'a', 'Title'])])
    assert rec.get_linkage('245', link) is None


def test_linkage_skips_invalid_and_unmatched_fields(make_record):
    rec = make_record([
        ('880', ['a', 'No linkage']),
        ('880', ['6', '', 'a', 'Blank linkage']),
        ('880', ['6', '245-010', 'a', 'Prefix only']),
        ('880', ['6', '100-01', 'a', 'Wrong tag']),
        ('880', ['6', '245-02', 'a', 'Wrong occurrence']),
    ])
    assert rec.get_linkage('245', '880-01') is None
    assert read_publisher(rec) is None


def test_publisher_fallback(make_record):
    rec = make_record([
        ('880', ['a', 'Unlinked']),
        ('880', ['6', '', 'b', 'Blank']),
        ('880', ['6', '260-03/$1', 'a', 'Place', 'b', 'Publisher']),
    ])
    assert read_publisher(rec) == {'publishers': ['Publisher'], 'publish_places': ['Place']}
