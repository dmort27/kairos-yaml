"""Converts CMU YAML into KAIROS SDF JSON-LD."""

import argparse
from collections import Counter, defaultdict
import json
import logging
from pathlib import Path
import random
import typing
from typing import Any, Dict, Mapping, Optional, Sequence, Union

import yaml

EVENT_ONTOLOGY: Optional[Mapping[str, Any]] = None


def get_event_ontology() -> Mapping[str, Any]:
    global EVENT_ONTOLOGY

    if EVENT_ONTOLOGY is None:
        with Path("events.json").open() as file:
            EVENT_ONTOLOGY = json.load(file)

    return EVENT_ONTOLOGY


def get_step_type(step: Mapping[str, Any]) -> str:
    """Gets type of step.

    Args:
        step: Step data.

    Returns:
        Step type.
    """
    # Add missing "Unspecified"s
    primitive = step["primitive"].split(".")
    if len(primitive) < 3:
        primitive.extend(["Unspecified"] * (3 - len(primitive)))
    primitive = ".".join(primitive)

    if primitive not in get_event_ontology():
        logging.warning(f"Primitive '{step['primitive']}' in step '{step['id']}' not in ontology")

    return f"kairos:Primitives/Events/{primitive}"


def get_slot_role(slot: Mapping[str, Any], step_type: str) -> str:
    """Gets slot role.

    Args:
        slot: Slot data.
        step_type: Type of step.

    Returns:
        Slot role.
    """
    event_type = get_event_ontology().get(step_type.split("/")[-1], None)
    if event_type is not None and slot['role'] not in event_type['args']:
        logging.warning(f"Role '{slot['role']}' is not valid for event '{event_type['type']}'")

    return f"{step_type}/Slots/{slot['role']}"


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
    return [f"kairos:Primitives/Entities/{x}" for x in constraints]


def create_slot(slot: Mapping[str, Any], schema_slot_counter, schema_id, step_type, slot_shared: bool, entity_map):
    cur_slot: Dict[str, Any] = {
        "name": get_slot_name(slot, slot_shared),
        "@id": get_slot_id(slot, schema_slot_counter, schema_id, slot_shared),
        "role": get_slot_role(slot, step_type),
    }

    constraints = get_slot_constraints(slot.get("constraints", []))
    if constraints:
        cur_slot["entityTypes"] = constraints
    if "reference" in slot:
        cur_slot["reference"] = slot["reference"]

    # Get entity ID for relations
    if "refvar" in slot:
        entity_map[cur_slot["@id"]] = slot["refvar"]
        cur_slot["refvar"] = slot["refvar"]
    else:
        logging.warning(f"{slot} misses refvar")
        entity_map[cur_slot["@id"]] = str(random.random())

    return cur_slot


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
            "name": step["id"],
            "@type": get_step_type(step),
            "comment": comments[idx + 1],
        }
        if "comment" in step:
            cur_step["comment"] += "\n" + step["comment"]

        if "provenance" in step:
            cur_step["provenance"] = step["provenance"]

        step_map[step["id"]] = {"id": cur_step["@id"], "step_idx": idx + 1}

        slots = []
        for slot in step["slots"]:
            slot_shared = sum([slot["role"] == sl["role"] for sl in step["slots"]]) > 1

            slots.append(
                create_slot(slot, schema_slot_counter, schema["@id"], cur_step["@type"], slot_shared, entity_map))

        cur_step["participants"] = slots
        steps.append(cur_step)

    slots = []
    for slot in yaml_data["slots"]:
        slot_shared = sum([slot["role"] == sl["role"] for sl in yaml_data["slots"]]) > 1

        parsed_slot = create_slot(slot, schema_slot_counter, schema["@id"], schema["@id"], slot_shared, entity_map)
        parsed_slot["roleName"] = parsed_slot["role"]
        del parsed_slot["role"]

        slots.append(parsed_slot)
    schema["slots"] = slots

    # Cleaning "-a" suffix for slots with counter == 1.
    for step in steps:
        for slot in step["participants"]:
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
    # for v in reverse_entity_map.values():
    #     cur_entity_relation = {
    #         "relationSubject": v[0],
    #         "relations": [{
    #             "relationPredicate": "kairos:Relations/sameAs",
    #             "relationObject": x
    #         } for x in v[1:]]
    #     }
    #     if cur_entity_relation["relations"]:
    #         entity_relations.append(cur_entity_relation)
    schema["entityRelations"] = entity_relations

    return schema


def merge_schemas(schema_list: Sequence[Mapping[str, Any]], schema_id: str) -> Mapping[str, Any]:
    """Merge multiple schemas.

    Args:
        schema_list: List of SDF schemas.
        schema_id: ID of schema collection.

    Returns:
        Data in JSON output format.
    """
    sdf = {
        "@context": ["https://kairos-sdf.s3.amazonaws.com/context/kairos-v0.8.jsonld"],
        "sdfVersion": "0.8",
        "@id": schema_id,
        "schemas": schema_list,
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

    json_data = merge_schemas(schemas, json_file.stem)
    with json_file.open("w") as file:
        json.dump(json_data, file, ensure_ascii=True, indent=4)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input-files", nargs="+", type=Path, required=True,
                   help="Paths to input YAML schemas.")
    p.add_argument("--output-file", type=Path, required=True,
                   help="Path to output JSON schema.")
    args = p.parse_args()

    convert_files(args.input_files, args.output_file)


if __name__ == "__main__":
    main()
