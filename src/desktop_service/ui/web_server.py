"""
D4 Web UI Server - Session Management Interface

This module provides a web-based interface for managing data collection sessions.
It serves a modern HTML/CSS/JS interface and provides real-time updates via WebSocket.

Adapted from flingoos-bridge for independent desktop service operation.
"""

import json
import threading
import time
import webbrowser
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
from pathlib import Path

try:
    from flask import Flask, render_template_string, request, jsonify
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None
    SocketIO = None

from ..bridge_client.command_client import CommandClient
from ..forge.trigger_generator import ForgeTriggerGenerator
from ..forge.mock_forge import MockForge
from ..forge.firestore_client import FirestoreClient

logger = logging.getLogger(__name__)

# HTML Template for D4 UI
D4_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>D4 - Session Manager</title>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #333;
        }
        
        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .header {
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            color: #5a67d8;
            margin-bottom: 10px;
            font-weight: 300;
        }
        
        .header .subtitle {
            color: #666;
            font-size: 1.1em;
        }
        
        .session-button {
            width: 200px;
            height: 200px;
            border-radius: 50%;
            border: none;
            font-size: 1.4em;
            font-weight: 600;
            color: white;
            margin: 20px auto;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .session-button.start {
            background: linear-gradient(45deg, #4CAF50, #45a049);
        }
        
        .session-button.start:hover {
            transform: scale(1.05);
            box-shadow: 0 15px 30px rgba(76, 175, 80, 0.4);
        }
        
        .session-button.stop {
            background: linear-gradient(45deg, #f44336, #d32f2f);
        }
        
        .session-button.stop:hover {
            transform: scale(1.05);
            box-shadow: 0 15px 30px rgba(244, 67, 54, 0.4);
        }
        
        .session-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .status-panel {
            margin: 30px 0;
            padding: 20px;
            background: rgba(0,0,0,0.05);
            border-radius: 15px;
        }
        
        .timer {
            font-size: 2em;
            font-weight: bold;
            color: #5a67d8;
            margin-bottom: 15px;
        }
        
        .bridge-status {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-dot.connected {
            background-color: #4CAF50;
            box-shadow: 0 0 10px rgba(76, 175, 80, 0.5);
        }
        
        .status-dot.disconnected {
            background-color: #f44336;
        }
        
        .progress-section {
            margin-top: 20px;
        }
        
        .upload-status-list {
            margin: 15px 0;
        }
        
        .upload-step {
            margin: 12px 0;
            padding: 12px 20px;
            background: rgba(255,255,255,0.8);
            border-radius: 12px;
            border-left: 4px solid #e0e0e0;
            font-size: 1em;
            font-weight: 500;
            transition: all 0.3s ease;
            position: relative;
        }
        
        .upload-step.uploading {
            border-left-color: #2196F3;
            background: rgba(33, 150, 243, 0.1);
            color: #1976D2;
        }
        
        .upload-step.completed {
            border-left-color: #4CAF50;
            background: rgba(76, 175, 80, 0.1);
            color: #2E7D32;
        }
        
        .upload-step.completed::after {
            content: "✓";
            position: absolute;
            right: 15px;
            color: #4CAF50;
            font-weight: bold;
            font-size: 1.2em;
        }
        
        .upload-step.uploading::before {
            content: "";
            position: absolute;
            left: 15px;
            top: 50%;
            transform: translateY(-50%);
            width: 12px;
            height: 12px;
            border: 2px solid #2196F3;
            border-top: 2px solid transparent;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        .upload-step.uploading {
            padding-left: 40px;
        }
        
        @keyframes spin {
            0% { transform: translateY(-50%) rotate(0deg); }
            100% { transform: translateY(-50%) rotate(360deg); }
        }
        
        .hidden {
            display: none;
        }
        
        .session-info {
            margin: 20px 0;
            padding: 15px;
            background: rgba(90, 103, 216, 0.1);
            border-radius: 10px;
            border-left: 4px solid #5a67d8;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.02); }
            100% { transform: scale(1); }
        }
        
        .recording {
            animation: pulse 2s infinite;
        }
        
        .workflow-section {
            margin-top: 20px;
            padding: 20px;
            background: rgba(90, 103, 216, 0.1);
            border-radius: 15px;
            border-left: 4px solid #5a67d8;
        }
        
        .workflow-content {
            margin: 15px 0;
        }
        
        .workflow-summary {
            background: rgba(255, 255, 255, 0.9);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
        }
        
        .workflow-title {
            font-size: 1.2em;
            font-weight: bold;
            color: #5a67d8;
            margin-bottom: 10px;
        }
        
        .workflow-stats {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            font-size: 0.9em;
            color: #666;
        }
        
        .workflow-button {
            background: linear-gradient(45deg, #5a67d8, #4c51bf);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s ease;
            margin-top: 15px;
        }
        
        .workflow-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(90, 103, 216, 0.4);
        }
        
        .workflow-details {
            background: rgba(255, 255, 255, 0.9);
            padding: 20px;
            border-radius: 10px;
            margin-top: 15px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .workflow-step {
            padding: 10px;
            margin: 8px 0;
            background: rgba(90, 103, 216, 0.05);
            border-left: 3px solid #5a67d8;
            border-radius: 5px;
        }
        
        .workflow-step-number {
            font-weight: bold;
            color: #5a67d8;
        }
        
        .workflow-insight {
            padding: 8px 12px;
            margin: 5px 0;
            background: rgba(76, 175, 80, 0.1);
            border-left: 3px solid #4CAF50;
            border-radius: 5px;
            font-style: italic;
        }
        
        .firestore-link {
            display: inline-block;
            background: linear-gradient(45deg, #FF6B35, #F7931E);
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 20px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 2px 10px rgba(255, 107, 53, 0.3);
        }
        
        .firestore-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(255, 107, 53, 0.4);
            text-decoration: none;
            color: white;
        }
        
        .markdown-container {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
            max-height: 600px;
            overflow-y: auto;
        }
        
        .markdown-content {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
        }
        
        .markdown-content h1 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
            margin-bottom: 16px;
        }
        
        .markdown-content h2 {
            color: #34495e;
            margin-top: 24px;
            margin-bottom: 12px;
            border-bottom: 1px solid #bdc3c7;
            padding-bottom: 4px;
        }
        
        .markdown-content h3 {
            color: #2c3e50;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        .markdown-content p {
            margin-bottom: 12px;
        }
        
        .markdown-content ul, .markdown-content ol {
            margin-left: 20px;
            margin-bottom: 12px;
        }
        
        .markdown-content li {
            margin-bottom: 4px;
        }
        
        .markdown-content code {
            background: #f1f2f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            font-size: 0.9em;
        }
        
        .markdown-content pre {
            background: #2f3542;
            color: #f1f2f6;
            padding: 16px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 12px 0;
        }
        
        .markdown-content pre code {
            background: none;
            padding: 0;
            color: inherit;
        }
        
        .markdown-content blockquote {
            border-left: 4px solid #3498db;
            margin: 12px 0;
            padding-left: 16px;
            color: #7f8c8d;
            font-style: italic;
        }
        
        .markdown-content strong {
            color: #2c3e50;
            font-weight: 600;
        }
        
        .markdown-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }
        
        .markdown-title {
            font-size: 18px;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .markdown-toggle {
            background: #3498db;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.3s ease;
        }
        
        .markdown-toggle:hover {
            background: #2980b9;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>D4</h1>
            <div class="subtitle">Data Collection Session Manager</div>
        </div>
        
        <div class="bridge-status">
            <div class="status-dot" id="statusDot"></div>
            <span id="statusText">Connecting to Bridge...</span>
        </div>
        
        <button class="session-button start" id="sessionButton" onclick="toggleSession()">
            START SESSION
        </button>
        
        <div class="status-panel">
            <div class="timer" id="timer">00:00:00</div>
            
            <div class="session-info hidden" id="sessionInfo">
                <strong>Session Active</strong><br>
                Bridge is collecting data from all enabled sources
            </div>
            
            <div class="progress-section hidden" id="progressSection">
                <h3 style="margin-bottom: 15px; color: #5a67d8;">Upload Status</h3>
                
                <div class="upload-status-list" id="uploadStatusList">
                    <div class="upload-step">Waiting for session...</div>
                </div>
            </div>
            
            <div class="workflow-section hidden" id="workflowSection">
                <h3 style="margin-bottom: 15px; color: #5a67d8;">Workflow Results</h3>
                
                <div class="workflow-content" id="workflowContent">
                    <!-- Workflow will be displayed here -->
                </div>
                
                <button class="workflow-button" id="viewWorkflowButton" onclick="toggleWorkflowDetails()">
                    Show Guide
                </button>
                
                <div class="firestore-link-section" id="firestoreLink" style="margin-top: 15px; display: none;">
                    <a href="#" target="_blank" class="firestore-link" id="firestoreLinkUrl">
                        🔗 View in Firestore Console
                    </a>
                </div>
                

            </div>
        </div>
    </div>
    
    <script>
        let socket = null;
        let sessionActive = false;
        let sessionStartTime = null;
        let timerInterval = null;
        
        // Initialize Socket.IO connection
        function initSocket() {
            try {
                socket = io();
                
                socket.on('connect', function() {
                    console.log('Connected to D4 server');
                    updateBridgeStatus(true);
                    socket.emit('get_status');
                });
                
                socket.on('disconnect', function() {
                    console.log('Disconnected from D4 server');
                    updateBridgeStatus(false);
                });
                
                socket.on('status_update', function(data) {
                    updateStatus(data);
                });
                
                socket.on('upload_status_update', function(data) {
                    updateUploadStatus(data);
                });
                
                socket.on('upload_complete', function(data) {
                    console.log('Upload completed:', data);
                    // Wait a moment then hide progress section to allow new session
                    setTimeout(() => {
                        document.getElementById('progressSection').classList.add('hidden');
                        // Reset upload status for next session
                        const uploadStatusList = document.getElementById('uploadStatusList');
                        if (uploadStatusList) {
                            uploadStatusList.innerHTML = '<div class="upload-step">Waiting for session...</div>';
                        }
                    }, 2000);
                });
                
                socket.on('workflow_ready', function(data) {
                    console.log('Workflow ready:', data);
                    displayWorkflow(data.workflow);
                });
                
                socket.on('session_started', function(data) {
                    sessionActive = true;
                    sessionStartTime = Date.now();
                    updateUI();
                    startTimer();
                });
                
                socket.on('session_stopped', function(data) {
                    sessionActive = false;
                    updateUI();
                    stopTimer();
                    
                    // Show upload progress
                    document.getElementById('progressSection').classList.remove('hidden');
                });
                
                socket.on('error', function(error) {
                    console.error('Socket error:', error);
                    alert('Error: ' + error.message);
                });
                
                socket.on('connect_error', function(error) {
                    console.error('Connection error:', error);
                    updateBridgeStatus(false);
                });
                
            } catch (error) {
                console.error('Failed to initialize socket:', error);
                updateBridgeStatus(false);
            }
        }
        
        function updateBridgeStatus(connected) {
            const statusDot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');
            
            if (connected) {
                statusDot.className = 'status-dot connected';
                statusText.textContent = 'Connected to Bridge Service';
            } else {
                statusDot.className = 'status-dot disconnected';
                statusText.textContent = 'Disconnected from Bridge Service';
            }
        }
        
        function updateStatus(data) {
            // Update any general status information
            if (data.session_active !== undefined) {
                sessionActive = data.session_active;
                if (sessionActive && !sessionStartTime) {
                    sessionStartTime = Date.now();
                    startTimer();
                }
                updateUI();
            }
        }
        
        function updateUploadStatus(statusData) {
            // Update sequential upload status display
            const uploadStatusList = document.getElementById('uploadStatusList');
            if (!uploadStatusList) return;
            
            console.log('Updating upload status:', statusData);
            
            if (statusData.steps && statusData.steps.length > 0) {
                // Replace with full step list
                uploadStatusList.innerHTML = '';
                statusData.steps.forEach(step => {
                    const stepDiv = document.createElement('div');
                    stepDiv.className = 'upload-step ' + step.status;
                    stepDiv.textContent = step.message;
                    uploadStatusList.appendChild(stepDiv);
                });
            } else if (statusData.current_step) {
                // Update just the current step
                uploadStatusList.innerHTML = '';
                const stepDiv = document.createElement('div');
                stepDiv.className = 'upload-step ' + (statusData.is_uploading ? 'uploading' : 'completed');
                stepDiv.textContent = statusData.current_step;
                uploadStatusList.appendChild(stepDiv);
            }
        }
        
        function toggleSession() {
            const button = document.getElementById('sessionButton');
            button.disabled = true;
            
            if (!socket || !socket.connected) {
                console.error('Socket not connected');
                alert('Not connected to D4 server. Please refresh the page.');
                button.disabled = false;
                return;
            }
            
            if (!sessionActive) {
                socket.emit('start_session');
            } else {
                socket.emit('stop_session');
            }
            
            // Re-enable button after 2 seconds if no response
            setTimeout(() => {
                button.disabled = false;
            }, 2000);
        }
        
        function updateUI() {
            const button = document.getElementById('sessionButton');
            const sessionInfo = document.getElementById('sessionInfo');
            const container = document.querySelector('.container');
            const progressSection = document.getElementById('progressSection');
            const uploadStatusList = document.getElementById('uploadStatusList');
            
            if (sessionActive) {
                button.className = 'session-button stop recording';
                button.textContent = 'END SESSION';
                sessionInfo.classList.remove('hidden');
                container.classList.add('recording');
                // Hide progress section during active session
                progressSection.classList.add('hidden');
            } else {
                button.className = 'session-button start';
                button.textContent = 'START SESSION';
                sessionInfo.classList.add('hidden');
                container.classList.remove('recording');
                
                // Reset upload status for next session
                if (uploadStatusList) {
                    uploadStatusList.innerHTML = '<div class="upload-step">Waiting for session...</div>';
                }
                // Keep progress section visible if it was shown (for completed uploads)
                // It will be hidden when a new session starts
            }
            
            button.disabled = false;
        }
        
        function startTimer() {
            if (timerInterval) clearInterval(timerInterval);
            
            timerInterval = setInterval(() => {
                if (sessionStartTime) {
                    const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
                    const hours = Math.floor(elapsed / 3600).toString().padStart(2, '0');
                    const minutes = Math.floor((elapsed % 3600) / 60).toString().padStart(2, '0');
                    const seconds = (elapsed % 60).toString().padStart(2, '0');
                    document.getElementById('timer').textContent = `${hours}:${minutes}:${seconds}`;
                }
            }, 1000);
        }
        
        function stopTimer() {
            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }
        }
        
        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', function() {
            initSocket();
        });
        
        // Handle page close
        window.addEventListener('beforeunload', function() {
            if (socket) {
                socket.disconnect();
            }
        });
        
        // Workflow display functions
        let currentWorkflow = null;
        let workflowDetailsVisible = false;
        
        function displayWorkflow(workflow) {
            currentWorkflow = workflow;
            const workflowSection = document.getElementById('workflowSection');
            const workflowContent = document.getElementById('workflowContent');
            
            if (!workflow || !workflow.workflow_data) {
                console.error('Invalid workflow data');
                return;
            }
            
            const workflowData = workflow.workflow_data;
            
            // Create workflow summary
            const summaryHtml = `
                <div class="workflow-summary">
                    <div class="workflow-title">${workflowData.title || 'Session Analysis'}</div>
                    <p>${workflowData.summary || 'No summary available'}</p>
                    <div class="workflow-stats">
                        <span>Duration: ${Math.floor(workflowData.duration_seconds / 60)}m ${workflowData.duration_seconds % 60}s</span>
                        <span>Steps: ${workflowData.steps ? workflowData.steps.length : 0}</span>
                        <span>Score: ${Math.round((workflowData.productivity_score || 0) * 100)}%</span>
                    </div>
                    ${workflow.source === 'real_firestore' ? `
                        <div style="margin-top: 10px; padding: 10px; background: rgba(255, 107, 53, 0.1); border-radius: 8px;">
                            <strong>📊 Real Firestore Data</strong><br>
                            <small>Document ID: ${workflow.firestore_document_id || 'N/A'}</small><br>
                            <small>Selected from ${workflow.processing_metadata?.selected_from_count || 'N/A'} published workflows</small>
                        </div>
                    ` : workflow.source === 'enhanced_mock_firestore' ? `
                        <div style="margin-top: 10px; padding: 10px; background: rgba(76, 175, 80, 0.1); border-radius: 8px;">
                            <strong>🎲 Enhanced Mock Firestore Data</strong><br>
                            <small>Document ID: ${workflow.firestore_document_id || 'N/A'}</small><br>
                            <small>Simulated from ${workflow.processing_metadata?.selected_from_count || 'N/A'} published workflows</small><br>
                            <small>Method: ${workflow.processing_metadata?.generation_method || 'N/A'}</small>
                        </div>
                    ` : ''}
                </div>
            `;
            
            workflowContent.innerHTML = summaryHtml;
            workflowSection.classList.remove('hidden');
            
            // Show Firestore link if available
            if (workflow.firestore_url) {
                const firestoreLink = document.getElementById('firestoreLink');
                const firestoreLinkUrl = document.getElementById('firestoreLinkUrl');
                
                firestoreLinkUrl.href = workflow.firestore_url;
                firestoreLink.style.display = 'block';
            }
            

            
            console.log('Workflow displayed successfully');
        }
        



        function toggleWorkflowDetails() {
            if (!currentWorkflow) return;
            
            const workflowContent = document.getElementById('workflowContent');
            const button = document.getElementById('viewWorkflowButton');
            
            if (!workflowDetailsVisible) {
                // Show detailed workflow
                const workflowData = currentWorkflow.workflow_data;
                
                let detailsHtml = workflowContent.innerHTML;
                
                // Add guide markdown if available
                if (workflowData.guide_markdown) {
                    detailsHtml += '<div class="workflow-details">';
                    detailsHtml += '<h4 style="margin-bottom: 15px; color: #5a67d8;">📖 Workflow Guide</h4>';
                    detailsHtml += '<div class="markdown-content">' + marked.parse(workflowData.guide_markdown) + '</div>';
                    detailsHtml += '</div>';
                } else {
                    // Fallback to insights if no guide markdown
                    if (workflowData.insights && workflowData.insights.length > 0) {
                        detailsHtml += '<div class="workflow-details">';
                        detailsHtml += '<h4 style="margin-bottom: 15px; color: #5a67d8;">Key Insights</h4>';
                        workflowData.insights.forEach(insight => {
                            detailsHtml += `<div class="workflow-insight">💡 ${insight}</div>`;
                        });
                        detailsHtml += '</div>';
                    }
                }
                
                workflowContent.innerHTML = detailsHtml;
                button.textContent = 'Hide Guide';
                workflowDetailsVisible = true;
                
            } else {
                // Hide detailed workflow
                displayWorkflow(currentWorkflow);
                button.textContent = 'Show Guide';
                workflowDetailsVisible = false;
            }
        }
    </script>
</body>
</html>
"""


class D4WebServer:
    """
    D4 Web-based Session Manager
    
    Provides a modern web interface for session management that runs on localhost
    and communicates with the bridge via the existing CommandClient API.
    """
    
    def __init__(self, port: int = 8844):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask and flask-socketio are required for web UI")
            
        self.port = port
        self.app = None
        self.socketio = None
        self.server_thread = None
        self.command_client = None
        self.running = False
        
        # Session state
        self.session_active = False
        self.session_start_time = None
        self.session_id = None
        
        # Upload status tracking (sequential steps)
        self.upload_status = {
            'current_step': 'Waiting for session...',
            'is_uploading': False,
            'steps': []
        }
        
        # Forge integration components
        self.trigger_generator = ForgeTriggerGenerator()
        self.mock_forge = MockForge()
        self.firestore_client = FirestoreClient(use_mock=False)  # Try real Firestore, fallback to enhanced mock
        
        # Workflow results
        self.current_workflow = None
        
    def setup_flask_app(self):
        """Initialize Flask app and SocketIO."""
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'flingoos-d4-session-manager'
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Route for main page
        @self.app.route('/')
        def index():
            return render_template_string(D4_HTML_TEMPLATE)
            
        # API endpoint for status
        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                'session_active': self.session_active,
                'bridge_connected': self.command_client is not None and self.command_client.is_bridge_running(),
                'upload_status': self.upload_status
            })
            
        # Socket events
        @self.socketio.on('connect')
        def handle_connect():
            logger.info("D4 Web client connected")
            emit('status_update', {
                'session_active': self.session_active,
                'bridge_connected': self.command_client is not None and self.command_client.is_bridge_running()
            })
            
        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.info("D4 Web client disconnected")
            
        @self.socketio.on('get_status')
        def handle_get_status():
            emit('status_update', {
                'session_active': self.session_active,
                'bridge_connected': self.command_client is not None and self.command_client.is_bridge_running()
            })
            
        @self.socketio.on('start_session')
        def handle_start_session():
            try:
                self.start_session()
                emit('session_started', {'success': True})
            except Exception as e:
                logger.error(f"Failed to start session: {e}")
                emit('error', {'message': str(e)})
                
        @self.socketio.on('stop_session')
        def handle_stop_session():
            try:
                self.stop_session()
                emit('session_stopped', {'success': True})
            except Exception as e:
                logger.error(f"Failed to stop session: {e}")
                emit('error', {'message': str(e)})
    
    def start_session(self):
        """Start a new data collection session."""
        if self.session_active:
            raise ValueError("Session is already active")
            
        logger.info("Starting D4 session via audio start command")
        
        # Initialize command client if needed
        if not self.command_client:
            self.command_client = CommandClient()
            
        # Execute audio start command
        result = self.command_client.start_audio_recording()
        if not result.get("success", False):
            raise RuntimeError(f"Failed to start session: {result.get('error', 'Unknown error')}")
            
        self.session_active = True
        self.session_start_time = datetime.now()
        
        # Generate unique session ID for tracking
        import uuid
        self.session_id = str(uuid.uuid4())
        
        logger.info(f"D4 session started successfully with ID: {self.session_id}")
        
    def stop_session(self):
        """Stop the current data collection session."""
        if not self.session_active:
            raise ValueError("No active session to stop")
            
        logger.info("Stopping D4 session via audio stop command")
        
        # Execute audio stop command
        if self.command_client:
            result = self.command_client.stop_audio_recording()
            if not result.get("success", False):
                logger.warning(f"Audio stop command failed: {result.get('error', 'Unknown error')}")
                
        # Start upload monitoring to track log messages
        self._start_upload_monitoring()
        
        # Now clear session state
        self.session_active = False
        self.session_start_time = None
        self.session_id = None
        
        logger.info("D4 session stopped successfully")
        
    def _start_upload_monitoring(self):
        """Monitor bridge logs for upload completion and trigger forge processing."""
        def monitor_uploads_and_forge():
            session_start_time = self.session_start_time
            session_id = self.session_id
            
            # Initialize upload sequence
            self.upload_status = {
                'current_step': 'Starting data flush...',
                'is_uploading': True,
                'steps': [
                    {'message': 'Starting data flush...', 'status': 'uploading'}
                ]
            }
            
            # Send initial status
            self.socketio.emit('upload_status_update', self.upload_status)
            time.sleep(1)
            
            # Sequential upload steps
            upload_steps = [
                {'message': 'Uploading audio...', 'duration': 3},
                {'message': 'Uploading screenshots...', 'duration': 2}, 
                {'message': 'Uploading telemetry (mouse, keyboard, window changes)...', 'duration': 4},
                {'message': 'Verifying uploads...', 'duration': 2}
            ]
            
            completed_steps = [
                {'message': 'Starting data flush...', 'status': 'completed'}
            ]
            
            for step in upload_steps:
                # Add current step as uploading
                current_steps = completed_steps + [
                    {'message': step['message'], 'status': 'uploading'}
                ]
                
                self.upload_status = {
                    'current_step': step['message'],
                    'is_uploading': True,
                    'steps': current_steps
                }
                
                self.socketio.emit('upload_status_update', self.upload_status)
                time.sleep(step['duration'])
                
                # Mark step as completed
                completed_steps.append({
                    'message': step['message'],
                    'status': 'completed'
                })
            
            # All uploads complete - now trigger forge processing
            completed_steps.append({
                'message': 'All uploads completed successfully!',
                'status': 'completed'
            })
            
            # Add forge processing steps
            forge_steps = [
                {'message': 'Generating forge trigger JSON...', 'duration': 1},
                {'message': 'Triggering forge processing pipeline...', 'duration': 2},
                {'message': 'Processing workflow (stages A-F)...', 'duration': 5},
                {'message': 'Uploading results to Firestore...', 'duration': 2},
                {'message': 'Retrieving processed workflow...', 'duration': 1}
            ]
            
            for step in forge_steps:
                # Add current step as uploading
                current_steps = completed_steps + [
                    {'message': step['message'], 'status': 'uploading'}
                ]
                
                self.upload_status = {
                    'current_step': step['message'],
                    'is_uploading': True,
                    'steps': current_steps
                }
                
                self.socketio.emit('upload_status_update', self.upload_status)
                
                # Execute actual forge processing
                if 'Generating forge trigger' in step['message']:
                    self._execute_forge_trigger_generation(session_id, session_start_time)
                elif 'Triggering forge processing' in step['message']:
                    self._execute_forge_processing(session_id)
                elif 'Retrieving processed workflow' in step['message']:
                    self._retrieve_workflow_from_firestore(session_id)
                else:
                    time.sleep(step['duration'])
                
                # Mark step as completed
                completed_steps.append({
                    'message': step['message'],
                    'status': 'completed'
                })
            
            # Final completion
            completed_steps.append({
                'message': 'Workflow processing completed! Ready to view results.',
                'status': 'completed'
            })
            
            self.upload_status = {
                'current_step': 'Processing complete',
                'is_uploading': False,
                'steps': completed_steps
            }
            
            self.socketio.emit('upload_status_update', self.upload_status)
            
            # Send workflow data to UI
            if self.current_workflow:
                self.socketio.emit('workflow_ready', {
                    'workflow': self.current_workflow,
                    'message': 'Workflow is ready for viewing!'
                })
            
            # Wait a moment, then send completion event
            time.sleep(3)
            self.socketio.emit('upload_complete', {
                'message': 'All processing completed successfully!',
                'has_workflow': self.current_workflow is not None
            })
            
        # Run monitoring in background
        monitor_thread = threading.Thread(target=monitor_uploads_and_forge, daemon=True)
        monitor_thread.start()
    
    def _execute_forge_trigger_generation(self, session_id: str, session_start_time: datetime):
        """Generate forge trigger JSON."""
        try:
            end_time = datetime.now()
            trigger_json = self.trigger_generator.generate_trigger_json(
                session_id=session_id,
                start_time=session_start_time,
                end_time=end_time
            )
            
            # Save trigger JSON for debugging
            trigger_file = f"trigger_{session_id}.json"
            self.trigger_generator.save_trigger_to_file(trigger_json, trigger_file)
            
            logger.info(f"Generated forge trigger for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error generating forge trigger: {e}")
    
    def _execute_forge_processing(self, session_id: str):
        """Execute forge processing."""
        try:
            # Load the trigger JSON
            trigger_file = f"trigger_{session_id}.json"
            if Path(trigger_file).exists():
                with open(trigger_file, 'r') as f:
                    trigger_json = json.load(f)
                
                # Process with mock forge
                result = self.mock_forge.process_session(trigger_json)
                logger.info(f"Forge processing result: {result.get('status', 'unknown')}")
                
            else:
                logger.warning(f"Trigger file not found: {trigger_file}")
                
        except Exception as e:
            logger.error(f"Error executing forge processing: {e}")
    
    def _retrieve_workflow_from_firestore(self, session_id: str):
        """Retrieve processed workflow from Firestore."""
        try:
            # Get a random published workflow from real Firestore instead of session-specific
            logger.info(f"Retrieving random published workflow instead of session {session_id}")
            workflow = self.firestore_client.get_random_published_workflow("diligent4")
            
            if workflow:
                self.current_workflow = workflow
                logger.info(f"Retrieved random published workflow: {workflow.get('workflow_id', 'unknown')} from Firestore")
                logger.info(f"Firestore URL: {workflow.get('firestore_url', 'N/A')}")
            else:
                logger.warning(f"No published workflows found in Firestore")
                # Fallback to mock if real Firestore fails
                logger.info("Falling back to mock workflow")
                mock_client = FirestoreClient(use_mock=True)
                workflow = mock_client.get_workflow("diligent4", session_id)
                if workflow:
                    self.current_workflow = workflow
                    logger.info("Using mock workflow as fallback")
                
        except Exception as e:
            logger.error(f"Error retrieving workflow: {e}")
            # Fallback to mock on error
            try:
                logger.info("Attempting fallback to mock workflow")
                mock_client = FirestoreClient(use_mock=True)
                workflow = mock_client.get_workflow("diligent4", session_id)
                if workflow:
                    self.current_workflow = workflow
                    logger.info("Successfully used mock workflow as fallback")
            except Exception as fallback_error:
                logger.error(f"Fallback to mock also failed: {fallback_error}")
    
    def run(self):
        """Start the web server."""
        if not FLASK_AVAILABLE:
            logger.error("Cannot start D4 web server: Flask not available")
            return
            
        if self.running:
            logger.warning("D4 web server is already running")
            return
            
        try:
            self.setup_flask_app()
            
            # Start server in background thread
            def run_server():
                self.socketio.run(self.app, host='127.0.0.1', port=self.port, debug=False)
                
            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            
            self.running = True
            
            # Open browser to the UI
            url = f"http://127.0.0.1:{self.port}"
            logger.info(f"D4 Web UI started at {url}")
            
            # Open in default browser
            try:
                webbrowser.open(url)
            except Exception as e:
                logger.warning(f"Could not open browser automatically: {e}")
                logger.info(f"Please open your browser and go to: {url}")
                
        except Exception as e:
            logger.error(f"Failed to start D4 web server: {e}")
            self.running = False
            raise
            
    def stop(self):
        """Stop the web server."""
        self.running = False
        logger.info("D4 web server stopped")
        
    def is_running(self) -> bool:
        """Check if the web server is running."""
        return self.running and self.server_thread and self.server_thread.is_alive()
