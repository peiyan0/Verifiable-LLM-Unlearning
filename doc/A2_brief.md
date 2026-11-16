**MAC5043**

# Data Management and Privacy Engineering

**ASSIGNMENT 2 (10%)**

*Tools, Technologies and Execution Roadmap for the Proposed Solution, with a Legal and Regulatory Compliance Verification Plan*

Assignment Brief, Section-by-Section Writing Guide, Marking Criteria and Exemplar Extracts

September 2026 Semester

|  |  |
| --- | --- |
| **Document contents** |  |
| **Part A** | Assignment brief: overview, learning outcomes, task steps, tool catalogue, compliance requirements, required structure, writing guide with examples, deliverables, checklist |
| **Part B** | Marking criteria: mark allocation, detailed rubric, penalties, weak-versus-strong examples, marking sheet |
| **Part C** | Exemplar extracts: tool selection matrix, Gantt chart and compliance verification table for the healthcare exemplar |
| **Appendices** | Tool selection matrix, work-breakdown structure, compliance verification checklist, risk register, repository README template and declaration |

**Briefing: Week 9 (23�27 November 2026) | Submission: 20 December 2026 (tentative)**

## PART A: ASSIGNMENT BRIEF

### A.1 Assignment Overview

Assignment 1 described **what** you will build and **why**. Assignment 2 specifies **how** you will build it and **how you will prove that it handles personal data lawfully**. You will turn your approved research proposal into an executable engineering plan: the concrete tools, libraries, platforms and datasets you will use, the implementation architecture, a week-by-week execution roadmap with an experiment plan, and a compliance verification plan that checks your data handling against legal and regulatory frameworks such as the GDPR and Malaysia's Personal Data Protection Act 2010 (as amended in 2024).

Assignment 2 is also a feasibility gate. You must show a working **proof of setup**: your development environment is built, your dataset is loaded and profiled, and your non-private baseline runs end to end. This ensures that the Case Study Report (50%) can be executed in Weeks 12�13.


**Figure A.1:** Where Assignment 2 sits in the MAC5043 assessment pathway **Table A.1:** Assessment summary

|  |  |
| --- | --- |
| **Item** | **Details** |
| **Course** | MAC5043 Data Management and Privacy Engineering (September 2026 semester) |
| **Assessment** | Assignment 2: tools, technologies, execution roadmap and compliance verification plan for your Assignment 1 proposal |
| **Weight** | 10% of the final course grade (marked out of 100 and scaled to 10) |
| **Course learning outcome** | CLO3: Verify that data handling complies with legal and regulatory frameworks and ensure compliance with regional data protection laws and ethical standards (A5, PLO11) |
| **Mode** | Individual |
| **Briefing** | Week 9 (23�27 November 2026) |
| **Submission** | Tentatively 20 December 2026 (end of Week 12), through the elearn submission system |
| **Length** | 3,000�4,000 words, excluding title page, tables, figure captions, references and appendices |
| **Deliverables** | (1) Report (.docx + PDF); (2) public or lecturer-shared Git repository link showing the proof of setup; (3) completed Appendices 1�5 |
| **Continuity rule** | Must implement the design approved in Assignment 1. Changes are allowed but must be listed and justified in the change log (Section 1) |
| **Related weeks** | Weeks 5�10: data integration, privacy engineering fundamentals, PETs, anonymisation, data ethics, legal and regulatory compliance (GDPR, regional requirements) |

### A.2 Learning Outcomes of this Assignment

On successful completion of this assignment you should be able to:

1. Derive functional, non-functional and privacy requirements from a research proposal and trace them to implementation components.
2. Select and justify tools, technologies and datasets using explicit, weighted criteria.
3. Map a system design onto a concrete implementation and deployment architecture.
4. Plan execution with a work-breakdown structure, milestones, dependencies and an experiment matrix.
5. Verify that the planned data handling complies with the GDPR, the PDPA and sectorspecific rules, and document the verification with evidence and tests (CLO3).
6. Manage technical, data, legal and schedule risks and set up a reproducible research repository.

### A.3 Task Description

#### Step 1: Revisit your proposal and record changes

Read the feedback on Assignment 1 and update your design. Record each change, its reason and its effect on objectives or metrics in a change-log table. If there are no changes, say so explicitly.

#### Step 2: Specify requirements

