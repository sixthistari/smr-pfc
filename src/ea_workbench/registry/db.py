"""Database connection management and schema initialisation for the element registry.

Option C schema: 21 purpose-built tables replacing the 4-table generic schema.
Old tables (elements, capabilities, element_capabilities) are retained for backward
compatibility. The relationships table is updated to the cross-table format.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiosqlite

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Legacy schema — retained for backward compatibility
# ---------------------------------------------------------------------------
_LEGACY_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS elements (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT DEFAULT 'proposed',
    description TEXT,
    source_spec TEXT,
    source_line INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    confidence REAL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS capabilities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    parent_id TEXT REFERENCES capabilities(id),
    level INTEGER NOT NULL,
    domain TEXT,
    maturity TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS element_capabilities (
    element_id TEXT REFERENCES elements(id),
    capability_id TEXT REFERENCES capabilities(id),
    relationship_type TEXT DEFAULT 'realizes',
    PRIMARY KEY (element_id, capability_id)
);

CREATE VIEW IF NOT EXISTS v_orphan_elements AS
SELECT e.* FROM elements e
LEFT JOIN element_capabilities ec ON e.id = ec.element_id
WHERE ec.capability_id IS NULL;

CREATE VIEW IF NOT EXISTS v_domain_summary AS
SELECT domain, archimate_type, status, COUNT(*) as count
FROM elements GROUP BY domain, archimate_type, status;
"""

