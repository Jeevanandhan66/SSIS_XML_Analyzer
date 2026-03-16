from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json
import os
import re

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def _safe_filename(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return "unknown"
    # Keep alnum, underscore, dash. Replace everything else with underscore.
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", s)
    return s.strip("_") or "unknown"


def _safe_identifier(s: str) -> str:
    # For names inside JSON/sql identifiers; keep wider but deterministic.
    s = (s or "").strip()
    if not s:
        return "unknown"
    return re.sub(r"\s+", "_", s)


def _map_ssis_type_to_spark(ssis_type: str, length: Optional[int] = None, precision: Optional[int] = None, scale: Optional[int] = None) -> str:
    t = (ssis_type or "").upper()
    if not t:
        return "STRING"

    if "INT" in t:
        if "BIG" in t:
            return "BIGINT"
        if "SMALL" in t:
            return "SMALLINT"
        return "INT"
    if "DECIMAL" in t or "NUMERIC" in t:
        p = precision if precision is not None else 38
        s = scale if scale is not None else 18
        return f"DECIMAL({p},{s})"
    if "MONEY" in t:
        return "DECIMAL(19,4)"
    if "FLOAT" in t or t in ("R4", "R8"):
        return "DOUBLE"
    if "BIT" in t or "BOOL" in t:
        return "BOOLEAN"
    if "DATE" in t or "TIME" in t:
        if "STAMP" in t or "DATETIME" in t:
            return "TIMESTAMP"
        return "DATE"
    if "BINARY" in t or "IMAGE" in t:
        return "BINARY"
    if "GUID" in t or "UNIQUEIDENTIFIER" in t:
        return "STRING"
    # Default: string (incl. DT_WSTR/DT_STR etc.)
    return "STRING"


@dataclass(frozen=True)
class TableMigrationSpec:
    source_schema: str
    source_table: str
    source_query: str
    target_catalog: str
    target_schema: str
    target_table: str
    load_type: str  # FULL | INCREMENTAL
    watermark_column: Optional[str]
    columns: List[Tuple[str, str]]  # (name, spark_type)


class MigrationArtifactGenerator:
    """
    Generates a deployable migration bundle (DLT pipeline JSON + job JSON + metadata SQL + UC SQL + deploy script)
    using already-parsed SSIS metadata (no DTSX parsing here).
    """

    def __init__(
        self,
        *,
        templates_dir: Optional[Path] = None,
        env_name: Optional[str] = None,
        repo_path: Optional[str] = None,
        development: Optional[bool] = None,
    ):
        base_dir = Path(__file__).parent
        self._templates_dir = templates_dir or (base_dir / "migration_templates")
        self._env_name = env_name or os.getenv("MIGRATION_ENV", "dev")
        self._repo_path = repo_path or os.getenv("DATABRICKS_REPO_PATH", "<repo_path>")
        self._development = True if development is None else bool(development)

        self._jinja = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=False,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def build_migration_package(self, parsed_data: Dict[str, Any], out_dir: Path) -> Path:
        """
        Materialize `migration_package/` under out_dir and return the path.
        """
        pkg_root = out_dir / "migration_package"
        pipelines_dir = pkg_root / "pipelines"
        jobs_dir = pkg_root / "jobs"
        metadata_dir = pkg_root / "metadata"
        unity_catalog_dir = pkg_root / "unity_catalog"
        cli_dir = pkg_root / "cli"

        for d in (pipelines_dir, jobs_dir, metadata_dir, unity_catalog_dir, cli_dir):
            d.mkdir(parents=True, exist_ok=True)

        package_name = (
            parsed_data.get("metadata", {}).get("packageName")
            or parsed_data.get("metadata", {}).get("objectName")
            or "SSISPackage"
        )

        table_specs = self._extract_table_specs(parsed_data)
        if not table_specs:
            # Still generate empty but deployable skeleton.
            (unity_catalog_dir / "create_tables.sql").write_text("-- No destination tables detected.\n", encoding="utf-8")
            (metadata_dir / "ControlTableIntegrated.sql").write_text("-- No source/destination pairs detected.\n", encoding="utf-8")
            (metadata_dir / "SourceDetails.sql").write_text("-- No source tables detected.\n", encoding="utf-8")
            deploy_sh = self._render("deploy.sh.j2", {})
            (cli_dir / "deploy.sh").write_text(deploy_sh, encoding="utf-8")
            return pkg_root

        # Render per-table artifacts
        for spec in table_specs:
            table_file_key = _safe_filename(spec.target_table)
            pipeline_name = self._pipeline_name(spec.target_catalog, spec.target_schema, spec.target_table)

            dlt_json = self._render(
                "dlt_pipeline.json.j2",
                {
                    "name": pipeline_name,
                    "catalog": spec.target_catalog,
                    "schema": spec.target_schema,
                    "adf_job_name": f"adf*{_safe_identifier(spec.target_table)}_load",
                    "repo_path": self._repo_path,
                    "development": self._development,
                },
            )
            (pipelines_dir / f"dlt_pipeline_{table_file_key}.json").write_text(dlt_json + "\n", encoding="utf-8")

            job_json = self._render(
                "job.json.j2",
                {
                    "name": f"job_dlt_{_safe_identifier(spec.target_table)}",
                    "pipeline_id": "<pipeline_id_placeholder>",
                },
            )
            (jobs_dir / f"job_{table_file_key}.json").write_text(job_json + "\n", encoding="utf-8")

        # Metadata SQL
        control_sql = self._render(
            "control_table_integrated.sql.j2",
            {
                "rows": [
                    {
                        "pipeline_name": self._pipeline_name(s.target_catalog, s.target_schema, s.target_table),
                        "source_schema": s.source_schema,
                        "source_table": s.source_table,
                        "target_catalog": s.target_catalog,
                        "target_schema": s.target_schema,
                        "target_table": s.target_table,
                        "load_type": s.load_type,
                        "watermark_column": s.watermark_column,
                    }
                    for s in table_specs
                ],
                "package_name": package_name,
            },
        )
        (metadata_dir / "ControlTableIntegrated.sql").write_text(control_sql + "\n", encoding="utf-8")

        source_sql = self._render(
            "source_details.sql.j2",
            {
                "rows": [
                    {
                        "source_schema": s.source_schema,
                        "source_table": s.source_table,
                        "source_query": s.source_query,
                    }
                    for s in table_specs
                ],
                "package_name": package_name,
            },
        )
        (metadata_dir / "SourceDetails.sql").write_text(source_sql + "\n", encoding="utf-8")

        # Unity Catalog SQL (unique catalogs/schemas/tables)
        create_tables_sql = self._render(
            "create_tables.sql.j2",
            {
                "tables": [
                    {
                        "catalog": s.target_catalog,
                        "schema": s.target_schema,
                        "table": s.target_table,
                        "columns": s.columns,
                    }
                    for s in table_specs
                ],
                "package_name": package_name,
            },
        )
        (unity_catalog_dir / "create_tables.sql").write_text(create_tables_sql + "\n", encoding="utf-8")

        # CLI script
        deploy_sh = self._render("deploy.sh.j2", {})
        (cli_dir / "deploy.sh").write_text(deploy_sh, encoding="utf-8")

        return pkg_root

    def _render(self, template_name: str, ctx: Dict[str, Any]) -> str:
        tpl = self._jinja.get_template(template_name)
        rendered = tpl.render(**ctx)
        # Pretty-print JSON templates if they are JSON
        if template_name.endswith(".json.j2"):
            try:
                obj = json.loads(rendered)
                return json.dumps(obj, indent=2, sort_keys=False)
            except Exception:
                return rendered
        return rendered

    def _pipeline_name(self, catalog: str, schema: str, table: str) -> str:
        # Deterministic naming rule: dlt_<env>*<catalog>*<schema>_<table>
        return f"dlt_{_safe_identifier(self._env_name)}*{_safe_identifier(catalog)}*{_safe_identifier(schema)}_{_safe_identifier(table)}"

    def _extract_table_specs(self, parsed_data: Dict[str, Any]) -> List[TableMigrationSpec]:
        """
        Build one migration spec per detected destination table in Data Flow Tasks.
        Uses destinationMetadata (targetDBName/targetSchemaName/targetTableName) and sourceMetadata when available.
        """
        specs: List[TableMigrationSpec] = []

        metadata = parsed_data.get("metadata") or {}
        _ = metadata  # reserved for future naming enhancements

        for activity in parsed_data.get("activities", []) or []:
            if not isinstance(activity, dict):
                continue
            if activity.get("type") != "Data Flow Task":
                continue
            components = activity.get("components") or []
            if not isinstance(components, list) or not components:
                continue

            source_comp = next((c for c in components if isinstance(c, dict) and c.get("componentType") == "Source" and c.get("sourceMetadata")), None)
            dest_comp = next((c for c in components if isinstance(c, dict) and c.get("destinationMetadata")), None)
            if not dest_comp:
                continue

            sm = (source_comp or {}).get("sourceMetadata") or {}
            dm = (dest_comp or {}).get("destinationMetadata") or {}

            source_schema = (sm.get("sourceSchemaName") or "") or ""
            source_table = (sm.get("sourceTableName") or "") or ""
            source_query = (sm.get("sourceQuery") or "") or ""

            target_catalog = (dm.get("targetDBName") or "") or ""
            target_schema = (dm.get("targetSchemaName") or "") or ""
            target_table = (dm.get("targetTableName") or "") or ""

            if not (target_catalog and target_schema and target_table):
                # Skip incomplete UC mapping
                continue

            copy_mode = (dm.get("copyMode") or "Full") or "Full"
            load_type = "INCREMENTAL" if str(copy_mode).lower() == "incremental" else "FULL"

            watermark_column = None
            if load_type == "INCREMENTAL" and isinstance(source_query, str) and source_query.strip():
                # Minimal heuristic (keep generator independent of api_server implementation)
                m = re.search(r"WHERE\s+\[?(\w+)\]?\s*[><=]", source_query, flags=re.IGNORECASE | re.DOTALL)
                if m:
                    watermark_column = m.group(1)

            # Infer columns from source outputColumns when possible
            columns: List[Tuple[str, str]] = []
            if source_comp and isinstance(source_comp, dict):
                out_cols = source_comp.get("outputColumns") or []
                if isinstance(out_cols, list) and out_cols:
                    for col in out_cols:
                        if not isinstance(col, dict):
                            continue
                        col_name = (col.get("name") or "").strip()
                        if not col_name:
                            continue
                        spark_type = _map_ssis_type_to_spark(
                            col.get("dataType") or "",
                            col.get("length"),
                            col.get("precision"),
                            col.get("scale"),
                        )
                        columns.append((col_name, spark_type))

            specs.append(
                TableMigrationSpec(
                    source_schema=source_schema,
                    source_table=source_table,
                    source_query=source_query,
                    target_catalog=target_catalog,
                    target_schema=target_schema,
                    target_table=target_table,
                    load_type=load_type,
                    watermark_column=watermark_column,
                    columns=columns,
                )
            )

        # De-duplicate by target catalog/schema/table (keep first)
        seen = set()
        unique: List[TableMigrationSpec] = []
        for s in specs:
            key = (s.target_catalog, s.target_schema, s.target_table)
            if key in seen:
                continue
            seen.add(key)
            unique.append(s)
        return unique

