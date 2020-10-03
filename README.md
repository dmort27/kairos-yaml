# kairos-yaml

Conversion between DARPA KAIROS data formats and YAML

## Installation

Use Python 3.7.

Run `pip install -r requirements.txt`.

## Usage

To convert schemas from YAML to JSON, run the following:

```bash
python convert_ontology.py --in-file KAIROS_Annotation_Tagset_Phase_1_V2.0.xlsx --out-file ontology.json
mkdir -p output
python sdf/yaml2sdf.py
```
