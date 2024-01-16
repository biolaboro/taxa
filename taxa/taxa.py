#!/usr/bin/env python3

import io
import sys
import tarfile
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser, FileType
from collections import deque
from contextlib import contextmanager
from csv import DictReader, DictWriter
from functools import partial
from getpass import getpass
from itertools import chain

import networkx as nx
from sqlalchemy import create_engine, func, select
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from .model import Base, TaxMerged, TaxName, TaxNode

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
    sql = text(
        """
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
    )

    lineage = deque()
    while taxon != ROOT:
        row = curs.execute(sql, params=dict(tax_id=taxon)).mappings().first()
        if row:
            lineage.appendleft(row)
            taxon = row["parent_tax_id"]
        else:
            break

    if lineage:
        row = curs.execute(sql, params=dict(tax_id=taxon)).mappings().first()
        lineage.appendleft(row)

    return lineage


def descendants(curs, taxon):
    def _descendants(curs, taxon):
        stmt = select(TaxNode).where(TaxNode.parent_tax_id == taxon)
        rows = [row[0].tax_id for row in curs.execute(stmt).all()]
        if rows:
            yield from rows
            yield from chain.from_iterable(map(partial(_descendants, curs), rows))

    return list(_descendants(curs, taxon))


def parse_args_to_url(args):
    keys = ("drivername", "username", "password", "host", "port", "database")
    return URL.create(**{key: getattr(args, key) for key in keys})


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
        rows = (dict(taxon=taxon, **entry) for taxon in taxa for entry in ancestors(session, taxon))
        row = next(rows)
        writer = DictWriter(sys.stdout, fieldnames=row, delimiter=delimiter)
        writer.writeheader()
        writer.writerows((row, *rows))


def main_descendants(engine, taxa):
    with session_scope(sessionmaker(bind=engine)) as curs:
        for taxon in taxa:
            rows = descendants(curs, taxon)
            print(taxon, *rows, sep="\n")


def main_custom(engine, file):
    with file as file:
        data = {row["key"]: row for row in DictReader(file, delimiter="\t")}

    tax_map = {}
    with session_scope(sessionmaker(bind=engine)) as session:
        # get the next available identifiers
        tax_id = session.execute(
            text(
                """
                    SELECT MAX(tax_id)+1 FROM (
                        SELECT MAX(tax_id) AS tax_id FROM tax_node UNION
                        SELECT MAX(parent_tax_id) AS tax_id FROM tax_node
                    );
                """
            )
        ).scalar()
        id = session.query(func.max(TaxName.id)).scalar() + 1
        # load custom taxonomy as a directed graph
        D = nx.DiGraph(((row["parent_tax_id"], row["key"]) for row in data.values()))
        # for each directed graph
        for nodes in nx.weakly_connected_components(D):
            # find the root
            root = next(node for node in nodes if D.in_degree(node) == 0)
            # assert that the root exists in the database
            count = session.execute(select(func.count(TaxNode.tax_id)).where(TaxNode.tax_id == root)).scalar()
            assert count == 1
            # calculate breadth first search traversal
            T = nx.traversal.breadth_first_search.bfs_tree(D, root)
            # assert the directed graph is a tree
            assert nx.is_arborescence(T)
            # for each edge, add the new node with attributes and track the assigned taxonomy identifiers
            tax_map[root] = root
            for edge in T.edges():
                attr = data[edge[1]]
                session.add(
                    TaxNode(
                        tax_id=tax_id,
                        parent_tax_id=tax_map[edge[0]],
                        rank=attr["rank"]
                    )
                )
                session.add(
                    TaxName(
                        id=id,
                        tax_id=tax_id,
                        name_txt=attr["name_txt"],
                        unique_name=attr["unique_name"],
                        name_class=attr["name_class"]
                    )
                )
                tax_map[edge[1]] = tax_id
                tax_id += 1
                id += 1

    # report the new node taxonmy identifiers
    for key, val in tax_map.items():
        if key != val:
            print(key, val, sep="\t")


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
    parser = ArgumentParser(description="taxonomy tool", formatter_class=ArgumentDefaultsHelpFormatter)

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
        help="the lineage mode"
    )
    subparser.add_argument(
        "-delimiter",
        default="\t",
        help="the delimiter for the resulting table"
    )

    subparser = subparsers.add_parser(
        "custom",
        help="this program inserts a custom taxonomy into the database"
    )
    subparser.add_argument(
        "file",
        help="the tsv file",
        type=FileType()
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

    elif args.command == "custom":
        main_custom(engine, args.file)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
