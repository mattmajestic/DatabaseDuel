from pathlib import Path
import time
import pandas as pd
import plotly.express as px
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import output_widget, render_plotly
from models import DatabaseConnection, DatabasePerformance, DatabaseType, UploadData

app_dir = Path(__file__).parent

# In-memory storage for databases and performance data
database_connections = [
    DatabaseConnection(name="DuckDB", db_type=DatabaseType.DUCKDB),
    DatabaseConnection(name="Postgres", db_type=DatabaseType.POSTGRES, host="localhost", port=5432)
]

# In-memory storage for performance results
database_performance_data = []

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.input_selectize(
            "databases",
            "Select Databases to Duel",
            choices=[db.name for db in database_connections],
            multiple=True,
            selected=["DuckDB", "Postgres"],
        ),
        ui.input_text("new_db", "Add New Database Type"),
        ui.input_action_button("add_db", "Add Database"),
        ui.input_file("csv_file", "Upload CSV File", multiple=False, accept=[".csv"]),
        ui.input_dark_mode(mode="dark"),
    ),
    ui.layout_column_wrap(
        ui.value_box(
            "Average Execution Time",
            ui.output_ui("avg_exec_time"),
            showcase=ui.tags.i(class_="fa fa-calendar fa-2x"),
        ),
        ui.value_box(
            "Total Queries Run",
            ui.output_ui("total_queries"),
            showcase=ui.tags.i(class_="fa fa-database fa-2x"),
        ),
        ui.value_box(
            "Performance Difference",
            ui.output_ui("perf_difference"),
            showcase=ui.tags.i(class_="fa fa-percent fa-2x"),
        ),
        fill=False,
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Current Database Duels ⚔️"),
            output_widget("db_comparison_plot"),
            full_screen=True,
        ),
        ui.card(
            ui.card_header("Database Connections"),
            ui.output_data_frame("db_connections_table"),
        ),
        col_widths=[7, 5],
    ),
    ui.include_css(app_dir / "styles.css"),
    title=ui.output_text("app_title"),
    fillable=True,
)

def server(input: Inputs, output: Outputs, session: Session):
    # Reactive value to store the list of databases
    databases = reactive.Value([db.name for db in database_connections])

    # Handle adding a new database
    @reactive.Effect
    @reactive.event(input.add_db)
    def _():
        new_db = input.new_db().strip()
        if new_db:
            if new_db not in databases():
                new_db_conn = DatabaseConnection(name=new_db, db_type=DatabaseType.DUCKDB)  # Default to DuckDB
                database_connections.append(new_db_conn)
                databases().append(new_db)
                databases().sort()
                # Update the choices in the selectize input
                ui.update_selectize("databases", choices=databases(), selected=input.databases())
            else:
                ui.notification_show(f"Database '{new_db}' is already in the list.", type="warning")
        else:
            ui.notification_show("Please enter a valid database name.", type="warning")

    # Reactive value to store the uploaded DataFrame
    uploaded_df = reactive.Value(pd.DataFrame())

    @reactive.Effect
    @reactive.event(input.csv_file)
    def _():
        file_info = input.csv_file()
        
        if file_info is not None:
            file_path = file_info["datapath"][0]
            file_name = file_info["name"][0]
            file_extension = file_name.split(".")[-1].lower()  # Get the file extension

            try:
                # Instantiate the UploadData class with the file path and type
                uploader = UploadData(file_path=file_path, file_type=file_extension)
                uploader.load_file()
                df = uploader.get_data()

                # Set the uploaded DataFrame
                uploaded_df.set(df)
                ui.notification_show(f"{file_extension.upper()} file uploaded successfully.", type="message")

                # Optionally print the first few rows of the data to console (for debugging)
                print(df.head())  # This prints the first 5 rows of the DataFrame
            except Exception as e:
                ui.notification_show(f"Error reading {file_extension.upper()} file: {e}", type="error")
        else:
            uploaded_df.set(pd.DataFrame())

    # Function to run queries and measure execution time
    def run_queries_on_db(db_connection: DatabaseConnection, df):
        query_times = []
        queries = [
            "SELECT COUNT(*) FROM sample_table;",
            "SELECT * FROM sample_table LIMIT 1000;",
        ]

        if df.empty:
            df = pd.DataFrame({"A": range(10000), "B": range(10000)})

        start_total = time.time()

        start_insert = time.time()
        time.sleep(0.1 if db_connection.db_type == DatabaseType.DUCKDB else 0.2)  # Simulated insertion time
        end_insert = time.time()

        for query in queries:
            start_time = time.time()
            time.sleep(0.05 if db_connection.db_type == DatabaseType.DUCKDB else 0.1)  # Simulated query time
            end_time = time.time()
            query_times.append(end_time - start_time)

        end_total = time.time()
        avg_query_time = sum(query_times) / len(query_times)
        total_queries = len(queries)
        total_time = end_total - start_total

        return DatabasePerformance(
            db_name=db_connection.name,
            avg_query_time=avg_query_time,
            total_queries=total_queries,
            total_time=total_time,
            data_insertion_time=end_insert - start_insert,
        )

    @reactive.Calc
    def get_database_performance():
        selected_dbs = input.databases()
        df = uploaded_df()
        performance_data = []
        for db_name in selected_dbs:
            db_connection = next((db for db in database_connections if db.name == db_name), None)
            if db_connection:
                performance_metrics = run_queries_on_db(db_connection, df)
                performance_data.append(performance_metrics.dict())
        return performance_data

    @output
    @render.text
    def app_title():
        dbs = input.databases()
        return "DatabaseDuel ⚔️ - Comparing: " + ", ".join(dbs)

    @output
    @render.ui
    def avg_exec_time():
        data = get_database_performance()
        avg_times = [d["avg_query_time"] for d in data]
        overall_avg = sum(avg_times) / len(avg_times) if avg_times else 0
        return f"{overall_avg:.3f} seconds"

    @output
    @render.ui
    def total_queries():
        data = get_database_performance()
        total_queries = sum(d["total_queries"] for d in data)
        return str(total_queries)

    @output
    @render.ui
    def perf_difference():
        data = get_database_performance()
        if len(data) >= 2:
            times = [d["total_time"] for d in data]
            max_time = max(times)
            min_time = min(times)
            difference = ((max_time - min_time) / min_time) * 100 if min_time != 0 else 0
            return f"{difference:.2f}%"
        else:
            return "N/A"

    @output
    @render_plotly
    def db_comparison_plot():
        data = get_database_performance()
        if not data:
            return px.bar(title="No Data to Display")
        df = pd.DataFrame(data)
        fig = px.bar(
            df,
            x="db_name",
            y=["avg_query_time", "data_insertion_time"],
            title="Database Performance Metrics",
            barmode="group",
        )
        fig.update_layout(
            xaxis_title="Database",
            yaxis_title="Time (seconds)",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    @output
    @render.data_frame
    def db_connections_table():
        df = pd.DataFrame([conn.dict() for conn in database_connections])
        return render.DataTable(
            df,
            editable=True,  
        )


app = App(app_ui, server)
