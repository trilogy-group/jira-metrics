# Copyright (C) 2021 Constantine Kulak (ck@vilia.fr)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import sys
from datetime import datetime
from os import getenv

from atlassian import Jira
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
JIRA = Jira(
    url=getenv("URL"),
    username=getenv("USER_NAME"),
    password=getenv("PASSWORD"),
    timeout=int(getenv("TIMEOUT"))
)
custom_fields = dict()
fields_to_delete = set(getenv("FIELDS_TO_DELETE").split('|'))


def init_fields():
    for f in JIRA.get_all_fields():
        custom_fields[f['id']] = f['name']


def get_history(issue_key):
    history = list()
    try:
        for histories in JIRA.get_issue_changelog(issue_key)['histories']:
            for item in histories['items']:
                history.append({
                    'who': get_user_name(histories.get('author', dict())),
                    'when': histories.get('created', 'N/A'),
                    'what': item.get('field', 'N/A'),
                    'from': item.get('fromString', 'N/A'),
                    'to': item.get('toString', 'N/A'),
                })
    except:
        print(f"WARNING: Could not get history for {issue_key}")
    return history


def get_user_name(a):
    return a.get('name', a.get('emailAddress', a.get('displayName', a.get('accountId', 'N/A'))))


def simplify_issue(issue):
    fields = dict()
    for f in issue['fields']:
        value = issue['fields'][f]
        if value:
            if isinstance(value, dict):
                if 'self' in value and 'value' in value and 'id' in value:
                    value = value['value']
                elif 'id' in value and 'name' in value:
                    value = value['name']
                elif 'emailAddress' in value and 'displayName' in value:
                    value = value['displayName']
                elif 'accountId' in value and 'displayName' in value:
                    value = value['displayName']
                elif 'emailAddress' in value and 'name' in value:
                    value = value['name']
                elif 'emailAddress' in value and 'avatarUrls' in value:
                    value = value['emailAddress']
                elif 'watchCount' in value and 'isWatching' in value:
                    value = value['watchCount']
                elif 'votes' in value and 'hasVoted' in value:
                    value = value['votes']
                elif 'comments' in value and 'total' in value:
                    value = value['comments']
                    for comment in value:
                        if 'author' in comment:
                            comment['author'] = get_user_name(comment['author'])
                        if 'updateAuthor' in comment:
                            comment['updateAuthor'] = get_user_name(comment['updateAuthor'])
            fields[custom_fields.get(f, f)] = value

    links = list()
    for link in issue['fields'].get('issuelinks', []):
        if 'inwardIssue' in link:
            key = link['inwardIssue']['key']
            link_type = link['type']['inward']
            link_direction = 'inward'
        if 'outwardIssue' in link:
            key = link['outwardIssue']['key']
            link_type = link['type']['outward']
            link_direction = 'outward'
        links.append({
            'type': link_type,
            'key': key,
            'direction': link_direction
        })

    for f in fields_to_delete:
        if f in fields:
            del fields[f]

    return {**{'links': links, 'key': issue['key']}, **fields}


def get_all_issues(project):
    issues = list()
    start_at = 0
    max_results = 100000
    res = JIRA.jql(f'project = {project}', start=start_at, limit=1)
    total = res['total']
    with tqdm(total=total) as pbar:
        while start_at < total:
            res = JIRA.jql(f'project = {project}', start=start_at, limit=max_results)
            max_results = res['maxResults']
            start_at = res['startAt'] + max_results
            total = res['total']
            issues += res['issues']
            pbar.update(len(res['issues']))
    return issues


def get_issues(project):
    res = get_all_issues(project)
    print()
    print(f'Queried {len(res)} issues')
    i = 0
    with tqdm(total=len(res)) as pbar:
        for issue in res:
            i += 1
            key = issue['key']

            simple = simplify_issue(issue)
            if 'Sub-Tasks' in simple:
                simple_subtasks = list()
                for subtask in simple['Sub-Tasks']:
                    simple_subtasks.append(simplify_issue(subtask))
                simple['Sub-Tasks'] = simple_subtasks

            history = get_history(key)
            simple['history'] = history
            all_issues[key] = simple
            dump_one(f'issues/{key}.json', simple)
            pbar.update(1)

    print(f'Processed {len(res)} issues')


def dump_one(filename, issue):
    with open(filename, 'w') as outfile:
        json.dump(issue, outfile, indent=4)


#####################################################################
######################### The main sequence #########################
#####################################################################

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python %s <PROJECT>' % sys.argv[0])
        exit(1)

    project = sys.argv[1]

    start_time = datetime.now()
    print(f'JIRA extract starts at {start_time}')

    print('Initializing field mapping...')
    init_fields()
    print(f'Done: {len(custom_fields)} fields')

    all_issues = dict()
    get_issues(project)
    print(f'Downloaded {len(all_issues)} issues')

    end_time = datetime.now()
    print(f'Finished at {end_time}, ran for {end_time - start_time}')
