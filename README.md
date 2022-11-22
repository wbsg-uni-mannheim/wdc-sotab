# sotab-benchmark

This repository contains the code for recreating the <a href="http://webdatacommons.org/structureddata/sotab/"> Schema.org Table Annotation Benchmark </a>.

## Schema.org Table Corpus

SOTAB is created based on the <a href="http://webdatacommons.org/structureddata/schemaorgtables/"> Schema.org Table Corpus </a>. To run the code for creating SOTAB, all zip files from the top100 and minimum3 subsets of Schema.org Table Corpus need to be downloaded and put in the directory: data/stc_zip_files/

Run `download.sh` to download processed datasets for the VizNet corpus.
It will also create `data` directory.

  
```console
$ bash download.sh

```

## SOTAB creation

To create the SOTAB datasets for Column Type Annotation and Column Property Annotation the notebooks need to be run in the order stated below:

1. Language Detection
2. MatchColumnNamesToSchema.org
3. Expand properties-CreateTables
4. AnnotatingTables
5. TableSelection-CPA
6. Different-Formats-CPA
7. RandomColumns-CPA
8. TableSelection-CTA
9. CreatingSplits-CPA
10. CreatingSplits-CTA
