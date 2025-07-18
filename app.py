from flask import Flask, request, jsonify
from flask_cors import CORS
import pyodbc
import os
import re

app = Flask(__name__)
CORS(app)

@app.route('/conectar', methods=['POST'])
def conectar():
    data = request.json
    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={data['servidor']};"
            f"UID={data['usuario']};"
            f"PWD={data['senha']}"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sys.databases WHERE database_id > 4")  # ignora system dbs
        bancos = [row[0] for row in cursor.fetchall()]
        return jsonify({'success': True, 'bancos': bancos})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/query', methods=['POST'])
def query():
    data = request.json
    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={data['servidor']};"
            f"DATABASE={data['banco']};"
            f"UID={data['usuario']};"
            f"PWD={data['senha']}"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(data['query'])

        if cursor.description:
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return jsonify({
                'success': True,
                'columns': columns,
                'rows': [list(r) for r in rows]
            })
        else:
            conn.commit()
            return jsonify({'success': True, 'message': 'Query executada com sucesso.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/preview', methods=['POST'])
def preview():
    data = request.json
    try:
        conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={data['servidor']};"
            f"DATABASE={data['banco']};"
            f"UID={data['usuario']};"
            f"PWD={data['senha']}"
        )
        conn = pyodbc.connect(conn_str, autocommit=False)
        cursor = conn.cursor()

        # Executa a query original (sem commit)
        cursor.execute(data['query'])

        # Gera SELECT correspondente
        select_query = construir_select_para_preview(data['query'])
        if not select_query:
            raise Exception("Não foi possível gerar SELECT para pré-visualização")

        cursor.execute(select_query)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

        conn.rollback()

        return jsonify({
            'success': True,
            'columns': columns,
            'rows': [list(r) for r in rows],
            'message': 'Essa é a pré-visualização. Nenhuma alteração foi salva.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def construir_select_para_preview(query):
    query_upper = query.strip().upper()

    if query_upper.startswith("UPDATE"):
        tabela = re.search(r'UPDATE\s+([^\s]+)', query, re.IGNORECASE)
        where = re.search(r'\bWHERE\b\s+(.+)', query, re.IGNORECASE)
    elif query_upper.startswith("DELETE"):
        tabela = re.search(r'DELETE\s+FROM\s+([^\s]+)', query, re.IGNORECASE)
        where = re.search(r'\bWHERE\b\s+(.+)', query, re.IGNORECASE)
    else:
        return None

    if not tabela:
        return None

    tabela_nome = tabela.group(1)
    where_clause = where.group(1) if where else ""

    if where_clause:
        return f"SELECT TOP 100 * FROM {tabela_nome} WHERE {where_clause}"
    else:
        return f"SELECT TOP 100 * FROM {tabela_nome}"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
