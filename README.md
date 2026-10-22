# CivicSense 🏙️
### Smarter Cities Start with Every Citizen.

**CivicSense** is an AI-powered civic issue reporting and resolution platform designed to help citizens report local infrastructure problems and help administrators organize, prioritize, and track complaints through a centralized system.

From potholes and garbage accumulation to drainage issues and broken streetlights, CivicSense aims to make civic reporting more intelligent, transparent, and accountable.

---

## 🚀 Problem Statement

Citizens often face difficulties reporting civic issues and tracking their resolution. Fragmented reporting channels, duplicate complaints, inconsistent prioritization, and limited visibility into complaint status can make civic issue management inefficient.

CivicSense addresses these challenges by bringing civic reporting, AI-assisted analysis, location intelligence, and administrative review into one platform.

## 💡 Our Solution

CivicSense provides a centralized workflow that transforms citizen reports into structured, trackable civic tickets.

- Submit civic complaints with descriptions and optional image evidence.
- Associate reports with geographical locations.
- Use AI-assisted text analysis to suggest issue categories.
- Identify potential duplicate complaints.
- Generate explainable priority scores.
- Enable administrators to review reports and manage complaint status.
- Track tickets and maintain an audit trail of important actions.

*AI-generated suggestions support administrative decisions; they do not replace human review.*

## ✨ Key Features

### 📝 Civic Issue Reporting
Submit complaints about common civic problems through a centralized reporting interface.

### 📍 Geospatial Intelligence
Use PostgreSQL and PostGIS to store geographical information and support location-based queries.

### 🤖 AI-Assisted Classification
Use MiniLM-based text embeddings and domain-specific rules to help categorize incoming complaints.

### 🔄 Duplicate Detection
Identify potentially related complaints using text similarity, geographical distance, and recency.

### ⚡ Explainable Priority Scoring
Evaluate complaints using configurable factors to help administrators prioritize their work.

### 🛠️ Administrative Dashboard
Support complaint review, category correction, duplicate management, assignment workflows, and status updates.

### 🎫 Complaint Tracking
Provide ticket-based status lookup so citizens can follow the progress of their reports.

### 📊 Civic Operations Insights
Support operational features such as hotspot analysis, department routing, workload views, and service-level agreement (SLA) tracking, as documented in the project.

### 🖼️ Optional Image Intelligence
CLIP-based image classification can be enabled as an optional component. It is disabled by default in the documented configuration.

## 🧠 AI Workflow

CivicSense combines language understanding with configurable business rules to assist civic issue management.

1. **Input:** Receive a complaint description and optional image.
2. **Text Analysis:** Generate semantic embeddings using MiniLM and compare the report against category representations.
3. **Rule-Based Evidence:** Apply domain-specific keyword rules to supplement text similarity.
4. **Priority Assessment:** Calculate a score from configured priority factors.
5. **Duplicate Matching:** Compare text similarity, geographical proximity, and report recency.
6. **Human Review:** Allow administrators to confirm or override classifications and review duplicate suggestions.
7. **Tracking:** Maintain ticket status and relevant audit events.

No model accuracy or real-world performance figures are claimed without evaluation.

## 🏗️ Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite |
| UI and Styling | Tailwind CSS |
| Maps and Visualization | React Leaflet, Recharts |
| Backend | Python, FastAPI |
| ORM | SQLAlchemy |
| Database | PostgreSQL |
| Geospatial Processing | PostGIS |
| NLP and Semantic Similarity | Sentence Transformers, MiniLM |
| Optional Computer Vision | CLIP, Transformers |
| Containerization | Docker, Docker Compose |

*The stack and optional components are based on the repository's documented configuration.*

## 🏛️ System Architecture

The platform follows a modular architecture:

```text
Citizen / Administrator
          |
          v
    React Frontend
          |
          v
    FastAPI Backend
          |
          v
   Business Logic Layer
    /      |       \
   AI   Priority   Duplicate
 Services Scoring   Detection
          |
          v
 PostgreSQL + PostGIS
          |
          v
 Complaint Records,
 Locations, Tickets
 and Audit Events
```

The frontend communicates with the backend through API endpoints. The backend coordinates complaint processing, AI-assisted analysis, priority assessment, administrative workflows, and database operations.

## ⚙️ Getting Started

### Prerequisites

Make sure the following tools are installed:

- Git
- Docker
- Docker Compose

### 1. Clone the Repository

```bash
git clone https://github.com/nitinkumargupta613-tech/hello-.git
```

### 2. Navigate to the Project Directory

```bash
cd hello-
```

### 3. Configure Environment Variables

Review the repository's environment configuration and setup documentation. Create the required environment file and configure database credentials, authentication settings, and optional AI components as needed.

Do not commit passwords, secret keys, or other sensitive configuration values.

### 4. Start the Application

If the repository's Docker Compose configuration is available, start the application using:

```bash
docker compose up --build
```

### 5. Access the Application

The documented local development ports are:

- **Frontend:** http://localhost:5173
- **Backend API documentation:** http://localhost:8000/docs

Check the repository configuration if your local ports differ.

## 🧪 Demo and Testing

The repository documentation describes seeded sample reports for demonstrating the platform locally.

A suggested demo workflow:

1. Submit a civic complaint.
2. Inspect the suggested category and priority breakdown.
3. Review potential duplicate complaints.
4. Open the administrative interface.
5. Confirm or override the suggested classification.
6. Update the ticket status.
7. Track the complaint using its ticket reference.

Seeded sample records are intended for demonstration and should not be interpreted as real citizen reports or evidence of production usage.

## 🔐 Security and Accountability

CivicSense is designed with administrative access controls and traceable complaint workflows.

Important considerations include:

- Password hashing and session-based authentication.
- Restricted access to administrative operations.
- Human review of uncertain AI classifications.
- Traceability of important status changes and review decisions.
- Secure handling of environment variables and credentials.

A production deployment should additionally undergo security testing, privacy review, and operational validation.

## 🌍 Expected Impact

CivicSense aims to support more effective civic issue management by enabling:

- Better organization of citizen complaints.
- Reduced duplicate administrative effort.
- More consistent complaint prioritization.
- Improved visibility into ticket progress.
- More informed resource allocation through location-based insights.
- Greater accountability through traceable workflows.

These are intended benefits and require real-world pilot evaluation before measurable impact can be claimed.

## 🔮 Future Roadmap

- Improve multilingual complaint understanding.
- Evaluate and calibrate classification and duplicate-detection models.
- Expand image-based issue analysis.
- Integrate with official municipal complaint systems where partnerships permit.
- Improve accessibility for citizens with different digital literacy levels.
- Add operational analytics based on validated civic data.
- Conduct pilot studies and measure real-world resolution outcomes.

## 🤝 Contributing

Contributions, suggestions, and improvements are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Implement and test your changes.
4. Submit a pull request describing your contribution.

## 👨‍💻 Team

**Project:** CivicSense  
**Team:** Gryffindor 
**Team Members:** Parv Mahajan, Pari Tiwari, Nitin Kumar  
**Institution:** MANIT


### CivicSense

**Report Better. Resolve Smarter. Build Better Cities.**

GitHub Repository: https://github.com/nitinkumargupta613-tech/hello-