Convert your proposal into numbered requirements: functional (FR), non-functional (NFR) and privacy and compliance (PR). Each requirement must be verifiable, that is, it must have an acceptance test you can run or inspect in the Case Study.

**Example:** *PR3: No direct identifier (name, IC number, MRN) shall be stored outside the ingestion zone. Acceptance test: an automated scan of all downstream tables returns zero matches for identifier patterns.*

#### Step 3: Select tools, technologies and datasets

For each component of your design, shortlist at least two candidate tools and choose one using a weighted selection matrix (Appendix 1). Typical criteria are: fit to requirement, privacy guarantee offered, maturity and community support, documentation, licence, performance and scalability, cost, and learning curve. State the exact version you will use. The catalogue below lists commonly used open-source options; you may choose others.

**Table A.2:** Indicative catalogue of tools by component (not exhaustive; verify versions and licences yourself)

|  |  |
| --- | --- |
| **Component** | **Example tools and libraries** |
| **Storage and databases** | PostgreSQL (with pgcrypto, row-level security), MySQL, MongoDB (client-side field-level and queryable encryption), Neo4j, InfluxDB/TimescaleDB, SQLite, MinIO/S3-compatible object storage |
| **Integration and pipelines** | Python (pandas, Polars), Apache NiFi, Apache Kafka, Airbyte, dbt, Apache Airflow; standards such as HL7 FHIR, ISO 20022, GS1 |
| **Data quality and profiling** | Great Expectations, ydata-profiling, pandera |
| **Data modelling** | dbdiagram.io, draw.io, MySQL Workbench, pgModeler, PlantUML |
| **De-identification and anonymisation** | ARX Data Anonymization Tool, sdcMicro (R), Microsoft Presidio (PII detection and masking), keyed hashing (HMAC-SHA-256) for pseudonymisation |
| **Component** | **Example tools and libraries** |
| **Differential privacy** | OpenDP, Google differential-privacy library, IBM diffprivlib, Opacus (PyTorch), TensorFlow Privacy |
| **Federated learning** | Flower, TensorFlow Federated, NVIDIA FLARE, PySyft |
| **Cryptographic PETs** | Microsoft SEAL, OpenFHE, TenSEAL, CrypTen, MP-SPDZ |
| **Synthetic data** | SDV (Synthetic Data Vault), synthcity, Synthea (synthetic patient generator) |
| **Access control and governance** | Keycloak, Open Policy Agent, Apache Ranger, Hyperledger Fabric (permissioned ledger for audit or consent) |
| **Privacy attack and risk evaluation** | ML Privacy Meter, IBM Adversarial Robustness Toolbox (inference attacks), Anonymeter (synthetic-data re-identification risk), ARX risk analysis |
| **Reproducibility** | Git and GitHub/GitLab, Docker, conda/venv with pinned requirements, DVC, MLflow, Jupyter |
| **Compliance documentation** | CNIL PIA software, LINDDUN threat-modelling cards and tutorials, ICO DPIA template |

**Datasets.** Use public, credentialed-access or synthetic datasets only, and record the licence and access conditions. Examples: Synthea and MIMIC-IV (healthcare; MIMIC requires PhysioNet credentialing and training), PaySim and the ULB credit-card fraud dataset (finance), Online Retail II and MovieLens (e-commerce), UCI Adult (census), Open University Learning Analytics Dataset (education), GeoLife trajectories (mobility). Real personal data from an employer or other organisation are **not** allowed.

#### Step 4: Design the implementation architecture

Draw a deployment view of your system: containers or processes, where each runs (laptop, Docker network, free cloud tier), the data stores, network flows, secrets and key management, and trust boundaries. Provide a component-to-tool mapping table that links every design component from Assignment 1 to the tool, version, configuration and the requirements it satisfies.

#### Step 5: Build the execution roadmap and experiment plan

* **Work-breakdown structure (WBS):** work packages (WP), tasks, deliverables, estimated effort in hours, and dependencies (Appendix 2).
* **Gantt chart:** Weeks 9�13 with milestones (M1 environment ready, M2 baseline reproduced, M3 proposed method running, M4 evaluation complete, M5 report submitted). Mark the critical path.
* **Experiment matrix:** every run you will execute: method � dataset � privacy setting � seed, with the metric collected and expected run time. Check that the total compute time fits your schedule.
* **Definition of done** for each milestone.

#### Step 6: Verify legal, regulatory and ethical compliance (core of CLO3)

