# Advance AI Project 2026

This repository contains the final project for the **Advanced Machine Learning** course, **Winter Semester 2025/26**.

The project focuses on building a **Python-based question answering system over the DBpedia Knowledge Graph**. Users can enter natural language questions, and the system processes them, generates or selects a suitable SPARQL query, retrieves results from DBpedia, and presents the answer through a simple web interface.

---

## Project Summary

The goal of this project is to develop an interactive question answering application that connects natural language input with structured knowledge from DBpedia.

The system is designed to:
- accept a user question through a web interface
- process the question in Python
- generate or select a SPARQL query
- send the query to the DBpedia SPARQL endpoint
- retrieve and format the response
- display the final answer to the user

This project combines concepts from machine learning, knowledge graphs, natural language processing, and web-based user interaction.

---

## How the Project Works

The workflow of the system is planned as follows:

1. The user enters a question in the web interface.
2. The system analyzes the question.
3. A matching SPARQL query is generated either through predefined templates or an LLM-assisted component.
4. The query is sent to the DBpedia Knowledge Graph.
5. The returned result is processed and converted into a readable answer.
6. The answer is shown in the application.

In short:

**User Question → Question Processing → SPARQL Query Generation → DBpedia Query Execution → Answer Formatting → Web Interface Output**

---

## Prerequisites

Before running this project, make sure the following tools are installed:

- **Python 3.10 or newer**
- **Visual Studio Code**
- **Git**
- **Internet connection** for accessing the DBpedia endpoint
- optionally, **API access credentials** if an LLM-based query generation module is added later

Required Python packages may include:

- `streamlit`
- `requests`
- `SPARQLWrapper`
- `python-dotenv`

These dependencies will be listed in the `requirements.txt` file.

---

## Project Structure

The project is organized as follows:

```text
Advance_AI_Project-2026/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env
├── .env.example
│
├── data/
│   ├── working_questions.txt
│   ├── non_working_questions.txt
│   └── sample_questions.json
│
├── src/
│   ├── dbpedia_client.py
│   ├── query_builder.py
│   ├── answer_formatter.py
│   ├── llm_client.py
│   └── utils.py
│
├── docs/
│   └── architecture.png
│
└── team.txt
### Folder and File Description

- **app.py**  
  Main entry point of the application. It runs the web interface and connects the user input with the backend logic.

- **requirements.txt**  
  Contains all Python dependencies required to install and run the project.

- **README.md**  
  Project documentation, including summary, setup instructions, structure, and usage information.

- **.gitignore**  
  Defines files and folders that should not be tracked in Git, such as virtual environments, cache files, and secrets.

- **.env**  
  Stores local environment variables such as API keys or configuration values. This file should not be pushed to GitHub.

- **.env.example**  
  Example template for environment variables, so other users know which values they need to provide locally.

- **data/**  
  Contains sample input files and evaluation material for testing the system.

  - **working_questions.txt**  
    List of example questions that the system is expected to answer correctly.

  - **non_working_questions.txt**  
    List of example questions that currently fail or are outside the supported scope.

  - **sample_questions.json**  
    Structured sample questions that can be used for testing or development.

- **src/**  
  Contains the core Python modules of the project.

  - **dbpedia_client.py**  
    Handles communication with the DBpedia SPARQL endpoint.

  - **query_builder.py**  
    Converts user questions into SPARQL queries using templates or logic rules.

  - **answer_formatter.py**  
    Processes query results and converts them into readable answers.

  - **llm_client.py**  
    Optional module for LLM-based SPARQL generation if API access is added later.

  - **utils.py**  
    Stores helper functions used across different parts of the project.

- **docs/**  
  Contains supporting project documentation.

  - **architecture.png**  
    Visual diagram showing how the system components interact.

- **team.txt**  
  Contains the names of team members and optionally their roles or responsibilities in the project.

---

## How to Build and Run the Project

### 1. Clone the repository

```bash
git clone https://github.com/ayesha-jabeen-ryk/Advance_AI_Project-2026.git
cd Advance_AI_Project-2026
2. Create a virtual environment
python -m venv .venv
3. Activate the virtual environment

On Windows PowerShell:

.venv\Scripts\Activate.ps1

On Command Prompt:

.venv\Scripts\activate.bat
4. Install required packages
pip install -r requirements.txt
5. Run the application
streamlit run app.py