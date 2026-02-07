#!/usr/bin/env python3
"""
Simple validation script for RAG service module structure.

This script validates the RAG service without requiring all dependencies.
It checks for:
- Proper singleton export
- Required methods
- Correct function signatures
"""

import ast
import os
import sys


def validate_rag_service():
    """Validate the RAG service module structure."""
    
    # Get path to rag_service.py relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rag_service_path = os.path.join(script_dir, '..', 'rag_service.py')
    
    with open(rag_service_path, 'r') as f:
        source = f.read()
    
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"❌ Syntax error in rag_service.py: {e}")
        return False
    
    # Check for required exports
    has_all_export = False
    has_singleton_creation = False
    has_rag_service_class = False
    has_is_enabled_method = False
    has_get_context_method = False
    has_stop_observer_method = False
    has_default_embeddings_model = False
    
    for node in ast.walk(tree):
        # Check for __all__ definition
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == '__all__':
                    has_all_export = True
                    # Verify it contains 'rag_service'
                    if isinstance(node.value, ast.List):
                        exports = [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)]
                        if 'rag_service' not in exports:
                            print("❌ __all__ does not export 'rag_service'")
                            return False
                        if 'RAGService' not in exports:
                            print("❌ __all__ does not export 'RAGService'")
                            return False
                
                # Check for singleton instantiation
                if isinstance(target, ast.Name) and target.id == 'rag_service':
                    has_singleton_creation = True
                
                # Check for DEFAULT_EMBEDDINGS_MODEL
                if isinstance(target, ast.Name) and target.id == 'DEFAULT_EMBEDDINGS_MODEL':
                    has_default_embeddings_model = True
        
        # Check for RAGService class
        if isinstance(node, ast.ClassDef) and node.name == 'RAGService':
            has_rag_service_class = True
            
            # Check for required methods
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name == 'is_enabled':
                        has_is_enabled_method = True
                        # Verify it has correct signature (self)
                        if len(item.args.args) != 1:
                            print(f"❌ is_enabled method has wrong signature")
                            return False
                    
                    if item.name == 'get_context':
                        has_get_context_method = True
                        # Verify it's async and has correct signature (self, topic)
                        if not isinstance(item, ast.AsyncFunctionDef):
                            print(f"❌ get_context method is not async")
                            return False
                        if len(item.args.args) != 2:
                            print(f"❌ get_context method has wrong signature")
                            return False
                    
                    if item.name == 'stop_observer':
                        has_stop_observer_method = True
                        if not isinstance(item, ast.AsyncFunctionDef):
                            print(f"❌ stop_observer method is not async")
                            return False
    
    # Report findings
    issues = []
    if not has_default_embeddings_model:
        issues.append("Missing DEFAULT_EMBEDDINGS_MODEL constant")
    if not has_rag_service_class:
        issues.append("Missing RAGService class")
    if not has_is_enabled_method:
        issues.append("Missing is_enabled() method in RAGService")
    if not has_get_context_method:
        issues.append("Missing get_context() method in RAGService")
    if not has_stop_observer_method:
        issues.append("Missing stop_observer() method in RAGService")
    if not has_singleton_creation:
        issues.append("Missing rag_service singleton instantiation")
    if not has_all_export:
        issues.append("Missing __all__ export definition")
    
    if issues:
        print("❌ Validation failed:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("✅ RAG service structure validation passed:")
    print("  ✓ DEFAULT_EMBEDDINGS_MODEL constant defined")
    print("  ✓ RAGService class defined")
    print("  ✓ is_enabled() method present")
    print("  ✓ get_context() async method present")
    print("  ✓ stop_observer() async method present")
    print("  ✓ rag_service singleton created")
    print("  ✓ __all__ properly exports ['rag_service', 'RAGService']")
    return True


if __name__ == '__main__':
    success = validate_rag_service()
    sys.exit(0 if success else 1)
