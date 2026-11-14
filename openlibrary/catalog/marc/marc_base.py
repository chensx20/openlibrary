import re

re_isbn = re.compile(r'([^ ()]+[\dX])(?: \((?:v\. (\d+)(?: : )?)?(.*)\))?')
# handle ISBN like: 1402563884c$26.95
re_isbn_and_price = re.compile(r'^([-\d]+X?)c\$[\d.]+$')


class MarcException(Exception):
    # Base MARC exception class
    pass


class BadMARC(MarcException):
    pass


class NoTitle(MarcException):
    pass


class MarcBase:
    def get_linkage(self, original: str, link: str):
        if not re.fullmatch(r'[0-9]{3}', original):
            return None
        match = re.fullmatch(r'880-([0-9]{2})(?:/\S+)?', link)
        if not match:
            return None
        return self.get_linked_field(original, match.group(1))

    def get_linked_field(self, original: str, occurrence: str = '[0-9]{2}'):
        target = re.compile(rf'{original}-{occurrence}(/\S+)?')
        for _, field in self.read_decoded_fields(['880']):
            if any(target.fullmatch(value) for value in field.get_subfield_values(['6'])):
                return field
        return None

    def read_isbn(self, f):
        found = []
        for k, v in f.get_subfields(['a', 'z']):
            m = re_isbn_and_price.match(v)
            if not m:
                m = re_isbn.match(v)
            if not m:
                continue
            found.append(m.group(1))
        return found

    def read_decoded_fields(self, want: list[str]):
        """Decode each parser's native field representation exactly once."""
        for tag, field in self.read_fields(want):
            yield tag, self.decode_field(field)

    def build_fields(self, want: list[str]) -> None:
        self.fields = {}
        want = set(want)
        for tag, line in self.read_decoded_fields(want):
            self.fields.setdefault(tag, []).append(line)

    def get_fields(self, tag: str) -> list:
        return list(self.fields.get(tag, []))
