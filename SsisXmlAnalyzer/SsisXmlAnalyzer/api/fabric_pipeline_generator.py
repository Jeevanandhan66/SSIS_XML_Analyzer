"""
MODULE 7: Fabric Pipeline Generator (Backend)
Transforms the mapped execution model into valid, deployable Fabric Pipeline JSON.
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from fabric_mapping_engine import MappingEngine


class FabricPipelineGenerator:
    """Generates Fabric Pipeline JSON from SSIS mapped model."""
    
    def __init__(self, mapping_engine: Optional[MappingEngine] = None):
        """Initialize pipeline generator."""
        self.mapping_engine = mapping_engine or MappingEngine()
        self.activity_name_cache: Set[str] = set()
        
    def generate_pipeline(self, package_data: Dict[str, Any], mapping_trace: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete Fabric Pipeline JSON.
        
        Args:
            package_data: Original SSIS package data
            mapping_trace: Mapping trace from mapping engine
            
        Returns:
            Complete Fabric Pipeline JSON structure
        """
        # Generate pipeline metadata
        pipeline_metadata = self._generate_pipeline_metadata(package_data)
        
        # Generate global parameters from variables
        global_parameters = self._generate_global_parameters(mapping_trace.get('variablesMapping', {}))
        
        # Generate activities
        activities = []
        activity_dependencies = {}
        
        mapped_activities = mapping_trace.get('mappedActivities', [])
        for mapped_activity in mapped_activities:
            fabric_activity = self._generate_activity(mapped_activity)
            if fabric_activity:
                activities.append(fabric_activity)
                
                # Build dependency map
                ssis_activity = mapped_activity.get('ssis', {})
                activity_dependencies[ssis_activity.get('id')] = self._extract_dependencies(
                    mapped_activity, package_data
                )
        
        # Resolve dependencies and set dependsOn
        self._resolve_dependencies(activities, activity_dependencies, mapped_activities)
        
        # Build Fabric Pipeline JSON (simplified structure compared to ADF)
        pipeline = {
            'name': pipeline_metadata['name'],
            'type': 'Microsoft.Fabric/pipelines',  # Fabric type, not ADF
            'properties': {
                'description': pipeline_metadata.get('description', ''),
                'activities': activities,
                'parameters': global_parameters,
                'concurrency': 1,
                'annotations': [
                    f"Converted from SSIS: {package_data.get('metadata', {}).get('objectName', 'Unknown')}",
                    f"Conversion Date: {datetime.now().isoformat()}"
                ],
                'folder': {
                    'name': 'SSIS_Converted'
                }
            }
        }
        
        return pipeline
    
    def _generate_pipeline_metadata(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate pipeline metadata from package metadata."""
        metadata = package_data.get('metadata', {})
        
        package_name = metadata.get('objectName', metadata.get('name', 'SSISPackage'))
        # Sanitize name for Fabric
        pipeline_name = self._sanitize_name(package_name, prefix='Pipeline')
        
        return {
            'name': pipeline_name,
            'description': metadata.get('description', f"Converted from SSIS package: {package_name}"),
            'version': metadata.get('versionBuild', '1.0.0')
        }
    
    def _generate_global_parameters(self, variables_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Generate global pipeline parameters from SSIS variables."""
        parameters = {}
        
        mapping = variables_mapping.get('mapping', {})
        var_parameters = mapping.get('parameters', [])
        
        for param in var_parameters:
            param_name = param.get('name', f"param_{uuid.uuid4().hex[:8]}")
            param_name = self._sanitize_name(param_name, prefix='Param')
            
            parameters[param_name] = {
                'type': param.get('type', 'String'),
                'defaultValue': param.get('defaultValue')
            }
            
            # Remove None values
            if parameters[param_name]['defaultValue'] is None:
                del parameters[param_name]['defaultValue']
        
        return parameters
    
    def _generate_activity(self, mapped_activity: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate a Fabric activity from mapped activity."""
        ssis = mapped_activity.get('ssis', {})
        fabric = mapped_activity.get('fabric', {})
        classification = mapped_activity.get('classification', {})
        
        activity_type = fabric.get('activityType')
        if not activity_type:
            return None
        
        # Generate activity name
        activity_name = self._generate_activity_name(
            activity_type,
            ssis.get('name', 'Activity'),
            ssis.get('type', '')
        )
        
        # Base activity structure
        activity = {
            'name': activity_name,
            'type': self._map_activity_type_to_fabric(activity_type),
            'dependsOn': [],  # Will be populated later
            'policy': {
                'timeout': '7.00:00:00',
                'retry': 0,
                'retryIntervalInSeconds': 30
            }
        }
        
        # Generate activity-specific properties (Fabric format)
        type_mapping = mapped_activity.get('mappingResult', {}).get('mapping', {})
        
        if activity_type == 'SQLScript':
            activity['typeProperties'] = self._generate_sql_script_properties(ssis, type_mapping)
        elif activity_type == 'Copy':
            activity['typeProperties'] = self._generate_copy_properties(mapped_activity, type_mapping)
            # Add inputs/outputs for Copy activity (Fabric requires dataset references)
            copy_props = type_mapping
            source = copy_props.get('source', {})
            destination = copy_props.get('destination', {})
            
            source_dataset_name = self._generate_dataset_name(
                ssis.get('name', 'CopyActivity'), 'Source', source
            )
            destination_dataset_name = self._generate_dataset_name(
                ssis.get('name', 'CopyActivity'), 'Sink', destination
            )
            
            activity['inputs'] = [
                {
                    'referenceName': source_dataset_name,
                    'type': 'DatasetReference'
                }
            ]
            activity['outputs'] = [
                {
                    'referenceName': destination_dataset_name,
                    'type': 'DatasetReference'
                }
            ]
        elif activity_type == 'ForEach':
            activity['typeProperties'] = self._generate_foreach_properties(mapped_activity, type_mapping)
        elif activity_type == 'MappingDataFlow':
            activity['typeProperties'] = self._generate_mapping_dataflow_properties(mapped_activity, type_mapping)
        elif activity_type == 'Notebook':
            activity['typeProperties'] = self._generate_notebook_properties(mapped_activity, type_mapping)
        else:
            # Generic activity - add typeProperties if present
            if type_mapping:
                activity['typeProperties'] = type_mapping
        
        # Add user properties for traceability
        activity['userProperties'] = [
            {
                'name': 'ssisActivityId',
                'value': ssis.get('id', '')
            },
            {
                'name': 'ssisActivityName',
                'value': ssis.get('name', '')
            },
            {
                'name': 'ssisActivityType',
                'value': ssis.get('type', '')
            },
            {
                'name': 'conversionConfidence',
                'value': str(classification.get('confidenceScore', 0.0))
            }
        ]
        
        return activity
    
    def _generate_sql_script_properties(self, ssis_activity: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Generate properties for SQL Script activity (Fabric format)."""
        sql_props = ssis_activity.get('sqlTaskProperties', {})
        
        # Extract SQL statement from multiple possible sources
        sql_statement = (
            mapping.get('sqlStatement') or 
            sql_props.get('sqlStatementSource') or 
            ssis_activity.get('sqlCommand') or 
            ''
        )
        
        # Decode HTML entities if present (e.g., &gt; -> >, &#xA; -> newline)
        if sql_statement:
            import html
            sql_statement = html.unescape(sql_statement)
        
        # Check if SQL statement contains expressions (e.g., @variable, @pipeline(), @{...})
        has_expressions = False
        if sql_statement:
            import re
            # Check for SSIS expression patterns: @variable, @[System::Variable], pipeline parameters
            expression_patterns = [
                r'@[A-Za-z_][A-Za-z0-9_]*',  # @variable
                r'@\[.*?\]',  # @[System::Variable]
                r'@\{.*?\}',  # @{expression}
                r'@pipeline\(\)',  # pipeline parameters
                r'@activity\(\)'  # activity parameters
            ]
            for pattern in expression_patterns:
                if re.search(pattern, sql_statement):
                    has_expressions = True
                    break
        
        # Check if there are parameter bindings that would require expressions
        has_parameters = bool(mapping.get('parameters'))
        use_expression = has_expressions or has_parameters
        
        # If SQL is empty, provide a warning placeholder (will need manual intervention)
        if not sql_statement or not sql_statement.strip():
            sql_statement = '-- ERROR: No SQL statement found in SSIS task. Please manually add SQL statement.'
            use_expression = False  # Don't use Expression for placeholder
        
        # Fabric SqlScript activity uses connection instead of scriptLinkedService
        connection_name = self._generate_linked_service_name(
            mapping.get('connectionManager') or ssis_activity.get('connectionId', '')
        )
        
        # Return just typeProperties (type is already set in activity)
        # Fabric SqlScript expects script as object with value and type when using expressions,
        # or can accept just a string for static SQL. Using object format for consistency.
        if use_expression:
            # When there are expressions, use Expression type
            script_prop = {
                'value': sql_statement,
                'type': 'Expression'
            }
        else:
            # For static SQL, use Expression type but with the literal SQL value
            # Note: Some Fabric versions may accept just a string, but object format is more reliable
            script_prop = {
                'value': sql_statement,
                'type': 'Expression'  # Even static SQL uses Expression type in Fabric
            }
        
        return {
            'script': script_prop,
            'connection': {
                'connectionName': connection_name
            },
            'parameters': self._generate_sql_parameters(mapping.get('parameters', []))
        }
    
    def _generate_copy_properties(self, mapped_activity: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Generate properties for Copy activity (Fabric format)."""
        source = mapping.get('source', {})
        destination = mapping.get('destination', {})
        
        # Generate dataset names for source and destination
        ssis_activity = mapped_activity.get('ssis', {})
        activity_name = ssis_activity.get('name', 'CopyActivity')
        
        source_dataset_name = self._generate_dataset_name(activity_name, 'Source', source)
        destination_dataset_name = self._generate_dataset_name(activity_name, 'Sink', destination)
        
        # Fabric Copy activity requires dataset references
        # Return just typeProperties (type is already set in activity)
        source_type = self._map_source_type(source.get('targetActivityType', 'DelimitedText'))
        sink_type = self._map_destination_type(destination.get('targetActivityType', 'SqlSink'))
        
        return {
            'source': {
                'type': source_type,
                'storeSettings': self._generate_source_store_settings(source, source_type),
                'formatSettings': self._generate_format_settings(source, source_type)
            },
            'sink': {
                'type': sink_type,
                'storeSettings': self._generate_sink_store_settings(destination, sink_type),
                'formatSettings': self._generate_format_settings(destination, sink_type, is_sink=True)
            },
            'enableStaging': False,
            'parallelCopies': 1,
            'dataIntegrationUnits': 0  # Auto
        }
    
    def _generate_foreach_properties(self, mapped_activity: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Generate properties for ForEach activity (Fabric format)."""
        # Return just typeProperties (type is already set in activity)
        return {
            'items': {
                'value': f"@pipeline().parameters.{mapping.get('variableMappings', [{}])[0].get('name', 'items')}",
                'type': 'Expression'
            },
            'activities': []  # Nested activities would go here
        }
    
    def _generate_mapping_dataflow_properties(self, mapped_activity: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Generate properties for Mapping Data Flow activity (Fabric format)."""
        # Return just typeProperties (type is already set in activity)
        return {
            'dataflow': {
                'referenceName': self._generate_dataflow_name(mapped_activity),
                'type': 'DataFlowReference'
            },
            'staging': {},
            'compute': {
                'coreCount': 8,
                'computeType': 'General'
            }
        }
    
    def _generate_notebook_properties(self, mapped_activity: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Generate properties for Notebook activity (Fabric format - SynapseNotebook)."""
        # Return just typeProperties (type is already set in activity)
        return {
            'notebook': {
                'referenceName': self._generate_notebook_path(mapped_activity),
                'type': 'NotebookReference'
            },
            'parameters': {}
        }
    
    def _generate_sql_parameters(self, parameter_bindings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate SQL parameters from SSIS parameter bindings."""
        params = {}
        for binding in parameter_bindings:
            param_name = binding.get('name', '').lstrip('@')
            variable_name = binding.get('variableName', '')
            
            if variable_name:
                # Map to pipeline parameter
                params[param_name] = {
                    'value': f"@pipeline().parameters.{self._sanitize_name(variable_name)}",
                    'type': 'Expression'
                }
            else:
                params[param_name] = {
                    'value': binding.get('defaultValue', ''),
                    'type': 'Expression'
                }
        
        return params
    
    def _resolve_dependencies(
        self,
        activities: List[Dict[str, Any]],
        activity_dependencies: Dict[str, List[str]],
        mapped_activities: List[Dict[str, Any]]
    ):
        """Resolve activity dependencies and set dependsOn."""
        # Create mapping from SSIS ID to Fabric activity name
        id_to_name = {}
        for mapped_activity in mapped_activities:
            ssis_id = mapped_activity.get('ssis', {}).get('id')
            fabric_activity_name = next(
                (a['name'] for a in activities if a.get('userProperties', [{}])[0].get('value') == ssis_id),
                None
            )
            if fabric_activity_name:
                id_to_name[ssis_id] = fabric_activity_name
        
        # Set dependsOn for each activity
        for activity in activities:
            ssis_id = next(
                (prop['value'] for prop in activity.get('userProperties', []) if prop['name'] == 'ssisActivityId'),
                None
            )
            
            if ssis_id and ssis_id in activity_dependencies:
                depends_on_ids = activity_dependencies[ssis_id]
                depends_on_names = [id_to_name[id] for id in depends_on_ids if id in id_to_name]
                activity['dependsOn'] = [
                    {
                        'activity': name,
                        'dependencyConditions': ['Succeeded']
                    }
                    for name in depends_on_names
                ]
    
    def _extract_dependencies(self, mapped_activity: Dict[str, Any], package_data: Dict[str, Any]) -> List[str]:
        """Extract dependency IDs for an activity."""
        ssis_activity = mapped_activity.get('ssis', {})
        activity_id = ssis_activity.get('id')
        
        # Find activity in package data
        activities = package_data.get('activities', [])
        activity = next((a for a in activities if a.get('id') == activity_id), None)
        
        if activity and activity.get('previousActivities'):
            return [prev.get('id') for prev in activity['previousActivities']]
        
        return []
    
    def _generate_activity_name(self, activity_type: str, ssis_name: str, ssis_type: str) -> str:
        """Generate deterministic activity name."""
        # Format: <Type>_<SSIS_TaskName>
        type_prefix = activity_type.replace('Script', 'Script').replace('DataFlow', 'DataFlow')
        
        # Sanitize SSIS name
        sanitized_name = self._sanitize_name(ssis_name, prefix='')
        
        # Generate full name
        full_name = f"{type_prefix}_{sanitized_name}" if sanitized_name else type_prefix
        
        # Ensure uniqueness
        original_name = full_name
        counter = 1
        while full_name in self.activity_name_cache:
            full_name = f"{original_name}_{counter}"
            counter += 1
        
        self.activity_name_cache.add(full_name)
        return full_name
    
    def _sanitize_name(self, name: str, prefix: str = '') -> str:
        """Sanitize name for Fabric (alphanumeric, underscore, hyphen)."""
        import re
        
        # Remove invalid characters
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip('_')
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"_{sanitized}"
        # Add prefix if provided
        if prefix:
            sanitized = f"{prefix}_{sanitized}" if sanitized else prefix
        
        # Limit length (Fabric has name length limits)
        max_length = 260
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized or f"Item_{uuid.uuid4().hex[:8]}"
    
    def _map_activity_type_to_fabric(self, activity_type: str) -> str:
        """Map activity type to Fabric activity type string."""
        # Fabric uses different activity type names
        type_mapping = {
            'SQLScript': 'SqlScript',  # Fabric uses SqlScript, not SqlServerStoredProcedure
            'Copy': 'Copy',
            'ForEach': 'ForEach',
            'MappingDataFlow': 'ExecuteDataFlow',
            'Notebook': 'SynapseNotebook',  # Fabric uses SynapseNotebook
            'Script': 'Script'
        }
        return type_mapping.get(activity_type, 'Wait')
    
    def _map_source_type(self, source_type: str) -> str:
        """Map source type to Fabric source type."""
        # Fabric uses simplified source types
        type_mapping = {
            'ADLSGen2': 'DelimitedTextSource',
            'OneLake': 'DelimitedTextSource',
            'FabricWarehouse': 'SqlSource',
            'SQLEndpoint': 'SqlSource',
            'DelimitedText': 'DelimitedTextSource'
        }
        return type_mapping.get(source_type, 'DelimitedTextSource')
    
    def _map_destination_type(self, dest_type: str) -> str:
        """Map destination type to Fabric sink type."""
        # Fabric uses simplified sink types
        type_mapping = {
            'FabricWarehouse': 'SqlSink',
            'SQLEndpoint': 'SqlSink',
            'ADLSGen2': 'DelimitedTextSink',
            'OneLake': 'DelimitedTextSink',
            'SqlSink': 'SqlSink'
        }
        return type_mapping.get(dest_type, 'SqlSink')
    
    def _generate_linked_service_name(self, connection_id: str) -> str:
        """Generate linked service name from connection ID."""
        # Extract meaningful name from connection ID or use default
        if '[' in connection_id and ']' in connection_id:
            name = connection_id.split('[')[1].split(']')[0]
            return self._sanitize_name(name, prefix='LS')
        return f"LS_{uuid.uuid4().hex[:8]}"
    
    def _generate_dataflow_name(self, mapped_activity: Dict[str, Any]) -> str:
        """Generate data flow name."""
        ssis_name = mapped_activity.get('ssis', {}).get('name', 'DataFlow')
        return self._sanitize_name(ssis_name, prefix='DF')
    
    def _generate_notebook_path(self, mapped_activity: Dict[str, Any]) -> str:
        """Generate notebook path."""
        ssis_name = mapped_activity.get('ssis', {}).get('name', 'Notebook')
        return f"/{self._sanitize_name(ssis_name, prefix='')}"
    
    def _generate_dataset_name(self, activity_name: str, direction: str, component: Dict[str, Any]) -> str:
        """Generate dataset name for Copy activity."""
        component_name = component.get('name', activity_name)
        sanitized = self._sanitize_name(f"{component_name}_{direction}", prefix='DS')
        
        # Ensure uniqueness
        if sanitized not in self.activity_name_cache:
            self.activity_name_cache.add(sanitized)
            return sanitized
        
        counter = 1
        original = sanitized
        while sanitized in self.activity_name_cache:
            sanitized = f"{original}_{counter}"
            counter += 1
        self.activity_name_cache.add(sanitized)
        return sanitized
    
    def _generate_source_store_settings(self, source: Dict[str, Any], source_type: str) -> Dict[str, Any]:
        """Generate store settings for Copy activity source."""
        if 'Sql' in source_type or 'FabricWarehouse' in source.get('targetActivityType', ''):
            return {
                'type': 'SqlServerReadSettings'
            }
        elif 'OneLake' in source.get('targetActivityType', '') or 'Lakehouse' in source.get('targetActivityType', ''):
            return {
                'type': 'LakehouseReadSettings'
            }
        else:
            # Default to blob storage
            return {
                'type': 'AzureBlobStorageReadSettings',
                'recursive': True
            }
    
    def _generate_sink_store_settings(self, destination: Dict[str, Any], sink_type: str) -> Dict[str, Any]:
        """Generate store settings for Copy activity sink."""
        if 'Sql' in sink_type or 'FabricWarehouse' in destination.get('targetActivityType', ''):
            return {
                'type': 'SqlServerWriteSettings',
                'writeBehavior': 'insert'
            }
        elif 'OneLake' in destination.get('targetActivityType', '') or 'Lakehouse' in destination.get('targetActivityType', ''):
            return {
                'type': 'LakehouseWriteSettings',
                'copyBehavior': 'MergeFiles'
            }
        else:
            # Default to blob storage
            return {
                'type': 'AzureBlobStorageWriteSettings',
                'copyBehavior': 'MergeFiles'
            }
    
    def _generate_format_settings(self, component: Dict[str, Any], component_type: str, is_sink: bool = False) -> Dict[str, Any]:
        """Generate format settings for Copy activity."""
        # Determine format based on component type
        if 'DelimitedText' in component_type or 'Delimited' in component_type:
            delimiter = component.get('delimiter', ',')
            text_qualifier = component.get('textQualifier', '"')
            first_row_header = component.get('firstRowHeader', False)
            
            format_settings = {
                'type': 'DelimitedTextReadSettings' if not is_sink else 'DelimitedTextWriteSettings',
                'columnDelimiter': delimiter
            }
            
            if text_qualifier:
                format_settings['quoteChar'] = text_qualifier
            
            if not is_sink and first_row_header:
                format_settings['firstRowAsHeader'] = True
            
            return format_settings
        elif 'Sql' in component_type:
            # SQL doesn't typically need format settings
            return {}
        else:
            # Default to delimited text
            return {
                'type': 'DelimitedTextReadSettings' if not is_sink else 'DelimitedTextWriteSettings',
                'columnDelimiter': ',',
                'firstRowAsHeader': True
            }
    
    def _generate_linked_service_name(self, connection_id: str) -> str:
        """Generate linked service/connection name from connection ID (Fabric format)."""
        if not connection_id:
            return f"Connection_{uuid.uuid4().hex[:8]}"
        
        # Extract meaningful name from connection ID
        if '[' in connection_id and ']' in connection_id:
            name = connection_id.split('[')[1].split(']')[0]
            # Clean up the name
            name = name.replace('..', '.').replace('Package.ConnectionManagers[', '').strip()
            return self._sanitize_name(name, prefix='Connection')
        
        # Try to extract from GUID or other patterns
        if '{' in connection_id and '}' in connection_id:
            # Use first 8 chars of GUID
            guid_part = connection_id.split('{')[1].split('}')[0].replace('-', '')[:8]
            return f"Connection_{guid_part}"
        
        return self._sanitize_name(connection_id, prefix='Connection') if connection_id else f"Connection_{uuid.uuid4().hex[:8]}"
    
    def validate_pipeline(self, pipeline: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate Fabric pipeline JSON and return validation results.
        
        Returns:
            Dictionary with validation results:
            - valid: Boolean
            - errors: List of errors
            - warnings: List of warnings
        """
        errors = []
        warnings = []
        
        # Basic structure validation
        if 'properties' not in pipeline:
            errors.append("Missing 'properties' in pipeline")
            return {'valid': False, 'errors': errors, 'warnings': warnings}
        
        properties = pipeline['properties']
        
        # Validate activities
        if 'activities' not in properties:
            warnings.append("No activities in pipeline")
        else:
            activities = properties['activities']
            
            # Check for cycles in dependencies
            cycle_detected = self._detect_cycles(activities)
            if cycle_detected:
                errors.append("Circular dependency detected in activities")
            
            # Validate activity names are unique
            activity_names = [a.get('name') for a in activities]
            if len(activity_names) != len(set(activity_names)):
                errors.append("Duplicate activity names found")
            
            # Validate each activity has required fields
            for activity in activities:
                if 'name' not in activity:
                    errors.append("Activity missing 'name' field")
                if 'type' not in activity:
                    errors.append(f"Activity '{activity.get('name', 'Unknown')}' missing 'type' field")
        
        # Validate parameters
        if 'parameters' in properties:
            params = properties['parameters']
            for param_name, param_def in params.items():
                if 'type' not in param_def:
                    errors.append(f"Parameter '{param_name}' missing 'type' field")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def _detect_cycles(self, activities: List[Dict[str, Any]]) -> bool:
        """Detect cycles in activity dependencies using DFS."""
        # Build adjacency list
        graph = {}
        activity_names = {a['name']: a for a in activities}
        
        for activity in activities:
            name = activity['name']
            graph[name] = []
            for dep in activity.get('dependsOn', []):
                dep_name = dep.get('activity') if isinstance(dep, dict) else dep
                if dep_name in activity_names:
                    graph[name].append(dep_name)
        
        # DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    return True
        
        return False
    
    def generate_conversion_summary(self, mapping_trace: Dict[str, Any], pipeline: Dict[str, Any], validation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate conversion summary report."""
        diagnostics = mapping_trace.get('diagnostics', {})
        
        return {
            'conversionDate': datetime.now().isoformat(),
            'originalPackage': mapping_trace.get('diagnostics', {}).get('totalActivities', 0),
            'convertedActivities': len(pipeline.get('properties', {}).get('activities', [])),
            'overallConfidence': diagnostics.get('overallConfidence', 0.0),
            'validation': validation,
            'supportBreakdown': mapping_trace.get('conversionSummary', {}),
            'manualRemediationCount': diagnostics.get('manualRemediationCount', 0),
            'warnings': diagnostics.get('warnings', []),
            'pipelineName': pipeline.get('name', ''),
            'pipelineParameters': len(pipeline.get('properties', {}).get('parameters', {}))
        }