Show, requirement by requirement, that the way your system will collect, store, process, share, retain and delete personal data would be lawful if deployed in a real organisation in your chosen domain. Even though you use public or synthetic data, you must perform the verification as if the data were real. As a minimum:

* **Record of processing activities (ROPA):** data categories, data subjects, purposes, recipients, retention, transfers, security measures.
* **Lawful basis and special categories:** the GDPR Art. 6 basis and, for health, biometric or similar data, the Art. 9 condition; the corresponding PDPA position (consent, sensitive personal data under s. 40).
* **Principle-by-principle mapping:** the seven PDPA Personal Data Protection Principles (General, Notice and Choice, Disclosure, Security, Retention, Data Integrity, Access) and the GDPR Art. 5 principles (lawfulness, fairness and transparency; purpose limitation; data minimisation; accuracy; storage limitation; integrity and confidentiality; accountability) mapped to concrete design controls.
* **PDPA (Amendment) Act 2024 obligations:** data breach notification, appointment of a data protection officer, the data portability right, security obligations of data processors, and the revised cross-border transfer rules. Check the current commencement status of each provision with the Personal Data Protection Department (JPDP) before you cite it.
* **Data protection impact assessment (DPIA):** screening against GDPR Art. 35 criteria; if high risk, a full assessment of necessity, proportionality, risks to individuals and mitigations.
* **Data protection by design and by default (GDPR Art. 25)** and security of processing (Art. 32): show where each control is implemented.
* **Data-subject rights:** how access, rectification, erasure, objection and portability requests would be fulfilled in your architecture (including in models or aggregates derived from the data).
* **Sector and regional rules where relevant:** e.g., Bank Negara Malaysia Risk Management in Technology (RMiT) and PCI DSS for finance; HIPAA de-identification standards as a comparison point for health data; consumer-protection and e-commerce rules for online retail.
* **Verification method:** for every requirement, the evidence you will produce

(configuration, log, test result, document) and the test you will run in the Case Study to show it is met (Appendix 3).

#### Step 7: Manage risks and prove the setup

Complete a risk register (Appendix 4) covering technical, data, legal, ethical and schedule risks. Then build your repository using the structure in Appendix 5 and demonstrate the proof of setup: the environment builds from a single command, the dataset is loaded and profiled, and the non-private baseline runs and produces a first metric. Include screenshots and the commit hash in Section 8 of your report.

### A.4 Required Structure of the Report

**Table A.3:** Required structure of the Assignment 2 report

|  |  |  |
| --- | --- | --- |
| **Section** | **Required content** | **Indicative length** |
| **Title page** | Title, student name and ID, course code, domain, word count, repository link and commit hash, GenAI declaration | � |
| **Executive summary** | What will be built, with which tools, by when, and how compliance will be verified | 150�200 words |
| **Section** | **Required content** | **Indicative length** |
| **1. Introduction and change log** | Recap of the problem, aim and design from Assignment 1; change-log table | 300�400 words |
| **2. Requirements** | Numbered FR, NFR and PR with acceptance tests | 300�500 words |
| **3. Tools, technologies and datasets** | Candidate comparison, weighted selection matrix, final tool stack with versions and licences, dataset profile and licence | 600�900 words |
| **4. Implementation architecture** | Deployment diagram, component-to-tool mapping table, key and secret management | 400�600 words |
| **5. Execution roadmap and experiment plan** | WBS, Gantt chart with milestones and critical path, experiment matrix, definition of done | 400�600 words |
| **6. Legal, regulatory and ethical compliance verification plan** | ROPA, lawful basis, PDPA and GDPR principle mapping,  DPIA, data-subject rights, sector rules, verification table | 700�1,000 words |
| **7. Risk management** | Risk register summary and contingency plans | 200�300 words |
| **8. Reproducibility and proof of setup** | Repository structure, environment, seeds, data licences, screenshots, first baseline result | 200�300 words |
| **9. Conclusion** | Readiness for execution and what remains | 100�150 words |
| **References** | IEEE style; legislation and standards cited by section or article | � |
| **Appendices** | Appendices 1�6 completed | � |

### A.5 Section-by-Section Writing Guide

#### 1. Introduction and change log

* Summarise the problem, aim, objectives and design from Assignment 1 in one or two paragraphs.
* Provide a change-log table: change, reason (feedback, feasibility, new evidence), impact on objectives, metrics or schedule.

