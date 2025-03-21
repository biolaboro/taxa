# Abstract

This package provides a pythonic interface to interact with a custom subset of NCBI Taxonomy database. Additional command line tools can query taxonomy node ancestors and descendants or import custom taxonomy. Warning: this package is in early development and currently no tests are provided, so please use at your own risk!

# Examples

## Install

```bash
pip3 install build && python3 -m build && pip3 install dist/taxa-0.0.3.tar.gz
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
666	2	Bacteria	Bacteria <bacteria>	131567	domain
666	3379134	Pseudomonadati		2	kingdom
666	1224	Pseudomonadota		3379134	phylum
666	1236	Gammaproteobacteria		1224	class
666	135623	Vibrionales		1236	order
666	641	Vibrionaceae		135623	family
666	662	Vibrio		641	genus
666	666	Vibrio cholerae		662	species
```

## Descendants

Query the descendants of *Vibrio cholera* (NCBI:txid666).

```bash
python3 -m taxa.taxa -database taxa.db lineage -mode descendants 666 | cut -f 3 | paste - - - - - - - -
```

```
tax_id	44104	45888	66861	127906	156539	185331	185332
345072	345073	345074	345075	345076	404974	412614	412883
412966	412967	417397	417398	417399	567107	579112	592313
593585	593586	593587	593589	593590	617130	663913	663914
663915	663958	675807	675808	675809	693735	693736	693737
693738	693739	693740	693741	693742	693743	693744	694561
694562	694563	694564	694565	696085	696086	707239	753500
935297	948564	991923	991924	991925	991926	991927	991928
991929	991930	991931	991932	991933	991934	991935	991936
991937	991938	991939	991940	991941	991942	991943	991944
991945	991946	991947	991948	991949	991950	991951	991952
991953	991954	991955	991956	991957	991958	991959	991960
991961	991962	991963	991965	991966	991967	991968	991969
991970	991971	991972	991973	991974	991975	991976	991977
991978	991979	991980	991981	991982	991983	991984	991985
991986	991987	991988	991989	991990	991991	991992	991993
991994	991995	991996	991997	992000	992001	992002	992003
992004	992005	992006	992007	992008	992009	1000950	1000951
1000952	1000953	1051362	1093790	1147127	1149858	1220509	1225781
1225782	1225783	1233524	1235442	1235443	1235444	1235454	1235456
1235473	1236549	1258564	1263862	1290431	1290432	1294144	1294275
1306408	1339249	1343738	1352358	1398492	1399573	1399574	1399575
1400004	1408477	1408478	1420885	686	593588	914149	925768
925769	1055325	1095638	1095639	1095640	1095641	1095642	1095643
1095644	1095645	1095646	1095647	1095648	1095649	1095650	1095651
1095652	1095653	1095654	1095655	1095656	1095657	1095658	1095660
1095661	1095662	1124468	1124469	1124470	1124471	1124472	1124473
1124474	1124475	1124476	1124477	1124478	1124479	1124480	1124481
1124482	1124483	1124484	1124485	1124486	1124487	1134456	1175247
1175248	1175249	1175250	1175251	1175253	1175254	1175255	1175256
1175257	1175258	1175259	1175260	1175261	1175262	1175263	1175264
1175265	1175266	1175267	1175268	1175269	1175270	1175271	1175272
1175273	1175274	1175275	1175276	1175277	1175285	1175286	1175287
1175288	1175289	1175290	1175291	1175292	1175293	1224154	1288389
1433144	243277	417400	661513	1416746	1416747	1416748	1416749
1458274
```

## Custom taxonomy

The custom taxonomy file format is tab-separated. Multiple taxonomy subtrees may be specified. The root of each subtree must have a parent_tax_id that exists in the database.

custom.tsv:
```
key	rank	name_class	name_txt	unique_name	parent_tax_id
I	clade	scientific name	MPXV-I	Monkeypox virus clade I	10244
II	clade	scientific name	MPXV-II	Monkeypox virus clade II	10244
IIa	clade	scientific name	MPXV-IIa	Monkeypox virus clade IIa	II
IIb	clade	scientific name	MPXV-IIb	Monkeypox virus clade IIb	II
beast	clade	scientific name	VCH-beast	Vibrio cholerae beast	666
```

```bash
python3 -m taxa.taxa -database taxa.db custom custom.tsv
```

The result maps each key to its new tax_id value.

```
I	3114305
II	3114306
IIa	3114307
IIb	3114308
beast	3114309
```

```
python3 -m taxa.taxa -database taxa.db lineage -mode ancestors 3114307
```

```
taxon	tax_id	name_txt	unique_name	parent_tax_id	rank
3114307	1	root		1	no rank
3114307	10239	Viruses		1	superkingdom
3114307	2732004	Varidnaviria		10239	clade
3114307	2732005	Bamfordvirae		2732004	kingdom
3114307	2732007	Nucleocytoviricota		2732005	phylum
3114307	2732525	Pokkesviricetes		2732007	class
3114307	2732527	Chitovirales		2732525	order
3114307	10240	Poxviridae		2732527	family
3114307	10241	Chordopoxvirinae		10240	subfamily
3114307	10242	Orthopoxvirus		10241	genus
3114307	10244	Monkeypox virus		10242	species
3114307	3114306	MPXV-II	Monkeypox virus clade II	10244	clade
3114307	3114307	MPXV-IIa	Monkeypox virus clade IIa	3114306	clade
```
