#!/usr/bin/env python3
"""
Test script to verify WSGI application works correctly
"""

import os
import sys

def test_wsgi():
    """Test WSGI application loading"""
    print("=== Testing WSGI Application ===")
    
    try:
        # Set up environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminder_app.settings')
        
        # Import Django
        import django
        django.setup()
        print("✅ Django setup successful")
        
        # Import WSGI application
        from reminder_app.wsgi import application
        print("✅ WSGI application imported successfully")
        
        # Test that application is callable
        if callable(application):
            print("✅ WSGI application is callable")
        else:
            print("❌ WSGI application is not callable")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ WSGI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_server():
    """Test simple HTTP server"""
    print("\n=== Testing Simple HTTP Server ===")
    
    try:
        import http.server
        import socketserver
        import threading
        import time
        import requests
        
        # Create a simple test server
        class TestHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b"Test server is working!")
        
        # Start server on port 8081
        with socketserver.TCPServer(("", 8081), TestHandler) as httpd:
            print("✅ Test HTTP server started on port 8081")
            
            # Test the server
            time.sleep(1)
            response = requests.get("http://localhost:8081", timeout=5)
            if response.status_code == 200:
                print("✅ Test HTTP server responded correctly")
                return True
            else:
                print(f"❌ Test HTTP server returned status {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Simple server test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 WSGI and Server Test")
    print("=" * 50)
    
    # Test 1: WSGI application
    wsgi_ok = test_wsgi()
    
    # Test 2: Simple HTTP server
    server_ok = test_simple_server()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"WSGI Application: {'✅ OK' if wsgi_ok else '❌ FAILED'}")
    print(f"HTTP Server: {'✅ OK' if server_ok else '❌ FAILED'}")
    
    if not wsgi_ok:
        print("\n🔧 FIX: Check Django configuration and WSGI setup")
    elif not server_ok:
        print("\n🔧 FIX: Check network/port configuration")
    else:
        print("\n✅ All tests passed! WSGI should work correctly.")

if __name__ == "__main__":
    main()
