# ALP Jira metrics

A simple script to help understanding why some of the Jira tickets pass QC on the first try, while the others take multiple iterations.

**Below this line is the original README of [jiractor](https://github.com/vilia-fr/jiractor) tool.**

# Jiractor is a JIRA extractor

A simple command-line tool to extract all JIRA issues for a given project in 
simple human-readable JSON with history and links.

## Installation

The tool requires a reasonably recent Python 3 installation.

```shell
pip install -r requirements.txt
```

## Usage

Specify your JIRA credentials in the `.env` file. Then execute:

```shell
python jira_extract.py <PROJECT>
```

The tool will generate a bunch of `ISSUE-123.json` files in `issues` folder. You can then use
`merge_json.py` to merge them into one large JSON file, if you want:

```shell
python merge_json.py <output.json>
```

An example script, which prints out all issues, which were reopened in the last 30 days:

```shell
python example.py
```

## Known bugs and limitations

- The tool always exports the entire project. It will be much more efficient to do it incrementally,
extracting the last modification date from the file timestamps and adjusting the JQL accordingly.

Copyright (C) 2021 Constantine Kulak (ck@vilia.fr)
