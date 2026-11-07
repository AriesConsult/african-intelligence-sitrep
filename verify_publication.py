#!/usr/bin/env python3
"""Independent publication gate for BDBV SitRep-derived statistics and narratives.

Check public output against archived, reconciled table snapshots. An incomplete
historical archive may be transparently PARTIAL; inconsistent published claims
must fail the CI job and are never silently accepted.
"""
from __future__ import annotations
import argparse
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
METRICS = {
    'alerts_received': ('table_3', 'alerts_received', 'count'),
    'alerts_validated': ('table_3', 'suspected_alerts', 'count'),
    'contacts_to_follow': ('table_4', 'contacts_to_follow', 'count'),
    'contacts_seen': ('table_4', 'contacts_seen', 'count'),
    'contact_follow_up_rate': ('table_4', 'contact_follow_up_rate', 'percent'),
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify(published: Path, registry_path: Path, *, check_narratives: bool = True):
    failures = []
    totals = Counter()
    try:
        reg = read_json(registry_path)
        index = read_json(published / 'table_index.json')
        feed = read_json(published / 'feed.json')
        audit = read_json(published / 'ingestion_audit.json')
    except (OSError, ValueError) as e:
        return {'pass': False, 'errors': [{'reason': 'required_index_unreadable', 'detail': str(e)[:150]}]}
    if not audit.get('source_consistency', {}).get('pass'):
        failures.append({'reason': 'source_integrity_audit_failed'})
    if audit.get('original_pdf_archives', {}).get('status') in ('INDEX_UNREADABLE', 'INVENTORY_INVALID'):
        failures.append({'reason':'original_pdf_release_inventory_invalid'})
    index_by_key = {}
    for report in index.get('reports', []):
        key = (report.get('report_number'), report.get('sha256'))
        if key in index_by_key:
            failures.append({'reason': 'duplicate_table_index_identity', 'key': str(key)})
        index_by_key[key] = report
    cache = {}
    def snapshot(report):
        rel = report.get('snapshot_path')
        if not rel or not re.fullmatch(r'tables/\d{3}_[a-f0-9]{12}\.json', rel):
            raise ValueError('missing_or_unsafe_snapshot_path')
        if rel not in cache:
            cache[rel] = read_json(published / rel)
        return cache[rel]
    seen = set()
    dates_by_metric = {}
    for obs in feed.get('observations', []):
        totals['observations_checked'] += 1
        identity = (obs.get('date'), obs.get('metric_id'), obs.get('scope'))
        if identity in seen:
            failures.append({'reason': 'duplicate_published_observation', 'identity': identity})
        seen.add(identity)
        metric = obs.get('metric_id')
        if obs.get('evidence_status') == 'human_verified':
            if not obs.get('reviewed_by'):
                failures.append({'reason': 'unnamed_human_review', 'identity': identity})
            totals['human_verified'] += 1
            continue
        if metric not in METRICS or obs.get('evidence_status') != 'machine_validated':
            failures.append({'reason': 'unapproved_machine_metric_or_status', 'identity': identity})
            continue
        no, sha = obs.get('report_number'), obs.get('source_sha256')
        if not isinstance(no, int) or not re.fullmatch(r'[0-9a-f]{64}', sha or ''):
            failures.append({'reason': 'invalid_observation_source_identity', 'identity': identity})
            continue
        registry_key = f'{no:03d}:{sha}'
        indexed = index_by_key.get((no, sha))
        if registry_key not in reg.get('documents', {}) or indexed is None:
            failures.append({'reason': 'observation_source_not_registered_and_indexed', 'identity': identity})
            continue
        try:
            snap = snapshot(indexed)
            tab, field, unit = METRICS[metric]
            t = snap['tables'][tab]
            national = t['national']
            expected = national[field]
            if t.get('status') != 'MACHINE_VALIDATED' or national.get('scope') != 'DRC':
                raise ValueError('national_table_not_machine_validated')
            if expected is None or not isinstance(expected, (int, float)):
                raise ValueError('validated_field_missing')
            val = obs.get('value')
            if not isinstance(val, (int, float)) or not math.isfinite(val) or abs(val - expected) > 1e-6:
                raise ValueError('published_value_differs_from_reconciled_table')
            if obs.get('unit') != unit or obs.get('scope') != 'DRC':
                raise ValueError('wrong_published_unit_or_scope')
            if (obs.get('date') != snap.get('date') or obs.get('source_url') != snap.get('source_url')
                    or sha != snap.get('source_sha256')):
                raise ValueError('observation_source_date_url_or_hash_mismatch')
            if (obs.get('page') != national.get('source', {}).get('page')
                    or obs.get('table_id') != national.get('source', {}).get('table_id')):
                raise ValueError('published_page_or_table_mismatch')
            totals['machine_observations_reconciled'] += 1
            if metric not in dates_by_metric or obs['date'] > dates_by_metric[metric]:
                dates_by_metric[metric] = obs['date']
        except (ValueError, TypeError, KeyError, OSError) as e:
            failures.append({'reason': 'published_observation_reconciliation_failure',
                             'identity': identity, 'detail': str(e)[:150]})
    if feed.get('observations_count') != len(feed.get('observations', [])):
        failures.append({'reason': 'feed_observations_count_mismatch'})
    if feed.get('latest_by_metric', {}) != dates_by_metric:
        failures.append({'reason': 'feed_latest_dates_mismatch'})
    if check_narratives:
        try:
            nidx = read_json(published / 'narrative_index.json')
            for entry in nidx.get('reports', []):
                totals['narrative_reports_checked'] += 1
                rel = entry.get('snapshot_path', '')
                if not re.fullmatch(r'narrative_candidates/\d{3}_[a-f0-9]{12}\.json', rel):
                    raise ValueError('unsafe_narrative_snapshot_path')
                snap = read_json(published / rel)
                if (snap.get('report_number') != entry.get('report_number')
                        or snap.get('source_sha256') != entry.get('source_sha256')
                        or snap.get('candidates_count') != entry.get('candidate_count')):
                    raise ValueError(f'narrative_identity_or_count_mismatch_{entry.get("report_number")}')
                keys = [x.get('candidate_id') for x in snap.get('candidates', [])]
                if len(keys) != len(set(keys)) or len(keys) != snap.get('candidates_count'):
                    raise ValueError('duplicate_or_incomplete_narrative_blocks')
                if any(x.get('review_status') != 'REVIEW_REQUIRED' for x in snap.get('candidates', [])):
                    raise ValueError('narrative_published_without_review')
                totals['narrative_candidate_blocks_checked'] += len(keys)
        except (OSError, ValueError, TypeError) as e:
            failures.append({'reason': 'narrative_snapshot_validation_failed', 'detail': str(e)[:160]})
    return {
        'schema_version': 'bdbv-publication-gate-v1',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'pass': not failures,
        'numerical_archive_completeness': audit.get('assessment', 'UNKNOWN'),
        'narrative_coverage': audit.get('narratives', {}).get('status', 'UNKNOWN'),
        'original_pdf_archive_coverage': audit.get('original_pdf_archives', {}).get('status', 'UNKNOWN'),
        'counters': dict(totals),
        'errors': failures,
        'interpretation': 'PASS certifies published-record consistency, not historical completeness or independent source verification.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--published', type=Path, default=ROOT / 'published')
    parser.add_argument('--registry', type=Path, default=ROOT / 'state' / 'registry.json')
    args = parser.parse_args()
    result = verify(args.published, args.registry)
    (args.published / 'publication_qa.json').write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'pass': result['pass'], 'counts': result.get('counters', {}),
                      'errors': result['errors'][:10]}, ensure_ascii=False))
    raise SystemExit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
