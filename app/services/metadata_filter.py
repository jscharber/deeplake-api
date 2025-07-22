"""
Advanced metadata filtering service with complex filter expressions.

This module provides sophisticated metadata filtering capabilities including:
- Complex boolean expressions (AND, OR, NOT)
- Comparison operators (=, !=, <, >, <=, >=, IN, LIKE)
- Data type support (string, numeric, boolean, array)
- Nested metadata filtering
- SQL-like expression parsing
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class FilterOperator(Enum):
    """Supported filter operators."""
    EQ = "="           # Equal
    NE = "!="          # Not equal
    LT = "<"           # Less than
    LE = "<="          # Less than or equal
    GT = ">"           # Greater than
    GE = ">="          # Greater than or equal
    IN = "IN"          # In list
    NOT_IN = "NOT_IN"  # Not in list
    LIKE = "LIKE"      # Pattern matching
    NOT_LIKE = "NOT_LIKE"  # Not pattern matching
    EXISTS = "EXISTS"  # Field exists
    NOT_EXISTS = "NOT_EXISTS"  # Field doesn't exist
    IS_NULL = "IS_NULL"        # Field is null
    IS_NOT_NULL = "IS_NOT_NULL"  # Field is not null


class BooleanOperator(Enum):
    """Boolean operators for combining filters."""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


@dataclass
class FilterCondition:
    """Represents a single filter condition."""
    field: str
    operator: FilterOperator
    value: Any
    data_type: Optional[str] = None  # 'string', 'number', 'boolean', 'date', 'array'


@dataclass
class FilterExpression:
    """Represents a complex filter expression."""
    operator: Optional[BooleanOperator] = None
    conditions: List[FilterCondition] = None
    sub_expressions: List['FilterExpression'] = None
    
    def __post_init__(self):
        if self.conditions is None:
            self.conditions = []
        if self.sub_expressions is None:
            self.sub_expressions = []


class MetadataFilterService:
    """Service for parsing and applying complex metadata filters."""
    
    def __init__(self):
        self.logger = logger.bind(service="metadata_filter")
    
    def parse_filter_expression(self, filter_input: Union[str, Dict[str, Any]]) -> FilterExpression:
        """
        Parse filter expression from various input formats.
        
        Supports:
        1. Simple dict: {"category": "tech", "priority": 1}
        2. Complex dict: {"$and": [{"category": "tech"}, {"priority": {"$gt": 1}}]}
        3. SQL-like string: "category = 'tech' AND priority > 1"
        4. JSON string: '{"$and": [{"category": "tech"}, {"priority": {"$gt": 1}}]}'
        """
        try:
            if isinstance(filter_input, str):
                # Try parsing as JSON first
                try:
                    filter_dict = json.loads(filter_input)
                    return self._parse_dict_expression(filter_dict)
                except json.JSONDecodeError:
                    # Parse as SQL-like string
                    return self._parse_sql_expression(filter_input)
            elif isinstance(filter_input, dict):
                return self._parse_dict_expression(filter_input)
            else:
                raise ValueError(f"Unsupported filter input type: {type(filter_input)}")
        except Exception as e:
            self.logger.error("Failed to parse filter expression", error=str(e), filter_input=filter_input)
            raise ValueError(f"Invalid filter expression: {e}")
    
    def _parse_dict_expression(self, filter_dict: Dict[str, Any]) -> FilterExpression:
        """Parse dictionary-based filter expression."""
        if not filter_dict:
            return FilterExpression()
        
        # Handle MongoDB-style operators
        if "$and" in filter_dict:
            return FilterExpression(
                operator=BooleanOperator.AND,
                sub_expressions=[self._parse_dict_expression(expr) for expr in filter_dict["$and"]]
            )
        elif "$or" in filter_dict:
            return FilterExpression(
                operator=BooleanOperator.OR,
                sub_expressions=[self._parse_dict_expression(expr) for expr in filter_dict["$or"]]
            )
        elif "$not" in filter_dict:
            return FilterExpression(
                operator=BooleanOperator.NOT,
                sub_expressions=[self._parse_dict_expression(filter_dict["$not"])]
            )
        else:
            # Simple field conditions
            conditions = []
            for field, value in filter_dict.items():
                if isinstance(value, dict):
                    # Handle comparison operators
                    for op, op_value in value.items():
                        operator = self._map_dict_operator(op)
                        conditions.append(FilterCondition(
                            field=field,
                            operator=operator,
                            value=op_value,
                            data_type=self._infer_data_type(op_value)
                        ))
                else:
                    # Simple equality
                    conditions.append(FilterCondition(
                        field=field,
                        operator=FilterOperator.EQ,
                        value=value,
                        data_type=self._infer_data_type(value)
                    ))
            
            return FilterExpression(
                operator=BooleanOperator.AND if len(conditions) > 1 else None,
                conditions=conditions
            )
    
    def _parse_sql_expression(self, sql_expr: str) -> FilterExpression:
        """Parse SQL-like filter expression."""
        # This is a simplified SQL parser - in production, consider using a proper parser
        # For now, we'll handle basic cases
        
        # Remove extra whitespace
        sql_expr = re.sub(r'\s+', ' ', sql_expr.strip())
        
        # Handle parentheses by recursively parsing
        if '(' in sql_expr and ')' in sql_expr:
            return self._parse_sql_with_parentheses(sql_expr)
        
        # Handle AND/OR operators
        if ' OR ' in sql_expr.upper():
            parts = re.split(r'\s+OR\s+', sql_expr, flags=re.IGNORECASE)
            return FilterExpression(
                operator=BooleanOperator.OR,
                sub_expressions=[self._parse_sql_expression(part.strip()) for part in parts]
            )
        elif ' AND ' in sql_expr.upper():
            parts = re.split(r'\s+AND\s+', sql_expr, flags=re.IGNORECASE)
            return FilterExpression(
                operator=BooleanOperator.AND,
                sub_expressions=[self._parse_sql_expression(part.strip()) for part in parts]
            )
        else:
            # Single condition
            condition = self._parse_sql_condition(sql_expr)
            return FilterExpression(conditions=[condition])
    
    def _parse_sql_with_parentheses(self, sql_expr: str) -> FilterExpression:
        """Parse SQL expression with parentheses."""
        # Simple parentheses handling - extract innermost parentheses first
        # This is a simplified implementation
        
        # Find the first complete parentheses group
        stack = []
        start = -1
        for i, char in enumerate(sql_expr):
            if char == '(':
                if not stack:
                    start = i
                stack.append(char)
            elif char == ')':
                stack.pop()
                if not stack:
                    # Found complete group
                    inner_expr = sql_expr[start+1:i]
                    before = sql_expr[:start].strip()
                    after = sql_expr[i+1:].strip()
                    
                    # Parse the inner expression
                    inner_result = self._parse_sql_expression(inner_expr)
                    
                    # Combine with before and after parts
                    if before and after:
                        # This is a complex case - for now, just return the inner result
                        return inner_result
                    elif before:
                        # Handle NOT operator
                        if before.upper().endswith('NOT'):
                            return FilterExpression(
                                operator=BooleanOperator.NOT,
                                sub_expressions=[inner_result]
                            )
                    elif after:
                        # Handle continuation after parentheses
                        if after.upper().startswith('AND'):
                            remaining = self._parse_sql_expression(after[3:].strip())
                            return FilterExpression(
                                operator=BooleanOperator.AND,
                                sub_expressions=[inner_result, remaining]
                            )
                        elif after.upper().startswith('OR'):
                            remaining = self._parse_sql_expression(after[2:].strip())
                            return FilterExpression(
                                operator=BooleanOperator.OR,
                                sub_expressions=[inner_result, remaining]
                            )
                    
                    return inner_result
        
        # No parentheses found, parse normally
        return self._parse_sql_expression(sql_expr)
    
    def _parse_sql_condition(self, condition: str) -> FilterCondition:
        """Parse a single SQL condition."""
        # Regular expression for SQL condition
        patterns = [
            (r'(\w+)\s*(>=|<=|!=|<>|=|>|<)\s*([\'"]?)([^\'"]*)([\'"]?)', 'comparison'),
            (r'(\w+)\s+IN\s*\(([^)]+)\)', 'in_list'),
            (r'(\w+)\s+NOT\s+IN\s*\(([^)]+)\)', 'not_in_list'),
            (r'(\w+)\s+LIKE\s+([\'"]?)([^\'"]*)([\'"]?)', 'like'),
            (r'(\w+)\s+NOT\s+LIKE\s+([\'"]?)([^\'"]*)([\'"]?)', 'not_like'),
            (r'(\w+)\s+IS\s+NULL', 'is_null'),
            (r'(\w+)\s+IS\s+NOT\s+NULL', 'is_not_null'),
            (r'(\w+)\s+EXISTS', 'exists'),
            (r'(\w+)\s+NOT\s+EXISTS', 'not_exists'),
        ]
        
        for pattern, condition_type in patterns:
            match = re.match(pattern, condition.strip(), re.IGNORECASE)
            if match:
                return self._create_condition_from_match(match, condition_type)
        
        raise ValueError(f"Unable to parse SQL condition: {condition}")
    
    def _create_condition_from_match(self, match, condition_type: str) -> FilterCondition:
        """Create FilterCondition from regex match."""
        field = match.group(1)
        
        if condition_type == 'comparison':
            operator_str = match.group(2)
            value_str = match.group(4)  # Skip quotes
            
            # Map operator
            operator_map = {
                '=': FilterOperator.EQ,
                '!=': FilterOperator.NE,
                '<>': FilterOperator.NE,
                '<': FilterOperator.LT,
                '<=': FilterOperator.LE,
                '>': FilterOperator.GT,
                '>=': FilterOperator.GE,
            }
            
            operator = operator_map[operator_str]
            value = self._parse_value(value_str)
            
        elif condition_type == 'in_list':
            operator = FilterOperator.IN
            value_str = match.group(2)
            # Parse comma-separated values
            values = [self._parse_value(v.strip().strip('\'"')) for v in value_str.split(',')]
            value = values
            
        elif condition_type == 'not_in_list':
            operator = FilterOperator.NOT_IN
            value_str = match.group(2)
            values = [self._parse_value(v.strip().strip('\'"')) for v in value_str.split(',')]
            value = values
            
        elif condition_type == 'like':
            operator = FilterOperator.LIKE
            value = match.group(3)
            
        elif condition_type == 'not_like':
            operator = FilterOperator.NOT_LIKE
            value = match.group(3)
            
        elif condition_type == 'is_null':
            operator = FilterOperator.IS_NULL
            value = None
            
        elif condition_type == 'is_not_null':
            operator = FilterOperator.IS_NOT_NULL
            value = None
            
        elif condition_type == 'exists':
            operator = FilterOperator.EXISTS
            value = None
            
        elif condition_type == 'not_exists':
            operator = FilterOperator.NOT_EXISTS
            value = None
        
        return FilterCondition(
            field=field,
            operator=operator,
            value=value,
            data_type=self._infer_data_type(value)
        )
    
    def _map_dict_operator(self, op: str) -> FilterOperator:
        """Map dictionary operator to FilterOperator."""
        mapping = {
            '$eq': FilterOperator.EQ,
            '$ne': FilterOperator.NE,
            '$lt': FilterOperator.LT,
            '$le': FilterOperator.LE,
            '$lte': FilterOperator.LE,
            '$gt': FilterOperator.GT,
            '$ge': FilterOperator.GE,
            '$gte': FilterOperator.GE,
            '$in': FilterOperator.IN,
            '$nin': FilterOperator.NOT_IN,
            '$like': FilterOperator.LIKE,
            '$regex': FilterOperator.LIKE,
            '$exists': FilterOperator.EXISTS,
            '$null': FilterOperator.IS_NULL,
        }
        return mapping.get(op, FilterOperator.EQ)
    
    def _parse_value(self, value_str: str) -> Any:
        """Parse string value to appropriate type."""
        if not value_str:
            return value_str
        
        # Try to parse as number
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass
        
        # Try to parse as boolean
        if value_str.lower() in ('true', 'false'):
            return value_str.lower() == 'true'
        
        # Try to parse as date (ISO format)
        try:
            return datetime.fromisoformat(value_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        
        # Return as string
        return value_str
    
    def _infer_data_type(self, value: Any) -> str:
        """Infer data type from value."""
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, datetime):
            return 'date'
        elif isinstance(value, (list, tuple)):
            return 'array'
        else:
            return 'string'
    
    def apply_filter(self, metadata: Dict[str, Any], filter_expr: FilterExpression) -> bool:
        """Apply filter expression to metadata and return True if matches."""
        try:
            return self._evaluate_expression(metadata, filter_expr)
        except Exception as e:
            self.logger.error("Error applying filter", error=str(e), metadata=metadata)
            return False
    
    def _evaluate_expression(self, metadata: Dict[str, Any], expr: FilterExpression) -> bool:
        """Evaluate a filter expression against metadata."""
        # Handle conditions
        condition_results = []
        for condition in expr.conditions:
            result = self._evaluate_condition(metadata, condition)
            condition_results.append(result)
        
        # Handle sub-expressions
        sub_expr_results = []
        for sub_expr in expr.sub_expressions:
            result = self._evaluate_expression(metadata, sub_expr)
            sub_expr_results.append(result)
        
        # Combine all results
        all_results = condition_results + sub_expr_results
        
        if not all_results:
            return True  # Empty expression matches everything
        
        # Apply boolean operator
        if expr.operator == BooleanOperator.AND:
            return all(all_results)
        elif expr.operator == BooleanOperator.OR:
            return any(all_results)
        elif expr.operator == BooleanOperator.NOT:
            return not all_results[0] if all_results else True
        else:
            # No operator, default to AND
            return all(all_results)
    
    def _evaluate_condition(self, metadata: Dict[str, Any], condition: FilterCondition) -> bool:
        """Evaluate a single condition against metadata."""
        field_value = self._get_nested_value(metadata, condition.field)
        
        if condition.operator == FilterOperator.EXISTS:
            return field_value is not None
        elif condition.operator == FilterOperator.NOT_EXISTS:
            return field_value is None
        elif condition.operator == FilterOperator.IS_NULL:
            return field_value is None
        elif condition.operator == FilterOperator.IS_NOT_NULL:
            return field_value is not None
        
        # For other operators, if field doesn't exist, return False
        if field_value is None:
            return False
        
        # Convert types if needed
        field_value = self._convert_value_type(field_value, condition.data_type)
        condition_value = self._convert_value_type(condition.value, condition.data_type)
        
        if condition.operator == FilterOperator.EQ:
            return field_value == condition_value
        elif condition.operator == FilterOperator.NE:
            return field_value != condition_value
        elif condition.operator == FilterOperator.LT:
            return field_value < condition_value
        elif condition.operator == FilterOperator.LE:
            return field_value <= condition_value
        elif condition.operator == FilterOperator.GT:
            return field_value > condition_value
        elif condition.operator == FilterOperator.GE:
            return field_value >= condition_value
        elif condition.operator == FilterOperator.IN:
            return field_value in condition_value
        elif condition.operator == FilterOperator.NOT_IN:
            return field_value not in condition_value
        elif condition.operator == FilterOperator.LIKE:
            return self._match_pattern(str(field_value), str(condition_value))
        elif condition.operator == FilterOperator.NOT_LIKE:
            return not self._match_pattern(str(field_value), str(condition_value))
        
        return False
    
    def _get_nested_value(self, metadata: Dict[str, Any], field: str) -> Any:
        """Get value from nested metadata using dot notation."""
        if '.' not in field:
            return metadata.get(field)
        
        parts = field.split('.')
        current = metadata
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _convert_value_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type."""
        if target_type is None or value is None:
            return value
        
        try:
            if target_type == 'number' and not isinstance(value, (int, float)):
                return float(value)
            elif target_type == 'integer' and not isinstance(value, int):
                return int(value)
            elif target_type == 'boolean' and not isinstance(value, bool):
                return str(value).lower() in ('true', '1', 'yes', 'on')
            elif target_type == 'string' and not isinstance(value, str):
                return str(value)
            elif target_type == 'date' and not isinstance(value, datetime):
                return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except (ValueError, TypeError):
            pass
        
        return value
    
    def _match_pattern(self, value: str, pattern: str) -> bool:
        """Match string value against pattern (supports % and _ wildcards)."""
        # Convert SQL LIKE pattern to regex
        regex_pattern = pattern.replace('%', '.*').replace('_', '.')
        regex_pattern = f'^{regex_pattern}$'
        
        return bool(re.match(regex_pattern, value, re.IGNORECASE))


# Global instance
metadata_filter_service = MetadataFilterService()