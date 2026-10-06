"""Synthetic identity, blindness and annotation integrity checks."""
import copy
import unittest

from discovery.atlas_label_audit import primary_records, coverage, review_cards, template, validate_annotations


def definition(category='debt_issuance'):
    return {'tertiary_category': category, 'primary_category': 'capital', 'secondary_category': 'debt', 'description': 'Synthetic definition'}


def event(accession='a', text='The offering closed.', category='debt_issuance'):
    return {'cik': '001', 'accession_number': accession, 'filing_date': '2023-01-03',
            'primary_category': 'capital', 'secondary_category': 'debt', 'tertiary_category': category,
            'supporting_text': text, 'tickers': ['ONE', 'TWO'], 'future_return': 123}


class LabelAuditTests(unittest.TestCase):
    def test_duplicate_appearances_and_excerpts_preserve_provenance(self):
        records = primary_records([definition()], [('x', '001', [event(), event()]), ('y', '001', [event(text='Other exact excerpt.')])])
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0]['excerpts']), 2)
        self.assertEqual(len(records[0]['provenance']), 3)

    def test_same_date_filings_and_labels_do_not_collapse(self):
        records = primary_records([definition(), definition('other')], [('x', '001', [event(), event('b'), event(category='other')])])
        self.assertEqual(len(records), 3)
        self.assertEqual(len({r['accession'] for r in records}), 2)

    def test_missing_text_retained_and_empty_types_visible(self):
        records = primary_records([definition()], [('x', '001', [event(text=None)])])
        counts = coverage([definition(), definition('empty')], records)
        self.assertEqual(counts[0]['missing_text_filings'], 1)
        self.assertEqual(counts[1]['filings'], 0)

    def test_unknown_labels_conflicting_metadata_and_future_dates_fail(self):
        for change in [{'tertiary_category': 'absent'}, {'primary_category': 'wrong'}, {'filing_date': '2026-01-01'}, {'cik': '002'}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                primary_records([definition()], [('x', '001', [{**event(), **change}])])
        with self.assertRaises(ValueError):
            primary_records([definition()], [('x', '001', [event(), {**event(), 'filing_date': '2023-01-04'}])])

    def test_blind_cards_and_selection_ignore_market_values(self):
        events = [event(str(i)) for i in range(12)]
        records = primary_records([definition()], [('x', '001', events)])
        cards, key, sample = review_cards([definition()], records)
        self.assertEqual(len(sample), 5)
        self.assertEqual(set(cards[0]), {'card_id', 'category', 'definition', 'excerpts'})
        self.assertNotIn('future_return', str(cards))
        changed = [{**row, 'future_return': -999, 'tickers': ['DIFFERENT']} for row in events]
        other = primary_records([definition()], [('x', '001', changed)])
        self.assertEqual(review_cards([definition()], other)[2], sample)
        self.assertEqual(len(key), len(cards))

    def test_exact_evidence_and_provenance_required(self):
        records = primary_records([definition()], [('x', '001', [event()])])
        cards = review_cards([definition()], records)[0]
        annotation = template(cards[0])
        annotation.update(review_status='reviewed', reviewer='synthetic-reviewer', reviewed_at='2026-10-04T00:00:00Z', rationale='The excerpt states completion.')
        annotation['fields']['transaction_stage'] = {'value': 'completed', 'evidence': ['The offering closed.']}
        self.assertEqual(validate_annotations(cards, [annotation])[0], annotation)
        for modification in [{'reviewer': ''}, {'review_status': 'unreviewed'}, {'future_return': 4}]:
            with self.subTest(modification=modification), self.assertRaises(ValueError):
                validate_annotations(cards, [{**annotation, **modification}])
        incorrect = copy.deepcopy(annotation)
        incorrect['fields']['transaction_stage']['evidence'] = ['Funds received.']
        with self.assertRaises(ValueError): validate_annotations(cards, [incorrect])

    def test_missing_annotations_leave_all_primary_cards_unknown(self):
        records = primary_records([definition()], [('x', '001', [event(), event('b', None)])])
        cards = review_cards([definition()], records)[0]
        result = validate_annotations(cards, [])
        self.assertEqual(len(result), 2)
        self.assertEqual({a['review_status'] for a in result}, {'unreviewed', 'missing_text'})
        self.assertTrue(all(a['fields']['transaction_stage']['value'] == 'unknown' for a in result))

    def test_unknown_duplicate_and_illegal_values_fail(self):
        records = primary_records([definition()], [('x', '001', [event()])])
        cards = review_cards([definition()], records)[0]
        annotation = template(cards[0])
        for entries in [[annotation, annotation], [{**annotation, 'card_id': 'bad'}]]:
            with self.assertRaises(ValueError): validate_annotations(cards, entries)
        annotation['fields']['cash_receipt']['value'] = 'no_receipt'
        with self.assertRaises(ValueError): validate_annotations(cards, [annotation])


if __name__ == '__main__': unittest.main()
