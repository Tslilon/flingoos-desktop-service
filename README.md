# Flingoos Desktop Service

**Session-based desktop UI for triggering data collection, processing, and workflow display**

A multi-tenant desktop service that coordinates between the Flingoos Bridge (data collection) and Forge Pipeline (data processing) to provide users with a seamless session-based workflow analysis experience.

## Architecture Overview

The desktop service acts as an orchestration layer between existing components:
- **Bridge**: Handles session-based data collection 
- **Forge**: Processes session data and generates workflows
- **Desktop Service**: Coordinates the flow and provides UI

## System Integration

This service integrates with existing repositories:
- `flingoos-bridge`: Session recording API integration
- `flingoos-bridge-backend-service`: Authentication and Forge API
- `flingoos-admin-panel-main`: Forge pipeline and Firestore integration

## Implementation Status

🚧 **In Development** 

**Documentation**:
- [ROADMAP.md](./ROADMAP.md) - Implementation plan
- [ROADMAP.pdf](./ROADMAP.pdf) - **PDF version for offline reference**

## Quick Start

*Coming soon - implementation in progress*

## Security

Uses existing enterprise-grade security:
- JWT tokens for service authentication
- Firebase Auth for user authentication  
- GCP Signed URLs for secure data uploads
- Role-based access control with multi-tenant support

---

**License**: Not open-source. All rights reserved © Diligent4 2025
