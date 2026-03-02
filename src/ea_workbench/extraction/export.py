"""ArchiMate 3.2 Open Exchange XML export — pure Python, no LLM.

Converts approved staging files to ArchiMate Open Exchange XML for Orbus/iServer import.
"""

import logging
import os
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET

import yaml

logger = logging.getLogger(__name__)

ARCHIMATE_NS = "http://www.opengroup.org/xsd/archimate/3.0/"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

# Mapping from kebab-case ArchiMate element types → PascalCase XML type attributes
_TYPE_MAP: dict[str, str] = {
    # Motivation layer
    "stakeholder": "Stakeholder",
    "driver": "Driver",
    "assessment": "Assessment",
    "goal": "Goal",
    "outcome": "Outcome",
    "principle": "Principle",
    "requirement": "Requirement",
    "constraint": "Constraint",
    "meaning": "Meaning",
    "value": "Value",
    # Strategy layer
    "resource": "Resource",
    "capability": "Capability",
    "value-stream": "ValueStream",
    "course-of-action": "CourseOfAction",
    # Business layer
    "business-actor": "BusinessActor",
    "business-role": "BusinessRole",
    "business-process": "BusinessProcess",
    "business-function": "BusinessFunction",
    "business-service": "BusinessService",
    "business-object": "BusinessObject",
    "business-event": "BusinessEvent",
    # Application layer
    "application-component": "ApplicationComponent",
    "application-service": "ApplicationService",
    "application-interface": "ApplicationInterface",
    "data-object": "DataObject",
    # Technology layer
    "technology-node": "Node",
    "technology-service": "TechnologyService",
    "technology-interface": "TechnologyInterface",
    "system-software": "SystemSoftware",
    "artifact": "Artifact",
}

# Mapping for relationship types
_REL_TYPE_MAP: dict[str, str] = {
    "composition-relationship": "CompositionRelationship",
    "aggregation-relationship": "AggregationRelationship",
    "assignment-relationship": "AssignmentRelationship",
    "realization-relationship": "RealizationRelationship",
    "serving-relationship": "ServingRelationship",
    "access-relationship": "AccessRelationship",
    "flow-relationship": "FlowRelationship",
    "triggering-relationship": "TriggeringRelationship",
    "association-relationship": "AssociationRelationship",
    "influence-relationship": "InfluenceRelationship",
}