**Example:** *The homomorphic-encryption aggregation planned in Assignment 1 was replaced by secure aggregation with pairwise masking because a CKKS prototype took 40 minutes per round on a laptop; O2 and its metrics are unchanged.*

#### 2. Requirements

* Number every requirement (FR1, NFR1, PR1) and give an acceptance test for each.
* Privacy requirements must be quantified where possible (? budget, k threshold, maximum re-identification rate, retention period).

#### 3. Tools, technologies and datasets

* For each component, compare at least two candidates in a weighted selection matrix (criteria weights must sum to 100%).
* Justify the final choice with evidence: documentation, benchmarks, use in your Peer Review corpus, licence compatibility.
* List the final stack with exact versions (e.g., Python 3.11, PostgreSQL 16, Flower 1.x, Opacus 1.x) and licences.
* Profile the dataset: size, features, missingness, class balance, direct identifiers, quasiidentifiers, sensitive attributes, licence.

**Example:** *Opacus was preferred to TensorFlow Privacy (weighted score 4.3 vs 3.6) because the proposed model is written in PyTorch and Opacus provides per-sample gradient clipping and an RDP accountant without rewriting the training loop.*

#### 4. Implementation architecture

* A deployment diagram showing processes or containers, data stores, networks and trust boundaries.
* A component-to-tool mapping table: design component ? tool and version ? configuration ? requirement(s) satisfied.
* How keys and secrets (pseudonymisation keys, database passwords, encryption keys) are generated, stored and rotated; never commit secrets to the repository.

#### 5. Execution roadmap and experiment plan

* WBS with effort estimates; Gantt chart with milestones and critical path; buffer time for at least one slipped task.
* Experiment matrix listing every planned run and its estimated time; total compute must fit the schedule.
* Definition of done for each milestone, e.g., M2 = baseline metric within �2% of the published value or a documented explanation of the difference.

#### 6. Legal, regulatory and ethical compliance verification plan

* Start with a data inventory and ROPA table, then the lawful basis.
* Map each PDPA principle and GDPR Art. 5 principle to the specific design control and the requirement that implements it.
* Complete the DPIA screening; if high risk, include the full DPIA summary (risk to individuals, likelihood, severity, mitigation, residual risk).
* Explain how each data-subject right would be honoured, including the hard cases (erasure from trained models, aggregates or backups).
* Finish with the verification table (Appendix 3): requirement ? legal source ? control ? evidence ? test ? pass criterion. These tests will be executed in the Case Study.

**Example:** *PDPA Retention Principle ? PR5 (raw extracts deleted 30 days after model training) ? scheduled deletion job in Airflow ? job log and row counts before and after ? automated test asserts zero rows older than 30 days ? pass if zero.*

#### 7. Risk management

Summarise the top five risks from the register and the contingency plan for each, e.g., "if the federated simulation exceeds the time budget, reduce clients from 10 to 5 and rounds from 50 to 30, and report the change".

#### 8. Reproducibility and proof of setup

* Repository URL and commit hash; README with setup instructions; environment file or Dockerfile; fixed random seeds; data-download script (not the data itself if the licence forbids redistribution).
* Screenshots: environment running, dataset loaded and profiled, baseline training output with the first metric.
* A short statement of what has been verified to work and what has not yet been attempted.

### A.6 Required Tables, Figures and Evidence

**Table A.4:** Minimum visual elements and evidence

|  |  |  |
| --- | --- | --- |
| **Element** | **Purpose** | **Example** |
| **Change-log table** | Traceability to Assignment 1 | Section 1 |
| **Requirements table with acceptance**  **tests** | Verifiable requirements | Section 2 |
| **Weighted tool selection matrix** | Justified technology choices | Table C.1 |
| **Final tool stack table (versions, licences)** | Reproducibility | Section 3 |
| **Deployment / implementation architecture diagram** | How the system will run | Section 4 |
| **Component-to-tool mapping table** | Design-to-implementation traceability | Section 4 |
| **Gantt chart with milestones** | Feasibility and schedule | Figure C.1 |
| **Experiment matrix** | Completeness of evaluation | Section 5 |
| **ROPA and PDPA/GDPR principle mapping tables** | Compliance analysis | Section 6 |
| **Compliance verification table** | Requirement ? evidence ? test | Table C.2 |
| **Risk register** | Risk management | Appendix 4 |
| **Proof-of-setup screenshots and commit hash** | Feasibility evidence | Section 8 |

