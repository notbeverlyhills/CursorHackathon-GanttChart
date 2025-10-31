import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.figure_factory as ff
import pandas as pd
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # Required for Render

def get_db_connection():
    """Connect to Supabase PostgreSQL"""
    database_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(database_url, sslmode='require')

def save_state_to_db(user_id, project_id, tasks):
    """Save gantt state to database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    state_json = json.dumps(tasks)
    now = datetime.now()
    
    cur.execute('''
        INSERT INTO gantt_states (user_id, project_id, state_data, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, project_id) 
        DO UPDATE SET state_data = %s, updated_at = %s
    ''', (user_id, project_id, state_json, now, now, state_json, now))
    
    conn.commit()
    cur.close()
    conn.close()
    return True

def load_state_from_db(user_id, project_id):
    """Load gantt state from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute('''
            SELECT state_data, updated_at FROM gantt_states 
            WHERE user_id = %s AND project_id = %s
        ''', (user_id, project_id))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return json.loads(result['state_data'])
        return None
    except:
        return None

USER_ID = "default_user"
PROJECT_ID = "my_project"

DEFAULT_TASKS = [
    {"Task": "Project Planning", "Start": "2025-11-01", "Finish": "2025-11-05", 
     "Resource": "Project Manager", "Complete": 100},
    {"Task": "Requirements", "Start": "2025-11-04", "Finish": "2025-11-10", 
     "Resource": "Business Analyst", "Complete": 80},
    {"Task": "Design Phase", "Start": "2025-11-08", "Finish": "2025-11-15", 
     "Resource": "Design Team", "Complete": 60},
    {"Task": "Development Sprint 1", "Start": "2025-11-12", "Finish": "2025-11-20", 
     "Resource": "Dev Team", "Complete": 40},
    {"Task": "Development Sprint 2", "Start": "2025-11-18", "Finish": "2025-11-28", 
     "Resource": "Dev Team", "Complete": 20},
    {"Task": "Testing", "Start": "2025-11-25", "Finish": "2025-12-05", 
     "Resource": "QA Team", "Complete": 0},
]

def create_gantt_figure(tasks):
    if not tasks:
        tasks = DEFAULT_TASKS
    
    df = pd.DataFrame(tasks)
    df['TaskDisplay'] = df.apply(lambda row: f"{row['Task']} ({row.get('Complete', 0)}%)", axis=1)
    
    fig = ff.create_gantt(
        df, colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DFE6E9'],
        index_col='Resource', show_colorbar=True, group_tasks=True,
        title='📊 Project Gantt Chart'
    )
    
    fig.update_layout(xaxis_title="Timeline", height=500, hovermode='closest')
    return fig