def slug_id(name: str, prefix: str) -> str:
    """Generate a stable element identifier from a name (slugified, prefixed).

    The same name always produces the same ID — deterministic for round-trips.

    Args:
        name: Human-readable element name.
        prefix: Short prefix to prepend (e.g. 'id' or element type abbreviation).

    Returns:
        Stable identifier string, e.g. 'id-application-component-my-service'.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip())
    slug = slug.strip("-")
    return f"{prefix}-{slug}"


def _archimate_type(kebab_type: str) -> str:
    """Convert a kebab-case ArchiMate type to its PascalCase XML attribute value.

    Args:
        kebab_type: Kebab-case type string from staging file.

    Returns:
        PascalCase type string for XML export.
    """
    return _TYPE_MAP.get(kebab_type, "ApplicationComponent")


def _rel_archimate_type(kebab_type: str) -> str:
    """Convert a kebab-case relationship type to its PascalCase XML attribute.

    Args:
        kebab_type: Kebab-case relationship type string.

    Returns:
        PascalCase relationship type string.
    """
    return _REL_TYPE_MAP.get(kebab_type, "AssociationRelationship")


async def export_approved(
    workspace: str,
    confidence_threshold: float = 0.7,
    output_path: str | None = None,
) -> str:
    """Read approved staging files and build an ArchiMate 3.2 Open Exchange XML file.

    Reads `.staging/approved/*.yaml`, filters entities by confidence_threshold,
    and writes a valid ArchiMate XML file to `.staging/exports/`.

    Args:
        workspace: Path to the PFC workspace root.
        confidence_threshold: Minimum confidence to include an entity (default: 0.7).
        output_path: Override output file path. If None, auto-generates under .staging/exports/.

    Returns:
        Path of the written XML file.
    """
    approved_dir = Path(workspace) / ".staging" / "approved"
    exports_dir = Path(workspace) / ".staging" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    if output_path is None:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        output_path = str(exports_dir / f"archimate-export-{timestamp}.xml")

    # Collect entities and relationships from all approved files
    elements: list[dict] = []
    relationships: list[dict] = []

    if approved_dir.exists():
        for yaml_file in sorted(approved_dir.glob("*.yaml")):
            try:
                with yaml_file.open(encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
                if not isinstance(data, dict):
                    continue

                # Entity files
                for entity in data.get("entities", []):
                    if not isinstance(entity, dict):
                        continue
                    confidence = float(entity.get("confidence", 0.0))
                    if confidence >= confidence_threshold:
                        elements.append(entity)

                # Relationship files
                for rel in data.get("relationships", []):
                    if not isinstance(rel, dict):
                        continue
                    confidence = float(rel.get("confidence", 0.0))
                    if confidence >= confidence_threshold:
                        relationships.append(rel)

            except Exception as exc:
                logger.warning("Could not parse approved file %s: %s", yaml_file, exc)

    # Build XML
    ET.register_namespace("", ARCHIMATE_NS)
    ET.register_namespace("xsi", XSI_NS)

    model_el = ET.Element(
        f"{{{ARCHIMATE_NS}}}model",
        {
            f"{{{XSI_NS}}}schemaLocation": (
                "http://www.opengroup.org/xsd/archimate/3.0/ "
                "http://www.opengroup.org/xsd/archimate/3.1/archimate3_Diagram.xsd"
            ),
            "name": "Stanmore EA",
            "version": "3.2",
        },
    )

    elements_el = ET.SubElement(model_el, f"{{{ARCHIMATE_NS}}}elements")
    for entity in elements:
        name = entity.get("name", "")
        archimate_type = entity.get("archimate_type", "application-component")
        elem_id = slug_id(name, "id")
        xml_type = _archimate_type(archimate_type)

        elem_el = ET.SubElement(
            elements_el,
            f"{{{ARCHIMATE_NS}}}element",
            {
                "identifier": elem_id,
                f"{{{XSI_NS}}}type": xml_type,
                "name": name,
            },
        )
        description = entity.get("description")
        if description:
            doc_el = ET.SubElement(elem_el, f"{{{ARCHIMATE_NS}}}documentation")
            doc_el.text = description

    if relationships:
        rels_el = ET.SubElement(model_el, f"{{{ARCHIMATE_NS}}}relationships")
        for rel in relationships:
            source_name = rel.get("source_element", "")
            target_name = rel.get("target_element", "")
            rel_type = rel.get("archimate_type", "association-relationship")

            rel_el = ET.SubElement(
                rels_el,
                f"{{{ARCHIMATE_NS}}}relationship",
                {
                    f"{{{XSI_NS}}}type": _rel_archimate_type(rel_type),
                    "source": slug_id(source_name, "id"),
                    "target": slug_id(target_name, "id"),
                    "identifier": slug_id(f"{source_name}-{target_name}-{rel_type}", "rel"),
                },
            )
            description = rel.get("description")
            if description:
                doc_el = ET.SubElement(rel_el, f"{{{ARCHIMATE_NS}}}documentation")
                doc_el.text = description

    # Pretty-print XML
    rough_string = ET.tostring(model_el, encoding="unicode")
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ", encoding=None)
    # Remove the xml declaration line that minidom adds (we'll add our own)
    lines = pretty_xml.split("\n")
    if lines[0].startswith("<?xml"):
        lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    output_xml = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(output_xml)

    logger.info(
        "ArchiMate export written: %s (%d elements, %d relationships)",
        output_path,
        len(elements),
        len(relationships),
    )
    return output_path
