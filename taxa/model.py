#!/usr/bin/env python3

from sqlalchemy import Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class TaxMerged(Base):
    __tablename__ = 'tax_merged'

    old_tax_id = Column(Integer, primary_key=True)
    new_tax_id = Column(Integer, nullable=False)


class TaxName(Base):
    __tablename__ = 'tax_name'

    id = Column(Integer, primary_key=True)
    tax_id = Column(Integer, nullable=False, index=True)
    name_txt = Column(Text, nullable=False)
    unique_name = Column(Text)
    name_class = Column(Text, nullable=False)


class TaxNode(Base):
    __tablename__ = 'tax_node'

    tax_id = Column(Integer, primary_key=True)
    parent_tax_id = Column(Integer, nullable=False)
    rank = Column(Text, nullable=False)