### A.7 Formatting, Referencing and Integrity

* Microsoft Word, A4, Times New Roman 12 pt (tables 9�10 pt), 1.15�1.5 line spacing,

2.54 cm margins, page numbers; numbered headings, tables and figures.

* IEEE referencing. Cite legislation by Act and section or Regulation and article (e.g.,

"GDPR Art. 35", "PDPA 2010, s. 9"). Cite tool documentation with URL and access date.

* Generative AI may be used only for brainstorming and language polishing and must be declared. Code generated by AI assistants must be declared in the README and reviewed by you; you must be able to explain every line in the Case Study viva.
* This document is not legal advice to students; it asks you to analyse compliance as an engineering exercise using primary legal sources.

### A.8 Submission Checklist

? Change log against Assignment 1 included (or "no changes" stated).

? Numbered FR, NFR and PR requirements, each with an acceptance test.

? Weighted selection matrix for each major component; final stack with versions and licences.

? Dataset profile and licence; no real personal data from any organisation.

? Deployment diagram and component-to-tool mapping table.

? WBS, Gantt chart with milestones and critical path, experiment matrix.

? ROPA, lawful basis, PDPA and GDPR principle mapping, DPIA screening (and full DPIA if high risk), data-subject rights.

? Compliance verification table with evidence and tests for every privacy requirement.

? Risk register; repository link, commit hash and proof-of-setup screenshots.

? Appendices 1�6 completed; word count and GenAI declaration on the title page; .docx and PDF submitted.

## PART B: MARKING CRITERIA

### B.1 Mark Allocation

The assignment is marked out of 100 using the eight criteria below and then scaled to the 10% course weighting (final mark = total � 10). Criteria 2 and 5 carry the most weight: the quality of the technology choices and the compliance verification (CLO3). **Table B.1:** Summary of marking criteria

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **No.** | **Criterion** | **What is assessed** | **Marks** | **Course %** |
| 1 | Alignment with proposal and requirements | Change log; requirements derived from proposal; acceptance tests | 10 | 1.0 |
| 2 | Tools, technologies and datasets | Candidate comparison; weighted matrix; versions, licences; dataset profile and licence | 20 | 2.0 |
| 3 | Implementation architecture and mapping | Deployment diagram; component-to-tool mapping; key and secret management | 15 | 1.5 |
| 4 | Execution roadmap and experiment plan | WBS, Gantt, milestones, critical path; experiment matrix; definition of done | 15 | 1.5 |
| 5 | Legal, regulatory and ethical compliance | ROPA, lawful basis, PDPA/GDPR principle mapping, DPIA, data-subject rights, sector rules, verification table | 20 | 2.0 |
| 6 | Risk management and proof of setup | Risk register and contingencies; repository; proof of setup with first baseline result | 10 | 1.0 |
| 7 | Writing, visuals and referencing | Clarity, IEEE and legal citation, visuals | 5 | 0.5 |
| 8 | Compliance and presentation | Length, format, appendices, declaration | 5 | 0.5 |
|  | **Total** |  | **100** | **10.0** |


**Figure B.1:** Allocation of the 100 marks across the eight criteria and their contribution to the course grade

### B.2 Detailed Marking Rubric

Each criterion is marked holistically within the band that best describes the work.

