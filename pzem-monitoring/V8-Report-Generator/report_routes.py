#!/usr/bin/env python3
"""
Flask Routes untuk PDF Reporting - Integration dengan existing dashboard
"""

from flask import Blueprint, request, jsonify, send_file, render_template_string
from datetime import datetime, timedelta
import os
import logging
from report_generator import DatabaseManager, ReportGenerator

logger = logging.getLogger(__name__)

# Create blueprint
report_bp = Blueprint('reports', __name__, url_prefix='/reports')

# Initialize report components
db_manager = DatabaseManager()
report_generator = ReportGenerator(db_manager)

@report_bp.route('/')
def report_dashboard():
    """Halaman dashboard untuk report"""
    template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PZEM Report Generator</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
        }
        
        .header h1 {
            color: #2c3e50;
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .header p {
            color: #666;
            font-size: 1.2rem;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .form-group select,
        .form-group input {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .form-group select:focus,
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .date-range {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .generate-btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        
        .generate-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        .generate-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            font-weight: 600;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status.loading {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        
        .download-link {
            display: inline-block;
            margin-top: 10px;
            padding: 8px 16px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            transition: all 0.3s ease;
        }
        
        .download-link:hover {
            background: #218838;
            transform: translateY(-1px);
        }
        
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }
        
        .back-link:hover {
            text-decoration: underline;
        }
        
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        
        .feature-item {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border: 2px solid #e9ecef;
        }
        
        .feature-item i {
            font-size: 2rem;
            color: #667eea;
            margin-bottom: 10px;
        }
        
        .feature-item h3 {
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .feature-item p {
            color: #666;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">
            <i class="fas fa-arrow-left"></i> Back to Dashboard
        </a>
        
        <div class="header">
            <h1><i class="fas fa-file-pdf"></i> Report Generator</h1>
            <p>Generate comprehensive 3-Phase power analysis reports</p>
        </div>
        
        <!-- Features -->
        <div class="feature-grid">
            <div class="feature-item">
                <i class="fas fa-chart-line"></i>
                <h3>3-Phase Analysis</h3>
                <p>Complete power calculations and imbalance detection</p>
            </div>
            <div class="feature-item">
                <i class="fas fa-chart-pie"></i>
                <h3>Visual Charts</h3>
                <p>Power trends and distribution graphs</p>
            </div>
            <div class="feature-item">
                <i class="fas fa-lightbulb"></i>
                <h3>Recommendations</h3>
                <p>System optimization suggestions</p>
            </div>
            <div class="feature-item">
                <i class="fas fa-calculator"></i>
                <h3>Cost Analysis</h3>
                <p>Energy consumption and cost estimation</p>
            </div>
        </div>
        
        <!-- Report Form -->
        <form id="reportForm">
            <div class="form-group">
                <label for="periodType">
                    <i class="fas fa-calendar"></i> Report Period
                </label>
                <select id="periodType" name="period_type" required>
                    <option value="daily">Daily Report (Last 24 hours)</option>
                    <option value="weekly">Weekly Report (Last 7 days)</option>
                    <option value="monthly">Monthly Report (Last 30 days)</option>
                    <option value="custom">Custom Date Range</option>
                </select>
            </div>
            
            <div class="form-group" id="customDateRange" style="display: none;">
                <label>
                    <i class="fas fa-calendar-alt"></i> Custom Date Range
                </label>
                <div class="date-range">
                    <input type="datetime-local" id="startDate" name="start_date" placeholder="Start Date">
                    <input type="datetime-local" id="endDate" name="end_date" placeholder="End Date">
                </div>
            </div>
            
            <button type="submit" class="generate-btn" id="generateBtn">
                <i class="fas fa-file-pdf"></i>
                Generate Report
            </button>
        </form>
        
        <div id="status" class="status" style="display: none;"></div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const form = document.getElementById('reportForm');
            const periodSelect = document.getElementById('periodType');
            const customDateRange = document.getElementById('customDateRange');
            const generateBtn = document.getElementById('generateBtn');
            const status = document.getElementById('status');
            
            // Show/hide custom date range
            periodSelect.addEventListener('change', function() {
                if (this.value === 'custom') {
                    customDateRange.style.display = 'block';
                } else {
                    customDateRange.style.display = 'none';
                }
            });
            
            // Handle form submission
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(form);
                const params = new URLSearchParams();
                
                for (let [key, value] of formData.entries()) {
                    if (value) {
                        params.append(key, value);
                    }
                }
                
                // Show loading status
                showStatus('Generating report... This may take a few minutes.', 'loading');
                generateBtn.disabled = true;
                generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
                
                try {
                    const response = await fetch(`/reports/generate?${params.toString()}`);
                    const result = await response.json();
                    
                    if (result.success) {
                        showStatus(
                            `Report generated successfully! 
                            <a href="/reports/download/${result.filename}" class="download-link" target="_blank">
                                <i class="fas fa-download"></i> Download PDF
                            </a>`, 
                            'success'
                        );
                    } else {
                        showStatus(`Error: ${result.error}`, 'error');
                    }
                } catch (error) {
                    showStatus(`Network error: ${error.message}`, 'error');
                } finally {
                    generateBtn.disabled = false;
                    generateBtn.innerHTML = '<i class="fas fa-file-pdf"></i> Generate Report';
                }
            });
            
            function showStatus(message, type) {
                status.innerHTML = message;
                status.className = `status ${type}`;
                status.style.display = 'block';
                
                // Auto hide success/error after 10 seconds
                if (type !== 'loading') {
                    setTimeout(() => {
                        status.style.display = 'none';
                    }, 10000);
                }
            }
            
            // Set default dates for custom range
            const now = new Date();
            const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
            
            document.getElementById('startDate').value = weekAgo.toISOString().slice(0, 16);
            document.getElementById('endDate').value = now.toISOString().slice(0, 16);
        });
    </script>
</body>
</html>
    """
    return template

@report_bp.route('/generate')
def generate_report():
    """API endpoint untuk generate report"""
    try:
        # Get parameters
        period_type = request.args.get('period_type', 'daily')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Parse dates if provided
        start_dt = None
        end_dt = None
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except:
                pass
                
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except:
                pass
        
        logger.info(f"Generating {period_type} report from {start_dt} to {end_dt}")
        
        # Generate report
        output_file = report_generator.generate_report(
            period_type=period_type,
            start_date=start_dt,
            end_date=end_dt
        )
        
        if output_file and os.path.exists(output_file):
            # Move to reports directory
            reports_dir = os.path.join(os.getcwd(), 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            filename = os.path.basename(output_file)
            new_path = os.path.join(reports_dir, filename)
            
            # Move file
            if output_file != new_path:
                os.rename(output_file, new_path)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'message': 'Report generated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate report - no data available or database error'
            }), 500
            
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}'
        }), 500

@report_bp.route('/download/<filename>')
def download_report(filename):
    """Download generated report"""
    try:
        reports_dir = os.path.join(os.getcwd(), 'reports')
        file_path = os.path.join(reports_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Security check - only allow PDF files
        if not filename.endswith('.pdf'):
            return jsonify({'error': 'Invalid file type'}), 400
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        return jsonify({'error': 'Download error'}), 500

@report_bp.route('/list')
def list_reports():
    """List available reports"""
    try:
        reports_dir = os.path.join(os.getcwd(), 'reports')
        
        if not os.path.exists(reports_dir):
            return jsonify({'reports': []})
        
        reports = []
        for filename in os.listdir(reports_dir):
            if filename.endswith('.pdf'):
                file_path = os.path.join(reports_dir, filename)
                stat = os.stat(file_path)
                
                reports.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'download_url': f'/reports/download/{filename}'
                })
        
        # Sort by creation time (newest first)
        reports.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({'reports': reports})
        
    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        return jsonify({'error': 'Error listing reports'}), 500

@report_bp.route('/preview/<filename>')
def preview_report(filename):
    """Preview report in browser"""
    try:
        reports_dir = os.path.join(os.getcwd(), 'reports')
        file_path = os.path.join(reports_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            file_path,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error previewing report: {e}")
        return jsonify({'error': 'Preview error'}), 500

@report_bp.route('/api/summary')
def report_summary():
    """Get summary statistics for reports"""
    try:
        # Get basic stats from current data
        data = db_manager.get_report_data('daily')
        
        if not data or not data['phase_data']:
            return jsonify({
                'total_phases': 0,
                'total_power': 0,
                'total_energy': 0,
                'last_update': None
            })
        
        # Calculate summary
        total_power = sum(float(phase.get('avg_power', 0) or 0) for phase in data['phase_data'])
        total_energy = sum(float(phase.get('energy_consumed', 0) or 0) for phase in data['phase_data'])
        
        return jsonify({
            'total_phases': len(data['phase_data']),
            'total_power': round(total_power, 2),
            'total_energy': round(total_energy, 3),
            'last_update': data['end_date'].isoformat(),
            'period_start': data['start_date'].isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting report summary: {e}")
        return jsonify({'error': 'Error getting summary'}), 500

# Cleanup old reports (optional background task)
def cleanup_old_reports(days_to_keep=30):
    """Remove reports older than specified days"""
    try:
        reports_dir = os.path.join(os.getcwd(), 'reports')
        if not os.path.exists(reports_dir):
            return
        
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        
        for filename in os.listdir(reports_dir):
            if filename.endswith('.pdf'):
                file_path = os.path.join(reports_dir, filename)
                if os.path.getctime(file_path) < cutoff_time.timestamp():
                    os.unlink(file_path)
                    logger.info(f"Deleted old report: {filename}")
                    
    except Exception as e:
        logger.error(f"Error cleaning up old reports: {e}")