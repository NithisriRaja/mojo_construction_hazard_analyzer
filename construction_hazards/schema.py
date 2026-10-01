"""
Client-owned output schema -- must never change.
The hash guard below stops the program at import if the text is edited.
"""
import hashlib
import json

HAZARD_SCHEMA_TEXT = '{"type":"object","properties":{"hazards":{"type":"array","items":{"type":"object","properties":{"title":{"type":"string"},"description":{"type":"string"},"severity":{"type":"string","enum":["High","Medium","Low"]},"category":{"type":"string","enum":["Access and Egress","Confined Space","Compressed Gas Safety","Housekeeping and Site Organization","Slips, Trips, and Falls","Working at Heights and Fall Protection","Ladders and Stairways","Scaffolding","Excavation and Trenching","Electrical Safety","Lockout/Tagout and Hazardous Energy","Hand and Power Tools","Machinery Guarding","Heavy Equipment and Mobile Plant","Vehicle and Traffic Safety","Cranes, Hoisting, and Rigging","Aerial Lifts and Elevated Work Platforms","Material Handling and Storage","Manual Handling and Ergonomics","Personal Protective Equipment (PPE)","Hot Work—Welding, Cutting, and Grinding","Fire Prevention and Protection","Hazardous Chemicals and Hazard Communication","Dust, Silica, and Airborne Exposure","Respiratory Protection","Noise and Hearing Protection","Heat, Cold, and Weather Exposure","Falling Objects and Overhead Work","Struck-by and Caught-in/Between Hazards","Barricades, Signage, and Exclusion Zones","Demolition and Structural Stability","Concrete, Formwork, and Shoring","Steel Erection","Underground and Overhead Utilities","Working Near Water and Drowning Prevention","Emergency Preparedness and First Aid","Sanitation and Welfare Facilities","Public and Adjacent Property Protection","Work Planning, Permits, and Task Coordination"]}},"required":["title","description","severity","category"],"additionalProperties":false}}},"required":["hazards"],"additionalProperties":false}'
HAZARD_SCHEMA = json.loads(HAZARD_SCHEMA_TEXT)

_SCHEMA_SHA256 = "b916089b6d6be846fb83aa5839aaee834a17afea0f341d12da5c4638b4e039cc"
if hashlib.sha256(HAZARD_SCHEMA_TEXT.encode("utf-8")).hexdigest() != _SCHEMA_SHA256:
    raise RuntimeError("Client output schema was modified -- HAZARD_SCHEMA_TEXT must stay verbatim")

CATEGORIES = HAZARD_SCHEMA["properties"]["hazards"]["items"]["properties"]["category"]["enum"]

# Final output = client schema + a leading "message" field (code-generated
# from the hazard count). The model itself is still asked for, and validated
# against, the client schema above; "message" is added afterwards.
OUTPUT_SCHEMA = {
    **HAZARD_SCHEMA,
    "properties": {"message": {"type": "string"}, **HAZARD_SCHEMA["properties"]},
    "required": ["message", *HAZARD_SCHEMA["required"]],
}


def summary_message(count: int) -> str:
    if count == 0:
        return "I did not identify any construction hazards in this image"
    if count == 1:
        return "Here is 1 construction hazard I identified from the image"
    return f"Here are {count} construction hazards I identified from the image"
