#!/usr/bin/env python3

import io
import sys
import tarfile
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
from collections import deque
from contextlib import contextmanager
from functools import partial
from getpass import getpass
from itertools import chain
from operator import itemgetter

from sqlalchemy import create_engine
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker

from taxa.model import Base, TaxMerged, TaxName, TaxNode

ROOT = 1


@contextmanager
def session_scope(sessionmaker):
    session = sessionmaker()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def ancestors(curs, taxon):
    sql = """
        SELECT tax_name.tax_id, tax_name.name_txt, tax_name.unique_name, tax_node.parent_tax_id, tax_node.rank
          FROM tax_name
          JOIN tax_node ON tax_node.tax_id = tax_name.tax_id
          WHERE
              tax_name.name_class = 'scientific name' AND
              tax_name.tax_id = COALESCE(
                (SELECT new_tax_id FROM tax_merged WHERE old_tax_id = :tax_id), :tax_id
              )
          ;
    """

    lineage = deque()

    while taxon != ROOT:
        row = curs.execute(sql, params=dict(tax_id=taxon)).fetchone()
        if row:
            lineage.appendleft(row)
            taxon = row["parent_tax_id"]
        else:
            break

    if lineage:
        row = curs.execute(sql, params=dict(tax_id=ROOT)).fetchone()
        lineage.appendleft(row)

    return lineage


def descendants(curs, taxon):
    def _descendants(curs, taxon):
        sql = "SELECT tax_id FROM tax_node WHERE parent_tax_id = :tax_id;"
        rows = list(map(itemgetter(0), curs.execute(sql, params=dict(tax_id=taxon))))
        if rows:
            yield from rows
            yield from chain.from_iterable(map(partial(_descendants, curs), rows))

    return list(_descendants(curs, taxon))


def parse_args_to_url(args):
    keys = ("drivername", "username", "password", "host", "port", "database")
    return URL(**{key: getattr(args, key) for key in keys})


def parse_dump(file):
    yield from (list(map(str.strip, line.split("|"))) for line in file)


def main_create(engine, taxdump):
    Base.metadata.create_all(engine)
    with session_scope(sessionmaker(bind=engine)) as session:
        with tarfile.open(taxdump, "r") as tar:
            print("nodes...")
            with io.TextIOWrapper(tar.extractfile("nodes.dmp")) as file:
                fields = ("tax_id", "parent_tax_id", "rank")
                mappings = (dict(zip(fields, row)) for row in parse_dump(file))
                session.bulk_insert_mappings(TaxNode, mappings)
            print("merged...")
            with io.TextIOWrapper(tar.extractfile("merged.dmp")) as file:
                fields = ("old_tax_id", "new_tax_id")
                mappings = (dict(zip(fields, row)) for row in parse_dump(file))
                session.bulk_insert_mappings(TaxMerged, mappings)
            print("names...")
            with io.TextIOWrapper(tar.extractfile("names.dmp")) as file:
                fields = ("tax_id", "name_txt", "unique_name", "name_class")
                mappings = (dict(zip(fields, row)) for row in parse_dump(file))
                session.bulk_insert_mappings(TaxName, mappings)


def main_ancestors(engine, taxa, delimiter="\t"):
    with session_scope(sessionmaker(bind=engine)) as session:
        print(
            "taxon", "tax_id", "name_txt", "unique_name", "parent_tax_id", "rank",
            sep=delimiter
        )
        for taxon in taxa:
            for entry in ancestors(session, taxon):
                print(taxon, *entry, sep=delimiter)


def main_descendants(engine, taxa):
    for taxon in taxa:
        with session_scope(sessionmaker(bind=engine)) as curs:
            rows = descendants(curs, taxon)
            print(taxon, *rows, sep="\n")


def conn_kwargs(args):
    keys = ("drivername", "username", "password", "host", "port", "database")
    return {key: getattr(args, key) for key in keys}


def add_db_args(parser):
    parser.add_argument("-drivername", default="sqlite", help="the database driver name")
    parser.add_argument("-database", help="the taxonomy database")
    parser.add_argument("-username", help="the database user name")
    parser.add_argument("-password", action="store_true", help="the database user password")
    parser.add_argument("-host", help="the database host")
    parser.add_argument("-port", type=int, help="the database port")


def parse_argv(argv):
    parser = ArgumentParser(description="taxonomy tool",  formatter_class=ArgumentDefaultsHelpFormatter)

    add_db_args(parser)

    subparsers = parser.add_subparsers(
        help="commands",
        dest="command"
    )

    subparser = subparsers.add_parser(
        "create",
        help="this program creates the taxonomy database"
    )
    subparser.add_argument(
        "taxdump",
        help="the path to the taxonomy database dump (.tar.gz)"
    )

    subparser = subparsers.add_parser(
        "lineage",
        help="this program calculates the lineage for each taxon"
    )
    subparser.add_argument(
        "taxa",
        nargs="+",
        help="the list of taxon identifiers"
    )
    choices = ("ancestors", "descendants")
    subparser.add_argument(
        "-mode",
        choices=choices,
        default=choices[0],
        help="the delimiter for the resulting table"
    )
    subparser.add_argument(
        "-delimiter",
        default="\t",
        help="the delimiter for the resulting table"
    )

    args = parser.parse_args(argv)

    args.password = getpass("password: ") if args.password else None

    return args


def main(argv):
    args = parse_argv(argv[1:])

    dburl = parse_args_to_url(args)
    engine = create_engine(dburl)

    if args.command == "create":
        main_create(engine, args.taxdump)

    elif args.command == "lineage":
        if args.mode == "ancestors":
            main_ancestors(engine, args.taxa, delimiter=args.delimiter)
        elif args.mode == "descendants":
            main_descendants(engine, args.taxa)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
