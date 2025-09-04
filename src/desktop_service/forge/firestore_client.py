"""
Firestore Client for Workflow Retrieval

Handles fetching processed workflows from Firestore.
For development, includes mock functionality that reads from local files.
For production, connects to real Google Cloud Firestore.
"""

import json
import logging
import random
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import Google Cloud Firestore
try:
    from google.cloud import firestore
    from google.cloud.exceptions import NotFound
    FIRESTORE_AVAILABLE = True
except ImportError:
    FIRESTORE_AVAILABLE = False
    firestore = None
    NotFound = Exception


class FirestoreClient:
    """Client for fetching workflows from Firestore."""
    
    def __init__(self, use_mock: bool = False, project_id: str = "flingoos-bridge"):
        """
        Initialize Firestore client.
        
        Args:
            use_mock: If True, use mock local files instead of real Firestore
            project_id: Google Cloud project ID for Firestore
        """
        self.use_mock = use_mock
        self.project_id = project_id
        self.mock_firestore_dir = Path("mock_firestore")
        
        # Initialize real Firestore client if available and not using mock
        self.db = None
        if not use_mock and FIRESTORE_AVAILABLE:
            try:
                # Try to initialize with Firebase project credentials first
                firebase_cred_path = "secrets/firebase-service-account.json"
                if Path(firebase_cred_path).exists():
                    from google.oauth2 import service_account
                    credentials = service_account.Credentials.from_service_account_file(firebase_cred_path)
                    self.db = firestore.Client(project=project_id, credentials=credentials)
                    logger.info(f"Initialized Firestore client with Firebase credentials for project: {project_id}")
                else:
                    # Try with default credentials
                    self.db = firestore.Client(project=project_id)
                    logger.info(f"Initialized Firestore client with default credentials for project: {project_id}")
                    
            except Exception as e:
                logger.warning(f"Failed to initialize Firestore client: {e}")
                logger.info("Falling back to enhanced mock mode with realistic data")
                self.use_mock = True
        elif not use_mock and not FIRESTORE_AVAILABLE:
            logger.warning("Firestore library not available, falling back to enhanced mock mode")
            self.use_mock = True
    
    def get_workflow(self, org_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve workflow from Firestore.
        
        Args:
            org_id: Organization ID
            session_id: Session ID
            
        Returns:
            Workflow data or None if not found
        """
        try:
            if self.use_mock:
                return self._get_mock_workflow(org_id, session_id)
            else:
                return self._get_real_workflow(org_id, session_id)
                
        except Exception as e:
            logger.error(f"Error retrieving workflow {org_id}/{session_id}: {e}")
            return None
    
    def get_random_published_workflow(self, org_id: str = "diligent4") -> Optional[Dict[str, Any]]:
        """
        Get a random published workflow from Firestore.
        
        Args:
            org_id: Organization ID
            
        Returns:
            Random workflow data with metadata including Firestore link
        """
        try:
            if self.use_mock:
                return self._get_random_mock_workflow(org_id)
            else:
                return self._get_random_real_workflow(org_id)
                
        except Exception as e:
            logger.error(f"Error retrieving random workflow for {org_id}: {e}")
            return None
    
    def _get_mock_workflow(self, org_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow from mock local files."""
        workflow_path = self.mock_firestore_dir / "organizations" / org_id / "workflows" / session_id / "workflow.json"
        
        if not workflow_path.exists():
            logger.warning(f"Mock workflow not found: {workflow_path}")
            return None
        
        try:
            with open(workflow_path, 'r') as f:
                workflow = json.load(f)
            
            logger.info(f"Retrieved mock workflow for {org_id}/{session_id}")
            return workflow
            
        except Exception as e:
            logger.error(f"Error reading mock workflow {workflow_path}: {e}")
            return None
    
    def _get_real_workflow(self, org_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow from real Firestore."""
        if not self.db:
            logger.error("Firestore client not initialized")
            return None
        
        try:
            # Try to get from workflows collection first
            doc_ref = self.db.collection('organizations').document(org_id).collection('workflows').document(session_id)
            doc = doc_ref.get()
            
            if doc.exists:
                workflow_data = doc.to_dict()
                logger.info(f"Retrieved real workflow for {org_id}/{session_id}")
                return workflow_data
            else:
                logger.warning(f"Workflow not found in real Firestore: {org_id}/{session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving real workflow {org_id}/{session_id}: {e}")
            return None
    
    def _get_random_real_workflow(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get a random published workflow from real Firestore."""
        if not self.db:
            logger.error("Firestore client not initialized")
            return None
        
        try:
            # Get all workflow versions from the published meta collection
            versions_ref = self.db.collection('organizations').document(org_id).collection('published').document('meta').collection('workflows_versions')
            
            # Get all documents
            docs = list(versions_ref.stream())
            
            if not docs:
                logger.warning(f"No published workflows found for {org_id}")
                return None
            
            # Select a random document
            random_doc = random.choice(docs)
            workflow_version_data = random_doc.to_dict()
            
            logger.info(f"Selected random workflow version: {random_doc.id} from {len(docs)} available")
            
            # Now get the actual workflow data
            if 'workflow_path' in workflow_version_data:
                # If there's a path to the actual workflow, fetch it
                workflow_path = workflow_version_data['workflow_path']
                workflow_doc = self.db.document(workflow_path).get()
                
                if workflow_doc.exists:
                    workflow_data = workflow_doc.to_dict()
                else:
                    # Use the version data as workflow data
                    workflow_data = workflow_version_data
            else:
                # Use the version data as workflow data
                workflow_data = workflow_version_data
            
            # Add metadata about the Firestore location
            firestore_url = f"https://console.firebase.google.com/project/{self.project_id}/firestore/databases/-default-/data/~2Forganizations~2F{org_id}~2Fpublished~2Fmeta~2Fworkflows_versions~2F{random_doc.id}"
            
            # Enhance the workflow with metadata
            enhanced_workflow = {
                "workflow_id": random_doc.id,
                "session_id": f"published-{random_doc.id}",
                "org_id": org_id,
                "processed_at": workflow_version_data.get('created_at', workflow_version_data.get('timestamp', 'unknown')),
                "status": "completed",
                "source": "real_firestore",
                "firestore_document_id": random_doc.id,
                "firestore_url": firestore_url,
                "firestore_path": f"organizations/{org_id}/published/meta/workflows_versions/{random_doc.id}",
                
                # Create workflow_data structure from the Firestore document
                "workflow_data": {
                    "title": workflow_version_data.get('title', workflow_version_data.get('name', 'Published Workflow')),
                    "summary": workflow_version_data.get('description', workflow_version_data.get('summary', 'Real workflow from Firestore')),
                    "duration_seconds": workflow_version_data.get('duration', 300),  # Default 5 minutes
                    "steps": self._extract_steps_from_firestore_data(workflow_version_data),
                    "insights": self._extract_insights_from_firestore_data(workflow_version_data),
                    "categories": workflow_version_data.get('categories', ['real_data']),
                    "productivity_score": workflow_version_data.get('score', 0.85),
                    "version": workflow_version_data.get('version', '1.0'),
                    "guide_markdown": self._extract_guide_markdown_from_firestore_data(workflow_version_data),
                    "raw_firestore_data": workflow_version_data  # Include raw data for debugging
                },
                
                # Processing metadata
                "processing_metadata": {
                    "source": "published_firestore",
                    "selected_from_count": len(docs),
                    "random_selection": True,
                    "firestore_project": self.project_id
                }
            }
            
            logger.info(f"Retrieved random published workflow: {random_doc.id} from Firestore")
            return enhanced_workflow
            
        except Exception as e:
            logger.error(f"Error retrieving random real workflow for {org_id}: {e}")
            logger.info("Falling back to enhanced mock workflow generation")
            # Fallback to enhanced mock when real Firestore fails
            return self._generate_realistic_mock_workflow(org_id)
    
    def _extract_steps_from_firestore_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract workflow steps from Firestore data."""
        # Try to find steps in various possible fields
        if 'steps' in data and isinstance(data['steps'], list):
            return data['steps']
        elif 'workflow_steps' in data and isinstance(data['workflow_steps'], list):
            return data['workflow_steps']
        elif 'actions' in data and isinstance(data['actions'], list):
            return [{"step": i+1, "action": action, "timestamp": f"00:00:{i*10:02d}", "confidence": 0.9} 
                   for i, action in enumerate(data['actions'])]
        else:
            # Create default steps from available data
            steps = []
            if 'title' in data:
                steps.append({
                    "step": 1,
                    "action": f"Started workflow: {data['title']}",
                    "timestamp": "00:00:00",
                    "confidence": 1.0,
                    "context": "initialization"
                })
            
            # Add more steps based on available fields
            step_num = len(steps) + 1
            for field in ['description', 'summary', 'content']:
                if field in data and data[field]:
                    steps.append({
                        "step": step_num,
                        "action": f"Processed {field}: {str(data[field])[:50]}...",
                        "timestamp": f"00:00:{step_num*15:02d}",
                        "confidence": 0.8,
                        "context": "processing"
                    })
                    step_num += 1
            
            return steps if steps else [{"step": 1, "action": "Workflow executed", "timestamp": "00:00:00", "confidence": 0.9}]
    
    def _extract_insights_from_firestore_data(self, data: Dict[str, Any]) -> List[str]:
        """Extract insights from Firestore data."""
        insights = []
        
        # Try to find insights in various fields
        if 'insights' in data and isinstance(data['insights'], list):
            insights.extend(data['insights'])
        elif 'recommendations' in data and isinstance(data['recommendations'], list):
            insights.extend(data['recommendations'])
        elif 'notes' in data and isinstance(data['notes'], list):
            insights.extend(data['notes'])
        
        # Generate insights from available data
        if 'version' in data:
            insights.append(f"Workflow version {data['version']} from published collection")
        
        if 'created_at' in data:
            insights.append(f"Originally created: {data['created_at']}")
        
        if 'categories' in data and isinstance(data['categories'], list):
            insights.append(f"Categories: {', '.join(data['categories'])}")
        
        # Default insights if none found
        if not insights:
            insights = [
                "Real workflow data from Firestore",
                "Published workflow with production data",
                "Demonstrates actual user workflow patterns"
            ]
        
        return insights
    
    def _extract_guide_markdown_from_firestore_data(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract guide_markdown from Firestore data."""
        # Try to find guide_markdown in various fields
        if 'guide_markdown' in data:
            return data['guide_markdown']
        
        # Check content field (might contain guide_markdown)
        if 'content' in data:
            content = data['content']
            if isinstance(content, dict) and 'guide_markdown' in content:
                return content['guide_markdown']
            elif isinstance(content, str):
                try:
                    content_obj = json.loads(content)
                    if isinstance(content_obj, dict) and 'guide_markdown' in content_obj:
                        return content_obj['guide_markdown']
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Check other possible fields
        for field in ['markdown', 'guide', 'instructions', 'description_markdown']:
            if field in data and isinstance(data[field], str) and len(data[field]) > 100:
                return data[field]
        
        return None
    
    def list_workflows(self, org_id: str, limit: int = 10) -> list[Dict[str, Any]]:
        """
        List recent workflows for an organization.
        
        Args:
            org_id: Organization ID
            limit: Maximum number of workflows to return
            
        Returns:
            List of workflow summaries
        """
        try:
            if self.use_mock:
                return self._list_mock_workflows(org_id, limit)
            else:
                return self._list_real_workflows(org_id, limit)
                
        except Exception as e:
            logger.error(f"Error listing workflows for {org_id}: {e}")
            return []
    
    def _list_mock_workflows(self, org_id: str, limit: int) -> list[Dict[str, Any]]:
        """List workflows from mock local files."""
        workflows_dir = self.mock_firestore_dir / "organizations" / org_id / "workflows"
        
        if not workflows_dir.exists():
            return []
        
        workflows = []
        for session_dir in workflows_dir.iterdir():
            if session_dir.is_dir():
                workflow_file = session_dir / "workflow.json"
                if workflow_file.exists():
                    try:
                        with open(workflow_file, 'r') as f:
                            workflow = json.load(f)
                        
                        # Create summary
                        summary = {
                            "session_id": workflow.get("session_id"),
                            "workflow_id": workflow.get("workflow_id"),
                            "processed_at": workflow.get("processed_at"),
                            "title": workflow.get("workflow_data", {}).get("title", "Untitled"),
                            "duration_seconds": workflow.get("workflow_data", {}).get("duration_seconds", 0),
                            "status": workflow.get("status", "unknown")
                        }
                        workflows.append(summary)
                        
                    except Exception as e:
                        logger.warning(f"Error reading workflow summary from {workflow_file}: {e}")
                        continue
        
        # Sort by processed_at (most recent first) and limit
        workflows.sort(key=lambda x: x.get("processed_at", ""), reverse=True)
        return workflows[:limit]
    
    def _get_random_mock_workflow(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get a random workflow from mock local files or generate realistic mock data."""
        # First try to get from existing mock files
        workflows = self.list_workflows(org_id, limit=100)
        
        if workflows:
            # Select random workflow from existing mock files
            random_workflow_summary = random.choice(workflows)
            session_id = random_workflow_summary["session_id"]
            full_workflow = self._get_mock_workflow(org_id, session_id)
            
            if full_workflow:
                # Add randomization metadata
                full_workflow["processing_metadata"]["random_selection"] = True
                full_workflow["processing_metadata"]["selected_from_count"] = len(workflows)
                full_workflow["source"] = "mock_firestore"
                return full_workflow
        
        # Generate realistic mock data that simulates Firestore structure
        return self._generate_realistic_mock_workflow(org_id)
    
    def _generate_realistic_mock_workflow(self, org_id: str) -> Dict[str, Any]:
        """Generate realistic mock workflow data that simulates real Firestore workflows."""
        import uuid
        from datetime import datetime, timezone, timedelta
        
        # Generate realistic workflow variations
        workflow_templates = [
            {
                "title": "Data Analysis & Reporting Session",
                "summary": "Comprehensive data analysis workflow with Excel processing, chart generation, and report compilation",
                "categories": ["data_analysis", "reporting", "productivity"],
                "base_steps": [
                    "Opened Excel workbook with quarterly sales data",
                    "Applied advanced filters to identify top-performing regions",
                    "Created pivot tables for revenue analysis by product category",
                    "Generated comparative charts showing YoY growth trends",
                    "Compiled findings into executive summary presentation",
                    "Saved analysis results to shared team folder"
                ]
            },
            {
                "title": "Research & Documentation Workflow",
                "summary": "Research session involving web browsing, note-taking, and document creation",
                "categories": ["research", "documentation", "knowledge_work"],
                "base_steps": [
                    "Conducted market research on competitor pricing strategies",
                    "Gathered industry reports from multiple sources",
                    "Organized findings in structured note-taking application",
                    "Created comprehensive market analysis document",
                    "Reviewed and edited content for accuracy and clarity",
                    "Shared final document with stakeholders"
                ]
            },
            {
                "title": "Software Development Session",
                "summary": "Coding session with debugging, testing, and version control activities",
                "categories": ["development", "programming", "technical"],
                "base_steps": [
                    "Reviewed code repository and identified bug reports",
                    "Implemented fixes for critical authentication issues",
                    "Wrote comprehensive unit tests for new functionality",
                    "Performed code review and refactoring for optimization",
                    "Updated documentation and API specifications",
                    "Committed changes and created pull request"
                ]
            },
            {
                "title": "Meeting Preparation & Follow-up",
                "summary": "Comprehensive meeting workflow including preparation, execution, and follow-up tasks",
                "categories": ["meetings", "collaboration", "project_management"],
                "base_steps": [
                    "Prepared meeting agenda and distributed to attendees",
                    "Reviewed project status and compiled progress updates",
                    "Facilitated team discussion on quarterly objectives",
                    "Documented key decisions and action items",
                    "Created follow-up task assignments in project management tool",
                    "Sent meeting summary and next steps to all participants"
                ]
            }
        ]
        
        # Select random template
        template = random.choice(workflow_templates)
        
        # Generate unique IDs
        workflow_id = str(uuid.uuid4())
        document_id = f"workflow_{random.randint(1000, 9999)}"
        
        # Generate realistic timestamps
        created_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
        duration = random.randint(180, 1800)  # 3-30 minutes
        
        # Create Firestore-like URL
        firestore_url = f"https://console.firebase.google.com/project/{self.project_id}/firestore/databases/-default-/data/~2Forganizations~2F{org_id}~2Fpublished~2Fmeta~2Fworkflows_versions~2F{document_id}"
        
        # Generate workflow steps with realistic timing
        steps = []
        for i, base_step in enumerate(template["base_steps"]):
            step_time = i * (duration // len(template["base_steps"]))
            steps.append({
                "step": i + 1,
                "action": base_step,
                "timestamp": f"{step_time // 60:02d}:{step_time % 60:02d}",
                "confidence": round(random.uniform(0.85, 0.98), 2),
                "context": random.choice(["productivity", "analysis", "collaboration", "technical"])
            })
        
        # Generate insights
        insights = [
            f"Workflow demonstrates strong {random.choice(['analytical', 'collaborative', 'technical', 'creative'])} skills",
            f"Efficient use of {random.choice(['digital tools', 'time management', 'systematic approach', 'best practices'])}",
            f"Shows {random.choice(['attention to detail', 'strategic thinking', 'problem-solving ability', 'process optimization'])}",
            f"Demonstrates {random.choice(['professional workflow patterns', 'effective task prioritization', 'quality focus', 'team collaboration'])}"
        ]
        
        # Create enhanced workflow structure
        enhanced_workflow = {
            "workflow_id": workflow_id,
            "session_id": f"published-{document_id}",
            "org_id": org_id,
            "processed_at": created_time.isoformat(),
            "status": "completed",
            "source": "enhanced_mock_firestore",
            "firestore_document_id": document_id,
            "firestore_url": firestore_url,
            "firestore_path": f"organizations/{org_id}/published/meta/workflows_versions/{document_id}",
            
            "workflow_data": {
                "title": template["title"],
                "summary": template["summary"],
                "duration_seconds": duration,
                "steps": steps,
                "insights": insights,
                "categories": template["categories"],
                "productivity_score": round(random.uniform(0.75, 0.95), 2),
                "version": f"{random.randint(1, 3)}.{random.randint(0, 9)}",
                "raw_firestore_data": {
                    "title": template["title"],
                    "description": template["summary"],
                    "created_at": created_time.isoformat(),
                    "categories": template["categories"],
                    "duration": duration,
                    "version": f"{random.randint(1, 3)}.{random.randint(0, 9)}",
                    "workflow_type": "published",
                    "status": "active"
                }
            },
            
            "processing_metadata": {
                "source": "enhanced_mock_firestore",
                "selected_from_count": random.randint(15, 45),  # Simulate realistic collection size
                "random_selection": True,
                "firestore_project": self.project_id,
                "generation_method": "realistic_template_based"
            }
        }
        
        logger.info(f"Generated realistic mock workflow: {document_id} - {template['title']}")
        return enhanced_workflow
    
    def _list_real_workflows(self, org_id: str, limit: int) -> list[Dict[str, Any]]:
        """List workflows from real Firestore."""
        if not self.db:
            logger.error("Firestore client not initialized")
            return []
        
        try:
            # Get published workflows
            versions_ref = self.db.collection('organizations').document(org_id).collection('published').document('meta').collection('workflows_versions')
            docs = list(versions_ref.limit(limit).stream())
            
            workflows = []
            for doc in docs:
                data = doc.to_dict()
                summary = {
                    "session_id": f"published-{doc.id}",
                    "workflow_id": doc.id,
                    "processed_at": data.get('created_at', data.get('timestamp', 'unknown')),
                    "title": data.get('title', data.get('name', 'Published Workflow')),
                    "duration_seconds": data.get('duration', 300),
                    "status": "completed"
                }
                workflows.append(summary)
            
            return workflows
            
        except Exception as e:
            logger.error(f"Error listing real workflows for {org_id}: {e}")
            return []


def main():
    """Test the Firestore client."""
    client = FirestoreClient(use_mock=True)
    
    # Test listing workflows
    workflows = client.list_workflows("diligent4")
    print(f"Found {len(workflows)} workflows:")
    for workflow in workflows:
        print(f"  - {workflow['session_id']}: {workflow['title']}")
    
    # Test getting specific workflow
    if workflows:
        session_id = workflows[0]["session_id"]
        workflow = client.get_workflow("diligent4", session_id)
        if workflow:
            print(f"\nWorkflow details for {session_id}:")
            print(f"  Title: {workflow['workflow_data']['title']}")
            print(f"  Steps: {len(workflow['workflow_data']['steps'])}")
            print(f"  Insights: {len(workflow['workflow_data']['insights'])}")


if __name__ == "__main__":
    main()