# ---------------------------------------------------------------------------
# Option C schema — 21 purpose-built tables
# ---------------------------------------------------------------------------
_OPTION_C_SCHEMA_SQL = """
-- Cross-cutting: Domains
CREATE TABLE IF NOT EXISTS domains (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    priority INTEGER DEFAULT 0,
    maturity TEXT DEFAULT 'initial',
    autonomy_ceiling TEXT DEFAULT 'L5',
    track_default TEXT DEFAULT 'Track1',
    spec_coverage TEXT DEFAULT '',
    owner_role TEXT DEFAULT ''
);

-- Motivation layer
CREATE TABLE IF NOT EXISTS motivation (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL,
    domain_id TEXT,
    status TEXT DEFAULT 'draft',
    description TEXT DEFAULT '',
    confidence REAL DEFAULT 0.8,
    role TEXT DEFAULT '',
    influence_level TEXT DEFAULT '',
    driver_category TEXT DEFAULT '',
    evidence TEXT DEFAULT '',
    impact TEXT DEFAULT '',
    horizon TEXT DEFAULT '',
    requirement_type TEXT DEFAULT '',
    category TEXT DEFAULT '',
    threshold TEXT DEFAULT '',
    target TEXT DEFAULT '',
    acceptance_criteria TEXT DEFAULT '{}',
    solution_id TEXT DEFAULT '',
    engagement_ref TEXT DEFAULT ''
);

-- Strategy layer
CREATE TABLE IF NOT EXISTS strategy (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL,
    domain_id TEXT,
    status TEXT DEFAULT 'draft',
    description TEXT DEFAULT '',
    confidence REAL DEFAULT 0.8,
    parent_id TEXT REFERENCES strategy(id),
    level INTEGER DEFAULT 0,
    maturity TEXT DEFAULT '',
    stages TEXT DEFAULT '[]',
    value_proposition TEXT DEFAULT '',
    horizon TEXT DEFAULT '',
    traces_to_goal TEXT DEFAULT ''
);

-- Business Architecture layer
CREATE TABLE IF NOT EXISTS business_architecture (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL,
    domain_id TEXT,
    status TEXT DEFAULT 'draft',
    description TEXT DEFAULT '',
    confidence REAL DEFAULT 0.8,
    parent_id TEXT REFERENCES business_architecture(id),
    actor_type TEXT DEFAULT '',
    agent_augmented INTEGER DEFAULT 0,
    augmentation_level TEXT DEFAULT '',
    track TEXT DEFAULT '',
    governance_level TEXT DEFAULT '',
    trigger_event TEXT DEFAULT '',
    process_owner_id TEXT DEFAULT '',
    service_type TEXT DEFAULT '',
    has_authority_scoring INTEGER DEFAULT 0
);

-- Process steps (child of business_architecture process elements)
CREATE TABLE IF NOT EXISTS process_steps (
    id TEXT PRIMARY KEY,
    process_id TEXT NOT NULL REFERENCES business_architecture(id),
    sequence INTEGER NOT NULL,
    name TEXT NOT NULL,
    step_type TEXT DEFAULT 'human',
    role_id TEXT DEFAULT '',
    agent_id TEXT DEFAULT '',
    agent_autonomy TEXT DEFAULT '',
    description TEXT DEFAULT '',
    input_objects TEXT DEFAULT '[]',
    output_objects TEXT DEFAULT '[]',
    approval_required INTEGER DEFAULT 0,
    track_crossing INTEGER DEFAULT 0
);

-- Solution Architecture layer
CREATE TABLE IF NOT EXISTS solution_architecture (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL,
    domain_id TEXT,
    status TEXT DEFAULT 'draft',
    description TEXT DEFAULT '',
    confidence REAL DEFAULT 0.8,
    version TEXT DEFAULT '',
    deployment_status TEXT DEFAULT 'planned',
    is_agent INTEGER DEFAULT 0,
    default_autonomy TEXT DEFAULT '',
    default_track TEXT DEFAULT '',
    knowledge_base_ref TEXT DEFAULT '',
    promoted_to_actor INTEGER DEFAULT 0,
    is_knowledge_store INTEGER DEFAULT 0,
    store_type TEXT DEFAULT '',
    config_path TEXT DEFAULT '',
    fallback_ref TEXT DEFAULT '',
    ingestion_pipeline_ref TEXT DEFAULT '',
    platform TEXT DEFAULT '',
    environment TEXT DEFAULT '',
    provider TEXT DEFAULT '',
    region TEXT DEFAULT '',
    ga_status TEXT DEFAULT 'ga'
);

-- Implementation & Migration layer
CREATE TABLE IF NOT EXISTS implementation (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    archimate_type TEXT NOT NULL,
    domain_id TEXT,
    status TEXT DEFAULT 'draft',
    description TEXT DEFAULT '',
    solution_id TEXT DEFAULT '',
    phase TEXT DEFAULT '',
    target_date TEXT DEFAULT '',
    plateau_description TEXT DEFAULT ''
);

-- Cross-table relationships with metamodel validation support
CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    source_table TEXT DEFAULT '',
    source_id TEXT NOT NULL,
    target_table TEXT DEFAULT '',
    target_id TEXT NOT NULL,
    archimate_type TEXT NOT NULL,
    description TEXT DEFAULT '',
    evidence TEXT DEFAULT '',
    confidence REAL DEFAULT 1.0,
    created_by TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ArchiMate metamodel: permitted relationship pairs (seeded at init)
CREATE TABLE IF NOT EXISTS valid_relationships (
    source_archimate_type TEXT NOT NULL,
    target_archimate_type TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    PRIMARY KEY (source_archimate_type, target_archimate_type, relationship_type)
);

-- Portfolio
CREATE TABLE IF NOT EXISTS solutions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    domain_id TEXT,
    solution_type TEXT DEFAULT 'agent-service',
    status TEXT DEFAULT 'proposed',
    portfolio_product TEXT DEFAULT '',
    business_service_id TEXT DEFAULT '',
    owner TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS solution_components (
    solution_id TEXT NOT NULL REFERENCES solutions(id),
    element_id TEXT NOT NULL REFERENCES solution_architecture(id),
    role_in_solution TEXT DEFAULT '',
    PRIMARY KEY (solution_id, element_id)
);

CREATE TABLE IF NOT EXISTS solution_diagrams (
    id TEXT PRIMARY KEY,
    solution_id TEXT NOT NULL REFERENCES solutions(id),
    diagram_type TEXT DEFAULT '',
    title TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    notation TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS deployment_targets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    environment TEXT DEFAULT '',
    region TEXT DEFAULT '',
    subscription TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS solution_deployments (
    solution_id TEXT NOT NULL REFERENCES solutions(id),
    target_id TEXT NOT NULL REFERENCES deployment_targets(id),
    iac_path TEXT DEFAULT '',
    status TEXT DEFAULT 'planned',
    PRIMARY KEY (solution_id, target_id)
);

-- EA Practice artefacts index
CREATE TABLE IF NOT EXISTS practice_artefacts (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT DEFAULT '',
    archimate_type TEXT DEFAULT '',
    status TEXT DEFAULT 'draft',
    domain_id TEXT,
    file_path TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    supersedes TEXT DEFAULT ''
);

-- Stakeholder engagements
CREATE TABLE IF NOT EXISTS engagements (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    date TEXT DEFAULT '',
    type TEXT DEFAULT '',
    context TEXT DEFAULT '',
    session_id TEXT DEFAULT '',
    conversation_summary TEXT DEFAULT ''
);

-- Governance controls
CREATE TABLE IF NOT EXISTS governance_controls (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    target_table TEXT DEFAULT '',
    target_id TEXT DEFAULT '',
    standard_id TEXT DEFAULT '',
    constraint_id TEXT DEFAULT '',
    enforcement_type TEXT DEFAULT 'manual-audit',
    enforcement_mechanism TEXT DEFAULT '',
    assessment_frequency TEXT DEFAULT 'monthly',
    last_assessed TEXT DEFAULT '',
    compliance_status TEXT DEFAULT 'not-assessed',
    scope TEXT DEFAULT 'enterprise',
    domain_id TEXT
);

-- Staging items (Option C provenance)
CREATE TABLE IF NOT EXISTS staging_items (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_data TEXT DEFAULT '{}',
    target_table TEXT DEFAULT '',
    source_type TEXT DEFAULT 'chat',
    source_id TEXT DEFAULT '',
    confidence REAL DEFAULT 0.8,
    status TEXT DEFAULT 'staged'
);

-- Quality evaluations
CREATE TABLE IF NOT EXISTS quality_evaluations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    target_table TEXT DEFAULT '',
    target_id TEXT DEFAULT '',
    domain_id TEXT,
    evaluation_type TEXT DEFAULT '',
    phase TEXT DEFAULT '',
    baseline_ref TEXT DEFAULT '',
    methodology TEXT DEFAULT '',
    metrics TEXT DEFAULT '{}',
    pass_fail TEXT DEFAULT 'inconclusive',
    summary TEXT DEFAULT '',
    decision_ref TEXT DEFAULT '',
    evaluated_by TEXT DEFAULT '',
    evaluated_at TEXT DEFAULT ''
);


-- Agent run provenance
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    status TEXT DEFAULT 'running',
    entities_extracted INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    model_used TEXT DEFAULT ''
);

-- Chat session records
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at TEXT DEFAULT '',
    ended_at TEXT DEFAULT '',
    entities_staged INTEGER DEFAULT 0,
    items_approved INTEGER DEFAULT 0,
    items_rejected INTEGER DEFAULT 0,
    summary TEXT DEFAULT '',
    topics TEXT DEFAULT '[]',
    architectural_themes TEXT DEFAULT '[]',
    decisions_made TEXT DEFAULT '[]',
    decisions_deferred TEXT DEFAULT '[]',
    elements_discussed TEXT DEFAULT '[]',
    domain_ids TEXT DEFAULT '[]',
    engagement_ref TEXT DEFAULT '',
    semantic_summary TEXT DEFAULT ''
);
"""

