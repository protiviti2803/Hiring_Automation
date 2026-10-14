# Hiring Manager Interview Questionnaire

This document provides a set of high-level and functional questions that hiring managers can ask candidates. Each question is accompanied by a concise, 1-2 line guideline answer.

---

## 1. High-Level Questions (Behavioral, Leadership & Strategy)

### Q1: How do you handle conflicting requirements from two key business stakeholders?
*   **Answer:** I set up a joint alignment meeting to walk through the trade-offs of each requirement, helping them reach a consensus based on project ROI and timelines. If consensus isn't reached, I escalate to the steering committee with a data-driven recommendation.

### Q2: What is your approach to managing scope creep during the middle of a development sprint?
*   **Answer:** I log the new request in the product backlog, evaluate its impact on current delivery timelines, and negotiate with product owners to either swap it with an existing item of equal complexity or defer it to the next sprint.

### Q3: How do you ensure high quality and standard compliance when working under tight deadlines?
*   **Answer:** I prioritize critical path deliverables, enforce strict automated unit testing and CI/CD pipelines, and conduct peer code reviews on core components while leaving non-critical refactoring for technical debt cycles.

### Q4: Can you describe a time when a project release failed, and how you managed the recovery?
*   **Answer:** We immediately executed our rollback script to restore the stable production environment, then gathered the team for a post-mortem root cause analysis, resolving the issue and adding safety checks to prevent a recurrence.

### Q5: How do you keep yourself updated on emerging technologies like GenAI, and how do you decide when to apply them?
*   **Answer:** I follow industry newsletters, research papers, and build hands-on prototypes. I only recommend applying them when they address a clear business bottleneck, such as automating repetitive documentation or search.

---

## 2. Functional & Domain-Level Questions (System Design, DB & APIs)

### Q6: What is the difference between SWIFT, RTGS, and NEFT payment systems?
*   **Answer:** SWIFT is a global secure messaging network for international bank transfers; RTGS is a real-time, high-value settlement system for domestic transfers; NEFT is a batch-settled, low-to-medium value domestic transfer system.

### Q7: How do you secure APIs from unauthorized access and cross-site scripting (XSS) attacks?
*   **Answer:** I implement OAuth2/JWT token authentication, restrict access using HTTPS/TLS, enforce strict Input Validation and CORS policies, and sanitize all dynamic database queries.

### Q8: When designing a microservices architecture, how do you handle distributed transactions?
*   **Answer:** I avoid two-phase commits to maintain performance, and instead apply the Saga Pattern using event-driven orchestration or choreography to trigger compensating actions if a step fails.

### Q9: How do you optimize a database query that is experiencing significant response delays?
*   **Answer:** I run an execution plan (`EXPLAIN`) to locate bottlenecks, add appropriate database indexes on frequently filtered columns, and cache hot data in Redis to reduce direct DB hits.

### Q10: What is the difference between REST and gRPC, and when would you choose one over the other?
*   **Answer:** REST uses HTTP/1.1 and JSON, making it ideal for public-facing client-to-server APIs. gRPC uses HTTP/2 and Protocol Buffers, offering low latency and high throughput, which makes it perfect for internal microservices communication.
