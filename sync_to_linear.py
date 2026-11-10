#!/usr/bin/env python3
"""
Sincronizador automático de tareas hacia Linear API (GraphQL).
Uso:
    export LINEAR_API_KEY="lin_api_..."
    python3 sync_to_linear.py
"""

import os
import sys
import json
import httpx

LINEAR_API_URL = "https://api.linear.app/graphql"
API_KEY = os.environ.get("LINEAR_API_KEY")

if not API_KEY:
    print("Error: La variable de entorno LINEAR_API_KEY no está configurada.")
    print("Para importar a Linear, puedes:")
    print("1. Subir directamente el archivo generado 'linear_tasks_import.csv' en Linear -> Settings -> Import / Export -> CSV")
    print("2. O configurar tu API Key: set -x LINEAR_API_KEY 'lin_api_...' (Fish) y volver a ejecutar este script.")
    sys.exit(1)

HEADERS = {
    "Authorization": API_KEY,
    "Content-Type": "application/json"
}

def query_linear(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    response = httpx.post(LINEAR_API_URL, headers=HEADERS, json=payload, timeout=30.0)
    data = response.json()
    if "errors" in data:
        raise RuntimeError(f"Error en Linear GraphQL: {data['errors']}")
    return data.get("data", {})

def main():
    print("Conectando con Linear API...")
    viewer = query_linear("{ viewer { id name email } teams { nodes { id name key } } }")
    print(f"Autenticado como: {viewer['viewer']['name']} ({viewer['viewer']['email']})")
    
    teams = viewer.get("teams", {}).get("nodes", [])
    if not teams:
        print("No se encontraron equipos en esta cuenta de Linear.")
        sys.exit(1)
        
    team = teams[0]
    print(f"Usando equipo: {team['name']} ({team['key']})")
    
    # Crear o buscar proyecto
    project_title = "Crypto AI Agent Platform"
    print(f"Creando proyecto '{project_title}'...")
    create_proj_query = """
    mutation CreateProject($teamId: String!, $name: String!, $description: String!) {
        projectCreate(input: { teamIds: [$teamId], name: $name, description: $description }) {
            success
            project { id name }
        }
    }
    """
    try:
        res = query_linear(create_proj_query, {
            "teamId": team["id"],
            "name": project_title,
            "description": "Plataforma de Agente de IA para Mercado Crypto con DuckDB, MinIO y generación instantánea de gráficos."
        })
        project_id = res["projectCreate"]["project"]["id"]
        print(f"Proyecto creado con ID: {project_id}")
    except Exception as e:
        print(f"Proyecto ya existente o aviso: {e}")
        # buscar id
        projs = query_linear("{ projects { nodes { id name } } }")
        project_id = next((p["id"] for p in projs.get("projects", {}).get("nodes", []) if p["name"] == project_title), None)

    # Importar tareas
    from generate_tasks import TASKS
    
    create_issue_query = """
    mutation CreateIssue($teamId: String!, $projectId: String, $title: String!, $description: String!, $priority: Int, $estimate: Int) {
        issueCreate(input: {
            teamId: $teamId,
            projectId: $projectId,
            title: $title,
            description: $description,
            priority: $priority,
            estimate: $estimate
        }) {
            success
            issue { id identifier title url }
        }
    }
    """
    
    priority_map = {"Urgent": 1, "High": 2, "Medium": 3, "Low": 4}
    
    for t in TASKS:
        p_val = priority_map.get(t["linear_priority"], 2)
        try:
            issue_res = query_linear(create_issue_query, {
                "teamId": team["id"],
                "projectId": project_id,
                "title": t["title"],
                "description": t["description"],
                "priority": p_val,
                "estimate": t["story_points"]
            })
            issue = issue_res["issueCreate"]["issue"]
            print(f"✓ Creada en Linear: {issue['identifier']} - {issue['title']}")
        except Exception as err:
            print(f"Error creando {t['id']} en Linear: {err}")

if __name__ == "__main__":
    main()