**Table B.2:** Analytic rubric (marks in brackets are for each band)

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Criterion (marks)** | **Excellent (85 100%)** | **Good (70 84%)** | **Satisfactory (50 69%)** | **Poor (0 49%)** |
| **1. Alignment with proposal and requirements (10)** | Complete change log with reasons; FR, NFR and PR derived from the proposal, quantified and each with a runnable acceptance test. (8.5�10) | Requirements clear and mostly testable; change log present. (7�8) | Requirements vague or untestable; weak link to proposal. (5�6.5) | No requirements or no link to  Assignment 1. (0�4.5) |
| **2. Tools, technologies and datasets (20)** | ? 2 candidates per major component compared with a weighted matrix; choices justified with evidence; exact versions and licences; dataset profiled (identifiers, quasi-identifiers, sensitive attributes) with licence.  (17�20) | Sound choices with matrix; some justifications thin or versions missing. (14�16.5) | Tools listed with little comparison; dataset not profiled. (10�13.5) | Tool list only or inappropriate tools; dataset unsuitable or unlicensed. (0�9.5) |
| **3. Implementation architecture and mapping**  **(15)** | Clear deployment diagram with trust boundaries; every design component mapped to tool, version, configuration and requirement; sound key and secret management. (13�15) | Architecture and mapping mostly complete. (10.5�12.5) | Diagram generic; mapping incomplete. (7.5�10) | Missing or inconsistent with design. (0�7) |
| **4. Execution roadmap and experiment plan (15)** | WBS with effort and dependencies; Gantt with milestones, critical path and buffer; full experiment matrix with compute estimate; definitions of done.  (13�15) | Roadmap realistic; experiment matrix or critical path partly missing. (10.5�12.5) | Timeline only; no experiment plan. (7.5�10) | No credible plan. (0�7) |
| **5. Legal, regulatory and ethical compliance verification (20)** | Accurate ROPA and lawful basis; every PDPA and  GDPR Art. 5 principle mapped to a concrete control; DPIA screening and full DPIA where required; datasubject rights including hard cases; correct sector rules; every privacy requirement has evidence, test and pass criterion. (17�20) | Mostly accurate and specific; minor gaps in rights or verification tests. (14�16.5) | Generic description of laws; mapping to controls weak; few verification tests. (10�13.5) | Legal analysis missing or wrong; no verification. (0� 9.5) |
| **6. Risk management and proof of setup (10)** | Risk register with likelihood, impact, owner and contingency; repository builds from one command; dataset loaded; baseline runs with first metric; screenshots and commit hash. (8.5�10) | Setup mostly working; minor gaps. (7�8) | Repository exists but baseline not running. (5�6.5) | No repository or no evidence of setup. (0�4.5) |
| **7. Writing, visuals and referencing (5)** | Clear, precise; required visuals; correct IEEE and legal citations. (4.5�5) | Minor issues. (3.5�4) | Frequent issues. (2.5�3) | Poor. (0�2) |
| **8. Compliance and presentation (5)** | Within length; format and appendices complete. (4.5� 5) | Minor deviations. (3.5�4) | Several deviations. (2.5�3) | Major parts missing. (0�2) |

Page 11

### B.3 Penalties and Deductions

**Table B.3:** Penalties applied after marking

|  |  |
| --- | --- |
| **Issue** | **Penalty** |
| Repository link missing, private without lecturer access, or empty | Criterion 6 = 0 |
| Use of real personal data without authorisation and ethics approval | Zero for the assignment and referral to the university |
| Secrets, keys or personal data committed to the repository | ?5 marks; must be removed and keys rotated before the  Case Study |
| Design changed from Assignment 1 without a change log | Criterion 1 capped at the Satisfactory band |
| Fabricated tool versions, results or screenshots | Zero for criteria 2 and 6; referral for academic-integrity investigation |
| Exceeding the word limit by more than 10% | ?5 marks |
| Late submission without approved extension | As per university regulations (e.g., ?10% of the obtained marks per day, zero after five days) |

### B.4 What Distinguishes a Strong Plan

**Table B.4:** Weak versus strong plan elements

|  |  |  |
| --- | --- | --- |
| **Element** | **Weak** | **Strong** |
| **Tool justification** | We will use Python because it is popular. | Flower 1.x chosen over TensorFlow Federated (weighted score 4.55 vs 3.25, Table C.1): framework-agnostic, simulates 10 clients on one laptop, Apache-2.0 licence, used by two studies in the Peer Review corpus. |
| **Requirement** | The system must be secure. | PR2: database columns holding diagnoses are encrypted at rest with AES-256; test: a direct read without the key returns ciphertext. |
| **Compliance** | The project follows GDPR and PDPA. | Security Principle (PDPA s. 9) and GDPR Art. 32 ? RBAC via Keycloak + column encryption + audit log ? evidence:  role-permission matrix and denied-access log ? test: analyst role cannot query raw table. |
| **Data-subject rights** | Users can delete their data. | Erasure removes the record from the store and backups within 30 days; the model is not retrained, but DP with ? = 1 bounds the deleted person's influence; this residual is documented in the DPIA. |
| **Roadmap** | Week 10�13: implementation. | M2 (11 Dec): FedAvg baseline AUC within �2% of published value; 60 runs � 3 min = 3 h compute; 2-day buffer before M4. |

### B.5 Marking Sheet

**Table B.5:** Marking sheet for the lecturer

