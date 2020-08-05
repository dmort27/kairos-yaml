"""Converts CMU YAML into KAIROS SDF JSON-LD."""

from collections import Counter, defaultdict
import json
import logging
from pathlib import Path
import random
import typing
from typing import Any, Dict, Mapping, Optional, Sequence, Union

import yaml


def get_step_type(step: Mapping[str, Any]) -> str:
    """Gets type of step.

    Args:
        step: Step data.

    Returns:
        Step type.
    """
    # TODO: Sanity check whether the type exists the ontology?
    return f"kairos:Primitives/{step['primitive']}"


def get_slot_role(slot: Mapping[str, Any], step_type: Optional[str] = None) -> str:
    """Gets slot role.

    Args:
        slot: Slot data.
        step_type: Type of step.

    Returns:
        Slot role.
    """
    # TODO: Sanity check whether the role exists the ontology?
    return f"{step_type}/Roles/{slot['role']}"


def get_slot_name(slot: Mapping[str, Any], slot_shared: bool) -> str:
    """Gets slot name.

    Args:
        slot: Slot data.
        slot_shared: Whether slot is shared.

    Returns:
        Slot name.
    """
    name = "".join([' ' + x if x.isupper() else x for x in slot["role"]]).lstrip()
    name = name.split()[0].lower()
    if slot_shared:
        name += "-" + slot["refvar"]
    return name


def get_slot_id(slot: Mapping[str, Any], schema_slot_counter: typing.Counter[str],
                schema_id: str, slot_shared: bool) -> str:
    """Gets slot ID.

    Args:
        slot: Slot data.
        schema_slot_counter: Slot counter.
        schema_id: Schema ID.
        slot_shared: Whether slot is shared.

    Returns:
        Slot ID.
    """
    slot_name = get_slot_name(slot, slot_shared)
    slot_id = chr(schema_slot_counter[slot_name] + 97)
    schema_slot_counter[slot_name] += 1
    return f"{schema_id}/Slots/{slot_name}-{slot_id}"


def get_slot_constraints(constraints: Sequence[str]) -> Sequence[str]:
    """Gets slot constraints.

    Args:
        constraints: Constraints.

    Returns:
        Slot constraints.
    """
    return [f"kairos:{x}" for x in constraints]


def get_step_id(step: Mapping[str, Any], schema_id: str) -> str:
    """Gets step ID.

    Args:
        step: Step data.
        schema_id: Schema ID.

    Returns:
        Step ID.
    """
    return f"{schema_id}/Steps/{step['id']}"


def convert_yaml_to_sdf(yaml_data: Mapping[str, Any]) -> Mapping[str, Any]:
    """Converts YAML to SDF.

    Args:
        yaml_data: Data from YAML file.

    Returns:
        Schema in SDF format.
    """
    # assigned_info["schema_name"] = ''.join([' ' + x if x.isupper() else x for x
    #                                         in assigned_info["schema_id"][len("cmu:"):]]).lstrip()
    # assigned_info["schema_name"] = assigned_info["schema_name"][0] + \
    #                                assigned_info["schema_name"][1:].lower()
    schema = {
        "@id": yaml_data["schema_id"],
        "comment": '',
        "super": "kairos:Event",
        "name": yaml_data["schema_name"],
        "description": yaml_data["schema_dscpt"],
        "version": "6/2/2020",
        "steps": [],
        "order": [],
        "entityRelations": []
    }

    # Get comments
    comments = [x["id"].replace("-", " ") for x in yaml_data["steps"]]
    comments = ["Steps:"] + [f"{idx + 1}. {text}" for idx, text in enumerate(comments)]
    schema["comment"] = comments

    # Get steps
    steps = []

    # For sameAs relation
    entity_map = {}
    # For order
    step_map: Dict[str, Dict[str, Union[int, str]]] = {}

    # For naming slot ID
    schema_slot_counter: typing.Counter[str] = Counter()

    for idx, step in enumerate(yaml_data["steps"]):
        cur_step: Dict[str, Any] = {
            "@id": get_step_id(step, schema["@id"]),
            "@type": get_step_type(step),
            "comment": comments[idx + 1],
        }
        if "provenance" in step:
            cur_step["provenance"] = step["provenance"]

        step_map[step["id"]] = {"id": cur_step["@id"], "step_idx": idx + 1}

        slots = []
        for slot in step["slots"]:
            slot_shared = sum([slot["role"] == sl["role"] for sl in step["slots"]]) > 1

            cur_slot: Dict[str, Any] = {
                "name": get_slot_name(slot, slot_shared),
                "@id": get_slot_id(slot, schema_slot_counter, schema["@id"], slot_shared),
                "role": get_slot_role(slot, cur_step["@type"]),
            }

            constraints = get_slot_constraints(slot.get("constraints", []))
            if constraints:
                cur_slot["entityTypes"] = constraints
            if "reference" in slot:
                cur_slot["reference"] = slot["reference"]
            slots.append(cur_slot)

            # Get entity ID for relations
            if "refvar" in slot:
                entity_map[cur_slot["@id"]] = slot["refvar"]
            else:
                logging.warning(f"{slot} misses refvar")
                entity_map[cur_slot["@id"]] = str(random.random())

        cur_step["slots"] = slots
        steps.append(cur_step)

    # Cleaning "-a" suffix for slots with counter == 1.
    for step in steps:
        for slot in step["slots"]:
            if schema_slot_counter[slot["name"]] == 1:
                temp = entity_map[slot["@id"]]
                del entity_map[slot["@id"]]

                slot["@id"] = slot["@id"].strip("-a")

                entity_map[slot["@id"]] = temp

    schema["steps"] = steps

    orders = []
    for order in yaml_data["order"]:
        if "before" in order and "after" in order:
            before_idx = step_map[order['before']]['step_idx']
            before_id = step_map[order['before']]['id']
            after_idx = step_map[order['after']]['step_idx']
            after_id = step_map[order['after']]['id']
            if not before_id and not before_idx:
                logging.warning(f"before: {order['before']} does not appear in the steps")
            if not after_id and not after_idx:
                logging.warning(f"after: {order['after']} does not appear in the steps")
            cur_order = {
                "comment": f"{before_idx} precedes {after_idx}",
                "before": before_id,
                "after": after_id
            }
        elif "overlap" in order:
            raise NotImplementedError
        else:
            raise NotImplementedError
        orders.append(cur_order)
    schema["order"] = orders

    # Get entity relations
    entity_map = {x: y for x, y in entity_map.items() if y is not None}
    # Get same as relation
    reverse_entity_map = defaultdict(list)
    for k, v in entity_map.items():
        reverse_entity_map[v].append(k)
    entity_relations = []
    for v in reverse_entity_map.values():
        cur_entity_relation = {
            "relationSubject": v[0],
            "relations": [{
                "relationPredicate": "kairos:Relations/sameAs",
                "relationObject": x
            } for x in v[1:]]
        }
        if cur_entity_relation["relations"]:
            entity_relations.append(cur_entity_relation)
    schema["entityRelations"] = entity_relations

    return schema


