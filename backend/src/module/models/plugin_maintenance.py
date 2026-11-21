from sqlmodel import Field, SQLModel


class PluginMaintenanceRecord(SQLModel, table=True):
    __tablename__ = "plugin_maintenance"

    id: str = Field(primary_key=True)
    owner: str = Field(index=True)
    name: str
    state: str = "running"
    step: str = ""
    payload: str = "{}"
    backup_path: str = ""
    error: str = ""
