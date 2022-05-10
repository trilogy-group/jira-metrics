# Copyright (c) 2021 DevFactory. All rights reserved.
#
# This library is for internal use only. It is neither Open Source nor Free
# Software, and thus should not be distributed outside of DevFactory without
# explicit written permission from DevFactory management.
#
# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied.

import datetime
import json
from datetime import timedelta, datetime

import iso8601

since = (datetime.today() - timedelta(days=30)).astimezone()

def collect_versions(all, issue):
    versions = list(collect_versions_recursive(all, issue))
    versions.sort(key=lambda i: int(i.split('-')[1]))
    return versions


def short_summary(issue):
    k = issue['key'].ljust(12)[:12]
    d = issue['Summary'].ljust(60)[:60]
    s = issue.get('Resolved', 'N/A').ljust(10)[:10]
    a = issue.get('Implementer', 'N/A').ljust(20)[:20]
    q = issue.get('Internal Reviewer', 'N/A').ljust(20)[:20]
    return f"{k} : {s} : {d} : {a} : {q} : {issue['Status']} : {issue.get('Work Data Structure Link', 'N/A')}"


def collect_versions_recursive(all, issue):
    versions = set()
    versions.add(issue['key'])
    for h in issue.get('links', list()):
        if h['type'] == 'is caused by':
            if h['key'] in all:
                versions.update(collect_versions_recursive(all, all[h['key']]))
    return versions


def process():
    result = dict()
    types = set()

    since = (datetime.today() - timedelta(days=60)).astimezone()
    with open('all.json') as file:
        issues = json.load(file)['issues']
        versions = dict()
        for issue_id in issues:
            issue = issues[issue_id]
            if issue['Status'] in ('Delivered', 'Passed External QC') and \
                    issue['Issue Type'] != 'ALP Automated Deep Dive Work Unit' and \
                    'Resolved' in issue and iso8601.parse_date(issue['Resolved']) >= since:
                versions[issue_id] = collect_versions(issues, issue)
                types.add(issue['Issue Type'])

        print(f"{len(versions)} tickets were completed.")

        for type in types:
            print()
            print(f" == {type} ==")
            print()
            result[type] = versions
            for issue in versions:
                if issues[issue]['Issue Type'] == type:
                    print(f" - {issue} has {len(versions[issue])} version(s):")
                    for v in versions[issue]:
                        print(f'   + {short_summary(issues[v])}')
                    print()

    return issues, result


# Different JIRA fields contain emails, AD usernames, full names, etc.
# The easiest is just to hardcode the mapping here.
def map_qcer(qcer):
    m = {
        'yury.prokashev@devfactory.com': 'Yury Prokashev',
        'akshat.verma': 'Akshat Verma',
        'akshat.verma@devfactory.com': 'Akshat Verma',
        'manimaran.selvan@devfactory.com': 'Manimaran Selvan',
        'john.johansen@devfactory.com': 'John Johansen',
        'victor.hellberg@devfactory.com': 'Victor Hellberg',
        'aman.jain@codenation.co.in': 'Aman Jain',
        'david.carley@devfactory.com': 'David Carley',
        'steve.brain@devfactory.com': 'Steve Brain',
        'luis.benitez.ruiz@devfactory.com': 'Luis Benitez Ruiz',
        'david.hessing@devfactory.com': 'David Hessing',
        'nishit.patira@devfactory.com': 'Nishit Patira',
        'zeb.hardy': 'Zeb Hardy',
        'amer.farroukh@devfactory.com': 'Amer Farroukh',
        'mahesh.mogal@devfactory.com': 'Mahesh Mogal',
    }
    return m.get(qcer, qcer)


def analyze():
    issues, result = process()
    transitions = dict()
    transition_types = set()
    by_person = dict()
    by_type = dict()

    since = (datetime.today() - timedelta(days=90)).astimezone()
    for i in issues:
        issue = issues[i]
        if iso8601.parse_date(issue['Created']) >= since:
            if 'PRODUCT' in i and (issue['Issue Type'] == 'CC - AWS Cost Anomaly Deep Dive'):
                type = issue['Issue Type']
                if type not in by_type:
                    by_type[type] = 0
                by_type[type] += 1

                for h in issue['history']:
                    f = h['from']
                    t = h['to']
                    if f in ('Internal QC', 'External QC'):
                        transition = f"{f} -> {t}"
                        transition_types.add(transition)

                        qcer = None
                        if f == 'Internal QC':
                            qcer = issue.get("Internal Reviewer", None)
                        elif f == 'External QC':
                            qcer = issue.get("External QCer", None)
                        if qcer is None:
                            qcer = h.get('who', None)

                        if qcer is None or qcer == 'spec.automation@devfactory.com':
                            print(f'WARNING: No QCer for {i} / {transition}')
                        else:
                            qcer = map_qcer(qcer)
                            if qcer not in by_person:
                                by_person[qcer] = {
                                    'failed': 0,
                                    'passed': 0
                                }
                            if transition in ('Internal QC -> Failed Internal QC', 'External QC -> Failed External QC'):
                                by_person[qcer]['failed'] += 1
                            elif transition in ('External QC -> Delivered', 'External QC -> Passed External QC', 'Internal QC -> Delivered'):
                                by_person[qcer]['passed'] += 1

                            if qcer not in transitions:
                                transitions[qcer] = dict()
                            if transition not in transitions[qcer]:
                                transitions[qcer][transition] = list()
                            transitions[qcer][transition].append(i)

    for qcer in transitions:
        print(f"{qcer}:")
        for t in transitions[qcer]:
            print(f" - {t}: {', '.join(transitions[qcer][t])}")

    print()
    print('Transition types:')
    print('\n'.join(transition_types))
    print()

    lines = list()
    for person in by_person:
        failed = by_person[person]['failed']
        passed = by_person[person]['passed']
        if passed == 0:
            m = f' - {person} - All {failed} failed'
            lines.append((1000000, m))
        else:
            m = f' - {person} - {round(100 * failed / passed)}:100, total {failed + passed}'
            lines.append((round(100 * failed / passed), m))

    print(f"Person - failed:passed, total:")
    lines.sort(key=lambda l: l[0])
    for l in lines:
        print(l[1])

    by_type_list = list()
    for t in by_type:
        if by_type[t] > 10:
            by_type_list.append((t, by_type[t]))
    by_type_list.sort(key=lambda t: t[1])
    for t in by_type_list:
        print(f"{t[0]}: {t[1]}")


if __name__ == '__main__':
    analyze()