def merge_schemas(schema_list: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Merge multiple schemas.

    Args:
        schema_list: List of SDF schemas.

    Returns:
        Data in JSON output format.
    """
    sdf = {
        "@context": {
            "schema": "http://schema.org/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "kairos": "https://kairos-sdf.s3.amazonaws.com/context/kairos#",
            "schemas": "kairos:schemas",
            "super": {"@id": "kairos:super", "@type": "@id"},
            "name": "schema:name",
            "comment": "kairos:comment",
            "provenance": "kairos:provenance",
            "description": "schema:description",
            "version": "schema:version",
            "sdfVersion": "kairos:sdfVersion",
            "privateData": "kairos:privateData",
            "reference": {"@id": "kairos:reference", "@type": "@id"},
            "steps": "kairos:steps",
            "slots": "kairos:slots",
            "role": {"@id": "kairos:role", "@type": "@id"},
            "entityTypes": "kairos:entityTypes",
            "values": "kairos:values",
            "confidence": {"@id": "kairos:confidence", "@type": "xsd:float"},
            "entityRelations": "kairos:entityRelations",
            "relationSubject": {"@id": "kairos:relationSubject", "@type": "@id"},
            "relationPredicate": "kairos:relationPredicate",
            "relationObject": "kairos:relationObject",
            "relations": "kairos:relations",
            "aka": "kairos:aka",
            "temporal": "kairos:temporal",
            "duration": {"@id": "kairos:duration", "@type": "xsd:duration"},
            "startTime": {"@id": "kairos:startTime", "@type": "xsd:dateTime"},
            "endTime": {"@id": "kairos:endTime", "@type": "xsd:dateTime"},
            "absoluteTime": {"@id": "kairos:absoluteTime", "@type": "xsd:dateTime"},
            "minDuration": {"@id": "kairos:minDuration", "@type": "xsd:duration"},
            "maxDuration": {"@id": "kairos:maxDuration", "@type": "xsd:duration"},
            "order": "kairos:order",
            "before": {"@id": "kairos:before", "@type": "@id"},
            "after": {"@id": "kairos:after", "@type": "@id"},
            "container": {"@id": "kairos:container", "@type": "@id"},
            "contained": {"@id": "kairos:contained", "@type": "@id"},
            "overlaps": {"@id": "kairos:overlaps", "@type": "@id"},
            "flags": "kairos:flags",
            "aida": "https://darpa.mil/i2o/aida.official.namespace/",
            "cmu": "http://cs.cmu.edu/~kairos/kairos.cmu.namespace/"
        },
        "schemas": schema_list,
        "sdfVersion": "0.7"
    }

    return sdf


def convert_files(yaml_files: Sequence[Path], json_file: Path) -> None:
    """Converts YAML files into a single JSON file.

    Args:
        yaml_files: List of YAML file paths.
        json_file: JSON file path.
    """
    schemas = []
    for yaml_file in yaml_files:
        with yaml_file.open() as file:
            yaml_data = yaml.safe_load(file)
        for yaml_schema in yaml_data:
            out_json = convert_yaml_to_sdf(yaml_schema)
            schemas.append(out_json)

    json_data = merge_schemas(schemas)
    with json_file.open("w") as file:
        json.dump(json_data, file, ensure_ascii=True, indent=4)


def main() -> None:
    input_directory = Path("examples", "q2", "ta1")
    output_directory = Path("output")

    # For ied.json
    convert_files([input_directory / "ied.yaml"], output_directory / "ied.json")

    # For vbied.json
    convert_files([input_directory / "vbied-buy-explosives.yaml",
                   input_directory / "vbied-manufacture-explosives.yaml"],
                  output_directory / "vbied.json")

    # For dbied.json
    convert_files([input_directory / "dbied-buy-explosives.yaml",
                   input_directory / "dbied-manufacture-explosives.yaml"],
                  output_directory / "dbied.json")


if __name__ == "__main__":
    main()
