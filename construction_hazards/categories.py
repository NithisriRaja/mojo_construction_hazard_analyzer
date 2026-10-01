"""
Category guide used by the verify prompt (prompts.py).

Every key must match a category in the client schema exactly (checked at
import). The definitions and tie-break rules are general construction-safety
guidance -- they must describe categories, never specific sample images, so
they hold for any photo a user uploads.
"""
from construction_hazards.schema import CATEGORIES

CATEGORY_GUIDE = {
    "Access and Egress": "Safe ways into, out of and through the work area: blocked exits, doorways or walkways; no ladder, ramp or stair out of an excavation or up to a work level.",
    "Confined Space": "Work inside tanks, vaults, manholes, pits, ducts or other enclosed spaces with restricted entry and exit.",
    "Compressed Gas Safety": "Gas cylinders: not secured upright (no chain, strap, rack or cylinder cart), stored without a valve cap, damaged regulators or hoses, poor cylinder storage.",
    "Housekeeping and Site Organization": "General clutter, scrap, waste, debris and poorly organised materials or tools in work areas.",
    "Slips, Trips, and Falls": "Same-level slips and trips: cords, hoses, straps, loose items, uneven, wet or slippery surfaces. Not falls to a lower level.",
    "Working at Heights and Fall Protection": "Falls to a lower level from unprotected or inadequately protected edges, roofs, floor openings, holes, platforms, truck beds or other elevated surfaces.",
    "Ladders and Stairways": "Ladder and stair use and condition: standing on the top step or cap, overreaching, poor footing, damaged ladders, damaged or missing stair treads or handrails.",
    "Scaffolding": "Any scaffold hazard: missing scaffold guardrails or toeboards, unstable base, unlocked or unsupported casters, improper access, overloading.",
    "Excavation and Trenching": "Trenches and excavations: no shoring, shielding or sloping; spoil piles, materials or equipment loads at the edge; unstable or undermined walls; water in the excavation.",
    "Electrical Safety": "Exposed electrical parts, open energized panels or enclosures (especially with someone working in them), damaged cords or plugs, improper temporary power, blocked panel clearance.",
    "Lockout/Tagout and Hazardous Energy": "Servicing or maintaining machinery, piping or systems with stored energy (mechanical, hydraulic, pneumatic, pressure, thermal) where no isolation, lock or tag is visible.",
    "Hand and Power Tools": "Unsafe use or condition of hand or power tools: missing guards on grinders or saws, damaged tools or cords on tools, wrong tool for the task.",
    "Machinery Guarding": "Stationary machinery with exposed moving parts (belts, gears, shafts, blades, rollers) lacking guards.",
    "Heavy Equipment and Mobile Plant": "Excavators, loaders, skid steers, forklifts, telehandlers, concrete mixers and similar plant: operating near people on foot, near edges, blind spots, unsafe operation.",
    "Vehicle and Traffic Safety": "Road vehicles and site traffic routes: trucks and vans moving or reversing, traffic control, pedestrian routes on roads or yards with vehicle traffic.",
    "Cranes, Hoisting, and Rigging": "Crane and hoist lifts: people under or near a suspended load, damaged or unprotected slings, improper rigging, uncontrolled loads.",
    "Aerial Lifts and Elevated Work Platforms": "Boom lifts, scissor lifts and other MEWPs: occupants without fall restraint in boom lifts, climbing or standing on rails, operating near edges, holes or overhead hazards.",
    "Material Handling and Storage": "Stored or stacked materials that could topple, roll, slide or collapse; unstable stacks; unsecured loads; improper storage locations.",
    "Manual Handling and Ergonomics": "Lifting, carrying or pushing by hand: heavy or awkward loads, loads blocking the carrier's vision, awkward or repetitive postures.",
    "Personal Protective Equipment (PPE)": "Clearly visible absence or misuse of PPE needed for the task (hard hat, high-visibility clothing, eye or face protection, gloves, footwear).",
    "Hot Work—Welding, Cutting, and Grinding": "Hazards of the welding, cutting or grinding process itself: no welding screens or curtains, sparks and arc flash reaching others, no fire watch.",
    "Fire Prevention and Protection": "Combustible or flammable materials near ignition sources or hot work, missing or blocked fire extinguishers, improper flammable storage.",
    "Hazardous Chemicals and Hazard Communication": "Chemical containers, unlabeled containers, spills or leaks, improper chemical storage or handling.",
    "Dust, Silica, and Airborne Exposure": "Visible dust, fumes or airborne particles, e.g. cutting or grinding concrete or masonry without dust control.",
    "Respiratory Protection": "Tasks producing visible airborne contaminants where the workers exposed clearly have no respirator.",
    "Noise and Hearing Protection": "Clearly high-noise tasks (jackhammers, concrete saws, impact tools) where workers clearly have no hearing protection.",
    "Heat, Cold, and Weather Exposure": "Visible weather hazards: ice, snow, heavy rain, standing water from weather, extreme sun or heat exposure, high wind.",
    "Falling Objects and Overhead Work": "Objects that could fall onto people: unsecured tools or materials at height or near edges, platforms without toeboards, overhead work with people below and no exclusion zone.",
    "Struck-by and Caught-in/Between Hazards": "Being struck by moving objects or caught between objects, when no more specific category applies (e.g. materials being moved or lowered by hand toward people, pinch points).",
    "Barricades, Signage, and Exclusion Zones": "Missing or inadequate barricades, warning signs, tape or exclusion zones around a hazardous area such as a crane lift zone, opening or work area.",
    "Demolition and Structural Stability": "Partially demolished or unstable structures, unbraced walls, columns or members, risk of structural collapse.",
    "Concrete, Formwork, and Shoring": "Concrete placement, formwork, shoring and rebar: uncapped protruding rebar (impalement), unstable formwork or shoring, concrete pump or chute hazards.",
    "Steel Erection": "Structural steel erection activities: workers connecting or walking on steel members, decking, unsecured steel members during erection.",
    "Underground and Overhead Utilities": "Overhead power lines near equipment or work, exposed or damaged buried utilities.",
    "Working Near Water and Drowning Prevention": "Work over or next to water without barriers, life jackets or rescue equipment.",
    "Emergency Preparedness and First Aid": "Missing or blocked emergency equipment or routes: eyewash stations, first aid, emergency exits.",
    "Sanitation and Welfare Facilities": "Problems with toilets, hand washing, drinking water or welfare facilities.",
    "Public and Adjacent Property Protection": "Hazards to the public or neighbouring property: open site boundaries, debris or work extending into public areas.",
    "Work Planning, Permits, and Task Coordination": "Conflicting tasks in the same space, e.g. different trades working directly above or below each other.",
}

