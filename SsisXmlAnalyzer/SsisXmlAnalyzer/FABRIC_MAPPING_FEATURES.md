# SSIS → Fabric Mapping Features

This document describes the three new modules added to the SSIS XML Analyzer application for converting SSIS packages to Microsoft Fabric Pipelines.

## Overview

The application now includes three major modules:

- **MODULE 6**: SSIS → Fabric Mapping Engine (Backend)
- **MODULE 7**: Fabric Pipeline Generator (Backend)
- **MODULE 8**: Export & Deployment (Backend + Frontend)

## MODULE 6: SSIS → Fabric Mapping Engine

### Features

1. **Mapping Rules Framework**
   - Configuration-driven mapping rules (`mapping_rules.yaml`)
   - SSIS and Fabric activity taxonomy
   - Versioned mapping ruleset

2. **Component-Level Mapping Rules**
   - Execute SQL Task → SQL Script Activity
   - Data Flow Task → Copy Activity / Mapping Data Flow
   - Lookup Transform → Mapping Data Flow / Notebook
   - Flat File Source → ADLS Gen2 / OneLake
   - OLE DB Source → Fabric Warehouse / SQL Endpoint
   - ForEach Loop Container → ForEach Activity
   - Variables → Pipeline Parameters

3. **Classification & Diagnostics**
   - Support levels: ✅ Fully supported, ⚠ Partially supported, ❌ Unsupported
   - Confidence scoring (0-1)
   - Manual remediation list
   - Detailed warnings and explanations

### Files

- `api/mapping_rules.yaml` - Mapping rules configuration
- `api/fabric_mapping_engine.py` - Mapping engine implementation

### API Endpoints

- `POST /api/map-to-fabric` - Map SSIS package to Fabric execution model
- `POST /api/classify-activity` - Classify a single SSIS activity

## MODULE 7: Fabric Pipeline Generator

### Features

1. **Pipeline Skeleton Generation**
   - Pipeline metadata (name, description, version)
   - Global parameters from SSIS variables
   - Annotations for traceability

2. **Activity Generation**
   - Deterministic activity naming (`<Type>_<SSIS_TaskName>`)
   - Activity-specific properties mapping
   - User properties for SSIS traceability

3. **Dependency & Execution Order**
   - Converts SSIS precedence constraints to `dependsOn`
   - Preserves success/failure conditions
   - Validates DAG (no cycles)

4. **Validation & Linting**
   - JSON schema validation
   - Cycle detection in dependencies
   - Missing reference detection
   - Error/warning reporting

### Files

- `api/fabric_pipeline_generator.py` - Pipeline generator implementation

### API Endpoints

- `POST /api/generate-fabric-pipeline` - Generate Fabric Pipeline JSON
- `POST /api/validate-fabric-pipeline` - Validate pipeline JSON

## MODULE 8: Export & Deployment

### Frontend Features

1. **Fabric Mapping Tab**
   - Side-by-side SSIS → Fabric activity mapping view
   - Conversion summary with confidence scores
   - Manual remediation checklist
   - Pipeline preview

2. **Export Features**
   - Download Fabric Pipeline JSON
   - Pipeline preview with syntax highlighting
   - Conversion summary display

3. **Visual Indicators**
   - Support level badges (✅/⚠/❌)
   - Confidence scores
   - Warning indicators
   - Validation status

### Backend Features

1. **Export API**
   - `POST /api/export-fabric-pipeline` - Export pipeline JSON for download

2. **Deployment (Future)**
   - Optional Fabric REST API deployment
   - Workspace authentication
   - Pipeline creation via API

### Files

- `ui/client/src/pages/workflow-analyzer.tsx` - Updated with Fabric mapping UI
- `ui/shared/schema.ts` - Added Fabric mapping schemas

## Usage

### 1. Parse SSIS Package

Upload and parse your SSIS package as usual using the "Parsed View" tab.

### 2. Map to Fabric

1. Navigate to the "Fabric Mapping" tab
2. Click "Map to Fabric" button
3. Review the mapping results:
   - Check support levels for each activity
   - Review warnings and unsupported features
   - Review manual remediation list

### 3. Generate Pipeline

1. Click "Generate Pipeline" button
2. Review the conversion summary:
   - Overall confidence score
   - Support breakdown
   - Validation results

### 4. Export Pipeline

1. Click "Download JSON" button
2. The Fabric Pipeline JSON file will be downloaded
3. Deploy to Microsoft Fabric using your preferred method

## Mapping Details

### Execute SQL Task

- Maps to: SQL Script Activity
- Confidence: High (0.9)
- Supported: Full
- Unsupported: Result set bindings, stored procedure output
- Warnings: Dynamic SQL needs validation

### Data Flow Task

- Simple flows (single source → single destination):
  - Maps to: Copy Activity
  - Confidence: High (0.9)
  
- Complex flows (multiple transformations):
  - Maps to: Mapping Data Flow
  - Fallback: Notebook
  - Confidence: Medium (0.6)
  - Warnings: Error outputs, multiple outputs need manual mapping

### Lookup Transform

- Maps to: Mapping Data Flow (preferred) or Notebook
- Confidence: Medium (0.7) or Low (0.4) for no-cache mode
- Warnings: Performance risk for large datasets

### ForEach Loop Container

- Maps to: ForEach Activity
- Confidence: High (0.8)
- Supported: Partial
- Warnings: Nested loops may require refactoring

### Variables

- Package variables → Pipeline parameters
- Task variables → Activity parameters
- Confidence: High (0.9)
- Supported: Full

## Configuration

Mapping rules can be customized by editing `api/mapping_rules.yaml`. The configuration supports:

- Adding new activity mappings
- Adjusting confidence scores
- Modifying support levels
- Adding custom warnings

## Dependencies

New Python dependencies:
- `pyyaml>=6.0.1` - For YAML configuration parsing

The application gracefully handles missing optional dependencies (e.g., `pywin32` for Windows COM automation).

## Future Enhancements

### Planned Features

1. **Direct Fabric Deployment**
   - Authenticate to Fabric via Entra ID
   - Deploy pipeline via REST API
   - Workspace validation

2. **Advanced Mapping**
   - Expression conversion (SSIS → Fabric syntax)
   - Custom transformation rules
   - Template-based mapping

3. **Enhanced Validation**
   - Full Fabric schema validation
   - Pre-deployment checks
   - Compatibility reports

4. **Export Formats**
   - YAML export (alternative to JSON)
   - ARM template generation
   - Bicep template generation

## Troubleshooting

### Mapping Engine Not Available

If you see "Mapping engine not available":
1. Ensure `pyyaml` is installed: `pip install pyyaml>=6.0.1`
2. Check that `mapping_rules.yaml` exists in the `api/` directory
3. Restart the API server

### Pipeline Generation Fails

If pipeline generation fails:
1. Check the API logs for detailed error messages
2. Verify the SSIS package was parsed correctly
3. Review mapping trace for unsupported features
4. Check for circular dependencies in SSIS package

### Validation Errors

If pipeline validation reports errors:
1. Review the error list in the conversion summary
2. Check for missing references (linked services, datasets)
3. Verify activity dependencies don't form cycles
4. Ensure activity names follow Fabric naming constraints

## Support

For issues or questions:
1. Check the mapping trace diagnostics
2. Review the manual remediation list
3. Consult the warnings for each mapped activity
4. Refer to Microsoft Fabric documentation for specific activity requirements

