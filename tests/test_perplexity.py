#!/usr/bin/env python3
"""
Unit tests for Perplexity image and text generation utilities.
"""
import asyncio
import os
import sys

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


if __name__ == '__main__':
    # Run basic smoke tests
    print("Running Perplexity module smoke tests...")
    
    async def smoke_test():
        print("\n🧪 Test 1: Module imports")
        try:
            from utils.perplexity import generate_image, generate_text, PerplexityError
            print("✅ Module imports successful")
        except ImportError as e:
            print(f"❌ Import failed: {e}")
            return False
        
        print("\n🧪 Test 2: PerplexityError exception")
        try:
            raise PerplexityError("Test error")
        except PerplexityError as e:
            print(f"✅ PerplexityError works: {e}")
        except Exception as e:
            print(f"❌ Unexpected exception: {e}")
            return False
        
        print("\n🧪 Test 3: Function signatures")
        try:
            # Check that functions exist and have correct signatures
            import inspect
            from utils.perplexity import generate_image, generate_text
            
            # Check generate_image signature
            sig = inspect.signature(generate_image)
            params = list(sig.parameters.keys())
            assert 'prompt' in params, "generate_image should have 'prompt' parameter"
            assert 'model' in params, "generate_image should have 'model' parameter"
            
            # Check generate_text signature
            sig = inspect.signature(generate_text)
            params = list(sig.parameters.keys())
            assert 'prompt' in params, "generate_text should have 'prompt' parameter"
            assert 'model' in params, "generate_text should have 'model' parameter"
            
            print("✅ Function signatures are correct")
        except Exception as e:
            print(f"❌ Function signature check failed: {e}")
            return False
        
        return True
    
    success = asyncio.run(smoke_test())
    if success:
        print("\n✅ All Perplexity module smoke tests passed!")
    sys.exit(0 if success else 1)