app.layout = html.Div([
    html.Div([
        html.H1("📊 Interactive Gantt Chart", style={'display': 'inline-block', 'marginRight': '20px'}),
        html.Span("🟢 Connected to Cloud Database", style={'color': 'green', 'fontWeight': 'bold'})
    ], style={'backgroundColor': '#f5f5f5', 'padding': '20px', 'marginBottom': '20px'}),
    
    dcc.Store(id='gantt-store', storage_type='local'),
    dcc.Interval(id='auto-save-interval', interval=5000, n_intervals=0),
    
    html.Div([
        html.Button('💾 Save Now', id='manual-save-btn', n_clicks=0,
                   style={'padding': '10px 20px', 'marginRight': '10px', 
                          'backgroundColor': '#4CAF50', 'color': 'white', 
                          'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer'}),
        html.Button('🔄 Reload', id='reload-btn', n_clicks=0,
                   style={'padding': '10px 20px', 'marginRight': '10px',
                          'backgroundColor': '#2196F3', 'color': 'white', 
                          'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer'}),
        html.Span(id='save-status', style={'marginLeft': '20px', 'fontSize': '14px'})
    ], style={'marginBottom': '20px'}),
    
    dcc.Graph(id='gantt-chart', style={'marginBottom': '30px'}),
    
    html.Div([
        html.H3("➕ Add New Task"),
        html.Div([
            html.Div([
                html.Label("Task Name:"),
                dcc.Input(id='task-name', type='text', placeholder='Task name',
                         style={'width': '100%', 'padding': '8px', 'marginBottom': '10px'})
            ], style={'width': '48%', 'display': 'inline-block', 'marginRight': '4%'}),
            html.Div([
                html.Label("Resource:"),
                dcc.Input(id='resource', type='text', placeholder='Team/person',
                         style={'width': '100%', 'padding': '8px', 'marginBottom': '10px'})
            ], style={'width': '48%', 'display': 'inline-block'}),
        ]),
        html.Div([
            html.Div([
                html.Label("Start Date:"),
                dcc.Input(id='start-date', type='text', placeholder='YYYY-MM-DD',
                         style={'width': '100%', 'padding': '8px', 'marginBottom': '10px'})
            ], style={'width': '31%', 'display': 'inline-block', 'marginRight': '3%'}),
            html.Div([
                html.Label("End Date:"),
                dcc.Input(id='end-date', type='text', placeholder='YYYY-MM-DD',
                         style={'width': '100%', 'padding': '8px', 'marginBottom': '10px'})
            ], style={'width': '31%', 'display': 'inline-block', 'marginRight': '3%'}),
            html.Div([
                html.Label("Complete %:"),
                dcc.Input(id='complete-pct', type='number', value=0, min=0, max=100,
                         style={'width': '100%', 'padding': '8px', 'marginBottom': '10px'})
            ], style={'width': '31%', 'display': 'inline-block'}),
        ]),
        html.Button('➕ Add Task', id='add-task-btn', n_clicks=0,
                   style={'padding': '10px 30px', 'backgroundColor': '#9C27B0', 
                          'color': 'white', 'border': 'none', 'borderRadius': '4px', 
                          'cursor': 'pointer', 'fontSize': '16px'}),
    ], style={'backgroundColor': '#f9f9f9', 'padding': '20px', 'borderRadius': '8px'})
])

@app.callback(
    [Output('gantt-chart', 'figure'),
     Output('gantt-store', 'data'),
     Output('save-status', 'children'),
     Output('task-name', 'value'),
     Output('start-date', 'value'),
     Output('end-date', 'value'),
     Output('resource', 'value'),
     Output('complete-pct', 'value')],
    [Input('add-task-btn', 'n_clicks'),
     Input('manual-save-btn', 'n_clicks'),
     Input('reload-btn', 'n_clicks'),
     Input('auto-save-interval', 'n_intervals')],
    [State('task-name', 'value'),
     State('start-date', 'value'),
     State('end-date', 'value'),
     State('resource', 'value'),
     State('complete-pct', 'value'),
     State('gantt-store', 'data')]
)
def update_gantt(add_clicks, save_clicks, reload_clicks, intervals,
                 task_name, start_date, end_date, resource, complete_pct, stored_data):
    
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    if stored_data is None or triggered_id == 'reload-btn':
        loaded = load_state_from_db(USER_ID, PROJECT_ID)
        tasks = loaded if loaded else DEFAULT_TASKS.copy()
        stored_data = tasks
    else:
        tasks = stored_data if stored_data else DEFAULT_TASKS.copy()
    
    status_msg = ""
    clear_inputs = False
    
    if triggered_id == 'add-task-btn' and task_name and start_date and end_date:
        new_task = {
            "Task": task_name, "Start": start_date, "Finish": end_date,
            "Resource": resource or "Unassigned", "Complete": complete_pct or 0
        }
        tasks.append(new_task)
        status_msg = f"✅ Added: '{task_name}'"
        save_state_to_db(USER_ID, PROJECT_ID, tasks)
        clear_inputs = True
    elif triggered_id == 'manual-save-btn':
        save_state_to_db(USER_ID, PROJECT_ID, tasks)
        status_msg = f"✅ Saved at {datetime.now().strftime('%H:%M:%S')}"
    elif triggered_id == 'reload-btn':
        loaded = load_state_from_db(USER_ID, PROJECT_ID)
        tasks = loaded if loaded else tasks
        status_msg = "✅ Reloaded from database"
    elif triggered_id == 'auto-save-interval' and tasks:
        save_state_to_db(USER_ID, PROJECT_ID, tasks)
        status_msg = f"🔄 Auto-saved at {datetime.now().strftime('%H:%M:%S')}"
    
    fig = create_gantt_figure(tasks)
    
    if clear_inputs:
        return fig, tasks, status_msg, "", "", "", "", 0
    else:
        return fig, tasks, status_msg, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(host='0.0.0.0', port=port, debug=False)