# When two categories seem to fit, these rules pick exactly one. They are
# what makes the same hazard get the same category on every image.
TIE_BREAK_RULES = [
    "Choose the category of the specific equipment or activity causing the hazard, not the general consequence. Scaffolding, Ladders and Stairways, Aerial Lifts and Elevated Work Platforms, Excavation and Trenching, Cranes, Hoisting, and Rigging, Steel Erection and Concrete, Formwork, and Shoring take priority over Working at Heights and Fall Protection, Falling Objects and Overhead Work, Struck-by and Caught-in/Between Hazards, and Slips, Trips, and Falls.",
    "A possible fall to a lower level (edges, roofs, floor openings, holes, truck beds) is Working at Heights and Fall Protection, unless it is from a scaffold, ladder or aerial lift. A trip on the same level is Slips, Trips, and Falls.",
    "Hazards from an excavation itself (cave-in, unshored walls, spoil piles or loads at the edge) are Excavation and Trenching. No way out of an excavation is Access and Egress.",
    "Anything about a gas cylinder is Compressed Gas Safety.",
    "Combustible materials near hot work are Fire Prevention and Protection; hazards of the welding or cutting process itself are Hot Work—Welding, Cutting, and Grinding.",
    "Forklifts and construction plant near people are Heavy Equipment and Mobile Plant; road trucks and traffic routes are Vehicle and Traffic Safety.",
    "Someone under or near a suspended load is Cranes, Hoisting, and Rigging; a lift area with no barricade or exclusion zone is Barricades, Signage, and Exclusion Zones.",
    "Overhead work (other than crane lifts) with people below and no exclusion zone is Falling Objects and Overhead Work.",
    "Open electrical panels or exposed electrical parts are Electrical Safety.",
    "Cords, hoses and straps on the floor are Slips, Trips, and Falls; general clutter and debris are Housekeeping and Site Organization.",
]

SEVERITY_RUBRIC = [
    'High: could realistically cause death or permanent injury -- falls to a lower level, trench cave-in, people under suspended loads, exposed energized electrical parts, people close to operating heavy equipment, impalement, unsecured gas cylinders, combustibles exposed to hot work.',
    'Medium: could cause an injury needing treatment -- ladder misuse, trips over cords or hoses, falling hand tools, unstable stacked materials, manual handling, missing welding screens.',
    'Low: minor or housekeeping-level risk -- scattered debris or clutter with little injury potential.',
    'Judge by the realistic outcome of what is visible, not the worst imaginable one. A hazard next to an opening or edge can be raised one level.',
]

if list(CATEGORY_GUIDE) != CATEGORIES:
    raise RuntimeError("CATEGORY_GUIDE must match the schema categories exactly, in order")


def category_guide_text() -> str:
    return "\n".join(f"{i}. {name} -- {desc}" for i, (name, desc) in enumerate(CATEGORY_GUIDE.items(), 1))


def tie_break_text() -> str:
    return "\n".join(f"- {rule}" for rule in TIE_BREAK_RULES)


def severity_text() -> str:
    return "\n".join(f"- {line}" for line in SEVERITY_RUBRIC)