|  |  |  |  |
| --- | --- | --- | --- |
| **Criterion** | **Max** | **Mark** | **Feedback** |
| 1. Alignment with proposal and requirements | 10 |  |  |
| 2. Tools, technologies and datasets | 20 |  |  |
| 3. Implementation architecture and mapping | 15 |  |  |
| 4. Execution roadmap and experiment plan | 15 |  |  |
| 5. Legal, regulatory and ethical compliance | 20 |  |  |
| 6. Risk management and proof of setup | 10 |  |  |
| 7. Writing, visuals and referencing | 5 |  |  |
| 8. Compliance and presentation | 5 |  |  |
| Penalties (Table B.3) |  |  |  |
| Total (out of 100) | 100 |  |  |
| **Final mark (out of 10) = total � 10** | **10** |  |  |

## PART C: EXEMPLAR EXTRACTS

The extracts continue the reserved healthcare exemplar (federated, differentially private multi-hospital pipeline). Scores and estimates are illustrative of the format; students must produce their own evidence.

### C.1 Weighted Tool Selection (extract)

**Table C.1:** Weighted selection matrix for the federated-learning framework (scores 1�5)

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Criterion** | **Weight** | **Flower** | **TensorFlow Federated** | **NVIDIA FLARE** |
| Fit to requirement (FR2: simulate 3�10 sites on one machine) | 25% | 5 | 4 | 3 |
| Works with existing PyTorch model and Opacus DP | 20% | 5 | 2 | 4 |
| Documentation and community | 15% | 4 | 4 | 4 |
| Secure aggregation support | 15% | 4 | 3 | 4 |
| Licence (open source, permissive) | 10% | 5 | 5 | 5 |
| Learning curve within two weeks | 15% | 4 | 2 | 2 |
| **Weighted score** | 100% | **4.55** | **3.25** | **3.55** |

Weighted score = ? (weight � score). Flower is selected; NVIDIA FLARE is kept as the fallback if secure aggregation in Flower cannot be configured by milestone M3.

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Req.** | **Legal source** | **Design control** | **Evidence** | **Verification test and pass criterion** |

### C.2 Execution Roadmap (extract)

![](data:image/jpeg;base64...)

**Figure C.1:** Gantt chart for Weeks 9�13 with Assignment 2 and Case Study deadlines (exemplar)

### C.3 Compliance Verification (extract)

**Table C.2:** Compliance verification table (extract): requirement ? legal source ? control ? evidence ? test

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Req.** | **Legal source** | **Design control** | **Evidence** | **Verification test and pass criterion** |
| PR1 | PDPA General and  Notice & Choice  Principles; GDPR Art. 6,  9(2)(j) | Processing limited to approved research purpose; purpose recorded in ROPA | ROPA entry; ethics approval reference | Inspection: every dataset in the store is linked to a ROPA purpose (100%) |
| PR2 | PDPA Security  Principle; GDPR Art. 32 | Keyed-HMAC  pseudonymisation at ingestion; AES-256 column encryption; RBAC | Key-management note; role-permission matrix | Automated scan finds 0 direct identifiers downstream; analyst role denied on raw table |
| PR3 | GDPR Art. 25, 5(1)(c) data minimisation | Only 14 of 46 source fields ingested | Field-selection rationale | Schema diff shows no unapproved fields |
| PR4 | PDPA Retention Principle; GDPR Art.  5(1)(e) | Raw extracts deleted 30 days after training | Scheduler log | Test asserts no rows older than 30 days |
| PR5 | GDPR Art. 35; PDPA  (Amendment) Act 2024 breach notification | DPIA completed; breachresponse runbook | DPIA document; runbook | Tabletop exercise: breach notified to DPO within the internal deadline |
| PR6 | GDPR Art. 17; PDPA Access Principle | Erasure and access request handlers; DP bounds residual influence on model | API logs | Request for a test subject returns/erases all records; residual risk recorded in DPIA |

## APPENDICES

### Appendix 1: Weighted Tool Selection Matrix Template

**Table App.1:** Tool selection matrix (one per major component)

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| **Criterion** | **Weight (%)** | **Candidate A** | **Candidate B** | **Candidate C** |
| Fit to requirement(s) � |  |  |  |  |
| Privacy guarantee offered |  |  |  |  |
| Maturity and community |  |  |  |  |
| Documentation |  |  |  |  |
| Licence |  |  |  |  |
| Performance / scalability |  |  |  |  |
| Learning curve |  |  |  |  |
| **Weighted score** | **100** |  |  |  |

