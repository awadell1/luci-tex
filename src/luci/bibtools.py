import http.client as httplib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

import bibtexparser
import typer
from bibtexparser.bwriter import BibTexWriter
from tqdm import tqdm
from unidecode import unidecode

DOI_REGEX = re.compile(r'doi\.org/([^"^<^>]+)')


def normalize(string):
    string = re.sub(r'[{}\\\'"^]', "", string)
    string = re.sub(r"\$.*?\$", "", string)
    return unidecode(string)


def get_authors(entry) -> list[str] | None:
    def get_last_name(authors):
        for author in authors:
            author = author.strip(" ")
            if "," in author:
                yield author.split(",")[0]
            elif " " in author:
                yield author.split(" ")[-1]
            else:
                yield author

    authors = None
    for k in ["author", "editor"]:
        if k in entry:
            authors = entry[k]
            break
    if authors is None:
        return None

    authors = normalize(authors).split("and")
    return get_last_name(authors)


def searchdoi(title: str, authors: list[str]) -> str | None:
    for author in authors:
        params = urlencode(
            {
                "titlesearch": "titlesearch",
                "auth2": author,
                "atitle2": title,
                "multi_hit": "on",
                "article_title_search": "Search",
                "queryType": "author-title",
            }
        )
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": "www.crossref.org",
        }
        conn = httplib.HTTPConnection("www.crossref.org:80")
        conn.request("POST", "/guestquery/", params, headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()

        if m := DOI_REGEX.search(data.decode()):
            return m.group(0)

    return None


def add_dois_to_bib(bibfile: Path, cache: Path = Path("doi_cache.json")):
    with open(bibfile, "r") as fid:
        btp = bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False)
        bib = bibtexparser.load(fid, btp)

    doi_cache = json.loads(cache.read_text()) if cache.exists() else {}

    for entry in tqdm(bib.entries, desc="Adding DOIs"):
        id = entry["ID"]
        if "doi" not in entry or entry["doi"].isspace():
            authors = get_authors(entry)
            if authors is None:
                continue

            if id in doi_cache and (doi := doi_cache[id]) is not None:
                entry["doi"] = doi
            else:
                if (doi := searchdoi(entry["title"], authors)) is not None:
                    entry["doi"] = doi
                doi_cache[id] = doi
        else:
            doi_cache[id] = entry["doi"]

    cache.write_text(json.dumps(doi_cache, indent=2))
    return bib


def add_doi(
    bibfiles: list[Path],
    cache: Path = Path("doi_cache.json"),
    output: Path | None = None,
):
    output = output or bibfiles[0]
    bibs = []
    for bibfile in tqdm(bibfiles):
        bibs.append(add_dois_to_bib(bibfile, cache))

    writer = BibTexWriter()
    with open(output, "w") as fid:
        for bib in bibs:
            fid.write(writer.write(bib))


def parse_tidy_dups(
    input: typer.FileText = sys.stdin, output: typer.FileTextWrite = sys.stdout
):
    update_pattern = re.compile(r"DUPLICATE_ENTRY:.*?Entry (\S+) .*?entry (\S+)\.")

    key_updates = {}
    for line in input:
        match = update_pattern.match(line.strip())
        if match:
            old_key, new_key = match.groups()
            key_updates[old_key] = new_key

    json.dump(key_updates, output, indent=2)


def update_citation(duplicate_keys: typer.FileText, files: list[str]):
    key_updates = json.loads(duplicate_keys.read())
    cite_pattern = re.compile(r"(\\cite\w*\{([^}]+)\})")

    def replace_cite_keys(match):
        cite_command = match.group(1)
        keys_str = match.group(2)
        keys = [k.strip() for k in keys_str.split(",")]
        updated_keys = [key_updates.get(k, k) for k in keys]
        return f"{cite_command.split('{')[0]}{{{','.join(updated_keys)}}}"

    for file in files:
        with open(file, "r") as f:
            with open(file + ".tmp", "w") as tmp:
                for line in f:
                    tmp.write(cite_pattern.sub(replace_cite_keys, line))

        Path(file + ".tmp").rename(file)
