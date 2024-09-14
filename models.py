# models.py

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, SecretStr
import pandas as pd

class UploadData:
    def __init__(self, file_path: str, file_type: str):
        self.file_path = file_path
        self.file_type = file_type.lower()
        self.data = None

    def load_file(self):
        if self.file_type == 'csv':
            self.data = pd.read_csv(self.file_path)
        elif self.file_type == 'excel':
            self.data = pd.read_excel(self.file_path)
        elif self.file_type == 'json':
            self.data = pd.read_json(self.file_path)
        elif self.file_type == 'parquet':
            self.data = pd.read_parquet(self.file_path)
        else:
            raise ValueError(f"Unsupported file type: {self.file_type}")

    def get_data(self):
        if self.data is None:
            raise ValueError("No data has been loaded. Please load a file first.")
        return self.data


# Define the supported database types
class DatabaseType(str, Enum):
    DUCKDB = "DuckDB"
    POSTGRES = "Postgres"
    MYSQL = "MySQL"
    SQLITE = "SQLite"
    MONGODB = "MongoDB"
    # Add more databases as needed


# Base model for database connection settings
class DatabaseConnection(BaseModel):
    name: str = Field(..., description="Friendly name for the database")
    db_type: DatabaseType = Field(..., description="Type of the database")
    host: Optional[str] = Field(None, description="Hostname or IP address")
    port: Optional[int] = Field(None, description="Port number")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[SecretStr] = Field(None, description="Password")
    database: Optional[str] = Field(None, description="Database name")

    class Config:
        schema_extra = {
            "example": {
                "name": "Primary Database",
                "db_type": "Postgres",
                "host": "localhost",
                "port": 5432,
                "username": "user",
                "password": "password",
                "database": "sample_db",
            }
        }


# Model for database performance metrics
class DatabasePerformance(BaseModel):
    db_name: str
    avg_query_time: float = Field(..., description="Average query execution time in seconds")
    total_queries: int = Field(..., description="Total number of queries run")
    total_time: float = Field(..., description="Total time taken for all queries in seconds")
    data_insertion_time: float = Field(..., description="Time taken for data insertion")

    class Config:
        schema_extra = {
            "example": {
                "db_name": "Postgres",
                "avg_query_time": 0.075,
                "total_queries": 10,
                "total_time": 0.85,
                "data_insertion_time": 0.2,
            }
        }
