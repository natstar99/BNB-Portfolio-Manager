#!/usr/bin/env python3
"""
Simple coverage runner - tracks code usage and generates HTML report
"""

import coverage
import os

def run_with_coverage():
    """Run Flask app with simple coverage tracking"""
    
    # Initialize coverage
    cov = coverage.Coverage(
        source=['app'],
        omit=[
            '*/venv/*',
            '*/env/*', 
            '*/__pycache__/*',
            '*/tests/*',
            '*/test_*',
            'run.py',
            'enhanced_coverage.py'
        ],
        branch=True
    )
    
    # Start coverage tracking
    cov.start()
    
    try:
        # Import and run the Flask app
        from app import create_app
        
        print("🔍 Coverage tracking enabled")
        print("🌐 Backend running on http://localhost:5000")
        print("📊 Press Ctrl+C when done to generate coverage report")
        
        app = create_app()
        
        # Run the app
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Generating coverage report...")
        
    finally:
        # Stop coverage and generate reports
        cov.stop()
        cov.save()
        
        # Generate HTML report
        html_dir = 'coverage_html'
        cov.html_report(directory=html_dir)
        
        # Show summary
        print("\n📊 Coverage Report Generated")
        print(f"📄 HTML Report: {html_dir}/index.html")
        
        # Console summary
        cov.report(show_missing=True)

if __name__ == '__main__':
    run_with_coverage()