### Appendix 2: Work-Breakdown Structure Template

**Table App.2:** Work-breakdown structure

|  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- |
| **WP** | **Task** | **Deliverable** | **Effort (h)** | **Depends on** | **Week** | **Milestone** |
| WP1 |  |  |  |  |  |  |
| WP2 |  |  |  |  |  |  |
| WP3 |  |  |  |  |  |  |
| WP4 |  |  |  |  |  |  |
| WP5 |  |  |  |  |  |  |

### Appendix 3: Compliance Verification Checklist

**Table App.3:** Compliance verification checklist

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| **Principle / provision** | **Applies?**  **(Y/N, why)** | **Design control** | **Requireme**  **nt** | **Evidence** | **Test and pass criterion** |
| **PDPA General Principle**  **(consent; sensitive data)** |  |  |  |  |  |
| **PDPA Notice and Choice Principle** |  |  |  |  |  |
| **PDPA Disclosure Principle** |  |  |  |  |  |
| **PDPA Security Principle** |  |  |  |  |  |
| **PDPA Retention Principle** |  |  |  |  |  |
| **PDPA Data Integrity Principle** |  |  |  |  |  |
| **PDPA Access Principle** |  |  |  |  |  |
| **PDPA 2024 amendments: breach notification, DPO, portability, processors, crossborder transfer** |  |  |  |  |  |
| **GDPR Art. 5 principles** |  |  |  |  |  |
| **GDPR Art. 6 / Art. 9 lawful basis** |  |  |  |  |  |
| **GDPR Art. 25 data protection by design and default** |  |  |  |  |  |
| **Principle / provision** | **Applies?**  **(Y/N, why)** | **Design control** | **Requireme**  **nt** | **Evidence** | **Test and pass criterion** |
| **GDPR Art. 32 security of processing** |  |  |  |  |  |
| **GDPR Art. 35 DPIA** |  |  |  |  |  |
| **GDPR Arts. 15 22 data-**  **subject rights** |  |  |  |  |  |
| **Sector-** |  |  |  |  |  |

### Appendix 4: Risk Register Template

**Table App.4:** Risk register

|  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **ID** | **Risk** | **Category** | **Likelihood**  **(1 5)** | **Impact**  **(1 5)** | **Score** | **Mitigation / contingency** | **Owner** |
| R1 |  | Technical |  |  |  |  |  |
| R2 |  | Data |  |  |  |  |  |
| R3 |  | Legal / ethical |  |  |  |  |  |
| R4 |  | Schedule |  |  |  |  |  |
| R5 |  |  |  |  |  |  |  |

### Appendix 5: Repository Structure and README Template

**Table App.5:** Required repository structure

|  |  |
| --- | --- |
| **Path** | **Content** |
| **README.md** | Project title, problem, how to set up (one command), how to run each experiment, expected outputs, data licence, AI-assistance declaration |
| **environment.yml / requirements.txt / Dockerfile** | Pinned versions of every dependency |
| **data/README.md** | Dataset source, licence, download script; raw data not committed if the licence forbids redistribution |
| **src/** | Ingestion, pseudonymisation, storage, models, PETs, attacks |
| **configs/** | One configuration file per experiment (seeds, ?, k, clients, rounds) |
| **experiments/run\_all.sh** | Script that reproduces every table and figure |
| **results/** | Raw metrics (CSV/JSON) and generated figures |
| **compliance/** | ROPA, DPIA, verification test scripts and logs |
| **.gitignore** | Excludes secrets, keys, .env files and raw personal data |

### Appendix 6: Student Declaration

I declare that this plan is my own work, that it implements my own Assignment 1 proposal, that all tool versions, screenshots and results reported are genuine and reproducible from the repository commit stated, and that no real personal data have been used without authorisation.

Use of generative AI tools (tick one):

No generative AI tools were used.

Generative AI tools were used as declared below (brainstorming, language polishing or code assistance declared in the README).

**Table App.6:** Generative AI declaration

|  |  |  |
| --- | --- | --- |
| **Tool and version** | **Purpose** | **Sections or files affected** |
|  |  |  |
|  |  |  |

Student name: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_ Student ID: \_\_\_\_\_\_\_\_\_\_\_\_\_\_

Signature: \_\_\_\_\_\_\_\_\_\_\_\_\_\_ Date: \_\_\_\_\_\_\_\_\_\_\_\_
