"""AST parser for extracting code entities."""

import ast
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ASTParser:
    """
    Parse Python files to extract code entities.
    
    Extracts:
    - Functions (with docstrings and decorators)
    - Classes (with methods and attributes)
    - Imports and dependencies
    - Module-level constants
    """

    def __init__(self):
        """Initialize AST parser."""
        pass

    def parse_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Parse a Python file and extract code entities.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            List of code entity dictionaries
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source, filename=file_path)
            
            entities = []
            
            # Extract module-level entities
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    entities.append(self._extract_function(node, file_path))
                elif isinstance(node, ast.AsyncFunctionDef):
                    entities.append(self._extract_function(node, file_path, is_async=True))
                elif isinstance(node, ast.ClassDef):
                    entities.append(self._extract_class(node, file_path))
            
            logger.info(
                "ast_file_parsed",
                extra={"file": file_path, "entities": len(entities)},
            )
            
            return entities
            
        except SyntaxError as e:
            logger.warning(
                "ast_parse_syntax_error",
                extra={"file": file_path, "error": str(e)},
            )
            return []
        except Exception as e:
            logger.exception(
                "ast_parse_failed",
                extra={"file": file_path, "error": str(e)},
            )
            return []

    def _extract_function(
        self, node: ast.FunctionDef, file_path: str, is_async: bool = False
    ) -> Dict[str, Any]:
        """
        Extract function information.
        
        Args:
            node: AST function node
            file_path: Source file path
            is_async: Whether function is async
            
        Returns:
            Function entity dictionary
        """
        docstring = ast.get_docstring(node) or ""
        
        # Extract decorators
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]
        
        # Extract arguments
        args = [arg.arg for arg in node.args.args]
        
        # Extract return type if available
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns) if hasattr(ast, 'unparse') else None
        
        return {
            "entity_type": "function",
            "name": node.name,
            "file_path": file_path,
            "line_number": node.lineno,
            "description": docstring.split("\n")[0] if docstring else None,
            "is_async": is_async,
            "decorators": decorators,
            "arguments": args,
            "return_type": return_type,
            "ast_info": {
                "end_line": node.end_lineno,
                "is_method": False,  # Updated by class extraction
            },
        }

    def _extract_class(self, node: ast.ClassDef, file_path: str) -> Dict[str, Any]:
        """
        Extract class information.
        
        Args:
            node: AST class node
            file_path: Source file path
            
        Returns:
            Class entity dictionary
        """
        docstring = ast.get_docstring(node) or ""
        
        # Extract base classes
        bases = [self._get_base_name(base) for base in node.bases]
        
        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)
        
        return {
            "entity_type": "class",
            "name": node.name,
            "file_path": file_path,
            "line_number": node.lineno,
            "description": docstring.split("\n")[0] if docstring else None,
            "base_classes": bases,
            "methods": methods,
            "ast_info": {
                "end_line": node.end_lineno,
                "method_count": len(methods),
            },
        }

    def _get_decorator_name(self, node: ast.AST) -> str:
        """Get decorator name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return node.func.attr
        return "unknown"

    def _get_base_name(self, node: ast.AST) -> str:
        """Get base class name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return "unknown"

    def extract_dependencies(self, file_path: str) -> List[str]:
        """
        Extract import dependencies from a file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            List of imported module names
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            
            tree = ast.parse(source, filename=file_path)
            
            dependencies = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append(node.module)
            
            return list(set(dependencies))  # Deduplicate
            
        except Exception as e:
            logger.exception(
                "ast_dependencies_failed",
                extra={"file": file_path, "error": str(e)},
            )
            return []

    def get_file_summary(self, file_path: str) -> Dict[str, Any]:
        """
        Get high-level summary of a file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Summary dictionary
        """
        entities = self.parse_file(file_path)
        dependencies = self.extract_dependencies(file_path)
        
        function_count = sum(1 for e in entities if e["entity_type"] == "function")
        class_count = sum(1 for e in entities if e["entity_type"] == "class")
        
        return {
            "file_path": file_path,
            "function_count": function_count,
            "class_count": class_count,
            "total_entities": len(entities),
            "dependencies": dependencies,
            "dependency_count": len(dependencies),
        }
