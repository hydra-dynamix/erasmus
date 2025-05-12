from pathlib import Path
import sqlite3
from typing import Dict, List, Optional
from pydantic import BaseModel
from erasmus.utils.rich_console import get_console_logger
import os

class WarpRule(BaseModel):
    """Model for Warp AI rules."""
    document_type: str
    document_id: str
    rule: str

class WarpIntegration:
    """Manages integration with Warp's database and rule system."""
    
    def __init__(self, db_path: Optional[Path] = None) -> None:
        """Initialize Warp integration with specified database path."""
        windows_app_data_path = Path("/mnt/c/Users")
        ignore_list = ["All Users", "Default User",  "Default", "Public"]
        if windows_app_data_path.exists():
            for file_path in windows_app_data_path.iterdir():
                if file_path.name in ignore_list:
                    continue
                target_path = file_path / "AppData" / "Local" / "Warp" / "Warp" / "data" / "warp.sqlite"
                if target_path.exists():
                    console_logger.info(f'Found Warp database at: {target_path}')
                    self.db_path = target_path
                    break
        else:
            self.db_path = Path.home() / ".warp" / "warp.sqlite"
        self._validate_db_path()

    def _validate_db_path(self) -> None:
        """Validate that the database path exists and is accessible."""
        if not self.db_path.exists():
            raise FileNotFoundError(f'Warp database not found at: {self.db_path}')
        
    def connect(self) -> sqlite3.Connection:
        """Create a connection to the Warp database."""
        try:
            # Use URI mode to handle special characters in path
            conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True)
            return conn
        except sqlite3.Error as error:
            console_logger.error(f'Failed to connect to Warp database: {error}')
            raise

    def get_rules(self) -> List[WarpRule]:
        """Retrieve AI rules from Warp's database."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT document_type, document_id, rule FROM ai_rules')
                rules = [
                    WarpRule(
                        document_type=row[0],
                        document_id=row[1],
                        rule=row[2]
                    )
                    for row in cursor.fetchall()
                ]
                return rules
        except sqlite3.OperationalError as error:
            if 'disk I/O error' in str(e):
                console_logger.error('Disk I/O error: Unable to read from Warp database. Please check if the database is accessible and not in use by another process.')
                return []
            console_logger.error(f'Failed to retrieve rules: {error}')
            return []
        except sqlite3.Error as error:
            console_logger.error(f'Failed to retrieve rules: {error}')
            return []

    def update_rule(self, rule: WarpRule) -> bool:
        """Update or insert a rule in Warp's database. Returns True on success, False on failure."""
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO ai_rules (document_type, document_id, rule) VALUES (?, ?, ?)',
                    (rule.document_type, rule.document_id, rule.rule)
                )
                conn.commit()
            return True
        except sqlite3.OperationalError as error:
            if 'disk I/O error' in str(e):
                console_logger.error('Disk I/O error: Unable to write to Warp database. Please check if the database is accessible and not in use by another process.')
                return False
            console_logger.error(f'Failed to update rule: {error}')
            return False
        except sqlite3.Error as error:
            console_logger.error(f'Failed to update rule: {error}')
            return False

def main() -> None:
    """Main function for testing Warp integration."""
    try:
        warp = WarpIntegration()
        rules = warp.get_rules()
        console_logger.info(f'Found {len(rules)} rules in Warp database')
        for rule in rules:
            console_logger.info(f'Rule: {rule.model_dump_json(indent=2)}')
    except Exception as error:
        console_logger.error(f'Error: {error}')
        raise

if __name__ == '__main__':
    main()
