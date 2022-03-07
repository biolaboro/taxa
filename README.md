#!/usr/bin/env bash

# Abstract

This package provides a pythonic interface to interact with a custom subset of NCBI Taxonomy database.

# Examples

## Install

```bash
pip3 install build && python3 -m build && pip3 install dist/taxa-0.0.1.tar.gz
```

## Data

Download NCBI Taxonomy and create a local SQLite database.

```bash
URL="ftp://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz"
target="$(basename "$URL")"
curl -O "$URL" && \
  python3 -m taxa.taxa -database taxa.db create "$target" && \
  rm -f "$target"
```

## Ancestors

Query the ancestors of *Vibrio cholera* (NCBI:txid666).

```bash
python3 -m taxa.taxa -database taxa.db lineage -mode ancestors 666
```

```
taxon	tax_id	name_txt	unique_name	parent_tax_id	rank
666	1	root		1	no rank
666	131567	cellular organisms		1	no rank
666	2	Bacteria	Bacteria <bacteria>	131567	superkingdom
666	1224	Proteobacteria		2	phylum
666	1236	Gammaproteobacteria		1224	class
666	135623	Vibrionales		1236	order
666	641	Vibrionaceae		135623	family
666	662	Vibrio		641	genus
666	666	Vibrio cholerae		662	species
```