# ---------------------------------------------------------------------------
# Element registry view — unions all 5 concern tables + legacy elements
# ---------------------------------------------------------------------------
_REGISTRY_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS element_registry_view AS
SELECT id, name, archimate_type, domain_id AS domain, status, description, 'motivation' AS source_table
FROM motivation
UNION ALL
SELECT id, name, archimate_type, domain_id AS domain, status, description, 'strategy' AS source_table
FROM strategy
UNION ALL
SELECT id, name, archimate_type, domain_id AS domain, status, description, 'business_architecture' AS source_table
FROM business_architecture
UNION ALL
SELECT id, name, archimate_type, domain_id AS domain, status, description, 'solution_architecture' AS source_table
FROM solution_architecture
UNION ALL
SELECT id, name, archimate_type, domain_id AS domain, status, description, 'implementation' AS source_table
FROM implementation
UNION ALL
SELECT id, name, archimate_type, domain, status, description, 'elements' AS source_table
FROM elements;
"""

# ---------------------------------------------------------------------------
# Seed data: valid ArchiMate 3.2 relationship pairs (Appendix B)
# Covers the most common cross-layer permitted relationships.
# ---------------------------------------------------------------------------
_VALID_RELATIONSHIPS_SEED = [
    # Composition — structural
    ("capability", "capability", "composition"),
    ("business-actor", "business-role", "composition"),
    ("application-component", "application-component", "composition"),
    # Aggregation — structural
    ("capability", "capability", "aggregation"),
    ("application-component", "application-component", "aggregation"),
    # Assignment — role/actor to behaviour
    ("business-actor", "business-role", "assignment"),
    ("business-role", "business-process", "assignment"),
    ("business-role", "business-function", "assignment"),
    ("application-component", "application-service", "assignment"),
    ("application-component", "application-function", "assignment"),
    # Realisation — abstraction layers
    ("business-process", "business-service", "realisation"),
    ("business-function", "business-service", "realisation"),
    ("application-component", "application-service", "realisation"),
    ("capability", "goal", "realisation"),
    ("requirement", "goal", "realisation"),
    ("course-of-action", "capability", "realisation"),
    # Serving — cross-layer support
    ("application-service", "business-process", "serving"),
    ("application-service", "business-function", "serving"),
    ("application-service", "business-role", "serving"),
    ("technology-service", "application-component", "serving"),
    ("technology-service", "application-service", "serving"),
    # Access — data access
    ("business-process", "business-object", "access"),
    ("business-function", "business-object", "access"),
    ("application-function", "data-object", "access"),
    ("application-component", "data-object", "access"),
    # Influence — motivation
    ("driver", "assessment", "influence"),
    ("assessment", "goal", "influence"),
    ("stakeholder", "goal", "influence"),
    ("stakeholder", "driver", "influence"),
    # Triggering — process flow
    ("business-process", "business-process", "triggering"),
    ("business-event", "business-process", "triggering"),
    ("application-event", "application-process", "triggering"),
    # Flow — information/material
    ("business-process", "business-process", "flow"),
    ("application-component", "application-component", "flow"),
    # Specialisation — taxonomy
    ("business-role", "business-role", "specialisation"),
    ("capability", "capability", "specialisation"),
    ("business-service", "business-service", "specialisation"),
    # Association — generic
    ("stakeholder", "requirement", "association"),
    ("goal", "requirement", "association"),
    ("assessment", "driver", "association"),
    ("work-package", "deliverable", "association"),
    ("work-package", "plateau", "association"),
    ("gap", "plateau", "association"),
    ("solution", "application-component", "association"),
]


@asynccontextmanager
async def get_connection(db_path: str) -> AsyncIterator[aiosqlite.Connection]:
    """Open an aiosqlite connection with row_factory set to Row.

    Args:
        db_path: Path to the SQLite database file, or ':memory:' for in-memory.

    Yields:
        An open aiosqlite connection.
    """
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        yield conn


async def initialise_schema(db_path: str) -> None:
    """Create all tables and views if they do not already exist.

    Creates legacy tables (for backward compatibility), all 21 Option C tables,
    the element_registry_view, and seeds the valid_relationships table.

    Args:
        db_path: Path to the SQLite database file, or ':memory:'.
    """
    async with get_connection(db_path) as conn:
        # Legacy tables (backward compat)
        await conn.executescript(_LEGACY_SCHEMA_SQL)
        # Option C tables
        await conn.executescript(_OPTION_C_SCHEMA_SQL)
        # Registry view
        await conn.executescript(_REGISTRY_VIEW_SQL)
        # Seed valid_relationships (idempotent via INSERT OR IGNORE)
        await conn.executemany(
            "INSERT OR IGNORE INTO valid_relationships "
            "(source_archimate_type, target_archimate_type, relationship_type) VALUES (?, ?, ?)",
            _VALID_RELATIONSHIPS_SEED,
        )
        await conn.commit()
    logger.info("Element registry schema (Option C) initialised at %s", db_path)
