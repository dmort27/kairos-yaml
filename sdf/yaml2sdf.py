# %%
import os
import sys
import json
import yaml
from collections import defaultdict, OrderedDict, Counter
import random
import logging

# %% 

def get_step_type(step):
    # TODO sanity check whether the type exists the ontology?
    return f"kairos:Primitives/{step['primitive']}"

def get_slot_role(slot, step_type=None):
    # TODO sanity check whether the role exists the ontology?
    return f"{step_type}/Roles/{slot['role']}"

def get_slot_name(slot, slot_shared):
    name = "".join([' ' + x if x.isupper() else x for x in slot["role"]]).lstrip()
    name = name.split()[0].lower()
    if slot_shared:
        name += "-" + slot["refvar"]
    return name

def get_slot_id(slot, schema_slot_counter, schema_id, slot_shared):
    slot_name = get_slot_name(slot, slot_shared)
    slot_id = chr(schema_slot_counter[slot_name] + 97)
    schema_slot_counter[slot_name] += 1
    return f"{schema_id}/Slots/{slot_name}-{slot_id}"


def get_slot_constraints(constraints):
    return [f"kairos:{x}" for x in constraints]

def get_step_id(step, schema_id):
    return f"{schema_id}/Steps/{step['id']}"

def convert_yaml_to_sdf(yaml_file, assigned_info):
    """
    yaml_file: the input yaml file
    assigned_info: the schema id, descriptions are assigned manually
    """
    # assigned_info["schema_name"] = ''.join([' ' + x if x.isupper() else x for x in assigned_info["schema_id"][len("cmu:"):]]).lstrip()
    # assigned_info["schema_name"] = assigned_info["schema_name"][0] + assigned_info["schema_name"][1:].lower()
    schema = OrderedDict([
        ("@id", assigned_info["schema_id"]),
        ("comment", ''),
        ("super", "kairos:Event"),
        ("name", assigned_info["schema_name"]), 
        ("description", assigned_info["schema_dscpt"]),
        ("version", "6/2/2020"),
        ("steps", []),
        ("order", []),
        ("entityRelations", [])
    ])
    ds = yaml.load(open(yaml_file), Loader=yaml.FullLoader)    
    assert len(ds) == 1
    ds = ds[0]

    # get comments
    comments = [x["id"].replace("-", " ") for x in ds["steps"]]
    comments = ["Steps:"] + [f"{idx + 1}. {text}" for idx, text in enumerate(comments)]   
    schema["comment"] = comments
    
    # get steps
    steps = []

    # for sameAs relation
    entity_map = {}
    # for order
    step_map = defaultdict(lambda: defaultdict(str))

    # for naming slot id
    schema_slot_counter = Counter()

    for idx, step in enumerate(ds["steps"]):
        cur_step = {
            "@id": get_step_id(step, schema["@id"]), 
            "@type": get_step_type(step), 
            "comment": comments[idx + 1],
        }
        if "provenance" in step:
            cur_step["provenance"] = step["provenance"]
        
        step_map[step["id"]] = {"id": cur_step["@id"], "step_idx": idx+1}

        slots = []
        for sidx, slot in enumerate(step["slots"]):
            slot_shared = sum([slot["role"] == sl["role"] for sl in step["slots"]]) > 1

            cur_slot = {
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

            # get entity ID for relations
            if "refvar" in slot:
                entity_map[cur_slot["@id"]] = slot["refvar"]
            else:
                logging.warning(f"{slot} misses refvar")
                entity_map[cur_slot["@id"]] = str(random.random())
        
        cur_step["slots"] = slots
        steps.append(cur_step)

    # Cleaning "-a" suffix for slots with counter == 1. Just my OCD...
    for step in steps:
        for slot in step["slots"]:
            if schema_slot_counter[slot["name"]] == 1:
                temp = entity_map[slot["@id"]]
                del entity_map[slot["@id"]]

                slot["@id"] = slot["@id"].strip("-a")

                entity_map[slot["@id"]] = temp

    schema["steps"] = steps

    orders = []
    for order in ds["order"]:
        if "before" in order and "after" in order:
            before_idx = step_map[order['before']]['step_idx']
            before_id = step_map[order['before']]['id']
            after_idx = step_map[order['after']]['step_idx']
            after_id = step_map[order['after']]['id']
            if not before_id and not before_idx:
                logging.warning(f"before: {order['before']} does not appear in the steps")
            if not after_id and not after_idx:
                logging.warning(f"after: {order['after']} does not appear in the steps")
            cur_order = {"comment": f"{before_idx} precedes {after_idx}"}
            cur_order["before"] = before_id
            cur_order["after"] = after_id
        elif "overlap" in order:
            raise NotImplementedError
        else:
            raise NotImplementedError
        orders.append(cur_order)
    schema["order"] = orders

    # get entity relations
    entity_map = {x: y for x, y in entity_map.items() if y is not None}
    # get same as relation
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


# %%
# merge multiple schemas
def merge_schemas(schema_list, save_file):
    sdf = {}
    sdf["@context"] = OrderedDict([
        ("schema", "http://schema.org/"),
        ("xsd", "http://www.w3.org/2001/XMLSchema#"),
        ("kairos", "https://kairos-sdf.s3.amazonaws.com/context/kairos#"),
        ("schemas", "kairos:schemas"),
        ("super", { "@id": "kairos:super", "@type": "@id" }),
        ("name", "schema:name"),
        ("comment", "kairos:comment"),
        ("provenance", "kairos:provenance"),
        ("description", "schema:description"),
        ("version", "schema:version"),
        ("sdfVersion", "kairos:sdfVersion"),
        ("privateData", "kairos:privateData"),
        ("reference", { "@id": "kairos:reference", "@type": "@id" }),
        ("steps", "kairos:steps"),
        ("slots", "kairos:slots"),
        ("role", { "@id": "kairos:role", "@type": "@id" }),
        ("entityTypes", "kairos:entityTypes"),
        ("values", "kairos:values"),
        ("confidence", { "@id": "kairos:confidence", "@type": "xsd:float" }),
        ("entityRelations", "kairos:entityRelations"),
        ("relationSubject", { "@id": "kairos:relationSubject", "@type": "@id" }),
        ("relationPredicate", "kairos:relationPredicate"),
        ("relationObject", "kairos:relationObject"),
        ("relations", "kairos:relations"),
        ("aka", "kairos:aka"),
        ("temporal", "kairos:temporal"),
        ("duration", { "@id": "kairos:duration", "@type": "xsd:duration" }),
        ("startTime", { "@id": "kairos:startTime", "@type": "xsd:dateTime" }),
        ("endTime", { "@id": "kairos:endTime", "@type": "xsd:dateTime" }),
        ("absoluteTime", { "@id": "kairos:absoluteTime", "@type": "xsd:dateTime" }),
        ("minDuration", { "@id": "kairos:minDuration", "@type": "xsd:duration" }),
        ("maxDuration", { "@id": "kairos:maxDuration", "@type": "xsd:duration" }),
        ("order", "kairos:order"),
        ("before", { "@id": "kairos:before", "@type": "@id" }),
        ("after", { "@id": "kairos:after", "@type": "@id" }),
        ("container", { "@id": "kairos:container", "@type": "@id" }),
        ("contained", { "@id": "kairos:contained", "@type": "@id" }),
        ("overlaps", { "@id": "kairos:overlaps", "@type": "@id" }),
        ("flags",  "kairos:flags"),
        ("aida", "https://darpa.mil/i2o/aida.official.namespace/"),
        ("cmu",  "http://cs.cmu.edu/~kairos/kairos.cmu.namespace/")
    ])
    sdf["schemas"] = schema_list
    sdf["sdfVersion"] = "0.7"

    json.dump(sdf, open(save_file, "w+"), indent=4)

# %% 
if __name__ == "__main__":

    ## ied.json
    fname = "ied"
    assigned_info = {
        "schema_id": "cmu:make-ied",
        "schema_name": "IED Manufacture",
        "schema_dscpt": "General description of making IED"
    }

    yaml_file = os.path.join("examples/q2/ta1", "ied.yaml")
    out_json = convert_yaml_to_sdf(yaml_file, assigned_info)

    save_file = os.path.join("output", "ied.json")
    merge_schemas([out_json], save_file)


    ## vbied.json
    sch_list = []
    assigned_info = {
        "schema_id": "cmu:make-vbied-purchaseExpl",
        "schema_name": "VBIED Manufacture (explosives purchased)",
        "schema_dscpt": "Description of making vehicle-based IED, when explosives are purchased"
    }
    yaml_file = os.path.join("examples/q2/ta1", "vbied-buy-explosives.yaml")
    out_json = convert_yaml_to_sdf(yaml_file, assigned_info)
    sch_list.append(out_json)

    assigned_info = {
        "schema_id": "cmu:make-vbied-manufactureExpl",
        "schema_name": "VBIED Manufacture (explosives manufactured)",
        "schema_dscpt": "Description of making vehicle-based IED, when explosives are manufactured"
    }
    yaml_file = os.path.join("examples/q2/ta1", "vbied-manufacture-explosives.yaml")
    out_json = convert_yaml_to_sdf(yaml_file, assigned_info)
    sch_list.append(out_json)

    save_file = os.path.join("output", "vbied.json")
    merge_schemas(sch_list, save_file)
    
            
    ## dbied.json
    sch_list = []
    assigned_info = {
        "schema_id": "cmu:make-dbied-purchaseExpl",
        "schema_name": "DBIED Manufacture (explosives purchased)",
        "schema_dscpt": "Description of making drone-based IED, when explosives are purchased"
    }
    yaml_file = os.path.join("examples/q2/ta1", "dbied-buy-explosives.yaml")
    out_json = convert_yaml_to_sdf(yaml_file, assigned_info)
    sch_list.append(out_json)

    assigned_info = {
        "schema_id": "cmu:make-dbied-manufactureExpl",
        "schema_name": "DBIED Manufacture (explosives manufactured)",
        "schema_dscpt": "Description of making drone-based IED, when explosives are manufactured"
    }
    yaml_file = os.path.join("examples/q2/ta1", "dbied-manufacture-explosives.yaml")
    out_json = convert_yaml_to_sdf(yaml_file, assigned_info)
    sch_list.append(out_json)

    save_file = os.path.join("output", "dbied.json")
    merge_schemas(sch_list, save_file)


